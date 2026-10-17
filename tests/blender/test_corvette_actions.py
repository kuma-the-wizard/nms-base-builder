"""Synthetic, isolated keep-build repair and new-slot export operator checks."""
from pathlib import Path
from types import SimpleNamespace as NS, MethodType
from unittest.mock import patch
import copy, sys, tempfile, json
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, addon, QA, report
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_ship_link_resilience import fixture, TEMPLATE
actions = module('save_editor.corvette_actions')
repair = module('save_editor.ship_repair')
core = module('save_editor.ship_core')
files = module('save_editor.ship_files')
io = module('save_editor.corvette_io')
manager = module('save_editor.ship_management')
package = module('save_editor.ship_package')

def instance(cls, **kwargs):
    op = NS(**kwargs)
    for name in ('check', '_prepare', 'cancel'):
        if hasattr(cls, name): setattr(op, name, MethodType(getattr(cls, name), op))
    return op

with tempfile.TemporaryDirectory(dir=QA) as temporary:
    folder = Path(temporary); paths = [folder/'save.hg', folder/'save2.hg']
    def root_for_test():
        root = fixture('wrong_ship')
        p = core.player(root, 'Main')
        p['CharacterCustomisationData'] = [copy.deepcopy(TEMPLATE['custom']) for _ in range(23)]
        p['PersistentPlayerBases'][0]['Objects'] = [copy.deepcopy(TEMPLATE['base']['Objects'][0])]
        root['ExpeditionContext'] = copy.deepcopy(fixture(context='Season')['ExpeditionContext'])
        return core.translate(root, False)
    def write(root):
        for path in paths:
            save = files.SaveFile(path); save.json_data = root; save.save()
    def snapshot(root):
        write(root)
        loaded, hashes, _ = files.read(paths)
        return dict(root=loaded, hashes=hashes, links=paths, scene=bpy.context.scene, expected='test')
    notes = []
    reporter = lambda severity, message: notes.append((severity, message))
    backups = patch.object(files.backup_policy, 'settings', return_value=(str(folder/'backups'), 100))
    with backups, patch.object(io, 'cache_key', return_value='test'), patch.object(actions, 'refresh_selection'):
        root = root_for_test(); s = snapshot(root)
        op = instance(actions.BBE_OT_corvette_repair_keep, _s=s, context_name='Main', index=0, anchor=1,
                      in_manager=False, confirm=False, confirm_duplicates=False, confirm_resets=False, report=reporter)
        with patch.object(actions, 'report_error', side_effect=lambda op, sev, msg:reporter(sev,msg)):
            assert actions.BBE_OT_corvette_repair_keep.execute(op, bpy.context) == {'CANCELLED'}
        assert files.SaveFile(paths[0]).load() == root
        op.confirm = True
        assert actions.BBE_OT_corvette_repair_keep.execute(op, bpy.context) == {'FINISHED'}
        repaired = files.SaveFile(paths[0]).load()
        assert core.corvette(core.ships(repaired, 'Main')[0])
        assert core.get(core.get(core.player(repaired, 'Main'), 'PersistentPlayerBases')[0], 'Objects') == core.get(core.get(core.player(root, 'Main'), 'PersistentPlayerBases')[0], 'Objects')
        assert core.get(core.ships(root, 'Main')[0], 'Inventory_TechOnly') == core.get(core.ships(repaired, 'Main')[0], 'Inventory_TechOnly')
        assert files.SaveFile(paths[1]).load() == repaired
        assert any('unflyable' in message for _, message in notes)
        captured = package.from_save(repaired, 'Main', 0)  # No cockpit must not block package capture.
        addon._store_build_source(bpy.context.scene, captured, '.nmsship')
        bpy.context.scene.nms_base_tool.string_base_type = 'PlayerShipBase'
        warnings = []
        addon.NMSMain._export_ship_file(NS(serialise=lambda **kw:captured.objects), str(folder/'no-cockpit.nmsship'), '', NS(update=lambda *a:None), warnings=warnings)
        assert warnings and 'unflyable' in warnings[0]

        # Inventory resets require specific consent, not just a target confirmation.
        broken = root_for_test(); core.put(core.get(core.ships(broken, 'Main')[0], 'Inventory_TechOnly'), 'Width', 0)
        op._s = snapshot(broken)
        with patch.object(actions, 'report_error'):
            assert actions.BBE_OT_corvette_repair_keep.execute(op, bpy.context) == {'CANCELLED'}
        assert files.SaveFile(paths[0]).load() == broken
        op.confirm_resets = True
        assert actions.BBE_OT_corvette_repair_keep.execute(op, bpy.context) == {'FINISHED'}

        # Both Main/Expedition and overwrite/new-slot modes use the backed-up writer.
        objects = [copy.deepcopy(TEMPLATE['base']['Objects'][0])]
        objects[0]['Position'] = [123, 4, 5]
        for ctx in ('Main', 'Season'):
            for mode in ('NEW', 'SELECTED'):
                root = root_for_test(); s = snapshot(root)
                index = 4 if mode == 'NEW' else 0
                op = instance(actions.BBE_OT_corvette_export, _s=s, _objects=objects, _name='My design',
                              _signature='scene', optimized=False, context_name=ctx, destination=mode, slot=str(index),
                              _choice=None, confirm=False, confirm_resets=False, confirm_duplicates=False, report=reporter)
                assert op.check(bpy.context)
                op.confirm = True
                with patch.object(actions, 'scene_parts', return_value=(objects, 'My design', {}, 'scene')):
                    assert actions.BBE_OT_corvette_export.execute(op, bpy.context) == {'FINISHED'}
                result = files.SaveFile(paths[0]).load()
                ship = core.ships(result, ctx)[index]
                assert core.corvette(ship) and core.get(ship, 'Name') == 'My design'
                linked = repair.linked_builds(result, ctx, index)
                assert len(linked) == 1
                base = core.get(core.player(result, ctx), 'PersistentPlayerBases')[linked[0]]
                assert core.translate(core.get(base, 'Objects')) == objects
                assert result[core.key(result, 'ExpeditionContext' if ctx == 'Main' else 'BaseContext')] == root[core.key(root, 'ExpeditionContext' if ctx == 'Main' else 'BaseContext')]
                assert files.SaveFile(paths[1]).load() == result

        # Scene edits and game-save edits after the dialog invalidate the review.
        for changed in ('scene', 'save'):
            s = snapshot(root_for_test())
            data, _ = repair.rebuild_payload(s['root'], 'Main', 4, objects=objects, new=True)
            s.update(plan=repair.make_plan(s['root'], 'Main', 4, data, 'FULL'), signature='before', optimized=False, caption='Exported')
            if changed == 'save': paths[1].write_bytes(paths[1].read_bytes()+b'changed')
            before = [p.read_bytes() for p in paths]
            with patch.object(actions, 'scene_parts', return_value=(objects, '', {}, 'after' if changed == 'scene' else 'before')):
                try: actions.commit(s, bpy.context, reporter)
                except ValueError: pass
                else: raise AssertionError('Stale review wrote files')
            assert [p.read_bytes() for p in paths] == before

        # Actual Blender parts use the normal serializer/optimizer and writer.
        bpy.context.scene.nms_main.new_file()
        builder = module('builder_v2')
        first = builder.add_part('BUILDFLATPANEL', high_res=False, user_data=0).object
        second = builder.add_part('BUILDWALL', high_res=False, user_data=0).object
        second.location = (13, 2, 4)
        bpy.context.scene.nms_base_tool.string_base = 'Scene export'
        optimizer = module('save_editor.corvette_optimizer')
        with patch.object(optimizer, 'settings_file', return_value=folder/'optimizer.json'):
            for optimized in (False, True):
                s = snapshot(root_for_test())
                with actions.progress_ui.Activity('Testing scene export') as progress:
                    actual, name, counts, signature = actions.scene_parts(bpy.context, optimized, progress)
                assert len(actual) == 2 and repair.cockpit_warning(actual)
                data, _ = repair.rebuild_payload(s['root'], 'Main', 3, objects=actual, name=name, new=True)
                s.update(plan=repair.make_plan(s['root'], 'Main', 3, data, 'FULL'), signature=signature,
                         optimized=optimized, caption='Exported')
                # Progress must stay alive after the review closes, including
                # the expensive draft checks, file write and list refresh.
                live, stages = [], []
                class TrackingActivity(actions.progress_ui.Activity):
                    def __enter__(self):
                        live.append(self)
                        return super().__enter__()
                    def __exit__(self, *args):
                        try: return super().__exit__(*args)
                        finally: live.remove(self)
                def observed(label, fn):
                    def call(*args, **kwargs):
                        assert live, f'No progress overlay during {label}'
                        stages.append(label)
                        return fn(*args, **kwargs)
                    return call
                with patch.object(actions.progress_ui, 'Activity', TrackingActivity), \
                     patch.object(repair, 'apply_plan', observed('apply', repair.apply_plan)), \
                     patch.object(repair, 'validate_reviewed_draft', observed('validate', repair.validate_reviewed_draft)), \
                     patch.object(files, 'commit', observed('write', files.commit)), \
                     patch.object(actions, 'refresh_selection', observed('refresh', actions.refresh_selection)):
                    actions.commit(s, bpy.context, reporter)
                assert {'apply','validate','write','refresh'} <= set(stages) and not live
                result = files.SaveFile(paths[0]).load()
                n = repair.linked_builds(result, 'Main', 3)[0]
                assert core.translate(core.get(core.get(core.player(result, 'Main'), 'PersistentPlayerBases')[n], 'Objects')) == actual

        # Ship Management repair only stages a draft and preserves its ledger.
        root = root_for_test(); original = copy.deepcopy(root)
        session = dict(root=root, original=original, repairs=[], context='Main', index=0, busy=True)
        manager.SESSION = session
        op = instance(actions.BBE_OT_corvette_repair_keep, _s=dict(root=root), _session=session,
                      _fingerprint=repair.fingerprint(root), context_name='Main', index=0, anchor=1,
                      in_manager=True, confirm=True, confirm_duplicates=False, confirm_resets=False, report=reporter)
        assert actions.BBE_OT_corvette_repair_keep.execute(op, bpy.context) == {'FINISHED'}
        assert len(session['repairs']) == 1 and session['dirty']
        repair.validate_reviewed_draft(original, session['root'], session['repairs'])
        assert original == root
        manager.SESSION = None

        # RNA passes OperatorProperties to enum callbacks; keep choices alive
        # there, and reset the reused enum ordinal when changing destinations.
        key = 'enum-regression'
        slots = {('Main', 'SELECTED'): [('NONE', 'Choose ship', ''), ('0', 'Ship', '')],
                 ('Main', 'NEW'): [('3', 'First empty', ''), ('4', 'Second empty', '')]}
        actions._dialogs[key] = dict(contexts=[('Main', 'Main', '')], slots=slots)
        props = NS(dialog_key=key, context_name='Main', destination='NEW')
        assert actions.slot_items(props, None) == slots['Main', 'NEW']
        op = instance(actions.BBE_OT_corvette_export, _s=dict(root=root_for_test()), _objects=objects, _name='Design',
                      _slots=slots, _scope=('Main', 'SELECTED'), _choice=None, context_name='Main', destination='NEW',
                      slot='4', confirm=True, confirm_duplicates=True, confirm_resets=True)
        op.check(bpy.context)
        assert op.slot == '3' and not op.confirm and not op.confirm_duplicates and not op.confirm_resets
        op.destination = 'SELECTED'
        op.check(bpy.context)
        assert op.slot == 'NONE' and op._error
        actions._dialogs.pop(key)
    assert list((folder/'backups').rglob('*.hg'))
report('corvette_actions', dict(version=bpy.app.version_string, keep_build=True, no_cockpit_allowed=True,
       ship_data_preserved=True, reset_consent=True, new_slot=True, overwrite=True,
       main_and_expedition=True, stale_scene_and_save_rejected=True, manager_draft=True, backups=True))
