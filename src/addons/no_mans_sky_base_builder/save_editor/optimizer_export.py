"""Verified, backed-up write of an optimized Corvette to its selected save slot."""
import copy
import os
from pathlib import Path
import tempfile
import time

from .save_editor_utils import BaseType
from .save_translation import SaveTranslation as K, translate_to_obf_data
from . import backup_policy


def replace_file(source, target):
    # Antivirus/sync clients can briefly hold a newly written Windows file.
    for delay in (.05, .15, .35):
        try:
            source.replace(target)
            return
        except PermissionError:
            time.sleep(delay)
    source.replace(target)


def export(objects, identifier, links, base_name=None, progress=None):
    from .save_file import SaveFile
    if identifier.base_type != BaseType.CORVETTE:
        raise ValueError('Optimize & Export is only available for Corvettes')
    paths = list(dict.fromkeys(Path(p).resolve() for p in links if p))
    if not paths:
        raise ValueError('No save files selected')
    if progress:
        progress.update(.18, 'Preparing save files')
    prepared = []
    staged = []
    replaced = []
    try:
        # Resolve every destination before touching any save file.
        for index, path in enumerate(paths):
            if progress:
                progress.update(.20 + .34 * index / len(paths), f'Loading {path.name}')
            original = path.read_bytes()
            save = SaveFile(path)
            save.load()
            base = save.search_base_with_identifier(identifier)
            if base is not None:
                from . import ship_repair, ship_core
                ship_repair.require_objects_destination(save.json_data,
                    save.context or ship_core.get(save.json_data, 'ActiveContext'), base)
            if base is None:
                raise ValueError(f'Corvette not found in {path.name}; reselect or repin it')
            base[K.objects] = translate_to_obf_data(copy.deepcopy(objects))
            if base_name:
                ownership = save.get_ship_ownsership_element(int(identifier.user_data))
                if ownership is None:
                    raise ValueError(f'Corvette ownership not found in {path.name}')
                base[K.base_name] = base_name
                ownership[K.base_name] = base_name
            fd, filename = tempfile.mkstemp(prefix='.bbe-optimizer-', suffix='.tmp', dir=path.parent)
            os.close(fd)
            temp = Path(filename)
            staged.append(temp)
            save.save(output_path=temp)
            if progress:
                progress.update(.20 + .34 * (index + .7) / len(paths),
                                f'Verifying {path.name}')
            check = SaveFile(temp)
            if check.load() != save.json_data:
                raise ValueError(f'Save verification failed for {path.name}')
            prepared.append((path, original, temp))
        if progress:
            progress.update(.56, 'Backing up original saves')
        generation, backups = backup_policy.snapshot(paths, 'optimizer')
        if progress:
            progress.update(.73, 'Checking original saves')
        for path, original, temp in prepared:
            if path.read_bytes() != original:
                raise ValueError(f'{path.name} changed during export; try again')
        for index, (path, original, temp) in enumerate(prepared):
            if progress:
                progress.update(.80 + .14 * index / len(prepared),
                                f'Writing {path.name}')
            replace_file(temp, path)
            replaced.append((path, original))
        backup_policy.finish(generation)
        if progress:
            progress.update(.96, 'Save files verified')
        return backups
    except Exception:
        # If a later replacement fails, restore any files already replaced.
        for path, original in reversed(replaced):
            fd, filename = tempfile.mkstemp(prefix='.bbe-restore-', dir=path.parent)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(original)
            replace_file(Path(filename), path)
        raise
    finally:
        for temp in staged:
            if temp.exists():
                temp.unlink()
