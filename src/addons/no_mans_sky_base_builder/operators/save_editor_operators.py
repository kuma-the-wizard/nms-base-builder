from ..save_editor.save_manager import NMSSaveManager
import bpy

class ExportObfuscatedObjectsData(bpy.types.Operator):
    bl_idname = "object.nms_export_obfuscated_nms_data_objects"
    bl_label = "Clipboard Obfuscated Object Data"

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.export_obfuscated_nms_data(objects_only=True)
        return {"FINISHED"}
    

class OpenSaveFile(bpy.types.Operator):
    bl_idname = "object.nms_open_save_file"
    bl_label = "choose .hg file to import"
    
    def execute(self, context):
        #print("Selected:", self.filepath)
        
        manager = NMSSaveManager()
        accounts = manager.get_all_saves()
        #for account in accounts:
        #    print(account)
        """print("ACCOUNT: {account['account_id']}")
        print("=" * 50)

        for save in account["saves"]:

            print(f"Slot: {save['slot']}")
            print(f"Name: {save['save_name']}")
            print(f"Mode: {save['game_mode']}")
            print(f"File: {save['filepath']}")
            print("-" * 30)"""
    
        
        return {"FINISHED"}
    
    
    
class SelectSaveFolder(bpy.types.Operator):
    bl_idname = "object.nms_select_save_folder"
    bl_label = "Select Folder"

    directory: bpy.props.StringProperty(
        subtype='DIR_PATH'
    )

    def execute(self, context):
        package_name = __package__.rsplit(".", 1)[0]
        prefs = context.preferences.addons[package_name].preferences
        save_file_identifier = "HelloGames\\NMS\\"

        print("folder is :", self.directory)
        if str(self.directory).lower().endswith(save_file_identifier.lower()):
            prefs.nms_save_folder_path = self.directory
            bpy.ops.wm.save_userpref()
            print("Selected folder is valid:", prefs.nms_save_folder_path)
        else :
            self.report({'ERROR'}, f"Selected folder does not a NMS save folder. Please select the correct folder.")
            print("Selected folder is invalid:", self.directory)
        
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    
class AccountsList(bpy.types.Operator):
    bl_idname = "object.nms_save_accounts_list"
    bl_label = "select account"

    directory: bpy.props.StringProperty(
        subtype='DIR_PATH'
    )

    def execute(self, context):
        package_name = __package__.rsplit(".", 1)[0]
        prefs = context.preferences.addons[package_name].preferences
        save_file_identifier = "HelloGames\\NMS\\"

        print("folder is :", self.directory)
        if str(self.directory).lower().endswith(save_file_identifier.lower()):
            prefs.nms_save_folder_path = self.directory
            bpy.ops.wm.save_userpref()
            print("Selected folder is valid:", prefs.nms_save_folder_path)
        else :
            self.report({'ERROR'}, f"Selected folder does not a NMS save folder. Please select the correct folder.")
            print("Selected folder is invalid:", self.directory)
        
        return {'FINISHED'}
    
class ImportBaseFromSave(bpy.types.Operator):
    bl_idname = "object.nms_import_base_from_save"
    bl_label = "Import data from selected file"

    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        save_data.imort_base_from_save_file(context)
        return {"FINISHED"}
    
class ExportBaseToSave(bpy.types.Operator):
    bl_idname = "object.nms_export_base_to_save"
    bl_label = "Export data to save file"

    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        save_data.export_base_to_save_file(context)
        return {"FINISHED"}
    
classes = (
    ExportObfuscatedObjectsData,
    OpenSaveFile,
    SelectSaveFolder,
    ImportBaseFromSave,
    ExportBaseToSave
)