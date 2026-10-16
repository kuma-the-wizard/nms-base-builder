"""Standalone build-file interchange. No save-game files are changed here."""

import copy
import io
import json
import os
from pathlib import Path
import tempfile
import zipfile

MAX_FILE = 64 * 1024 * 1024
MAX_ENTRY = 32 * 1024 * 1024
MAX_ENTRIES = 256
BASE_TYPES = {
    'PlayerShipBase', 'HomePlanetBase', 'FreighterBase',
    'ExternalPlanetBase', 'PlayerSpaceBase', 'PlayerSpaceStationBase',
}


def _decode(raw, label):
    try:
        return json.loads(raw.decode('utf-8-sig'), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (UnicodeError, ValueError) as exc:
        raise ValueError(f'{label} is not valid UTF-8 JSON') from exc


def _objects(document):
    if isinstance(document, list):
        objects = document
    elif isinstance(document, dict):
        objects = document.get('Objects', document.get('objects', document.get('Prefab')))
    else:
        objects = None
    if not isinstance(objects, list) or any(not isinstance(part, dict) for part in objects):
        raise ValueError('The file needs an Objects array of build parts')
    return objects


def _base_type(document):
    if not isinstance(document, dict):
        return None
    value = document.get('BaseType')
    if isinstance(value, dict):
        value = value.get('PersistentBaseTypes')
    return value if value in BASE_TYPES else None


def _safe_name(name):
    return (bool(name) and not name.startswith(('/', '\\')) and
            '\\' not in name and ':' not in name and '..' not in name.split('/'))


def _encode(document):
    return json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False).encode('utf-8')


class BuildFile:
    def __init__(self, document, kind, source_bytes, entries=None):
        self.document = document
        self.objects = _objects(document)
        self.kind = kind
        self.source_bytes = source_bytes
        self.entries = entries

    @classmethod
    def from_bytes(cls, raw, suffix):
        if len(raw) > MAX_FILE:
            raise ValueError('Build file exceeds the 64 MB limit')
        suffix = suffix.lower()
        if suffix == '.nmsship':
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    infos = archive.infolist()
                    if len(infos) > MAX_ENTRIES or sum(i.file_size for i in infos) > MAX_FILE:
                        raise ValueError('Ship package exceeds the entry or unpacked size limit')
                    names = set()
                    for item in infos:
                        if (not _safe_name(item.filename) or item.filename in names or
                                item.file_size > MAX_ENTRY or item.flag_bits & 1 or
                                item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                            raise ValueError('Ship package has an unsafe or unsupported entry')
                        names.add(item.filename)
                    entries = {item.filename: archive.read(item) for item in infos}
            except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
                raise ValueError('Unreadable .nmsship package or checksum failure') from exc
            if not {'objects.json', 'so.json'} <= entries.keys():
                raise ValueError('A complete .nmsship needs objects.json and so.json')
            ownership = _decode(entries['so.json'], 'so.json')
            if not isinstance(ownership, dict):
                raise ValueError('so.json must contain a ship record')
            if 'ccd.json' in entries and not isinstance(_decode(entries['ccd.json'], 'ccd.json'), dict):
                raise ValueError('ccd.json must contain an appearance record')
            objects = _decode(entries['objects.json'], 'objects.json')
            _objects(objects)
            document = {'BaseType': {'PersistentBaseTypes': 'PlayerShipBase'},
                        'Name': str(ownership.get('Name') or 'Corvette'),
                        'Objects': _objects(objects)}
            return cls(document, 'ship', raw, entries)
        if suffix not in ('.json', '.txt', '.nmsbase', '.nmsprefab'):
            raise ValueError('Supported build files: .nmsship, .nmsbase, .nmsprefab, .json, .txt')
        try:
            document = _decode(raw, suffix)
        except ValueError:
            # Some shared .nmsbase templates are the comma-prefixed part
            # fragment intended to be pasted after a base computer.
            if suffix != '.nmsbase' or not raw.lstrip().startswith(b','):
                raise
            document = _decode(b'[' + raw.lstrip()[1:].rstrip().rstrip(b',') + b']', suffix)
        _objects(document)
        kind = 'base' if _base_type(document) else 'parts'
        return cls(document, kind, raw)

    @classmethod
    def read(cls, path):
        path = Path(path)
        if path.stat().st_size > MAX_FILE:
            raise ValueError('Build file exceeds the 64 MB limit')
        return cls.from_bytes(path.read_bytes(), path.suffix)

    def with_scene(self, scene_data):
        """Retain fields BBE does not edit, then substitute current scene parts."""
        _objects(scene_data)
        if self.kind == 'ship':
            return dict(scene_data)
        if isinstance(self.document, dict):
            result = copy.deepcopy(self.document)
            result.update(scene_data)
            return result
        return dict(scene_data)

    def ship_bytes(self, objects, name=None):
        if self.kind != 'ship':
            raise ValueError('A full .nmsship export needs an imported ship package or a template')
        _objects(objects)
        entries = dict(self.entries)
        old_doc = _decode(entries['objects.json'], 'objects.json')
        if isinstance(old_doc, list):
            new_doc = objects
        else:
            new_doc = copy.deepcopy(old_doc)
            new_doc['Objects' if 'Objects' in new_doc else 'objects'] = objects
        if new_doc != old_doc:
            entries['objects.json'] = _encode(new_doc)
        if name and name.strip():
            ownership = _decode(entries['so.json'], 'so.json')
            if ownership.get('Name') != name.strip():
                ownership['Name'] = name.strip()
                entries['so.json'] = _encode(ownership)
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
        result = stream.getvalue()
        self.from_bytes(result, '.nmsship')
        return result


def atomic_write(path, data):
    path = Path(path)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.bbe-build-', delete=False) as handle:
            temp = Path(handle.name)
            handle.write(data)
        os.replace(temp, path)
    finally:
        if temp and temp.exists():
            temp.unlink()
