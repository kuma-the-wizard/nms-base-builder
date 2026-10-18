"""Native roof bounds, legacy migration, quality switching and saved scenes.

Run with --factory-startup --disable-autoexec --python-exit-code 1.
Optionally pass a reporter .blend after -- to audit it without overwriting it.
Expected bounds come from the installed vanilla game's LOD0 geometry, with
the native mesh-node hierarchy applied (not the placement/snap locator).
"""
from pathlib import Path
import hashlib, sys
import bpy
import numpy as np
from mathutils import Matrix, Euler
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import addon, module, report, QA

b = module('builder_v2')
fix = module('utils.roof_alignment')
Part = module('part').Part
NATIVE_BOUNDS = {
    'T_ROOF_E_CAP': ((-.386474609375, -.030059814453125, -2.728515625), (.386474609375, 2.01953125, 2.728515625)),
    'F_ROOF_E_CAP': ((-.65625, -.00014591217041015625, -3.123046875), (.65625, 1.45703125, 3.123046875)),
    'S_ROOF_E_CAP': ((-.0791015625, 0, -2.416015625), (.0791015625, 1.392578125, 2.416015625)),
    'B_ROOF_E_CAP': ((-.65625, -.00014591217041015625, -3.123046875), (.65625, 1.45703125, 3.123046875)),
    'T_ROOF_E_Q': ((-.100341796875, -.00899505615234375, -1.375), (.100341796875, 3.294921875, 1.40625)),
    'F_ROOF_E_Q': ((-.2406005859375, -.0000017285346984863281, -1.3330078125), (.248291015625, 3.087890625, 1.3310546875)),
    'S_ROOF_E_Q': ((-.0791015625, .0001093149185180664, -1.237051248550415), (.0791015625, 3.005968689918518, 1.333261251449585)),
    'B_ROOF_E_Q': ((-.2406005859375, -.0000017285346984863281, -1.623046875), (.248291015625, 3.634765625, 1.3310546875)),
}


def points(mesh):
    return np.array([v.co[:] for v in mesh.vertices])


def raw_mesh(pid):
    with bpy.data.libraries.load(b.get_asset_index()[pid], link=False) as (src, dst):
        dst.objects = list(src.objects)
    mesh = next(o.data for o in dst.objects if o and o.type == 'MESH')
    for o in dst.objects:
        if o: bpy.data.objects.remove(o, do_unlink=True)
    return mesh


def normals(mesh):
    return np.array([n.vector[:] for n in mesh.corner_normals])


results = {}
for pid, expected in NATIVE_BOUNDS.items():
    raw = raw_mesh(pid)
    raw[b.MESH_TAG] = pid
    original = points(raw)
    edited = raw.copy()
    edited.vertices[0].co.x += .1
    edited_points = points(edited)
    assert not fix.correct(edited, pid)
    assert np.array_equal(edited_points, points(edited))
    old_normals = normals(raw)
    old_uvs = [[v.uv[:] for v in layer.data] for layer in raw.uv_layers]
    old_materials = list(raw.materials)
    obj = bpy.data.objects.new(pid + '_legacy', raw)
    bpy.context.scene.collection.objects.link(obj)
    obj['ObjectID'] = pid
    obj['UserData'] = 0
    obj['Timestamp'] = '1700000000'
    obj.matrix_world = (Matrix.Translation((7.5, -4, 11)) @ Euler((.63, -.29, 1.42)).to_matrix().to_4x4()
                        @ Matrix.Diagonal((.61, .61, .61, 1)))
    bpy.context.view_layer.update()
    part = Part(bpy_object=obj, builder_object=addon.BUILDER)
    before = part.serialise()
    matrix = obj.matrix_world.copy()
    assert fix.refresh_scene(bpy.context.scene) == 1
    corrected = points(raw)
    assert np.allclose((corrected.min(0), corrected.max(0)), expected, atol=3e-6, rtol=0), pid
    normal_error = float(np.abs(normals(raw) - old_normals).max())
    print('NORMAL_ERROR', pid, raw.has_custom_normals, normal_error, flush=True)
    assert normal_error < .001, pid  # under 0.1 degree; packed custom-normal quantisation
    assert old_materials == list(raw.materials)
    assert old_uvs == [[v.uv[:] for v in layer.data] for layer in raw.uv_layers]
    assert part.serialise() == before and obj.matrix_world == matrix
    assert not fix.correct(raw, pid)
    assert np.array_equal(corrected, points(raw))
    del raw[fix.REVISION]
    assert not fix.correct(raw, pid), 'lost marker must not cause a second shift'
    low = b.load_proxy_mesh(pid)
    low_points = points(low)
    assert not fix.correct(low, pid)
    assert np.array_equal(low_points, points(low))
    for _ in range(3):
        obj.data = b.load_proxy_mesh(pid)
        assert part.serialise() == before
        obj.data = b.load_high_res_mesh(pid)
        assert part.serialise() == before
        p = points(obj.data)
        assert np.allclose((p.min(0), p.max(0)), expected, atol=3e-6, rtol=0)
    results[pid] = dict(native_bounds=True, exports_unchanged=True, edited_mesh_preserved=True,
                        repeated_switches=3, materials_uvs_normals_preserved=True)

