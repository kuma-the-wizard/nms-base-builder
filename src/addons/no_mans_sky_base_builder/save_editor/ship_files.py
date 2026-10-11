"""Review snapshots and transactional Steam save operations."""
import hashlib
import json
import os
import tempfile
from pathlib import Path
from .save_file import SaveFile
from .optimizer_export import replace_file
from . import steam_metadata, backup_policy


def hashes(paths):
    return {str(Path(p)): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}


def read(links):
    paths = [Path(p) for p in links]
    latest = max(paths, key=lambda p: p.stat().st_mtime_ns)
    watched = paths + [p.with_name('mf_' + p.name) for p in paths if p.with_name('mf_' + p.name).exists()]
    return SaveFile(latest).load(), hashes(watched), latest


def slot_paths(folder, slot):
    if not 1 <= slot <= 15:
        raise ValueError('Choose a save slot from 1 to 15')
    return [Path(folder) / ('save.hg' if slot == 1 else f'save{slot*2-1}.hg'), Path(folder) / f'save{slot*2}.hg']


def empty_slots(folder):
    return [i for i in range(1,16) if not any(p.exists() or p.with_name('mf_'+p.name).exists() for p in slot_paths(folder,i))]


def commit(root, paths, expected, source=None, name=None, create=False):
    """All files staged/verified first. No replace of occupied duplicate targets."""
    prepared, temps, replaced, backups = [], [], [], []
    generation = None
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
        prepared.append((path, temp, None if create else path.read_bytes()))
    try:
        if hashes(expected) != expected:
            raise ValueError('Save changed since the review opened. Reopen Ship Management.')
        for path in paths:
            if create and (path.exists() or path.with_name('mf_'+path.name).exists()):
                raise ValueError('Destination save slot is occupied')
            fd, filename = tempfile.mkstemp(prefix='.bbe-encode-', dir=path.parent)
            os.close(fd)
            temp = Path(filename)
            temps.append(temp)
            save = SaveFile(temp)
            save.json_data = root
            save.save()
            if SaveFile(temp).load() != root:
                raise ValueError('Compressed save round-trip failed')
            encoded = temp.read_bytes()
            stage(path, encoded)
            meta_source = Path(source) if create else path
            meta = meta_source.with_name('mf_'+meta_source.name)
            if create and not meta.exists():
                raise ValueError('Steam metadata is required to create a new save slot')
            if meta.exists():
                decoded_size = len(json.dumps(root,separators=(',',':'),ensure_ascii=False).encode('utf8'))+1
                rebuilt = steam_metadata.rebuild(meta.read_bytes(), meta_source.name, path.name, len(encoded), decoded_size, name)
                stage(path.with_name('mf_'+path.name), rebuilt)
        if not create:
            generation, backups = backup_policy.snapshot(paths, 'ship-management')
        if hashes(expected) != expected:
            raise ValueError('Save changed during preparation; nothing was written')
        for path, temp, original in prepared:
            if create:
                # Hard-link publication is atomic and fails if another process creates the target.
                os.link(temp, path)
            else:
                replace_file(temp, path)
            replaced.append((path, original))
        if generation is not None:
            backup_policy.finish(generation)
        return backups
    except Exception:
        for path, original in reversed(replaced):
            if original is None:
                path.unlink()
            else:
                fd, filename = tempfile.mkstemp(prefix='.bbe-rollback-',dir=path.parent)
                with os.fdopen(fd,'wb') as stream:
                    stream.write(original)
                replace_file(Path(filename),path)
        raise
    finally:
        for temp in temps:
            if temp.exists():
                temp.unlink()
