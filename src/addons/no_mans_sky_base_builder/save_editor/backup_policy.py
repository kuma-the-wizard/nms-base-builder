"""One verified, bounded backup policy for all save-writing paths."""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


_SAVE_NAME = re.compile(r'(?:mf_)?save(\d*)\.hg$', re.IGNORECASE)
_SNAPSHOT_NAME = re.compile(r'\d{8}-\d{6}-\d{6}_[a-z-]+$')
_MARKER = '.bbe-backup.json'


def preferences():
    try:
        import bpy
        addon_id = __package__.rsplit('.', 1)[0]
        addon = bpy.context.preferences.addons.get(addon_id)
        return addon.preferences if addon else None
    except (ImportError, AttributeError, RuntimeError):
        return None


def settings():
    prefs = preferences()
    if prefs is None:
        return '', 20
    return prefs.nms_backup_folder_path.strip(), prefs.nms_backup_retention


def root_directory(backup_root=None):
    """Shared root for project recovery and NMS save backup subfolders."""
    configured = settings()[0] if backup_root is None else str(backup_root).strip()
    if configured:
        try:
            import bpy
            configured = bpy.path.abspath(configured)
        except ImportError:
            pass
        return Path(configured).expanduser().resolve()
    return (Path.home() / 'NoMansSkyBaseBuilder' / 'Backups').resolve()


def _slot(path):
    match = _SAVE_NAME.fullmatch(path.name)
    if match is None:
        raise ValueError(f'Not an NMS save file: {path.name}')
    number = int(match.group(1) or '1')
    return (number + 1) // 2


def directory(paths, backup_root=None):
    """Account-scoped, slot-scoped directory even when users share one root."""
    paths = [Path(path).resolve() for path in paths]
    if not paths or len({p.parent for p in paths}) != 1:
        raise ValueError('Backup inputs must belong to one save folder')
    slots = {_slot(path) for path in paths}
    if len(slots) != 1:
        raise ValueError('Backup inputs must belong to one save slot')
    root = root_directory(backup_root) / 'Game Saves'
    account = paths[0].parent
    identity = hashlib.sha256(str(account).casefold().encode('utf8')).hexdigest()[:10]
    return root / f'{account.name}-{identity}' / f'slot-{slots.pop():02}'


def _sources(paths):
    sources = list(dict.fromkeys(Path(path).resolve() for path in paths))
    if not sources or any(not p.is_file() for p in sources):
        raise ValueError('A selected save file is missing; no backup was made')
    for path in tuple(sources):
        if path.name.startswith('mf_'):
            continue
        metadata = path.with_name('mf_' + path.name)
        if metadata.is_file() and metadata not in sources:
            sources.append(metadata)
    directory(sources)  # Validate account and slot before creating directories.
    return sources


def snapshot(paths, reason, backup_root=None):
    """Create and verify a complete generation before a caller changes a save."""
    if not re.fullmatch(r'[a-z-]+', reason):
        raise ValueError('Invalid backup reason')
    sources = _sources(paths)
    parent = directory(sources, backup_root)
    parent.mkdir(parents=True, exist_ok=True)
    generation = parent / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '_' + reason)
    generation.mkdir()
    files = {}
    try:
        for source in sources:
            data = source.read_bytes()
            backup = generation / source.name
            with backup.open('xb') as stream:
                stream.write(data)
            digest = hashlib.sha256(data).hexdigest()
            if hashlib.sha256(backup.read_bytes()).hexdigest() != digest:
                raise OSError(f'Backup verification failed for {source.name}')
            files[source.name] = dict(source=str(source), sha256=digest)
        marker = dict(schema=1, files=files, reason=reason)
        (generation / _MARKER).write_text(json.dumps(marker, indent=2), encoding='utf8')
        return generation, [str(generation / name) for name in files]
    except Exception:
        for child in generation.iterdir():
            if child.is_file() and not child.is_symlink():
                child.unlink()
        generation.rmdir()
        raise


def _managed(generation):
    if not generation.is_dir() or generation.is_symlink() or not _SNAPSHOT_NAME.fullmatch(generation.name):
        return None
    marker = generation / _MARKER
    if not marker.is_file() or marker.is_symlink():
        return None
    try:
        record = json.loads(marker.read_text(encoding='utf8'))
        names = set(record['files'])
        if record.get('schema') != 1 or not names or any(Path(name).name != name for name in names):
            return None
        if {child.name for child in generation.iterdir()} != names | {_MARKER}:
            return None
        if any(not (generation / name).is_file() or (generation / name).is_symlink() for name in names):
            return None
        return names
    except (OSError, ValueError, KeyError, TypeError):
        return None


def prune(generation, retention=None):
    """Remove only older BBE-marked generations in the same account/slot."""
    generation = Path(generation).resolve()
    keep = settings()[1] if retention is None else retention
    if not 1 <= keep <= 500:
        raise ValueError('Backup retention must be between 1 and 500')
    parent = generation.parent
    managed = sorted((child for child in parent.iterdir() if _managed(child)), key=lambda p: p.name)
    for old in managed[:-keep]:
        if old == generation or not old.resolve().is_relative_to(parent.resolve()):
            continue
        names = _managed(old)
        if names is None:
            continue
        for name in names:
            (old / name).unlink()
        (old / _MARKER).unlink()
        old.rmdir()


def finish(generation):
    try:
        prune(generation)
    except OSError as exc:
        print(f'BBE: save backup retained; old backup cleanup failed: {exc}')
