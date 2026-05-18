import bpy
import json
from . import save_editor_utils

from .. import builder
from ..support_methods import ShowMessageBox

from . import save_editor_dependencies

BUILDER = builder.Builder()

#save data to persist within blend files.
class SaveData(bpy.types.PropertyGroup):
    
    enum_accounts_list = []
    
    #this will populate the enum property yo display list
    enum_save_slots_list = []
    #this stores data related to save slot like paths etd
    data_save_slot = []
    
    #this stores data for displaying list
    enum_base_list = []
    #this is cache for PersistentPlayerBases data
    data_persistent_base = {}
    
    save_data_loaded = False
    
    check_plugin_enabled: bpy.props.BoolProperty(
        name="Enable save editor",
        description="Enable/disbale Plugin",
        default=False,
        options={'SKIP_SAVE'},
        update = lambda self, context: self.on_check_plugin_enabled()
    )

    # there can be miltiple accounts on same device
    nms_account_selected: bpy.props.EnumProperty(
        name="",
        description="account from which save file will be loaded",
        items = lambda self, context: self.get_accounts_list(),
        update = lambda self, context: self.on_account_list_change(),
        options={'SKIP_SAVE'},
    )
    
    #save slot for that account
    nms_save_slot: bpy.props.EnumProperty(
        name="",
        description="Folder where save files are stored",
        items = lambda self, context: SaveData.enum_save_slots_list,
        update = lambda self, context: self.on_save_slot_list_change(),
        options={'SKIP_SAVE'}
    )
    
    # Index of base imorted, this is index of base inside PersistentPlayerBase array
    nms_base_index : bpy.props.EnumProperty(
        name="base index",
        description="Index of the base in the save file.",
        items = lambda self, context: SaveData.enum_base_list,
        options={'SKIP_SAVE'}
    )
    
    # base can be a corvette or a normal base
    nms_base_type: bpy.props.EnumProperty(
        name="base type",
        description="Type of the base.",
        items = [
            ("PlayerShipBase", "Corvette", "show list of corvettes and freighters"),
            ("HomePlanetBase", "Base", "show list of bases"),
        ],
        update = lambda self, context: self.on_base_type_selected(),
        options={'SKIP_SAVE'}
    )
    
    def on_check_plugin_enabled(self):
        save_editor_dependencies.installDependencies()
        self.nms_account_selected = "Select Account"

    def on_account_list_change(self):
        SaveData.enum_save_slots_list = self.get_save_slots_list()
        self.reset_save_slot()
        self.reset_base_list()
        
    def is_save_folder_correct(self,context):
        save_path = context.scene.nms_save_folder_path
        return str(save_path).endswith("/HelloGames/NMS")
    
    def get_accounts_list(self):
        default_account_list_item = ("Select Account", "Select Account", "No account selected")
        accounts_list = save_editor_utils.get_accounts_list()
        accounts_enum_list = [(str(account), account.name, "") for account in accounts_list]
        accounts_enum_list.insert(0, default_account_list_item)
        #self.nms_account_selected = "Select Account"
        return accounts_enum_list
    
    def on_save_slot_list_change(self):
        SaveData.save_data_loaded = False
        self.reset_base_list()
        
    def load_base_data(self):
        self.reset_base_list()
        current_slot_data = self.get_current_slot_data()
        if current_slot_data is not None:
            SaveData.data_persistent_base = save_editor_utils.get_persistent_player_bases(current_slot_data)
            SaveData.enum_base_list = self.get_bases_list()
            SaveData.save_data_loaded = True
            
    
    def get_save_slots_list(self):
        default_save_slot_list_item = ("Select Save Slot", "Select Save Slot", "No save slot selected")
        account_selected = self.nms_account_selected
        if not account_selected == "Select Account":
            print("account selected", account_selected)
            save_slots = save_editor_utils.get_save_slots_list(account_selected)
            SaveData.data_save_slot = save_slots
            enum_save_slots_list = []
            for slot in save_slots:
                save_name = slot["save_name"] 
                slot_list_name = "Slot "+str(slot["slot"])
                if save_name is not None:
                    slot_list_name += " : "+save_name
                slot_element = (str(slot["slot"]), slot_list_name, "save slot for importing base/corvette")
                enum_save_slots_list.append(slot_element)
            enum_save_slots_list.insert(0, default_save_slot_list_item)
            return enum_save_slots_list
        return default_save_slot_list_item
    
    def on_base_type_selected(self):
        if len(SaveData.enum_base_list) > 0:
            if len(SaveData.enum_base_list[0][0]) > 0:
                self.nms_base_index = SaveData.enum_base_list[0][0]
        if not self.nms_save_slot == "Select Save Slot":
            SaveData.enum_base_list = self.get_bases_list()
            

    def get_bases_list(self):
        default_base_list_item = (
            "Select Corvette" if self.nms_base_type == "PlayerShipBase" else "Select Base", 
            "Select Corvette" if self.nms_base_type == "PlayerShipBase" else "Select Base", 
            "No base selected"
        )
        
        key_base_type = save_editor_utils.eng_to_obf_translator("BaseType")
        key_persistent_base_types = save_editor_utils.eng_to_obf_translator("PersistentBaseTypes")
        key_name = save_editor_utils.eng_to_obf_translator("Name")
        key_userdata = save_editor_utils.eng_to_obf_translator("UserData")
        
        ud_enum_base_list = []
        for index, base in enumerate(SaveData.data_persistent_base):
            if(base[key_base_type][key_persistent_base_types] == self.nms_base_type):
                base_name = str(base[key_name])
                base_username = base[key_userdata]
                item_tuple = (str(index), base_name , base_username)
                ud_enum_base_list.append(item_tuple)
        
        if self.nms_base_type == "PlayerShipBase":
            ud_enum_base_list.sort(key=lambda x: x[2])
        
        enum_base_list = []
        for base in ud_enum_base_list:
            if self.nms_base_type == "PlayerShipBase":
                list_entry = f"{str(base[2]).rjust(2)}. {base[1]}"
            else :
                list_entry = base[1]
            entry_tuple = (base[0],list_entry,"")
            enum_base_list.append(entry_tuple)
        enum_base_list.insert(0, default_base_list_item)
        return enum_base_list
    
    def imort_base_from_save_file(self,context):
        base_index = self.nms_base_index
        
        if not str(base_index).isdigit():
            return 
        
        if int(base_index) < 0:
            return
        
        current_slot_data = self.get_current_slot_data()
        if current_slot_data is None:
            return
        
        base_identifiers = self.get_current_bae_identifiers()
        if base_identifiers is None:
            return
        
        newly_imported_base = save_editor_utils.import_paticular_base_from_save(base_identifiers, current_slot_data)
        if newly_imported_base is None:
            return
        
        translated_base_data = save_editor_utils.translate_to_eng_data(newly_imported_base)
        
        try:
            nms_import_data = json.dumps(translated_base_data)
            nms_base_json = json.loads(nms_import_data)
        except:
            message = ("Could not import base data" )
            ShowMessageBox(message=message, title="Import")
            return

        nms_tools = context.scene.nms_base_tool
        nms_tools.deserialise_from_data(nms_base_json)
        BUILDER.deserialise_from_data(nms_base_json)
        
    def export_base_to_save_file(self,context):
        nms_tools = context.scene.nms_base_tool
        serialised_base_objects_data  = nms_tools.serialise(objects_only = True)
        
        check_export_name = context.scene.nms_check_export_name
        base_name_from_fields = nms_tools.string_base if check_export_name else None
        
        new_enum_list = []
        for e_base in SaveData.enum_base_list:
            mid_val = e_base[1]
            if e_base[0] == self.nms_base_index:
                if self.nms_base_type == "PlayerShipBase":
                    mid_val = mid_val[:4] + base_name_from_fields
                else :
                    mid_val = base_name_from_fields
            new_enum_list.append((e_base[0],mid_val,e_base[2]))
        SaveData.enum_base_list = new_enum_list
                
        
        current_slot_data = self.get_current_slot_data()
    
        if current_slot_data is None:
            return
        
        base_identifiers = self.get_current_bae_identifiers()
        if base_identifiers is None:
            return
        
        save_editor_utils.save_base_to_save_file(serialised_base_objects_data, base_identifiers, current_slot_data, base_name_from_fields)
        
    def get_current_bae_identifiers(self):
        
        base_index = self.nms_base_index
        
        if not str(base_index).isdigit():
            return None
        
        if int(base_index) < 0:
            return None
        
        key_name = save_editor_utils.eng_to_obf_translator("Name")
        key_galactic_address = save_editor_utils.eng_to_obf_translator("GalacticAddress")
    
        base_type = self.nms_base_type
        base = SaveData.data_persistent_base[int(base_index)]
        base_name = base[key_name]
        base_galactic_address = base[key_galactic_address]
        
        base_identifiers = {
            "base_index": int(base_index),
            "base_name" : base_name,
            "base_type" : base_type,
            "galactic_address" : base_galactic_address
        }
        
        return base_identifiers
        
    def is_base_data_loaded(self):
        return len(SaveData.enum_base_list) > 0 and SaveData.save_data_loaded
        
    def get_current_slot_data(self):
        if not self.nms_save_slot == "Select Save Slot":
            for slot in SaveData.data_save_slot:
                if str(slot["slot"]) == self.nms_save_slot:
                    return slot
        return None
    
    def reset_save_slot(self):
        SaveData.save_data_loaded = False
        if SaveData.enum_save_slots_list is not None:
            if len(SaveData.enum_save_slots_list) > 0:
                if len(SaveData.enum_save_slots_list[0][0]) > 0:
                    try:
                        self.nms_save_slot = SaveData.enum_save_slots_list[0][0]
                    except:
                        SaveData.enum_save_slots_list = []

    def reset_base_list(self):
        SaveData.data_persistent_base = {}
        SaveData.enum_base_list = [("","","")]
        if len(SaveData.enum_base_list) > 0:
            if len(SaveData.enum_base_list[0][0]) > 0:
                self.nms_base_index = SaveData.enum_base_list[0][0]
        