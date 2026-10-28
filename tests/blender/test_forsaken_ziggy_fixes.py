"""Regression for the 7.10 variant groups and native mirrored counterparts."""
from pathlib import Path
import json, sys
import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).parent))
from test_support import addon, module, D, report

rows = module('asset_browser.utils.parts_definition').ROWS
Part = module('part').Part
manifest = json.loads((D / 'resources/forsaken_assets.json').read_text())
pairs = json.loads((D / 'resources/mirror_pairs.json').read_text())['pairs']
native = {item['id']: item for item in manifest['assets']}

for item in native.values():
    row = rows['^' + item['id']]
    assert (row[8] == 'True') == item['visible'], item['id']
    assert row[9] == ('^' + item['parent'] if item['parent'] else 'None'), item['id']
    if item['parent']:
        assert '^' + item['parent'] in rows, item['id']
        if item['parent'] in native:
            assert native[item['parent']]['visible'], item['id']

assert native['B_COK_C5']['parent'] == 'B_COK_C4'
assert native['B_COK_C8']['parent'] == 'B_COK_C7'
assert native['B_STR_AD_Y_NE']['parent'] == 'B_STR_AD_NE'
assert native['B_STR_AG_NE']['visible']
assert native['B_STR_AN_NE']['visible']

new_pairs = [p for p in pairs if p[0] in native and p[1] in native]
assert len(new_pairs) == 87, len(new_pairs)
for a, b in new_pairs:
    assert Part.get_mirror_part_id(a) == b, (a, b)
    assert Part.get_mirror_part_id(b) == a, (b, a)

def mirrored_error(before, after):
    tree = KDTree(len(before))
    for i, v in enumerate(before):
        tree.insert(v, i)
    tree.balance()
    points = after[::max(1, len(after) // 600)]
    return max(tree.find(v)[2] for v in points)

checks = []
for pid in ('B_WNG_S', 'B_WNG_T', 'B_WNG_U', 'B_WNG_V',
            'B_WNG_W', 'B_WNG_X', 'B_WNG_Y',
            'B_STR_AC_NE', 'B_STR_AC_N', 'B_STR_AH_NETB'):
    bpy.data.batch_remove(list(bpy.context.scene.objects))
    obj = module('builder_v2').add_part(pid, user_data=0).object
    bpy.context.view_layer.update()
    before = [obj.matrix_world @ v.co for v in obj.data.vertices]
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    assert bpy.ops.object.nms_universal_mirror_x() == {'FINISHED'}, pid
    bpy.context.view_layer.update()
    target = Part.get_mirror_part_id(pid)
    assert obj['ObjectID'] == target, (pid, obj['ObjectID'], target)
    expected = [Vector((-v.x, v.y, v.z)) for v in before]
    actual = [obj.matrix_world @ v.co for v in obj.data.vertices]
    error = mirrored_error(expected, actual)
    tolerance = 0.15 if pid == 'B_WNG_Y' else (0.08 if pid == 'B_WNG_W' else 0.07)
    assert error < tolerance, (pid, target, error)
    assert bpy.ops.object.nms_universal_mirror_x() == {'FINISHED'}, pid
    bpy.context.view_layer.update()
    assert obj['ObjectID'] == pid
    checks.append({'id': pid, 'target': target, 'surfaceError': round(error, 5)})

report('forsaken_ziggy_fixes_' + str(bpy.app.version[1]), {
    'variantGroups': len({x['id'] for x in native.values() if x['visible']}),
    'nativeMirrorPairs': len(new_pairs),
    'mirrorChecks': checks,
})
