"""Exercise package import, review cancellation and the actual backed-up writer."""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import copy, json, sys, tempfile, zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_support import module, report, QA
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_ship_link_resilience import fixture, TEMPLATE
repair=module('save_editor.ship_repair');core=module('save_editor.ship_core')
files=module('save_editor.ship_files');manager=module('save_editor.ship_management')
with tempfile.TemporaryDirectory(dir=QA) as tmp:
    folder=Path(tmp)
    package=folder/'replacement.nmsship'
    with zipfile.ZipFile(package,'w') as z:
        z.writestr('objects.json',json.dumps(TEMPLATE['base']['Objects']))
        z.writestr('so.json',json.dumps(TEMPLATE['ship']))
        z.writestr('ccd.json',json.dumps(TEMPLATE['custom']))
    data=repair.read_replacement(package,'FULL')
    root=fixture('wrong_ship');core.player(root,'Main')['CharacterCustomisationData']=[{} for _ in range(23)]
    original=copy.deepcopy(root)
    s=dict(root=root,original=original,repairs=[],context='Main',index=0,busy=True)
    review=dict(payload=data,mode='FULL',context='Main',index=0,records=[0],source=package.name,fingerprint=repair.fingerprint(root))
    s['replacement_review']=review;manager.SESSION=s
    errors=[]
    op=NS(_session=s,_review=review,anchor=1,confirm_duplicates=False,confirm_target=False,
          fail=lambda exc:errors.append(str(exc)) or {'CANCELLED'})
    assert manager.BBE_OT_ship_replace_review.execute(op,None)=={'CANCELLED'}
    assert s['root']==original and not s['repairs']
    op.confirm_target=True
    assert manager.BBE_OT_ship_replace_review.execute(op,None)=={'FINISHED'},errors
    repaired=s['root'];assert not repair.inspect_slots(repaired,'Main')[0][0]
    paths=[folder/'save.hg',folder/'save2.hg']
    for path in paths:
        save=files.SaveFile(path);save.json_data=original;save.save()
    initial={p:p.read_bytes() for p in paths}
    expected=files.hashes(paths)
    with patch.object(files.backup_policy,'settings',return_value=(str(folder/'backups'),20)):
        backups=files.commit(repaired,paths,expected)
        assert len(backups)==2
        for backup in backups:assert files.SaveFile(backup).load()==original
        for path in paths:assert files.SaveFile(path).load()==repaired
        # Reject a stale review before any write.
        for path in paths:path.write_bytes(initial[path])
        paths[1].write_bytes(initial[paths[1]]+b'changed')
        try:files.commit(repaired,paths,expected)
        except ValueError:pass
        else:raise AssertionError('stale save accepted')
        assert paths[0].read_bytes()==initial[paths[0]]
        paths[1].write_bytes(initial[paths[1]])
        # Inject a failure after the first replacement; original pair is restored.
        real=files.replace_file;calls=[]
        def fail_second(src,dst):
            calls.append(str(dst))
            if len(calls)==2:raise OSError('test write failure')
            return real(src,dst)
        with patch.object(files,'replace_file',side_effect=fail_second):
            try:files.commit(repaired,paths,expected)
            except OSError:pass
            else:raise AssertionError('failure not injected')
        assert all(p.read_bytes()==initial[p] for p in paths)
    manager.SESSION=None
report('ship_repair',dict(package=True,explicit_confirmation=True,backup_roundtrip=True,
                         stale_save_rejected=True,rollback=True))
