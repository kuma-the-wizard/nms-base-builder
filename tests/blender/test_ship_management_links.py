"""The actual manager operators open and save safe drafts with uncertain links."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, report, QA
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_ship_link_resilience import fixture

manager = module('save_editor.ship_management')
core = module('save_editor.ship_core')
files = module('save_editor.ship_files')
source = QA / 'ship-link-source-placeholder.hg'
source.write_bytes(b'test placeholder; never read as a game save')
notices = []
operator = SimpleNamespace(report=lambda level, message: notices.append(message),
                           fail=lambda exc: {'CANCELLED'})
data = SimpleNamespace(nms_base_type='PlayerShipBase',
                       get_current_slot_data=lambda: {'saves': [str(source)]},
                       get_current_base_identifiers=lambda: SimpleNamespace(save_context='Season', user_data=0),
                       refresh_bases_list=lambda: None)
context = SimpleNamespace(scene=SimpleNamespace(nms_save_data=data), window=None, window_manager=None)
root = fixture()
root['ExpeditionContext'] = fixture('duplicate', 'Season')['ExpeditionContext']
snapshot = copy.deepcopy(root)
with patch.object(files, 'read', return_value=(copy.deepcopy(root), {}, source)), \
        patch.object(manager, 'open_manager_window') as opened:
    result = manager.BBE_OT_ship_management.invoke(operator, context, None)
    assert result == {'FINISHED'}, notices
    opened.assert_called_once()
    assert manager.SESSION['context'] == 'Season'
    assert manager.SESSION['index'] == 0
    assert manager.SESSION['link_issues']['Season']
    assert not manager.SESSION['link_issues']['Main']

# Class/inventory changes on the affected context reach the existing backed-up
# writer; ownership edits must be rejected before that writer is called.
core.set_class(manager.SESSION['root'], 'Season', 0, 'C')
with patch.object(files, 'commit', return_value=['verified-backup']) as commit, \
        patch.object(files, 'read', return_value=(root, {}, source)):
    result = manager.BBE_OT_ship_save.execute(operator, context)
    assert result == {'FINISHED'}, notices
    commit.assert_called_once()
    submitted = commit.call_args.args[0]
    assert core.get(core.player(submitted, 'Season'), 'PersistentPlayerBases') == \
           core.get(core.player(snapshot, 'Season'), 'PersistentPlayerBases')
manager.SESSION['root']['ExpeditionContext']['PlayerStateData']['PersistentPlayerBases'][0]['UserData'] = 4
with patch.object(files, 'commit') as commit:
    assert manager.BBE_OT_ship_save.execute(operator, context) == {'CANCELLED'}
    commit.assert_not_called()
manager.SESSION = None
manager.SOURCE_WINDOW = None
report('ship_management_links', {'opened_with_uncertain_links': True,
                                 'selected_context_preserved': True,
                                 'safe_edit_reached_writer': True,
                                 'ownership_change_blocked_before_writer': True})
