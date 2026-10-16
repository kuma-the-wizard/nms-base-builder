"""Restore native glass placement in the four large-room HD proxies.

The shipped square-room assembly applied the first three corner frames twice
to their glass. Round rooms omitted RoofGlassLOD0's local Y=-4 transform.
Transparent shaders concealed these errors; Workbench exposes them in Solid.
Only the recognised library geometry is migrated, including embedded caches.
"""
import hashlib
import numpy as np
from mathutils import Matrix

REVISION = 'bbe_room_glass_revision'
TOPOLOGY = {
    'MAINROOMCUBE': (71030, 67007),
    'MAINROOMCUBE_W': (70474, 66911),
    'MAINROOM': (84060, 80962),
    'MAINROOM_WATER': (86012, 84739),
}
PREFIX = 'MODELS/PLANETS/BIOMES/COMMON/BUILDINGS/PARTS/BUILDABLEPARTS/'
CORNER_MATERIAL = PREFIX + 'PANELCORNER_DEFAULT/GLASSREFRACTIONMAT.MATERIAL.MBIN'
ROOF_MATERIAL = PREFIX + 'ROOM_ROOF/GLASS_MAT.MATERIAL.MBIN'
CORNER_DIGEST = 'fb75f8dd814a20cd3b4fbbad2a0543ac4c57ebca3baab5605f32e0c6d5def5b3'
ROOF_DIGEST = '8c6269d773160ee8cb4d23e94f9c1aca50b9b73e6a7f3152040a3785e64a3e21'


def correct(mesh, part_id):
    """Correct known pane coordinates once, preserving all other mesh data."""
    if part_id not in TOPOLOGY or mesh.get(REVISION) == 1:
        return False
    if (len(mesh.vertices), len(mesh.polygons)) != TOPOLOGY[part_id]:
        return False
    square = 'CUBE' in part_id
    path = CORNER_MATERIAL if square else ROOF_MATERIAL
    slots = {i for i, mat in enumerate(mesh.materials) if mat and
             mat.get('nms_material_path', '').replace('\\', '/').upper() == path}
    faces = [p for p in mesh.polygons if p.material_index in slots]
    ids = sorted({v for p in faces for v in p.vertices})
    if len(ids) != (2040 if square else 809):
        return False
    points = np.array([mesh.vertices[i].co[:] for i in ids])
    digest = hashlib.sha256(np.rint(points * 10000).astype('<i4').tobytes()).hexdigest()
    if digest != (CORNER_DIGEST if square else ROOF_DIGEST):
        # Do not reapply to a corrected mesh whose tag was lost, or move
        # user-edited/replaced geometry merely because the part ID matches.
        return False
    if square:
        # Native corner frame placements, also used by the opaque frames.
        a, y = 4.69302, .507
        frames = (
            Matrix(((0, 0, 1, -a), (0, 1, 0, y), (-1, 0, 0, -a), (0, 0, 0, 1))),
            Matrix(((-1, 0, 0, -a), (0, 1, 0, y), (0, 0, -1, a), (0, 0, 0, 1))),
            Matrix(((0, 0, -1, a), (0, 1, 0, y), (1, 0, 0, a), (0, 0, 0, 1))),
        )
        groups = [(ids[i*510:(i+1)*510], frame.inverted()) for i, frame in enumerate(frames)]
    else:
        groups = [(ids, Matrix.Translation((0, -4, 0)))]
    normals = None
    if mesh.has_custom_normals:
        normals = np.empty((len(mesh.loops), 3), dtype=np.float32)
        mesh.corner_normals.foreach_get('vector', normals.ravel())
    transforms = {}
    for indices, transform in groups:
        for index in indices:
            mesh.vertices[index].co = transform @ mesh.vertices[index].co
            transforms[index] = transform.to_3x3()
    if normals is not None:
        for face in faces:
            for loop_id in face.loop_indices:
                rotation = transforms.get(mesh.loops[loop_id].vertex_index)
                if rotation is not None:
                    normals[loop_id] = np.asarray(rotation) @ normals[loop_id]
        mesh.normals_split_custom_set(normals.tolist())
    mesh[REVISION] = 1
    mesh.update()
    return True


def refresh_scene(scene):
    """Refresh embedded HD meshes on file open without changing build records."""
    from . import materials_v2
    seen = set()
    for obj in scene.objects:
        pid = obj.get('ObjectID')
        if (obj.type == 'MESH' and pid in TOPOLOGY and
                materials_v2.is_high_res(obj) and obj.data.as_pointer() not in seen):
            seen.add(obj.data.as_pointer())
            correct(obj.data, pid)
