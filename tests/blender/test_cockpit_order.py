"""Stable RNA choices, scene-only swapping and saved-project persistence."""
from pathlib import Path
from types import SimpleNamespace as NS
import gc, sys, tempfile
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, QA, report
opt = module('save_editor.corvette_optimizer')
help_ui = module('save_editor.function_help')
builder = module('builder_v2')
bpy.context.scene.nms_main.new_file()
for index, name in enumerate(('Ziggy first', 'Alpha second', 'Other third')):
    obj = builder.add_part('B_COK_A', high_res=False, user_data=0).object
    obj.name = name
    obj.location = (index * 10, 0, index)
    obj['order'] = 0  # Ties must agree with the actual serializer, not alphabetic names.
wall = builder.add_part('BUILDWALL', high_res=False, user_data=0).object
wall.location = (2, 4, 6)
wall['order'] = 1
bpy.context.view_layer.update()

def serialise():
    bpy.context.view_layer.update()
    return bpy.context.scene.nms_main.serialise(objects_only=True)
def cockpit_positions(objects):
    return [o['Position'] for o in objects if o['ObjectID'].lstrip('^').startswith('B_COK_')]
def matrices():
    return {o.name: [list(row) for row in o.matrix_world] for o in bpy.context.scene.objects}
def prepare():
    op = NS()
    opt.prepare_cockpit_choices(op, bpy.context)
    return op

original = serialise()
original_matrices = matrices()
op = prepare()
items = opt.role_choices(op, bpy.context)
assert [row[1].split(' — ')[1] for row in items] == ['Ziggy first', 'Alpha second', 'Other third']
assert opt.role_choices(op, None) is items
for i in range(300):
    churn = [str(i) + ('x' * j) for j in range(250)]
    gc.collect()
    assert opt.role_choices(NS(choice_key=op.choice_key), bpy.context) is items
    assert items[0][1] == '1. B_COK_A — Ziggy first'

with tempfile.TemporaryDirectory(dir=QA) as temporary:
    folder = Path(temporary)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'original-project.blend'))
    bpy.ops.ed.undo_push(message='Before cockpit swap')
    assert bpy.ops.bbe.swap_corvette_cockpits('EXEC_DEFAULT', choice_key=op.choice_key, first='0', second='2') == {'FINISHED'}
    swapped = serialise()
    assert cockpit_positions(swapped) == list(reversed(cockpit_positions(original)))
    assert matrices() == original_matrices
    for config in (opt.core.defaults(), {'groups': [], 'delete_identical': False}):
        optimized, _ = opt.core.optimize(swapped, config)
        assert cockpit_positions(optimized) == cockpit_positions(swapped)
    # Save then reopen the original and swapped projects independently.
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'swapped-project.blend'))
    bpy.ops.ed.undo_push(message='After cockpit swap')
    assert bpy.ops.ed.undo() == {'FINISHED'}
    assert cockpit_positions(serialise()) == cockpit_positions(original)
    assert bpy.ops.ed.redo() == {'FINISHED'}
    assert cockpit_positions(serialise()) == cockpit_positions(swapped)
    bpy.ops.wm.open_mainfile(filepath=str(folder/'original-project.blend'))
    assert not opt._cockpit_dialogs
    assert cockpit_positions(serialise()) == cockpit_positions(original)
    bpy.ops.wm.open_mainfile(filepath=str(folder/'swapped-project.blend'))
    assert cockpit_positions(serialise()) == cockpit_positions(swapped)
    assert matrices() == original_matrices

    # Cancel has no effect; stale/changed lists must not redirect a choice.
    before = serialise(); op = prepare()
    opt.BBE_OT_swap_corvette_cockpits.cancel(op, bpy.context)
    assert op.choice_key not in opt._cockpit_dialogs and serialise() == before
    op = prepare()
    opt.placed_cockpits(bpy.context)[0].name += ' renamed'
    notes = []
    fake = NS(choice_key=op.choice_key, first='0', second='1', report=lambda *args:notes.append(args))
    assert opt.BBE_OT_swap_corvette_cockpits.execute(fake, bpy.context) == {'CANCELLED'}
    assert serialise() == before
    # Help is registered, local and contains explanations for each requested workflow.
    assert len(help_ui.TOPICS) == 7
    assert bpy.ops.bbe.function_help('EXEC_DEFAULT', topic='COCKPIT') == {'FINISHED'}
report('cockpit_order', dict(version=bpy.app.version_string, stable_label_lifetimes=True,
       same_id_cockpits=True, immediate_swap=True, positions_unchanged=True,
       ordinary_and_optimized=True, undo_redo=True, blend_persistence=True,
       independent_projects=True, stale_selection_rejected=True, help_topics=7))
