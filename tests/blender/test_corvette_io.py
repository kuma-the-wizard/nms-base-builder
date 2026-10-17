"""Read/import/export/repair synthetic saves only; never touch player saves."""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import copy, json, sys, tempfile
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, addon, report, QA
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_ship_link_resilience import fixture, TEMPLATE
core = module('save_editor.ship_core')
repair = module('save_editor.ship_repair')
package = module('save_editor.ship_package')
io = module('save_editor.corvette_io')
files = module('save_editor.ship_files')
utils = module('save_editor.save_editor_utils')
manager = module('save_editor.save_manager')
interchange = module('interchange')

def source(problem=None, ctx='Main', raw=False):
    root = fixture(problem, context=ctx)
    p = core.player(root, ctx)
    p['PlayerFreighterName'] = 'Keep freighter'
    p['CharacterCustomisationData'] = [copy.deepcopy(TEMPLATE['custom']) for _ in range(23)]
    p['ShipOwnership'][0]['UnrecognizedFutureField'] = {'preserve': 123}
    return core.translate(root, False) if raw else root

for ctx in ('Main', 'Season'):
    for raw in (False, True):
        root = source(ctx=ctx, raw=raw); before = copy.deepcopy(root)
        saved = package.from_save(root, ctx, 0)
        assert json.loads(saved.entries['so.json']) == core.translate(core.ships(root, ctx)[0])
        assert json.loads(saved.entries['ccd.json']) == TEMPLATE['custom']
        edited = copy.deepcopy(saved.objects); edited[0]['Position'][0] += 17
        exported = interchange.BuildFile.from_bytes(saved.ship_bytes(edited), '.nmsship')
        assert exported.objects == edited
        assert exported.entries['so.json'] == saved.entries['so.json']
        assert exported.entries['ccd.json'] == saved.entries['ccd.json']
        assert root == before
        for bad in ('wrong_ship', 'duplicate', -1, 12, '0', True):
            try: package.from_save(source(bad, ctx, raw), ctx, 0)
            except ValueError: pass
            else: raise AssertionError(f'Accepted uncertain metadata: {ctx}/{bad}')

