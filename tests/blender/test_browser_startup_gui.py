"""Run in a disposable GUI profile containing an older saved browser layout.

BBE_BROWSER_TEST_STARTUP and BBE_BROWSER_TEST_RESULT must point to test files.
The initial phase verifies a direct executable launch, without loading a file.
"""
import importlib, json, os, traceback
from pathlib import Path
import bpy, addon_utils
startup=Path(os.environ['BBE_BROWSER_TEST_STARTUP']).resolve()
result=Path(os.environ['BBE_BROWSER_TEST_RESULT']).resolve()
assert 'tests' in startup.parts and '.artifacts' in startup.parts
assert 'tests' in Path(bpy.utils.user_resource('CONFIG')).parts
scratch=result.parent/'tmp'
scratch.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.temporary_directory=str(scratch)
name=next(n for n in bpy.context.preferences.addons.keys() if n.endswith('.no_mans_sky_base_builder'))
stage=0
results={}
def check():
    global stage
    try:
        grid=importlib.import_module(name+'.tools.asset_browser_grid')
        if stage==1:
            addon_utils.enable(name,default_set=False,persistent=True)
            stage=2
            return 5
        assert len(grid._sessions)==1, (stage, list(grid._sessions))
        session=next(iter(grid._sessions.values()))
        assert len(session._tiles)>0, (stage, session._groups)
        assert len(grid._resources)==1
        label={0:'direct_startup',2:'disable_reenable',3:'file_reopen'}[stage]
        results[label]={'tiles':len(session._tiles),'sessions':len(grid._sessions)}
        print('BROWSER_GUI',label,results[label],flush=True)
        if stage==0:
            addon_utils.disable(name,default_set=False)
            assert not grid._resources and not grid._sessions
            stage=1
            return 1
        if stage==2:
            stage=3
            bpy.ops.wm.open_mainfile(filepath=str(startup))
            return 5
        results['passed']=True
        result.write_text(json.dumps(results,indent=2),encoding='utf-8')
        bpy.ops.wm.quit_blender()
    except Exception:
        traceback.print_exc()
        results['passed']=False
        result.write_text(json.dumps(results,indent=2),encoding='utf-8')
        bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(check,first_interval=8,persistent=True)
