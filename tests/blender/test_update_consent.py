"""Use only an isolated Blender config; never change the user's preferences."""
from pathlib import Path
import json
import os
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import addon, bpy, module

root = Path(os.environ['BBE_CONSENT_TEST_ROOT']).resolve()
assert root in Path(bpy.utils.user_resource('CONFIG')).resolve().parents
ui = module('release_updates')
Client = module('furby_updates').ProcessUpdateClient
ui._client.close()
state_dir = Path(tempfile.mkdtemp(prefix='updates-', dir=root))
ui._client = Client('bbe', '18.1.63', state=state_dir, require_consent=True)
calls = []
ui._client.start = lambda *args, **kwargs: calls.append('check')

assert not ui._offer_auto_updates(), 'Headless sessions must not show a popup'
ui._client.maybe_check()
assert not calls, 'A new install must not check before consent'

if bpy.app.online_access_override and not bpy.app.online_access:
    try:
        ui._set_auto_updates(bpy.context, True)
    except RuntimeError as error:
        assert 'offline mode' in str(error)
    else:
        raise AssertionError('Forced offline mode was ignored')
    assert not calls and not ui._client.settings['auto_check']
    print('FORCED_OFFLINE_PASS', bpy.app.version_string)
else:
    bpy.context.preferences.system.use_online_access = False
    ui._set_auto_updates(bpy.context, False)
    assert not bpy.app.online_access and not calls
    restored = Client('bbe', '18.1.64', state=state_dir, require_consent=True)
    assert not restored.needs_auto_consent and not restored.settings['auto_check']

    fake_bpy = SimpleNamespace(app=bpy.app, ops=SimpleNamespace(wm=SimpleNamespace(save_userpref=lambda: {'CANCELLED'})))
    with patch.object(ui, 'bpy', fake_bpy):
        try:
            ui._set_auto_updates(bpy.context, True)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Failed preference save was ignored')
    assert not bpy.app.online_access and not calls
    assert not ui._client.settings['auto_check']

    assert bpy.ops.furby_bbe.auto_update_choice(enabled=True) == {'FINISHED'}
    assert bpy.app.online_access and bpy.context.preferences.system.use_online_access
    assert ui._client.settings['auto_check'] and calls == ['check']
    restored = Client('bbe', '18.1.64', state=state_dir, require_consent=True)
    assert not restored.needs_auto_consent and restored.settings['auto_check']

    assert bpy.ops.furby_bbe.auto_update_choice(enabled=False) == {'FINISHED'}
    assert bpy.app.online_access, 'No must preserve existing internet access'
    assert not ui._client.settings['auto_check'] and calls == ['check']
    assert bpy.ops.furby_bbe.auto_update_choice(enabled=True) == {'FINISHED'}
    assert calls == ['check', 'check']
    assert not ui._offer_auto_updates()
    print('CONSENT_OPERATOR_PASS', bpy.app.version_string, 'Yes, No, persistence, save failure, no pre-consent network')
