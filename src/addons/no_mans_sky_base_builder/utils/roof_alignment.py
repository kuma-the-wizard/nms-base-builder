"""Remove the placement-locator translation baked into legacy HD roof ends.

The native BASIC_ROOF_END_CAP / BASIC_ROOF_END_QUARTER LOD0 meshes are
already in the part's placement coordinates. The HD library also applied
PlacementData's local Z=1.333333, shifting the preview along the gable.
Only recognised library coordinates are migrated; object transforms and
export records are not changed. See tests/blender/test_roof_alignment.py.
"""
import hashlib
import numpy as np

REVISION = 'bbe_roof_alignment_revision'
OFFSET_Z = 1.3333330154418945
# Vertex/face counts and rounded coordinate fingerprints of the shipped pack.
LEGACY = {
    'T_ROOF_E_CAP': (1460, 1204, 'b69737a83963604aa269336f69dde718eb567a815de37d9c32f1ef533aa9c961'),
    'T_ROOF_E_Q': (894, 712, '1042bc53348910da96f16dafd2b6bd5126a761099c051d6a103d1d64babae9f1'),
    'F_ROOF_E_CAP': (2680, 2680, 'da5dffd8497925d2a0e38e16a5f12b7d775add8d4d3c4f523b5ac88cbd994dc8'),
    'F_ROOF_E_Q': (1047, 786, 'f1cc60e4aaa708d760904be99dfaf98a9d8376c9e66c8c714d1f53ca4b157fac'),
    'S_ROOF_E_CAP': (106, 68, '518e6d1fd9c2e5fe5e976ad6b72b855af3f6d44e03f097d15081bc7861cc496b'),
    'S_ROOF_E_Q': (84, 52, '99edb703818046581dc55238794ef20b850c1aa1fda66c834252f025ac9102f8'),
    'B_ROOF_E_CAP': (2684, 2680, '1b8d36cf571a87d51f1c8a39b2093daa0b041017917f13ffb28125cbc0415233'),
    'B_ROOF_E_Q': (2450, 1662, '8a4d654fa6bab094769cea6362201934894d4ac47df759b7e152f0bf17ccffa3'),
}


def correct(mesh, part_id):
    """Migrate an unchanged library mesh once, including saved shared meshes."""
    expected = LEGACY.get(part_id)
    if (expected is None or mesh.get(REVISION) == 1 or mesh.library
            or mesh.shape_keys or mesh.is_editmode
            or (len(mesh.vertices), len(mesh.polygons)) != expected[:2]):
        return False
    points = np.empty((len(mesh.vertices), 3), dtype=np.float32)
    mesh.vertices.foreach_get('co', points.ravel())
    fingerprint = hashlib.sha256(
        np.rint(points.astype(np.float64) * 10000).astype('<i4').tobytes()
    ).hexdigest()
    if fingerprint != expected[2]:
        # Leave edited/custom geometry and already-corrected untagged meshes
        # alone. A matching ObjectID by itself is not enough to move vertices.
        return False
    normals = None
    if mesh.has_custom_normals:
        normals = np.empty((len(mesh.loops), 3), dtype=np.float32)
        mesh.corner_normals.foreach_get('vector', normals.ravel())
    points[:, 2] -= OFFSET_Z
    mesh.vertices.foreach_set('co', points.ravel())
    mesh[REVISION] = 1
    mesh.update()
    if normals is not None:
        mesh.normals_split_custom_set(normals.tolist())
    return True


def refresh_scene(scene):
    """Repair embedded detailed meshes even when the HD pack is unavailable."""
    from . import materials_v2
    seen = set()
    changed = 0
    for obj in scene.objects:
        pid = obj.get('ObjectID')
        if (obj.type == 'MESH' and pid in LEGACY and materials_v2.is_high_res(obj)
                and obj.data.as_pointer() not in seen):
            seen.add(obj.data.as_pointer())
            changed += correct(obj.data, pid)
    return changed
