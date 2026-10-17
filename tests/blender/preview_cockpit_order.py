"""Isolated cockpit selector/help UI; creates no user saves or preferences."""
from pathlib import Path
import sys, gc, json
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, QA
builder = module('builder_v2')
opt = module('save_editor.corvette_optimizer')
bpy.context.preferences.view.show_splash = False
bpy.context.scene.nms_main.new_file()
for index, name in enumerate(('Ziggy Front Cockpit', 'Ziggy Rear Cockpit', 'Spare Cockpit')):
    obj = builder.add_part('B_COK_A', high_res=False, user_data=0).object
    obj.name = name; obj.location = (index*10, 0, 0); obj['order'] = index
bpy.ops.wm.save_as_mainfile(filepath=str(QA/'BBE Cockpit QA.blend'))
def show():
    window = bpy.context.window
    area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
    region = next(r for r in area.regions if r.type == 'WINDOW')
    with bpy.context.temp_override(window=window, area=area, region=region):
        bpy.ops.bbe.swap_corvette_cockpits('INVOKE_DEFAULT')
    return None
bpy.app.timers.register(show, first_interval=3)
def stress_redraw():
    scratch = [str(i)*60 for i in range(5000)]
    gc.collect()
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas: area.tag_redraw()
    (QA/'cockpit_order_native_state.json').write_text(json.dumps([
        [o.name, o.get('order'), list(o.location)] for o in opt.placed_cockpits(bpy.context)]))
    return .25
bpy.app.timers.register(stress_redraw, first_interval=4)
