"""Regression for TestBed's coincident electrical wires; writes fixture saves only.

Run with --factory-startup --disable-autoexec -b <TestBed.blend> --python this.py.
"""
import copy, hashlib, json, sys, tempfile
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import addon, module, QA, report
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_ship_link_resilience import fixture, TEMPLATE

actions = module('save_editor.corvette_actions')
repair = module('save_editor.ship_repair')
core = module('save_editor.ship_core')
files = module('save_editor.ship_files')
io = module('save_editor.corvette_io')
package = module('save_editor.ship_package')
optimizer = module('save_editor.corvette_optimizer')
interchange = module('interchange')
original_path = Path(bpy.data.filepath)
original_hash = hashlib.sha256(original_path.read_bytes()).hexdigest()
scene = bpy.context.scene
renamed = 'Test Lab - Renamed'
scene.nms_base_tool.string_base = renamed
objects = scene.nms_main.serialise(objects_only=True)
assert len(objects) == 293
zero_wires = [o for o in objects if o['ObjectID'] == '^U_POWERLINE' and not any(o['At'])]
assert len(zero_wires) == 2
repair.validate_parts(objects)

# Cable endpoint displacement can be zero; a solid part still needs orientation.
example = copy.deepcopy(objects[0])
for cable_id in repair.CABLE_IDS:
    cable = dict(example, ObjectID='^' + cable_id, At=[0, 0, 0])
    repair.validate_parts([cable])
for field in ('Up', 'At'):
    bad = dict(example, ObjectID='^BUILDWALL', **{field: [0, 0, 0]})
    try: repair.validate_parts([bad])
    except ValueError as exc: assert 'BUILDWALL' in str(exc) and field in str(exc)
    else: raise AssertionError('Invalid solid transform accepted')
repair.validate_parts([dict(example, Up=[0, 1e-8, 0], At=[0, 0, 1e-8])])

