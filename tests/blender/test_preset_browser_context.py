"""A preset can be placed from both the popout and sidebar Asset Browsers."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import *


preset_module = module('preset')
preset_dir = QA / 'preset_browser_context'
preset_dir.mkdir(exist_ok=True)
(preset_dir / 'browser-context.nmsprefab').write_text(json.dumps({
    'Objects': [{
        'ObjectID': '^T_WALL_Q1',
        'UserData': 0,
        'Position': [0, 0, 0],
        'Up': [0, 1, 0],
        'At': [0, 0, 1],
    }],
}))
preset_module.Preset.PRESET_PATH = str(preset_dir)

bpy.context.scene.nms_main.new_file()
window = bpy.context.window
area = next(area for area in window.screen.areas if area.type == 'VIEW_3D')
space = area.spaces.active
space.overlay.show_relationship_lines = True

for editor_type in ('VIEW_3D', 'IMAGE_EDITOR'):
    area.type = editor_type
    with bpy.context.temp_override(window=window, area=area):
        result = bpy.ops.object.nms_asset_browser_object_selected(
            'EXEC_DEFAULT', object_id='browser-context', is_preset=True)
    assert result == {'FINISHED'}, (editor_type, result)
    controls = [obj for obj in bpy.context.scene.objects
                if obj.get('PresetID') == 'browser-context']
    assert len(controls) == (1 if editor_type == 'VIEW_3D' else 2)
    assert all(len(obj.children) == 1 for obj in controls)

area.type = 'VIEW_3D'
assert space.overlay.show_relationship_lines is False
report('preset_browser_context', {
    'sidebarContextPlaced': True,
    'popoutImageEditorContextPlaced': True,
    'relationshipLinesDisabledInViewport': True,
})
