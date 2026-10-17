"""Recognize old saved UI helpers without treating named build meshes as UI."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, report
grid = module('tools.asset_browser_grid')
bpy.ops.mesh.primitive_cube_add(size=.1)
obj = bpy.context.object
obj.name = 'Asset Browser Window'
for collection in tuple(obj.users_collection):
    collection.objects.unlink(obj)
obj.use_fake_user = True
left = NS(type='PROPERTIES', x=0, spaces=NS(active=NS(
    pin_id=obj, use_pin_id=True, context='CONSTRAINT')))
right = NS(type='IMAGE_EDITOR', x=400, spaces=NS(active=NS(show_region_header=False)))
window = NS(screen=NS(areas=[right, left]))
assert not grid._is_browser_pin(obj)  # Scene cleanup must remain strict.
assert grid._saved_browser_target(window) is right
assert grid._saved_browser_target(window) is right  # No migration/mutation needed.
assert not obj.keys() and not obj.users_collection
obj['ObjectID'] = '^TEST'
assert grid._saved_browser_target(window) is None
del obj['ObjectID']
bpy.context.scene.collection.objects.link(obj)
assert grid._saved_browser_target(window) is None
bpy.context.scene.collection.objects.unlink(obj)
left.spaces.active.context='OBJECT'
assert grid._saved_browser_target(window) is None
left.spaces.active.context='CONSTRAINT'
right.spaces.active.show_region_header=True
assert grid._saved_browser_target(window) is None
right.type='PROPERTIES'
right.spaces.active=NS(pin_id=obj, context='MODIFIER')
assert grid._saved_browser_target(window) is right
right.spaces.active.context='OBJECT'
assert grid._saved_browser_target(window) is None
report('browser_legacy_restore', {'legacy_cube':True,'legacy_two_properties':True,
    'ordinary_models_untouched':True,'cleanup_predicate_unchanged':True})
