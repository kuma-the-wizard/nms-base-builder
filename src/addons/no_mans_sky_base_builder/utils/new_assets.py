"""Per-user discovery markers for newly released parts, never stored in a build."""
import json
from pathlib import Path

_catalog = None
_seen = None


def _new_ids():
    global _catalog
    if _catalog is None:
        path = Path(__file__).resolve().parents[1] / 'resources/forsaken_assets.json'
        _catalog = {row['id'] for row in json.loads(path.read_text(encoding='utf-8'))['assets']}
    return _catalog


def _path():
    from .asset_browser_utils import get_user_data_directory
    return Path(get_user_data_directory()) / 'asset_browser' / 'viewed_new_parts.json'


def _viewed():
    global _seen
    if _seen is None:
        try:
            data = json.loads(_path().read_text(encoding='utf-8'))
            _seen = {entry for entry in data if isinstance(entry, str)} if isinstance(data, list) else set()
        except (OSError, ValueError):
            _seen = set()
    return _seen


def is_new(object_id):
    object_id = object_id.lstrip('^')
    return object_id in _new_ids() and object_id not in _viewed()


def mark_viewed(object_id):
    object_id = object_id.lstrip('^')
    if not is_new(object_id):
        return False
    _viewed().add(object_id)
    try:
        path = _path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(sorted(_viewed())), encoding='utf-8')
        temporary.replace(path)
    except OSError as exc:
        # A read-only profile must not stop placement; keep session state.
        print(f'BBE: Could not remember viewed part: {exc}')
    return True
