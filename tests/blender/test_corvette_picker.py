"""Corvette-only UI choices and stale selection regression; synthetic cache only."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, report
io = module('save_editor.corvette_io')
manager = module('save_editor.save_manager')
utils = module('save_editor.save_editor_utils')
Manager = manager.SaveManager

def build(ctx, index, kind):
    return NS(save_context=ctx, base_index=index, base_type=kind, user_data=0,
              base_name=ctx + ' test build', parts_count=8, issues=[])
corvettes = [build(ctx, 0, utils.BaseType.CORVETTE) for ctx in ('Main', 'Season')]
freighters = [build(ctx, 1, utils.BaseType.FREIGHTER) for ctx in ('Main', 'Season')]
cache = dict(corvettes=corvettes, freighters=freighters, missing_corvettes=[])
Manager.enum_accounts_list=[('Default','Select Account',''),('qa','QA account','')]
Manager.enum_save_slots_list=[('Default','Select Save Slot',''),('1','QA Save Slot','')]
Manager.data_save_slot=[dict(slot=1,saves=[],save_name='QA')]
Manager.extracted_base_data=cache; Manager.save_data_loaded=True
data=bpy.context.scene.nms_save_data
data['nms_account_selected']=1; data['nms_save_slot']=1
data.nms_base_type=utils.BaseType.CORVETTE
Manager.enum_base_list=data.get_bases_enum_list(cache)
assert {row[0] for row in Manager.enum_base_list} == {'Default', '', '0', 'Season:0'}
assert io.entries(data) == corvettes
for base in corvettes:
    assert bpy.ops.bbe.select_corvette(value=io.identifier(base), expected=io.cache_key(data)) == {'FINISHED'}
    assert data.get_current_base_identifiers() is base
for base in freighters:
    before=data.nms_base_index
    assert bpy.ops.bbe.select_corvette(value=io.identifier(base), expected=io.cache_key(data)) == {'CANCELLED'}
    assert data.nms_base_index == before
    fake=NS(nms_base_index=io.identifier(base), nms_base_type=utils.BaseType.CORVETTE,
            get_current_slot_data=lambda: {}, get_base_type_key=lambda: 'corvettes')
    assert Manager.get_current_base_identifiers(fake) is None
assert bpy.ops.bbe.select_corvette(value='Default', expected=io.cache_key(data)) == {'FINISHED'}
assert data.get_current_base_identifiers() is None
assert bpy.types.Menu.bl_rna_get_subclass_py('BBE_MT_corvette_picker') is io.BBE_MT_corvette_picker
assert bpy.types.Panel.bl_rna_get_subclass_py('BBE_PT_corvette_picker') is None
class Layout:
    def menu(self, name, **kwargs):
        assert name == 'BBE_MT_corvette_picker' and kwargs['text'] == 'Select Corvette'
for base in (None, corvettes[0]):
    io.draw_picker(Layout(), NS(get_current_base_identifiers=lambda: base))
report('corvette_picker', dict(version=bpy.app.version_string, corvette_only=True,
       stale_freighter_rejected=True, main_and_expedition=True, closing_menu_registered=True))
