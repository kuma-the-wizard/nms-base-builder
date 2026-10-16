"""Resolve fossil display variants without changing their game records."""
from pathlib import Path

BASE_IDS = frozenset({'FOS_HEAD', 'FOS_SKULL', 'FOS_BODY', 'FOS_TAIL', 'FOS_LIMBS'})
MODEL_IDS = frozenset(path.stem for path in
                      (Path(__file__).resolve().parents[1] / 'models' / 'fossil_parts').glob('*.fbx'))


def family_id(model_id):
    family = model_id.rsplit('_', 1)[0]
    return {'FOS_HEAD': 'FOS_SKULL', 'FOS_BI_BODY': 'FOS_BODY',
            'FOS_BI_TAIL': 'FOS_TAIL'}.get(family, family)


def resolve_model_id(record):
    """A fossil's ObjectID is its family; Message identifies its geometry."""
    part_id = str(record.get('ObjectID', '')).lstrip('^')
    if part_id not in BASE_IDS:
        return part_id
    variant = str(record.get('Message', '')).strip().lstrip('^')
    family = 'FOS_SKULL' if part_id == 'FOS_HEAD' else part_id
    if variant in MODEL_IDS and family_id(variant) == family:
        return variant
    return part_id


def refresh_scene(scene):
    """Repair old generic fossil meshes on file load, preserving object data.

    Missing variants remain untouched. This runs once on load; there is no
    fossil polling or dependency-graph work while the user edits the scene.
    """
    import bpy
    from .. import builder_v2
    from ..utils import materials_v2
    from ..tools_menu.base_builder_menu_operators import _preserve_selection, _suspend_scene_updates

    repaired = missing = 0
    proxy_cache, to_colour = {}, []
    detailed = getattr(scene, 'bbe_detailed_proxies', True)
    with _suspend_scene_updates(), _preserve_selection(bpy.context), materials_v2.defer_shared_data():
        for obj in list(scene.objects):
            part_id = str(obj.get('ObjectID', '')).lstrip('^')
            if obj.type != 'MESH' or part_id not in BASE_IDS or 'GroupID' in obj:
                continue
            model_id = resolve_model_id(obj)
            if model_id == part_id:
                missing += 1
                continue
            stored_model = (obj.data.get(builder_v2.MESH_TAG)
                            or obj.data.get(builder_v2.PROXY_PLACEMENT_TAG, '').split('/')[0]
                            or obj.data.get(builder_v2.PROXY_MESH_TAG))
            if stored_model == model_id:
                continue
            # Do not replace an untagged, potentially hand-edited fossil.
            # Known wrong library tags and the tiny fallback cube are repairable.
            if not stored_model and (len(obj.data.vertices) > 24 or len(obj.data.polygons) > 12):
                continue
            user_data = obj.get('UserData', 0)
            if detailed:
                if obj.data.get(builder_v2.MESH_TAG) == model_id:
                    continue
                mesh = builder_v2.load_high_res_mesh(model_id)
                if mesh is not None:
                    obj.data = mesh
                    to_colour.append((obj, user_data))
                    repaired += 1
                    continue
            if obj.data.get(builder_v2.PROXY_PLACEMENT_TAG) == f'{model_id}/{user_data}':
                continue
            repaired += int(builder_v2.apply_proxy_mesh(obj, model_id, user_data, cache=proxy_cache))
        materials_v2.apply_many(to_colour)
    if repaired or missing:
        print(f'BBE fossils: restored {repaired}; {missing} missing a usable variant in {scene.name}')
    return repaired, missing