with tempfile.TemporaryDirectory(dir=QA) as temporary:
    folder = Path(temporary)
    paths = [folder / 'save.hg', folder / 'save2.hg']
    def snapshot():
        root = fixture()
        core.player(root, 'Main')['CharacterCustomisationData'] = [copy.deepcopy(TEMPLATE['custom']) for _ in range(23)]
        ship = core.ships(root, 'Main')[0]
        ship['Inventory']['BaseStatValues'][0]['Value'] = 123.0
        ship['Inventory_TechOnly']['SpecialSlots'] = [{'Index': {'X': 0, 'Y': 0}, 'Type': {'InventorySpecialSlotType': 'TechBonus'}}]
        root = core.translate(root, False)
        for path in paths:
            save = files.SaveFile(path); save.json_data = root; save.save()
        loaded, hashes, _ = files.read(paths)
        return dict(root=loaded, hashes=hashes, links=paths, scene=scene, expected='test')
    with patch.object(files.backup_policy, 'settings', return_value=(str(folder / 'backups'), 100)), \
         patch.object(io, 'cache_key', return_value='test'), patch.object(actions, 'refresh_selection'), \
         patch.object(optimizer, 'settings_file', return_value=folder / 'optimizer.json'):
        counts = {}
        for optimized in (False, True):
            s = snapshot()
            with actions.progress_ui.Activity('Testing TestBed export') as progress:
                actual, name, stats, signature = actions.scene_parts(bpy.context, optimized, progress)
            for wire in zero_wires: assert wire in actual
            payload, resets = repair.rebuild_payload(s['root'], 'Main', 0, objects=actual, name=name)
            assert not resets, resets
            s.update(plan=repair.make_plan(s['root'], 'Main', 0, payload, 'FULL'), signature=signature,
                     optimized=optimized, caption='Exported')
            actions.commit(s, bpy.context, lambda *args: None)
            result = files.SaveFile(paths[0]).load()
            assert files.SaveFile(paths[1]).load() == result
            linked = repair.linked_builds(result, 'Main', 0)
            assert len(linked) == 1
            saved = core.get(core.player(result, 'Main'), 'PersistentPlayerBases')[linked[0]]
            assert core.translate(core.get(saved, 'Objects')) == actual
            before, after = core.ships(s['root'], 'Main')[0], core.ships(result, 'Main')[0]
            assert core.get(saved, 'Name') == core.get(after, 'Name') == renamed
            for key in ('Inventory', 'Inventory_TechOnly', 'Inventory_Cargo', 'Resource', 'ShipClass'):
                assert core.get(before, key) == core.get(after, key), key
            assert core.get(core.player(s['root'], 'Main'), 'CharacterCustomisationData') == core.get(core.player(result, 'Main'), 'CharacterCustomisationData')
            counts[str(optimized)] = len(actual)
        assert list((folder / 'backups').rglob('*.hg'))

    # New designs export without a downloaded/imported template or injected parts.
    assert not scene.get('bbe_build_source_suffix')
    assert bpy.ops.bbe.export_ship_file(filepath=str(folder / 'TestBed.blend'), use_selected_save=False) == {'FINISHED'}
    target = folder / 'TestBed.nmsship'
    exported = interchange.BuildFile.read(target)
    assert exported.objects == objects
    assert json.loads(exported.entries['so.json'])['Name'] == renamed
    assert not (folder / 'TestBed.blend').exists()
    repair.validate_payload(dict(ship=json.loads(exported.entries['so.json']), objects=exported.objects,
                                custom=json.loads(exported.entries['ccd.json'])), 'FULL')
    selected = []
    op = NS(filepath='', use_selected_save=False)
    context = NS(scene=scene, window_manager=NS(fileselect_add=lambda operator: selected.append(operator.filepath)))
    assert addon.ExportShipFile.invoke(op, context, None) == {'RUNNING_MODAL'}
    assert selected and selected[0].endswith('.nmsship') and not selected[0].endswith('.blend.nmsship')
    op.filepath = str(folder / 'Renamed.blend')
    assert addon.ExportShipFile.check(op, context) and op.filepath.endswith('Renamed.nmsship')
    assert not addon.ExportShipFile.check(op, context)

    # Defaults must never inject a cockpit, and retained metadata takes priority.
    panel = dict(copy.deepcopy(objects[0]), ObjectID='^BUILDWALL')
    warnings = []
    bare = folder / 'no-cockpit.nmsship'
    addon.NMSMain._export_ship_file(NS(serialise=lambda **kw: [panel]), str(bare), '',
                                  NS(update=lambda *args: None), warnings=warnings)
    assert interchange.BuildFile.read(bare).objects == [panel]
    assert any('unflyable' in warning for warning in warnings)
    imported = package.new_corvette_source()
    ship = json.loads(imported.entries['so.json'])
    ship['Inventory']['BaseStatValues'][0]['Value'] = 987.0
    imported.entries['so.json'] = json.dumps(ship).encode()
    imported.entries['extra.bin'] = b'keep unknown package data'
    with patch.object(addon, '_restore_build_source', return_value=imported):
        preserved = folder / 'retained.nmsship'
        warnings = []
        addon.NMSMain._export_ship_file(NS(serialise=lambda **kw: objects), str(preserved), '',
                                      NS(update=lambda *args: None), warnings=warnings)
        entries = interchange.BuildFile.read(preserved).entries
        assert json.loads(entries['so.json'])['Inventory'] == ship['Inventory']
        assert entries['ccd.json'] == imported.entries['ccd.json']
        assert entries['extra.bin'] == imported.entries['extra.bin']
        assert not any('defaults' in warning for warning in warnings)
    scene['bbe_build_source_suffix'] = '.nmsship'
    try:
        with patch.object(addon, '_restore_build_source', return_value=None):
            try:
                addon.NMSMain._export_ship_file(NS(serialise=lambda **kw: objects), str(folder / 'missing.nmsship'), '',
                                              NS(update=lambda *args: None), warnings=[])
            except ValueError as exc: assert 'metadata is unavailable' in str(exc)
            else: raise AssertionError('Lost imported metadata silently reset')
        assert not (folder / 'missing.nmsship').exists()
    finally:
        del scene['bbe_build_source_suffix']
    assert hashlib.sha256(original_path.read_bytes()).hexdigest() == original_hash
    report('testbed_exports', dict(blender=bpy.app.version_string, parts=counts, preserved_zero_wires=2,
           inventory_and_stats_preserved=True, backups=True, new_design_nmsship=True, filename=Path(selected[0]).name,
           original_blend_unchanged=True, renamed_save_and_nmsship=True))
