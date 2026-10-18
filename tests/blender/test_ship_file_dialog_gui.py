"""Verify the actual file-browser filename for a design started in Blender."""
import os, sys, traceback
from pathlib import Path
import bpy, addon_utils
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import addon, QA, report, module, name
step = 0
def run():
    global step
    try:
        if step == 0:
            if os.environ.get('BBE_TEST_DISABLE') == '1':
                window = bpy.context.window_manager.windows[0]
                area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
                space = area.spaces.active
                toolbar = module('tools_menu.base_builder_menu')
                previous = toolbar._original_visibility[space.as_pointer()]
                with bpy.context.temp_override(window=window, area=area):
                    addon_utils.disable(name, default_set=False)
                    assert space.show_region_tool_header == previous
                    addon_utils.enable(name, default_set=True, persistent=False)
                print('ORDINARY_DISABLE_REENABLE_PASS', flush=True)
            assert bpy.ops.bbe.export_ship_file('INVOKE_DEFAULT') == {'RUNNING_MODAL'}
            step = 1
            return 2
        if step == 2:
            assert not any(a.type == 'FILE_BROWSER' for w in bpy.context.window_manager.windows for a in w.screen.areas)
            bpy.ops.wm.quit_blender()
            return None
        window, area = next((w, a) for w in bpy.context.window_manager.windows for a in w.screen.areas if a.type == 'FILE_BROWSER')
        params = area.spaces.active.params
        assert params.filename.endswith('.nmsship'), params.filename
        assert not params.filename.endswith('.blend.nmsship'), params.filename
        report('ship_file_dialog', dict(filename=params.filename, version=bpy.app.version_string, passed=True))
        if os.environ.get('BBE_TEST_QUIT_FILE_BROWSER') == '1':
            # Regression: add-on shutdown must not update region visibility
            # after Blender clears its active window. This crashed natively.
            bpy.ops.wm.quit_blender()
            return None
        region = next(r for r in area.regions if r.type == 'WINDOW')
        with bpy.context.temp_override(window=window, area=area, region=region):
            assert bpy.ops.file.cancel() == {'FINISHED'}
        step = 2
        return 1
    except BaseException:
        (QA / 'ship-file-dialog-error.txt').write_text(traceback.format_exc())
        print(traceback.format_exc(), flush=True)
        bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(run, first_interval=2)
