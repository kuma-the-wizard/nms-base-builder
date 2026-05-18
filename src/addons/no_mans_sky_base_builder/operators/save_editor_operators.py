import bpy

import random


from ..save_editor import save_editor_dependencies
    
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
    
class LoadBases(bpy.types.Operator):
    bl_idname = "object.nms_load_bases_from_save_slot"
    bl_label = "Load"

    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        save_data.load_base_data()
        return {"FINISHED"}
    
class EnableSaveEditor(bpy.types.Operator):
    
    bl_idname = "object.nms_enable_save_editor"
    bl_label = "Enable Save Editor"
    
    def execute(self, context):
        save_editor_dependencies.installDependencies()
        return {"FINISHED"}
    

    
classes = (
    SelectSaveFolder,
    ImportBaseFromSave,
    ExportBaseToSave,
    EnableSaveEditor,
    LoadBases
)