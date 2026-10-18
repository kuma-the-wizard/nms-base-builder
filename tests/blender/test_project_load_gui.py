"""Select a local save, then open someone else's project in a disposable GUI."""
from pathlib import Path
import copy, hashlib, json, os, sys, traceback
from unittest.mock import patch
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, addon, QA, report
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_ship_link_resilience import fixture
manager = module('save_editor.save_manager')
utils = module('save_editor.save_editor_utils')
core = module('save_editor.ship_core')
files = module('save_editor.ship_files')
grid = module('tools.asset_browser_grid')
actions = module('save_editor.corvette_actions')
if os.environ.get('BBE_TEST_NO_HD'):
    hd = module('hd_library')
    hd.library_root = lambda: None
    hd.available = lambda: False
source = Path(os.environ.get('BBE_TEST_PROJECT', Path.home() / 'Downloads/TestBed.blend'))
original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
folder = QA / ('project_load_' + str(os.getpid()))
account = folder / 'st_123456789'
account.mkdir(parents=True)
for number in (1, 5):
    root = fixture()
    root['ActiveContext'] = 'Main'
    root['CommonStateData']['SaveName'] = 'QA destination ' + str(number)
    root['BaseContext']['PlayerStateData']['PlayerFreighterName'] = ''
    root['BaseContext']['PlayerStateData']['PersistentPlayerBases'][0]['Name'] = 'QA Corvette ' + str(number)
    for filename in (('save.hg', 'save2.hg') if number == 1 else ('save9.hg', 'save10.hg')):
        save = files.SaveFile(account / filename)
        save.json_data = core.translate(root, False)
        save.save()
save_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in account.glob('*.hg')}
bpy.context.preferences.addons[addon.__name__].preferences.nms_save_folder_path = str(folder)
data = bpy.context.scene.nms_save_data
data.check_plugin_enabled = True
data.nms_account_selected = str(account)
data.nms_save_slot = '5'
data.nms_base_index = '0'
assert data.get_current_base_identifiers().base_name == 'QA Corvette 5'
assert actions.snapshot(bpy.context)['links']
bpy.ops.object.nms_launch_asset_browser_window()
stage = 0
results = {'version': bpy.app.version_string, 'addon_file': addon.__file__,
           'no_hd': bool(os.environ.get('BBE_TEST_NO_HD'))}

def inspect_windows():
    return [dict(window=w.as_pointer(), screen=w.screen.as_pointer(), name=w.screen.name,
                 areas=[dict(type=a.type, ptr=a.as_pointer(), pin=str(getattr(a.spaces.active, 'pin_id', '')),
                             context=getattr(a.spaces.active, 'context', ''), use_pin=getattr(a.spaces.active, 'use_pin_id', False),
                             header=a.spaces.active.show_region_header,
                             ui=getattr(a.spaces.active, 'show_region_ui', None),
                             toolbar=getattr(a.spaces.active, 'show_region_toolbar', None))
                        for a in sorted(w.screen.areas, key=lambda a:a.x)])
            for w in bpy.context.window_manager.windows]

def check():
    global stage
    try:
        if stage == 0:
            assert len(grid._sessions) == 1 and len(next(iter(grid._sessions.values()))._tiles) > 0
            results['before_windows'] = inspect_windows()
            stage = 1
            bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=True, use_scripts=False)
            assert not module('hd_library_ui')._saved_hd_needs_simple_proxies(bpy.context.scene)
            return 6
        if stage == 2:
            stage = 3
            print('QA_LOAD_KEEP_UI_BEGIN', flush=True)
            bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
            assert not module('hd_library_ui')._saved_hd_needs_simple_proxies(bpy.context.scene)
            print('QA_LOAD_KEEP_UI_RETURNED', flush=True)
            return 6
        results['after_windows'] = inspect_windows()
        data = bpy.context.scene.nms_save_data
        results['after'] = dict(enabled=data.check_plugin_enabled, account=data.nms_account_selected,
                               slot=data.nms_save_slot, selected=data.nms_base_index,
                               last_account=data.last_account_selected, last_slot=data.last_slot_selected,
                               grid_sessions=len(grid._sessions), file_version=list(bpy.data.version))
        if os.environ.get('BBE_REPRO_ONLY'):
            report('project_load_gui_before', results)
        else:
            assert data.check_plugin_enabled, results['after']
            assert data.nms_account_selected == str(account) and data.nms_save_slot == '5', results['after']
            assert data.get_current_base_identifiers().base_name == 'QA Corvette 5', results['after']
            data.refresh_bases_list()
            assert data.get_current_base_identifiers().base_name == 'QA Corvette 5'
            assert {Path(p).name for p in actions.snapshot(bpy.context)['links']} == {'save9.hg', 'save10.hg'}
            assert bpy.context.scene.nms_base_tool.string_base == 'TEST LAB'
            assert len(grid._sessions) == 1, results['after_windows']
            session = next(iter(grid._sessions.values()))
            assert len(session._tiles) > 0
            left = min(session._window.screen.areas, key=lambda a:a.x)
            assert grid._is_browser_pin(left.spaces.active.pin_id)
            assert left.spaces.active.pin_id.name != 'B_DOOR0.002'
            results['restored_tiles'] = len(session._tiles)
            assert len([o for o in bpy.context.scene.objects if 'ObjectID' in o]) == 293
            if stage == 1:
                results['load_ui_true'] = True
                stage = 2
                return 1
            results['load_ui_false'] = True
            assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in account.glob('*.hg')} == save_hashes
            repair = module('save_editor.ship_repair')
            optimizer = module('save_editor.corvette_optimizer')
            with patch.object(files.backup_policy, 'settings', return_value=(str(folder/'backups'), 20)), \
                 patch.object(optimizer, 'settings_file', return_value=folder/'optimizer.json'):
                for optimized in (False, True):
                    s = actions.snapshot(bpy.context)
                    with actions.progress_ui.Activity('Testing export after project load') as progress:
                        objects, name, counts, signature = actions.scene_parts(bpy.context, optimized, progress)
                    payload, _ = repair.rebuild_payload(s['root'], 'Main', 0, objects=objects, name=name)
                    s.update(plan=repair.make_plan(s['root'], 'Main', 0, payload, 'FULL'),
                             signature=signature, optimized=optimized, caption='QA exported')
                    actions.commit(s, bpy.context, lambda *args: None)
                    saved = files.SaveFile(account/'save10.hg').load()
                    base = core.get(core.player(saved, 'Main'), 'PersistentPlayerBases')[0]
                    assert len(core.get(base, 'Objects')) == len(objects)
                    assert files.SaveFile(account/'save9.hg').load() == saved
                    assert data.get_current_base_identifiers().base_name == 'TEST LAB'
            results['normal_and_optimized_fixture_exports'] = True
            assert all(hashlib.sha256((account/name).read_bytes()).hexdigest() == save_hashes[name]
                       for name in ('save.hg', 'save2.hg'))
            results['passed'] = True
            report('project_load_gui', results)
        assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    except Exception:
        results['error'] = traceback.format_exc()
        report('project_load_gui_failed', results)
        traceback.print_exc()
    bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(check, first_interval=6, persistent=True)
