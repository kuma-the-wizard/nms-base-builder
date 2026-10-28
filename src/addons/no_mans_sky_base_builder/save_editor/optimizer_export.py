"""Verified, backed-up write of an optimized Corvette to its selected save slot."""
import copy
from pathlib import Path
import time

from .save_editor_utils import BaseType
from .save_translation import SaveTranslation as K, translate_to_obf_data


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
    from . import ship_files
    if identifier.base_type != BaseType.CORVETTE:
        raise ValueError('Optimize & Export is only available for Corvettes')
    paths = list(dict.fromkeys(Path(p).resolve() for p in links if p))
    if not paths:
        raise ValueError('No save files selected')
    if progress:
        progress.update(.18, 'Preparing save files')
    expected = ship_files.export_hashes(paths)
    roots = {}
    # Resolve every destination before touching any save file. Keep each save
    # point's own unrelated progress rather than cloning the newest root.
    for index, path in enumerate(paths):
        if progress:
            progress.update(.20 + .34 * index / len(paths), f'Loading {path.name}')
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
        roots[path] = save.json_data
    return ship_files.commit_roots(roots, expected, progress=progress)
