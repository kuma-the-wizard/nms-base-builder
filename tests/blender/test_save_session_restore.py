"""Local save identity survives project loads; missing/ambiguous targets do not."""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, report
m = module('save_editor.save_manager')
M = m.SaveManager
u = m.save_editor_utils
d = bpy.context.scene.nms_save_data
accounts = [('Default', 'Select Account', ''), ('local', 'Local', '')]
slots = [dict(slot=5, saves=['fixture-only'], save_name='Local slot')]

def build(context='Main', index=4, name='Chosen Corvette'):
    return NS(save_context=context, base_index=index, base_type=u.BaseType.CORVETTE,
              user_data=3, galactic_address='123', base_name=name, parts_count=8, issues=[])

def select(context='Main'):
    m._project_session = None
    m.restore_after_load()
    d.check_plugin_enabled = True
    d.nms_account_selected = 'local'
    d.nms_save_slot = '5'
    d.nms_base_index = 'Season:4' if context == 'Season' else '4'
    bpy.context.scene.nms_base_tool.string_base = 'Project design name'

with patch.object(M, 'get_accounts_enum_list', return_value=accounts) as discover, \
     patch.object(u, 'get_save_slots_list', return_value=slots) as find_slots, \
     patch.object(u, 'extract_bases_list_from_save') as read:
    for context in ('Main', 'Season'):
        read.return_value = dict(corvettes=[build(context)])
        select(context)
        m.capture_before_load()
        # These values represent someone else's old saved project metadata.
        d.last_account_selected = 'someone-else'
        d.last_slot_selected = '1'
        read.return_value = dict(corvettes=[build(context, index=9)])
        m.restore_after_load()
        assert d.check_plugin_enabled and d.nms_account_selected == 'local' and d.nms_save_slot == '5'
        assert d.nms_base_index == ('Season:9' if context == 'Season' else '9')
        assert bpy.context.scene.nms_base_tool.string_base == 'Project design name'

    for remaining in ([], [build(name='Different ship')], [build(), build(index=7)]):
        read.return_value = dict(corvettes=[build()]); select(); m.capture_before_load()
        read.return_value = dict(corvettes=remaining); m.restore_after_load()
        assert d.nms_base_index == 'Default' and not d.has_selected_base() and d.session_status

    for missing in ('account', 'slot', 'read'):
        read.return_value = dict(corvettes=[build()]); select(); m.capture_before_load()
        if missing == 'account': discover.return_value = accounts[:1]
        if missing == 'slot': find_slots.return_value = []
        if missing == 'read': read.side_effect = OSError('QA unavailable file')
        m.restore_after_load()
        assert d.check_plugin_enabled and not d.has_selected_base() and d.session_status
        if missing == 'account': assert d.nms_account_selected == 'Default'
        if missing == 'slot': assert d.nms_save_slot == 'Default'
        discover.return_value = accounts; find_slots.return_value = slots; read.side_effect = None
        if missing == 'read':
            d.refresh_bases_list()
            assert d.is_base_data_loaded() and not d.session_status

    d.check_plugin_enabled = False
    m.capture_before_load()
    d.last_account_selected = 'someone-else'; d.last_slot_selected = '1'
    m.restore_after_load()
    assert not d.check_plugin_enabled
    assert d.nms_account_selected == d.nms_save_slot == d.nms_base_index == 'Default'
    assert d.last_account_selected == d.last_slot_selected == 'Default'
    assert not M.extracted_base_data and not M.data_save_slot
report('save_session_restore', dict(version=bpy.app.version_string, main_and_expedition=True,
       identity_survives_reorder=True, missing_and_ambiguous_cleared=True,
       foreign_project_selection_ignored=True, disabled_stays_disabled=True, read_failure_recoverable=True))
