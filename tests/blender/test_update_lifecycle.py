"""A real Blender file load must not discard the updater's result polling timer."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from test_support import module, QA, report
import bpy
from types import SimpleNamespace
from unittest.mock import Mock

updates=module('release_updates')
assert bpy.app.timers.is_registered(updates.poll)
target=QA/'update-lifecycle.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(target))
bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False)
assert bpy.app.timers.is_registered(updates.poll), 'Updater timer vanished on file load'

real_bpy=updates.bpy;real_client=updates._client;real_reporter=updates._reporter
offer=updates._offer_auto_updates
try:
    client=module('furby_updates').ProcessUpdateClient('bbe','18.1.86',state=QA/'updater-isolated',require_consent=True)
    client.set_auto(True);client.settings['last_attempt']=0;client.start=Mock()
    updates._client=client;updates._reporter=None;updates._offer_auto_updates=lambda:False
    app=SimpleNamespace(background=False,online_access=False)
    updates.bpy=SimpleNamespace(app=app,context=SimpleNamespace(window_manager=SimpleNamespace(windows=[])))
    updates.poll();client.start.assert_not_called()
    app.online_access=True;updates.poll();client.start.assert_called_once()
    client.start.reset_mock();client.set_auto(False);updates.poll();client.start.assert_not_called()
finally:
    updates.bpy=real_bpy;updates._client=real_client;updates._reporter=real_reporter;updates._offer_auto_updates=offer
report('update_lifecycle',{'persistent_after_open':True,'online_later_check':True,'disabled_no_check':True,'blender':bpy.app.version_string})
