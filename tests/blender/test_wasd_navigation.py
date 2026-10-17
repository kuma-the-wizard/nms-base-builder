"""Run with --enable-event-simulate in an isolated GUI/factory-startup session."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys, traceback, json
import bpy
from mathutils import Quaternion
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_support import module, report, QA
bpy.context.preferences.view.show_splash=False
bpy.ops.wm.save_as_mainfile(filepath=str(QA/f'WASD Regression {bpy.app.version_string}.blend'))
nav=module('wasd_navigation')
prefs=nav.preferences(bpy.context)
assert not prefs.bbe_wasd_enabled
assert len(nav._keymaps)==2
assert abs(nav.direction({'W','D'},Quaternion()).length-1)<1e-6
assert nav.direction({'W','S'},Quaternion()).length==0
assert nav.direction({'E'},Quaternion()).z==1
assert not nav.input_is_owned(NS(window=NS(modal_operators=[NS(bl_idname='BBE_OT_sidebar_asset_grid')])))
assert not nav.input_is_owned(NS(window=NS(modal_operators=[NS(bl_idname='BBE_OT_asset_grid')])))
assert nav.input_is_owned(NS(window=NS(modal_operators=[NS(bl_idname='TRANSFORM_OT_translate')])))
window=bpy.context.window
area=next(a for a in window.screen.areas if a.type=='VIEW_3D')
region=next(r for r in area.regions if r.type=='WINDOW')
view=area.spaces.active.region_3d
original_location=view.view_location.copy()
matrices={o.name:o.matrix_world.copy() for o in bpy.data.objects}
stage=0
checks={}
def event(kind,value='PRESS'):
    window.event_simulate(type=kind,value=value,x=region.x+region.width//2,y=region.y+region.height//2)
def step():
    global stage, position
    try:
        if stage==0:
            # The user's saved workspace has this long-lived listener even
            # when its sidebar category is hidden. It must not block movement.
            sidebar=next(r for r in area.regions if r.type=='UI')
            with bpy.context.temp_override(window=window,area=area,region=sidebar):
                bpy.ops.bbe.sidebar_asset_grid('INVOKE_DEFAULT')
            assert any(o.bl_idname=='BBE_OT_sidebar_asset_grid' for o in window.modal_operators)
            prefs.bbe_wasd_enabled=True
            event('MOUSEMOVE','NOTHING')
            event('RIGHTMOUSE')
        elif stage==1:
            assert nav._active is not None, 'RMB did not start navigation'
            event('W')
        elif stage==2:
            assert (view.view_location-original_location).length>.1, 'W did not move viewport'
            event('W','RELEASE');event('RIGHTMOUSE','RELEASE')
            position=view.view_location.copy()
            checks['real_keymap_movement']=True
            checks['movement_with_sidebar_listener']=True
        elif stage==3:
            assert nav._active is None
            assert (view.view_location-position).length<1e-5
            assert all(o.matrix_world==matrices[o.name] for o in bpy.data.objects)
            checks['release_stops_without_object_changes']=True
            event('RIGHTMOUSE')
        elif stage==4:
            assert nav._active is not None
            prefs.bbe_wasd_enabled=False
            assert nav._active is None
            event('RIGHTMOUSE','RELEASE')
            checks['toggle_stops_session']=True
        elif stage==5:
            prefs.bbe_wasd_enabled=True
            event('RIGHTMOUSE')
        elif stage==6:
            assert nav._active is not None
            nav.before_load(None)
            assert nav._active is None
            event('RIGHTMOUSE','RELEASE')
            nav.unregister();assert not nav._keymaps
            nav.register();assert len(nav._keymaps)==2
            checks['load_and_reregister_cleanup']=True
            report('wasd_navigation_gui',dict(passed=True,**checks))
            bpy.ops.wm.quit_blender();return None
        stage+=1
        return .5
    except Exception:
        traceback.print_exc()
        report('wasd_navigation_gui',dict(passed=False,stage=stage,**checks))
        bpy.ops.wm.quit_blender()
        return None
bpy.app.timers.register(step,first_interval=20)
