import bpy
from bpy.types import Panel

from .. import icons
from .save_editor_utils import BaseType
from .save_manager import SaveManager

ADDON_ID = __package__.rsplit(".", 1)[0]

# Save Editor Panel ---
class NMS_PT_save_editor_panel(Panel):
    bl_idname = "NMS_PT_save_editor_panel"
    bl_label = "💾 Save Manager"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky Base Builder"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        save_data = context.scene.nms_save_data
        nms_tool = context.scene.nms_base_tool
        prefs = context.preferences.addons[ADDON_ID].preferences
        save_folder_path = prefs.nms_save_folder_path
        
        
        #display data related to a pinned base on top if there is any withing a blend file
        #if save_data.pinned_base_check:
        #    pinned_base_type  = save_data.get_base_type_string(save_data.pinned_base_type)
        #    pinned_box = layout.box()
        #    pinned_row = pinned_box.row(align = True)
        #    pinned_title_col = pinned_row.column(align = True)
        #    pinned_main_col = pinned_row.column(align = True)
        #    
        #    try:
        #        slot_data = save_data.pinned_save_slot_name.split(": ")
        #        slot_number = slot_data[0]
        #        slot_name = slot_data[1]
        #    except Exception:
        #        slot_number = "slot"
        #        slot_name = "unknown"
        #    
        #    pinned_title_col.scale_x = 0.2
        #    pinned_title_col.label(text = "", icon = "PINNED")
        #    pinned_title_col.separator()
        #    pinned_title_condensed_col = pinned_title_col.column(align = True)
        #    pinned_title_condensed_col.scale_y = 0.7
        #    pinned_title_condensed_col.label(text = "Name")
        #    pinned_title_condensed_col.label(text = f"{slot_number}")
        #    
        #    pinned_content_col = pinned_main_col.column(align = True)
        #    pinned_content_row = pinned_content_col.row(align = True)
        #    pinned_text_col = pinned_content_row.column(align = True)
        #    pinned_buttons_col = pinned_content_row.column(align = True)
        #    
        #    pinned_text_col.label(text = f"Pinned {pinned_base_type}")
        #    pinned_text_col.separator()
        #    pinned_text_condensed_column = pinned_text_col.column(align = True)
        #    pinned_text_condensed_column.scale_y = 0.7
        #    pinned_text_condensed_column.label(text = f"{nms_tool.string_base}")
        #    pinned_text_condensed_column.label(text = f"{slot_name}, (...{save_data.pinned_save_account[-3:]})")
        #    
        #    pinned_buttons_col.scale_x = 0.78
        #    pinned_buttons_col.operator("object.nms_unpin_base", icon="UNPINNED", text = f"Unpin {pinned_base_type}")
        #    pinned_buttons_col.operator("object.import_pinned_base", icon="IMPORT", text = "Import from Save")
        #    #pinned_buttons_col.prop(save_data,"check_also_update_name")
            
            
        #    #pinned_text_col.prop(save_data,"check_also_update_name")
        #    #pinned_text_col.separator()
        #    pinned_export_button_row = pinned_box.row(align = False)
        #    pinned_export_button_row.operator("object.export_pinned_base", icon="FILE_TICK", text = "Export to Save")
        #    pinned_export_button_backup_row = pinned_export_button_row.row(align = True)
        #    pinned_export_button_backup_row.scale_x = 0.7
        #    pinned_export_button_backup_row.operator("object.make_pinned_savefile_backup",  icon = "COLLECTION_NEW", text = "Backup Save files")
            
            
        #make a seprate section to display elements related to selecting bases
        save_folder_box = layout.box()
        sf_column = save_folder_box.column(align=True)
        sf_enable_row = sf_column.row(align = True)
        sf_enable_row.label(text = "Select Save")
        
        #this row will contain a field where location of save folder is displayed
        if save_data.check_plugin_enabled and save_data.validate_save_folder(save_folder_path):
            #button to choose path to save folder
            sf_enable_row.operator( "object.nms_select_save_folder", text="", icon='FILE_FOLDER')
        
        # A button to enable save editor, this will also install additional dependencies required when pressed
        sf_enable_row.separator()
        sf_enable_button_row = sf_enable_row.row(align = True)
        sf_enable_button_row.scale_x = 0.7 if not save_data.check_plugin_enabled else 1.0
        sf_enable_icon = "TRIA_DOWN" if not save_data.check_plugin_enabled else "TRIA_UP"
        sf_enable_text = "Enable"  if not save_data.check_plugin_enabled else ""
        sf_enable_button_row.prop(save_data,"check_plugin_enabled",  icon = sf_enable_icon, text = sf_enable_text)
        
         # Select Save
        if save_data.check_plugin_enabled:
            if not save_data.validate_save_folder(save_folder_path):
                sf_column.separator()
                select_folder_info_col = sf_column.column(align = True)
                select_folder_info_col.scale_y = 0.8
                select_folder_info_col.label(text = " Save Folder should end with")
                select_folder_info_col.label(text = r' path like : "...\HelloGames\NMS"')
                sf_column.separator()
                select_folder_button_col = sf_column.column(align = True)
                select_folder_button_col.alert = True
                select_folder_button_col.operator( "object.nms_select_save_folder", text="Select Save Folder", icon='FILE_FOLDER')
            else:
                is_base_data_loaded = save_data.is_base_data_loaded()
                sf_column.separator()
                #display list of accounts, will display steam ids for recognition
                sf_column.label(text = "Account / Save Slot")
                sf_column.prop(save_data, "nms_account_selected", icon = "COMMUNITY")#USER
                #display save slots present within an account
                sf_column.prop(save_data, "nms_save_slot", icon = "LINENUMBERS_ON") #linenumbers_on SORTSIZE

                #Section where bases can be selected to import/update/pin
                #this section will only be visible when base list has been loaded
                if is_base_data_loaded:
                    #display backup buttons when a slot is selected
                    base_type = save_data.get_base_type_string(save_data.nms_base_type)
                    backup_row = sf_column.row(align = True)
                    backup_row.operator("object.make_savefile_backup", icon="COLLECTION_NEW", text = "Backup Saves")
                    backup_row.operator("object.open_backup_folder", icon="FOLDER_REDIRECT", text = "Open Backup Folder")
                    
                    sf_column.separator()
                    sf_column.label(text = f"📦 Total Parts : {save_data.get_total_parts_count()}")
                    se_column = sf_column.column(align = True)
                    se_column.label(text = "Base Type:")# icon = "MOD_BUILD"
                    #radio buttons to select type of base
                    base_type_row = se_column.row(align=True)
                    base_type_row.prop(save_data, "nms_base_type",expand=True, text = "base type")
                    se_column.separator()
                    
                    #list of bases/corvettes
                    se_column.label(text = f"{base_type} Selected:")# icon = "ASSET_MANAGER"
                    
                    #show base list in red when on base/corvette is selected
                    base_index_row = se_column.row(align = True)
                    if not SaveManager.is_base_selected:
                        base_index_row.alert = True
                    else: 
                        base_index_row.alert = False
                        
                    if SaveManager.is_base_selected:
                        
                        #list of bases for selection
                        base_index_row.prop(save_data, "nms_base_index", text="")
                        
                        #display buttons when a base is selected from list
                        if save_data.nms_base_type != BaseType.EXTERNAL_BASE:
                            # show pin button and a base/corvette is selected
                            base_index_pin_row = base_index_row.row(align=True)
                            base_index_pin_row.scale_x = 0.6
                            #Pin button, pin a base without imorting it to scene, so that save data can be updated to location marked by it
                            base_index_pin_row.operator("object.nms_pin_base", icon="PINNED", text = " Pin for easy-access")
                        
                        se_column.separator()
                        import_export_row = se_column.row(align=True)
                        #Import button, this button will import base to scene
                        import_export_row.operator("object.nms_import_base_from_save", icon="IMPORT", text = "Import from Save")
                        
                        if save_data.nms_base_type != BaseType.EXTERNAL_BASE:
                            import_export_row.operator("object.nms_export_base_to_save", icon="EXPORT", text = "Export to Save")
                            
                    else :
                        #list of bases for selection
                        base_index_row.prop(save_data, "nms_base_index", text="", icon = "GEOMETRY_SET")
