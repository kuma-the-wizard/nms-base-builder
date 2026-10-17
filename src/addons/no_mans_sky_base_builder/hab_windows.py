"""Show the native open wall state where Corvette windows occupy hab slots.

Only display meshes change. Placement, colour, ownership and export data stay
on the original objects; removing/moving a window restores the closed section.
"""
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix
from bpy.app.handlers import persistent
from .utils import materials_v2
from . import undo_guard

SOURCE = 'bbe_hab_closed_mesh'
OPEN = 'bbe_hab_open_slots'
WINDOWS = {'B_WALL_WIND0', 'B_WALL_WIND1', 'B_WALL_WIND2'}
_table = None
_signatures = {}
_busy = False


def table():
    global _table
    if _table is None:
        _table = json.loads((Path(__file__).parent/'resources/hab_wall_slots.json').read_text())
    return _table


def source_mesh(obj):
    if not obj.data.get(OPEN):
        obj[SOURCE] = obj.data
    return obj.get(SOURCE, obj.data)


def open_mesh(source, pid, slots):
    token = ','.join(sorted(slots))
    for mesh in bpy.data.meshes:
        if mesh.get(OPEN) == token and mesh.get(SOURCE) == source:
            return mesh
    spec = table()[pid]
    # Do not apply face masks to an unrelated/custom or older asset revision.
    if len(source.vertices) != spec['vertices'] or len(source.polygons) != spec['polygons']:
        return source
    keep = np.ones(len(source.polygons), dtype=bool)
    for slot in slots:
        for first, last in spec['slots'][slot]['faces']:
            keep[first:last+1] = False
    faces = [p for p in source.polygons if keep[p.index]]
    loop_ids = np.array([i for p in faces for i in p.loop_indices], dtype=np.int32)
    mesh = bpy.data.meshes.new('BBE Hab / '+pid+' / '+token)
    mesh.from_pydata([v.co[:] for v in source.vertices], [], [p.vertices[:] for p in faces])
    for material in source.materials:
        mesh.materials.append(material)
    mesh.polygons.foreach_set('material_index', [p.material_index for p in faces])
    mesh.polygons.foreach_set('use_smooth', [p.use_smooth for p in faces])
    for uv in source.uv_layers:
        values = np.empty(len(source.loops)*2, dtype=np.float32)
        uv.data.foreach_get('uv', values)
        mesh.uv_layers.new(name=uv.name).data.foreach_set('uv', values.reshape(-1,2)[loop_ids].ravel())
    if source.has_custom_normals:
        normals = np.empty(len(source.loops)*3, dtype=np.float32)
        source.corner_normals.foreach_get('vector', normals)
        mesh.normals_split_custom_set(normals.reshape(-1,3)[loop_ids].tolist())
    for key, value in source.items():
        mesh[key] = value
    mesh[OPEN] = token
    mesh[SOURCE] = source
    mesh.update()
    return mesh


def refresh(scene=None, force=False):
    global _busy
    if _busy or not undo_guard.history_ready():
        return
    scene = scene or bpy.context.scene
    parts = [o for o in scene.objects if o.type == 'MESH' and o.get('ObjectID') in set(table())|WINDOWS]
    signature = (getattr(scene, 'bbe_detailed_proxies', True), tuple(
        (o.as_pointer(), o.data.as_pointer(), o.get('ObjectID'), tuple(round(v,5) for row in o.matrix_world for v in row))
        for o in parts))
    key = scene.as_pointer()
    if not force and _signatures.get(key) == signature:
        return
    _busy = True
    try:
        habs = [o for o in parts if o.get('ObjectID') in table() and materials_v2.is_high_res(o)]
        windows = [o for o in parts if o.get('ObjectID') in WINDOWS and materials_v2.is_high_res(o)]
        occupied = {o: set() for o in habs}
        if getattr(scene, 'bbe_detailed_proxies', True):
            for window in windows:
                best = None
                for hab in habs:
                    # Compare in hab space: rotated/scaled ships use the same
                    # native slot coordinates. Nearby decorations do not open it.
                    relative = hab.matrix_world.inverted_safe() @ window.matrix_world
                    for slot, spec in table()[hab['ObjectID']]['slots'].items():
                        expected = Matrix(spec['matrix'])
                        distance = (relative.translation-expected.translation).length
                        if distance > .05:
                            continue
                        if max(abs(relative[r][c]-expected[r][c]) for r in range(3) for c in range(3)) > .025:
                            continue
                        if best is None or distance < best[0]:
                            best = (distance, hab, slot)
                if best:
                    occupied[best[1]].add(best[2])
        for hab in habs:
            source = source_mesh(hab)
            wanted = open_mesh(source, hab['ObjectID'], occupied[hab]) if occupied[hab] else source
            if hab.data != wanted:
                hab.data = wanted
        _signatures[key] = signature
        # Keep unused display meshes: older undo steps can still own them.
    finally:
        _busy = False


def tick():
    try:
        if not bpy.app.is_job_running('RENDER'):
            refresh()
    except Exception as exc:
        print('BBE hab windows:', exc)
    return 1.0


@persistent
def loaded(_):
    _signatures.clear()
    # The timer refreshes after the load/undo settle period.


@persistent
def before_render(scene, *_):
    refresh(scene)


def register():
    if not bpy.app.timers.is_registered(tick):
        bpy.app.timers.register(tick, first_interval=.5, persistent=True)
    for handlers, callback in ((bpy.app.handlers.load_post, loaded), (bpy.app.handlers.render_pre, before_render)):
        if callback not in handlers:
            handlers.append(callback)


def unregister():
    if bpy.app.timers.is_registered(tick):
        bpy.app.timers.unregister(tick)
    for handlers, callback in ((bpy.app.handlers.load_post, loaded), (bpy.app.handlers.render_pre, before_render)):
        if callback in handlers:
            handlers.remove(callback)
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data.get(OPEN) and obj.get(SOURCE):
            obj.data = obj[SOURCE]
    _signatures.clear()
