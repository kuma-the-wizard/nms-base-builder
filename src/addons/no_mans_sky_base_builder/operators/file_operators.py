import bpy



# File Operators ---
class NewFile(bpy.types.Operator):
    bl_idname = "object.nms_new_file"
    bl_label = "New Base..."
    bl_options = {"REGISTER", "INTERNAL", "UNDO", "UNDO_GROUPED"}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.new_file()
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class SaveData(bpy.types.Operator):
    bl_idname = "object.nms_save_data"
    bl_label = "Save Base As..."
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.save_nms_data(self.filepath)
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class LoadData(bpy.types.Operator):
    bl_idname = "object.nms_load_data"
    bl_label = "Open Base..."
    bl_options = {"UNDO", "REGISTER"}
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.load_nms_data(self.filepath)
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class ImportData(bpy.types.Operator):
    bl_idname = "object.nms_import_nms_data"
    bl_label = "Import from Clipboard"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.import_nms_data()
        return {"FINISHED"}


class ExportData(bpy.types.Operator):
    bl_idname = "object.nms_export_nms_data"
    bl_label = "Export to Clipboard"

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.export_nms_data()
        return {"FINISHED"}


class ExportObjectsData(bpy.types.Operator):
    bl_idname = "object.nms_export_nms_data_objects"
    bl_label = "Export to Clipboard (Objects Only)"

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.export_nms_data(objects_only=True)
        return {"FINISHED"}
    
    
    
classes = (
    NewFile,
    SaveData,
    LoadData,
    ImportData,
    ExportData,
    ExportObjectsData
)