"""The browser's context helper leaves the scene when its window closes."""
from pathlib import Path
import sys
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, report

operators = module('tools.asset_browser_operators')
grid = module('tools.asset_browser_grid')
obj = operators.browser_pin_object()
assert obj.name in bpy.context.scene.collection.all_objects
assert obj.get('bbe_asset_browser_pin')
grid._unlink_closed_browser_pins(bpy.context.window_manager)
assert obj.name not in bpy.context.scene.collection.all_objects
assert bpy.data.objects.get(obj.name) == obj
operators.browser_pin_object()
assert obj.name in bpy.context.scene.collection.all_objects
report('closed_browser_pin', {'hidden_when_closed': True, 'relinked_on_open': True})