with tempfile.TemporaryDirectory(dir=QA) as temp:
    folder = Path(temp); paths = [folder/'save.hg', folder/'save2.hg']
    def write(root):
        for path in paths:
            save = files.SaveFile(path); save.json_data = root; save.save()
    root = source(raw=True); write(root)
    cache = utils.extract_bases_list_from_save(paths)
    selected = cache['corvettes'][0]
    assert not selected.issues and selected.save_context == 'Main'
    data, captured, error = utils.import_paticular_base_from_save(selected, paths, with_ship_source=True)
    assert captured.kind == 'ship' and not error and data['Objects'] == captured.objects
    # Exercise the actual manager import boundary without asynchronous model loading.
    def create_parts(document):
        for i, part in enumerate(document['Objects']):
            obj = bpy.data.objects.new(f'QA part {i}', bpy.data.meshes.new(f'QA mesh {i}'))
            obj['ObjectID'] = part['ObjectID']; bpy.context.scene.collection.objects.link(obj)
    with patch.object(manager.builder_v2, 'deserialise_from_data', side_effect=create_parts):
        result = bpy.context.scene.nms_save_data.import_base(bpy.context, selected, paths)
    assert 'Imported 8 parts' in result, result
    restored = addon._restore_build_source(bpy.context.scene)
    assert restored.entries == captured.entries
    # Reopen a .blend: source metadata must survive and a fresh project must clear it.
    project = folder/'roundtrip.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    bpy.ops.wm.open_mainfile(filepath=str(project))
    assert addon._restore_build_source(bpy.context.scene).entries == captured.entries
    edited = copy.deepcopy(captured.objects); edited[0]['Position'][0] += 10
    output = folder/'exported.nmsship'
    progress = NS(update=lambda *a: None)
    nms = NS(serialise=lambda **kw: edited)
    count = addon.NMSMain._export_ship_file(nms, str(output), '', progress)
    assert count == 8 and interchange.BuildFile.read(output).objects == edited
    assert interchange.BuildFile.read(output).entries['so.json'] == captured.entries['so.json']
    addon._clear_build_source(bpy.context.scene)
    # Explicit fallback for an older Blender project keeps edited objects, original metadata.
    fake = NS(extracted_base_data=cache, get_current_base_identifiers=lambda:selected,
              get_current_slot_data=lambda:{'saves':paths})
    explicit = package.selected_save_source(NS(scene=NS(nms_save_data=fake)))
    with patch.object(package, 'selected_save_source', return_value=explicit):
        addon.NMSMain._export_ship_file(nms, str(output), '', progress, True)
    assert interchange.BuildFile.read(output).objects == edited
    paths[1].write_bytes(paths[1].read_bytes()+b'changed')
    try: package.selected_save_source(NS(scene=NS(nms_save_data=fake)))
    except ValueError: pass
    else: raise AssertionError('Stale source accepted')
    # Health extraction remains usable with invalid links and missing builds.
    for bad in ('wrong_ship', 'duplicate', -1, 12, '0', True, 'missing_build'):
        write(source(bad, raw=True)); broken = utils.extract_bases_list_from_save(paths)
        if bad == 'missing_build': assert broken['missing_corvettes'][0]['index'] == 0
        else:
            assert broken['corvettes'][0].issues, bad
            before = {p:p.read_bytes() for p in paths}
            target = broken['corvettes'][0]
            try: utils.save_base_to_save_file(TEMPLATE['base']['Objects'], target, paths, base_name='Do not rename a shuttle')
            except ValueError: pass
            else: raise AssertionError(f'Unsafe objects-only export allowed: {bad}')
            assert all(p.read_bytes()==before[p] for p in paths)
            optimized = module('save_editor.optimizer_export')
            try: optimized.export(TEMPLATE['base']['Objects'], target, paths)
            except ValueError: pass
            else: raise AssertionError(f'Unsafe optimized export allowed: {bad}')
            assert all(p.read_bytes()==before[p] for p in paths)
    # Exercise actual repair review execute/cancel and committed backup round-trip.
    broken_root = source('wrong_ship', raw=True); write(broken_root)
    root, hashes, origin = files.read(paths)
    cache = utils.extract_bases_list_from_save(paths)
    payload = dict(ship=TEMPLATE['ship'], objects=TEMPLATE['base']['Objects'], custom=TEMPLATE['custom'])
    s = dict(root=root, hashes=hashes, source=origin, links=paths, context='Main', index=0,
             records=[0], anchor=0, payload=payload, filename='replacement.nmsship',
             scene=bpy.context.scene, expected='qa')
    op = NS(token='qa', confirm=False, duplicates=False, report=lambda *a: None)
    io._reviews['qa'] = s
    with patch.object(io, 'report_error'):
        assert io.BBE_OT_corvette_repair_review.execute(op, bpy.context) == {'CANCELLED'}
    assert files.SaveFile(paths[0]).load() == broken_root
    io._reviews['qa'] = s
    io.BBE_OT_corvette_repair_review.cancel(op, bpy.context)
    assert not io._reviews
    io._reviews['qa'] = s; op.confirm = True
    with patch.object(io, 'cache_key', return_value='qa'), patch.object(files.backup_policy, 'settings', return_value=(str(folder/'backups'), 20)):
        assert io.BBE_OT_corvette_repair_review.execute(op, bpy.context) == {'FINISHED'}
    repaired = files.SaveFile(paths[0]).load()
    assert not repair.inspect_slots(repaired, 'Main')[0][0]
    assert core.ships(repaired, 'Main')[1:] == core.ships(broken_root, 'Main')[1:]
    assert files.SaveFile(paths[1]).load() == repaired
    backups = list((folder/'backups').rglob('*.hg'))
    assert len(backups) == 2 and all(files.SaveFile(p).load() == broken_root for p in backups)
report('corvette_io', dict(version=bpy.app.version_string, save_import=True, blend_persistence=True,
       edited_export=True, explicit_old_project_source=True, stale_source_rejected=True,
       warnings=True, repair_cancel=True, repair_backup_roundtrip=True))
