import bpy
from ..utils import blend_utils

class MirrorAcrossX(bpy.types.Operator):
    """Mirror the object along the X axis."""

    bl_idname = "object.nms_universal_mirror_x"
    bl_label = "Mirror Across X"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        nms_mirror_tool = scene.nms_mirror_tool
        nms_mirror_tool.mirror_across_axis("X")
        return {"FINISHED"}
    
    
class MirrorAcrossY(bpy.types.Operator):
    """Mirror the object along the X axis."""

    bl_idname = "object.nms_universal_mirror_y"
    bl_label = "Mirror Across Y"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        nms_mirror_tool = scene.nms_mirror_tool
        nms_mirror_tool.mirror_across_axis("Y")
        return {"FINISHED"}
    
class MirrorAcrossZ(bpy.types.Operator):
    """Mirror the object along the X axis."""

    bl_idname = "object.nms_universal_mirror_z"
    bl_label = "Mirror Across Z"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        nms_mirror_tool = scene.nms_mirror_tool
        nms_mirror_tool.mirror_across_axis("Z")
        return {"FINISHED"}
    

class PeformAdvancedMirrorButton(bpy.types.Operator):
    """Mirror the object along the X axis."""

    bl_idname = "object.nms_advanced_mirror"
    bl_label = "Perform Mirror"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        nms_mirror_tool = scene.nms_mirror_tool
        nms_mirror_tool.advanced_mirror()
        return {"FINISHED"}
    
class CleanupScene(bpy.types.Operator):
    """Mirror the object along the X axis."""

    bl_idname = "object.nms_cleanup_scene"
    bl_label = "Cleanup Scene"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        result = blend_utils.cleanup_scene()
        self.report({'INFO'}, f"Removed {result} duplicates")
        return {"FINISHED"}
    
    
classes = (
    MirrorAcrossX,
    MirrorAcrossY,
    MirrorAcrossZ,
    PeformAdvancedMirrorButton,
    CleanupScene
)