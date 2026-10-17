"""Real save-copy callbacks must not starve BBE's timer or placement trigger."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import hashlib
import sys
import time
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module
r = module('project_recovery')
prefs = r._preferences()
prefs.bbe_recovery_mode = 'TIME'
prefs.bbe_recovery_minutes = 10

with TemporaryDirectory(prefix='bbe-timer-qa-') as temporary:
    root = Path(temporary)
    prefs.nms_backup_folder_path = str(root / 'backups')
    project = root / 'original.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    original = hashlib.sha256(project.read_bytes()).hexdigest()
    with patch.object(r.undo_guard, 'history_ready', return_value=True):
        # Another add-on saves every few minutes: retain the original BBE deadline.
        r._last_backup = time.monotonic() - 601
        baseline = r._last_backup
        r._pending_parts = 4
        for i in range(3):
            bpy.ops.wm.save_as_mainfile(filepath=str(root / f'other-{i}.blend'), copy=True)
            assert r._last_backup == baseline
            assert r._pending_parts == 4
        assert r._safe_to_save(), r._wait_reason()
        r.tick()
        assert len(r._backup_files(r._folder())) == 1
        assert r._last_backup > baseline
        assert r._pending_parts == 0
        assert r._status(prefs).startswith('Next backup in ')

        # Four due timers still leave three consecutive readable generations.
        for sequence in range(1, 5):
            bpy.context.scene['timer_sequence'] = sequence
            r._last_backup -= 601
            r.tick()
        files = r._backup_files(r._folder())
        assert len(files) == 3
        generations = []
        for path in files:
            with bpy.data.libraries.load(str(path)) as (available, loaded):
                loaded.scenes = [available.scenes[0]]
            generations.append(loaded.scenes[0]['timer_sequence'])
            bpy.data.scenes.remove(loaded.scenes[0])
        assert sorted(generations) == [2, 3, 4], generations
        assert bpy.data.filepath == str(project)
        assert hashlib.sha256(project.read_bytes()).hexdigest() == original

        # A delayed first idle tick must not start a second ten-minute wait.
        r.after_load(None)
        r._last_backup -= 601
        with patch.object(r, '_snapshot', wraps=r._snapshot) as snapshot:
            r.tick()
            snapshot.assert_called_once()

        # Errors stay visible, retry after one minute, and don't reset the deadline.
        r._last_backup -= 601
        baseline = r._last_backup
        with patch.object(r, '_snapshot', side_effect=OSError('Test disk full')) as snapshot:
            r.tick()
            assert r._last_backup == baseline
            assert r._last_error == 'Test disk full'
            assert r._status(prefs).startswith('Backup failed; retry in ')
            r.tick()
            assert snapshot.call_count == 1
        r._retry_at -= 61
        r.tick()
        assert not r._last_error and r._retry_at == 0

        # Edit mode defers the due backup and exposes why; leaving it resumes.
        bpy.ops.mesh.primitive_cube_add()
        r._last_backup -= 601
        bpy.ops.object.mode_set(mode='EDIT')
        assert r._status(prefs) == 'Waiting for Object Mode'
        with patch.object(r, '_snapshot', wraps=r._snapshot) as snapshot:
            r.tick()
            snapshot.assert_not_called()
            bpy.ops.object.mode_set(mode='OBJECT')
            r.tick()
            snapshot.assert_called_once()

        prefs.bbe_recovery_mode = 'PARTS'
        r._reset()
        r._pending_parts = prefs.bbe_recovery_parts
        bpy.ops.wm.save_as_mainfile(filepath=str(root / 'parts-other.blend'), copy=True)
        assert r._pending_parts == prefs.bbe_recovery_parts
        r.tick()
        assert r._pending_parts == 0
        # Save As changes project identity and starts its own schedule.
        bpy.ops.wm.save_as_mainfile(filepath=str(root / 'new-project.blend'))
        assert r._last_file == bpy.data.filepath
        assert time.monotonic() - r._last_backup < 5
print('RECOVERY_TIMER_18_1_78_PASS', bpy.app.version_string, flush=True)
