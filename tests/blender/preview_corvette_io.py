"""Isolated native UI review using synthetic saves. No user preferences written."""
from pathlib import Path
import copy, sys, os
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, QA
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_ship_link_resilience import fixture, TEMPLATE
utils = module('save_editor.save_editor_utils')
core = module('save_editor.ship_core')
files = module('save_editor.ship_files')
Manager = module('save_editor.save_manager').SaveManager
io = module('save_editor.corvette_io')
actions = module('save_editor.corvette_actions')
bpy.context.preferences.view.show_splash = False
folder = QA/'corvette_io_ui'/'NMS'; folder.mkdir(parents=True, exist_ok=True)
paths = [folder/'save.hg', folder/'save2.hg']
root = fixture()
p = core.player(root, 'Main')
p['PlayerFreighterName'] = 'My Freighter'
p['CharacterCustomisationData'] = [copy.deepcopy(TEMPLATE['custom']) for _ in range(23)]
p['ShipOwnership'][0]['Name'] = 'Healthy Corvette'
p['ShipOwnership'][1] = copy.deepcopy(TEMPLATE['ship'])
p['ShipOwnership'][1]['Resource']['Filename'] = 'MODELS/COMMON/SPACECRAFT/SHUTTLE.SCENE.MBIN'
p['ShipOwnership'][1]['Name'] = 'Shuttle slot'
p['ShipOwnership'][2] = copy.deepcopy(TEMPLATE['ship']); p['ShipOwnership'][2]['Name'] = 'Missing Build Corvette'
bad = copy.deepcopy(TEMPLATE['base']); bad['UserData'] = 1; bad['Name'] = 'Van design'
bad['Objects'] = [o for o in bad['Objects'] if not o['ObjectID'].lstrip('^').startswith('B_COK_')]
p['PersistentPlayerBases'].append(bad)
freighter = copy.deepcopy(TEMPLATE['base']); freighter['BaseType']['PersistentBaseTypes'] = 'FreighterBase'
p['PersistentPlayerBases'].append(freighter)
for path in paths:
    save=files.SaveFile(path); save.json_data=core.translate(root, False); save.save()
cache=utils.extract_bases_list_from_save(paths)
package = module('save_editor.ship_package').from_save(core.translate(root, False), 'Main', 0)
(folder/'replacement.nmsship').write_bytes(package.source_bytes)
Manager.enum_accounts_list=[('Default','Select Account',''),('qa','QA account','')]
Manager.enum_save_slots_list=[('Default','Select Save Slot',''),('1','QA Save Slot','')]
Manager.data_save_slot=[dict(slot=1,saves=[str(p) for p in paths],save_name='QA')]
Manager.extracted_base_data=cache; Manager.save_data_loaded=True
data=bpy.context.scene.nms_save_data
data['nms_account_selected']=1; data['nms_save_slot']=1; data['check_plugin_enabled']=True
Manager.enum_base_list=data.get_bases_enum_list(cache)
data.nms_base_index='1'
bpy.context.preferences.addons['no_mans_sky_base_builder'].preferences.nms_save_folder_path=str(folder)
bpy.context.preferences.addons['no_mans_sky_base_builder'].preferences.nms_backup_folder_path=str(folder/'backups')
class QA_PT_corvette(bpy.types.Panel):
    bl_label='Corvette selector and repair preview'
    bl_space_type='VIEW_3D'; bl_region_type='WINDOW'
    bl_ui_units_x=26
    def draw(self, context):
        self.layout.operator_context = 'INVOKE_DEFAULT'
        io.draw_picker(self.layout.row(),context.scene.nms_save_data)
        io.draw_status(self.layout,context.scene.nms_save_data)
        self.layout.operator('bbe.corvette_export', text='Export Corvette to Save...')
        self.layout.operator('bbe.corvette_export', text='Optimize and Export...').optimized = True
bpy.utils.register_class(QA_PT_corvette)
# Isolate native review UI from model creation; these are synthetic preview parts.
actions.scene_parts = lambda context, optimized, progress: (
    copy.deepcopy(bad['Objects']), 'Van design', dict(before=7, after=7, moved=0, removed=0), 'preview')
def show():
    window=bpy.context.window
    area=next(a for a in window.screen.areas if a.type=='VIEW_3D')
    region=next(r for r in area.regions if r.type=='WINDOW')
    with bpy.context.temp_override(window=window,area=area,region=region):
        if os.environ.get('BBE_QA_EXPORT'):
            bpy.ops.bbe.corvette_export('INVOKE_DEFAULT')
        else:
            bpy.ops.wm.call_panel(name='QA_PT_corvette',keep_open=True)
    return None
bpy.app.timers.register(show,first_interval=4)
