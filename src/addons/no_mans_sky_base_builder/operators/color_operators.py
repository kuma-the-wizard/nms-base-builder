import bpy
from bpy.props import (
    IntProperty,
)

class ApplyColour(bpy.types.Operator):
    """Apply this colour to the selected part."""

    bl_idname = "object.nms_apply_colour"
    bl_label = "Apply Colour"
    bl_options = {"UNDO", "REGISTER"}
    colour_index: IntProperty(default=0)

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        material = nms_tool.material_switch
        nms_tool.apply_colour(colour_index=self.colour_index, material=material)
        return {"FINISHED"}


class ApplyDefaultColour(bpy.types.Operator):
    """Revert the colour back to default on selected part."""

    bl_idname = "object.nms_apply_default_colour"
    bl_label = "Apply Default Colour"
    bl_options = {"UNDO", "REGISTER"}
    colour_index: IntProperty(default=0)

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.apply_default_colour()
        return {"FINISHED"}
    
classes = (
    ApplyColour,
    ApplyDefaultColour
)