# The actual load handler must also migrate an embedded legacy mesh without
# the optional pack, and must not accumulate another shift on repeated loads.
for obj in list(bpy.data.objects): bpy.data.objects.remove(obj, do_unlink=True)
legacy = raw_mesh('T_ROOF_E_CAP')
legacy[b.MESH_TAG] = 'T_ROOF_E_CAP'
obj = bpy.data.objects.new('saved_legacy_gable', legacy)
bpy.context.scene.collection.objects.link(obj)
obj['ObjectID'] = 'T_ROOF_E_CAP'
obj['UserData'] = 0
fixture = QA / 'roof_legacy.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(fixture))
hd = module('hd_library')
original_root = hd.scenes_root
hd.scenes_root = lambda: None
try:
    bpy.ops.wm.open_mainfile(filepath=str(fixture), load_ui=False, use_scripts=False)
    obj = bpy.data.objects['saved_legacy_gable']
    p = points(obj.data)
    assert np.allclose((p.min(0), p.max(0)), NATIVE_BOUNDS['T_ROOF_E_CAP'], atol=3e-6, rtol=0)
    module('stages').on_load(None)
    assert np.array_equal(p, points(obj.data))
    fixed_fixture = QA / 'roof_corrected.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(fixed_fixture))
    bpy.ops.wm.open_mainfile(filepath=str(fixed_fixture), load_ui=False, use_scripts=False)
    assert np.array_equal(p, points(bpy.data.objects['saved_legacy_gable'].data))
finally:
    hd.scenes_root = original_root

if '--' in sys.argv:
    source = Path(sys.argv[sys.argv.index('--') + 1])
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    # Disable just the migration callback to capture the unchanged original
    # export, then exercise the same callback used on normal file open.
    stages = module('stages')
    bpy.app.handlers.load_post.remove(stages.on_load)
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    bpy.app.handlers.load_post.append(stages.on_load)
    before = bpy.context.scene.nms_main.serialise(objects_only=True)
    matrices = {o.name: o.matrix_world.copy() for o in bpy.context.scene.objects}
    targets = [o for o in bpy.context.scene.objects if o.get('ObjectID') in NATIVE_BOUNDS]
    assert targets
    stages.on_load(None)
    assert bpy.context.scene.nms_main.serialise(objects_only=True) == before
    assert all(o.matrix_world == matrices[o.name] for o in bpy.context.scene.objects if o.name in matrices)
    for o in targets:
        p = points(o.data)
        assert np.allclose((p.min(0), p.max(0)), NATIVE_BOUNDS[o['ObjectID']], atol=3e-6, rtol=0)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    results['reporter'] = dict(parts=len(before), corrected_instances=len(targets),
                               exported_records_unchanged=True, source_sha256=digest, original_unchanged=True)

results['saved_mesh_migration_without_pack'] = True
results['save_reopen_idempotent'] = True
report('roof_alignment', results)
