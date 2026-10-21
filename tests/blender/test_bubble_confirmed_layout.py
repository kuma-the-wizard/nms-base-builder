"""Keep the user-confirmed NMS export stable without false closed-side warnings."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module

ex = module('bubble_export')
fixture = json.loads((Path(__file__).parents[1] / 'fixtures/bubble_confirmed_layout.json').read_text())
records = fixture['objects']
hints = {int(i): hint for i, hint in fixture['hints'].items()}
compiled, issues, displays = ex.plan_objects(records, hints)
assert not issues, issues
assert compiled == fixture['exported'], 'Changed the frames that worked in game'
assert ex.compile_objects(records, hints) == compiled
assert len(displays) == 30

# A real visible tip into a hidden side still proposes a junction. Two closed
# sides alone must not do so. The missing-end warning remains advisory.
def tube(center):
    return dict(ObjectID='^BASE_BUBPIPE', Position=[center[0], center[1]-1, center[2]],
                Up=[0, 1, 0], At=[0, 0, 1])

local = [tube((0, 0, 0)), tube((0, -2, 0)), tube((0, 0, 2)), tube((2, 0, 0))]
local_hints = {0: dict(name='Elbow', shape='ELBOW:Bot+Front'),
               1: dict(name='Bottom', shape='STRAIGHT:Y'),
               2: dict(name='Front', shape='STRAIGHT:Z'),
               3: dict(name='Side', shape='STRAIGHT:X')}
_, real_issues, _ = ex.plan_objects(local, local_hints)
assert 0 in real_issues, real_issues
local_hints[0]['shape'] = 'CORNER3:Bot+Front+Right'
assert not ex.plan_objects(local, local_hints)[1]

draft = {0: dict(name='Draft', shape='ELBOW:Bot+Front')}
assert ex.plan_objects(local[:1], draft)[1]
assert len(ex.compile_objects(local[:1], draft)) == 1
print('CONFIRMED_LAYOUT_EXPORT_UNCHANGED_PASS', flush=True)
print('CLOSED_SIDE_FALSE_WARNINGS_REMOVED_PASS', flush=True)
print('VISIBLE_CONNECTION_AND_ADVISORY_EXPORT_PASS', flush=True)
