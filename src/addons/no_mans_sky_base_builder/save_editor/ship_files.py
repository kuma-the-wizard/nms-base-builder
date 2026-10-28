"""Review snapshots and transactional Steam save operations."""
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from .. import progress_ui
from .save_file import SaveFile
from .optimizer_export import replace_file
from . import steam_metadata, backup_policy


def hashes(paths):
    return {str(Path(p)): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}


def export_hashes(paths):
    """Watch the data and companion metadata before reading either save point."""
    paths = [Path(p).resolve() for p in paths]
    return hashes(paths + [p.with_name('mf_' + p.name) for p in paths
                           if p.with_name('mf_' + p.name).exists()])


def commit_roots(roots, expected, progress=None):
    """Export each save point's own edited root, preserving its other progress."""
    roots = {Path(p).resolve(): root for p, root in roots.items()}
    if not roots:
        raise ValueError('No save files selected')
    if progress is not None:
        return _commit(None, roots, expected, None, None, False, progress, roots)
    with progress_ui.Activity('Exporting build to save') as progress:
        return _commit(None, roots, expected, None, None, False, progress, roots)


def read(links):
    with progress_ui.Activity('Loading Ship Management') as progress:
        paths = [Path(p) for p in links]
        latest = max(paths, key=lambda p: (p.stat().st_mtime_ns, str(p)))
        progress.update(.08, f'Loading {latest.name}')
        save = SaveFile(latest)
        root = save.load()
        progress.update(.72, 'Checking save files')
        watched = paths + [p.with_name('mf_' + p.name) for p in paths
                           if p.with_name('mf_' + p.name).exists()]
        current_hashes = hashes(watched)
        if current_hashes[str(latest)] != save.source_hash:
            raise ValueError('Save changed while reading. Refresh the save list and try again.')
        progress.update(1.0, 'Ship Management ready')
        return root, current_hashes, latest


def slot_paths(folder, slot):
    if not 1 <= slot <= 15:
        raise ValueError('Choose a save slot from 1 to 15')
    return [Path(folder) / ('save.hg' if slot == 1 else f'save{slot*2-1}.hg'), Path(folder) / f'save{slot*2}.hg']


def empty_slots(folder):
    return [i for i in range(1,16) if not any(p.exists() or p.with_name('mf_'+p.name).exists() for p in slot_paths(folder,i))]


def commit(root, paths, expected, source=None, name=None, create=False, progress=None):
    """All files staged/verified first. No replace of occupied duplicate targets."""
    if progress is not None:
        return _commit(root, paths, expected, source, name, create, progress)
    title = 'Creating new save slot' if create else 'Saving Ship Management changes'
    with progress_ui.Activity(title) as progress:
        return _commit(root, paths, expected, source, name, create, progress)


def _commit(root, paths, expected, source, name, create, progress, roots=None):
    prepared, temps, replaced, backups = [], [], [], []
    generation = None
    # The Steam metadata timestamp is whole Unix seconds. Publish all data and
    # metadata files with that same timestamp, as used by established editors.
    write_time = int(time.time())
    paths = [Path(p).resolve() for p in paths]
    if len(set(paths)) != len(paths):
        raise ValueError('Repeated save destination')
    def stage(path, data):
        fd, filename = tempfile.mkstemp(prefix='.bbe-ship-', dir=path.parent)
        temp = Path(filename)
        temps.append(temp)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        if temp.read_bytes() != data:
            raise ValueError('Staged file verification failed')
        original = None if create else path.read_bytes()
        stat = None if create else path.stat()
        os.utime(temp, (write_time, write_time))
        prepared.append((path, temp, original, stat))
    try:
        progress.update(.05, 'Checking source saves')
        if hashes(expected) != expected:
            raise ValueError('Save changed since the review opened. Reopen Ship Management.')
        for index, path in enumerate(paths):
            current_root = roots[path] if roots is not None else root
            progress.update(.10 + .45 * index / max(1, len(paths)),
                            f'Encoding and verifying {path.name}')
            if create and (path.exists() or path.with_name('mf_'+path.name).exists()):
                raise ValueError('Destination save slot is occupied')
            fd, filename = tempfile.mkstemp(prefix='.bbe-encode-', dir=path.parent)
            os.close(fd)
            temp = Path(filename)
            temps.append(temp)
            save = SaveFile(temp)
            save.json_data = current_root
            save.save()
            if SaveFile(temp).load() != current_root:
                raise ValueError('Compressed save round-trip failed')
            encoded = temp.read_bytes()
            stage(path, encoded)
            meta_source = Path(source) if create else path
            meta = meta_source.with_name('mf_'+meta_source.name)
            if create and not meta.exists():
                raise ValueError('Steam metadata is required to create a new save slot')
            if meta.exists():
                decoded_size = len(json.dumps(current_root,separators=(',',':'),ensure_ascii=False).encode('utf8'))+1
                rebuilt = steam_metadata.rebuild(meta.read_bytes(), meta_source.name, path.name, len(encoded), decoded_size, name, timestamp=write_time)
                stage(path.with_name('mf_'+path.name), rebuilt)
        progress.update(.60, 'Backing up original saves' if not create else 'Checking new slot')
        if not create:
            generation, backups = backup_policy.snapshot(paths, 'ship-management')
        progress.update(.76, 'Checking source saves again')
        if hashes(expected) != expected:
            raise ValueError('Save changed during preparation; nothing was written')
        for index, (path, temp, original, stat) in enumerate(prepared):
            progress.update(.82 + .14 * index / max(1, len(prepared)),
                            f'Writing {path.name}')
            if create:
                # Hard-link publication is atomic and fails if another process creates the target.
                os.link(temp, path)
            else:
                replace_file(temp, path)
            replaced.append((path, original, stat))
        if generation is not None:
            backup_policy.finish(generation)
        progress.update(1.0, 'Save files verified')
        return backups
    except Exception:
        for path, original, stat in reversed(replaced):
            if original is None:
                path.unlink()
            else:
                fd, filename = tempfile.mkstemp(prefix='.bbe-rollback-',dir=path.parent)
                with os.fdopen(fd,'wb') as stream:
                    stream.write(original)
                temps.append(Path(filename))
                os.utime(filename, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                replace_file(Path(filename),path)
        raise
    finally:
        for temp in temps:
            if temp.exists():
                temp.unlink()
