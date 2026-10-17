from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_support import module,report
import bpy
updates=module('release_updates'); diag=module('blender_diagnostics'); errors=module('furby_errors')
prompt=next(c for c in updates._classes if c.bl_idname=='furby_bbe.error_report_prompt')
with tempfile.TemporaryDirectory() as folder:
    reporter=errors.ErrorReporter('bbe','18.1.82','Windows / Blender '+bpy.app.version_string,directory=folder)
    payload=reporter.record('Synthetic Blender test','Known diagnostic; no user data')
    fake=SimpleNamespace(payload_json=json.dumps(payload),report=lambda *args:None)
    wm=SimpleNamespace(invoke_props_dialog=lambda *args,**kwargs:{'RUNNING_MODAL'})
    context=SimpleNamespace(window_manager=wm)
    old=updates._reporter;updates._reporter=reporter
    try:
        with patch.object(diag.subprocess,'Popen') as spawn:
            assert prompt.invoke(fake,context,None)=={'RUNNING_MODAL'}
            prompt.cancel(fake,context)
            assert not updates._error_prompt_open
            spawn.assert_not_called()
            bpy.context.preferences.system.use_online_access=False
            assert prompt.execute(fake,context)=={'CANCELLED'}
            spawn.assert_not_called()
            assert (Path(folder)/'latest-report.json').exists()
        bpy.context.preferences.system.use_online_access=True
        with patch.object(updates._diagnostics,'start') as start:
            assert prompt.execute(fake,context)=={'FINISHED'}
            assert start.call_args.kwargs==dict(consent=True,online=True)
            assert start.call_args.args[0]['report_id']==payload['report_id']
        # Exercise a real caught-error operator, through Blender registration.
        previous=errors._active_reporter;errors._active_reporter=reporter
        try:
            try:bpy.ops.bbe.ship_management('INVOKE_DEFAULT')
            except RuntimeError:pass # Blender poll failure is not a BBE handled error.
            from types import SimpleNamespace
            manager=module('save_editor.ship_management')
            manager.Dialog.fail(SimpleNamespace(report=lambda *args:None),ValueError('Synthetic handled ship error'))
            assert reporter.latest['title']=='Add-on error'
            assert 'Synthetic handled ship error' in reporter.latest['description']
        finally:errors._active_reporter=previous
    finally:updates._reporter=old;reporter.close()
report('diagnostic_consent',dict(cancel_no_network=True,offline_no_network=True,consent_required=True,handled_ship_error_captured=True))
