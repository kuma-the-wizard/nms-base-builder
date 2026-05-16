import bpy

from bpy.props import ( BoolProperty )

# Tool Operators ---
class ToggleRoom(bpy.types.Operator):
    bl_idname = "object.nms_toggle_room_visibility"
    bl_label = "Toggle Room Visibility: Normal"
    bl_options = {
        "UNDO",
        "REGISTER",
    }  # I think this must pass "UNDO" because it changes objects, but it probably doesn't interact correctly with the plugin?

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.toggle_room_visibility()
        return {"FINISHED"}

class Duplicate(bpy.types.Operator):
    """Duplicate the selected part."""

    bl_idname = "object.nms_duplicate"
    bl_label = "Duplicate"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.duplicate()
        return {"FINISHED"}


class Delete(bpy.types.Operator):
    """Remove the selected part from the scene."""

    bl_idname = "object.nms_delete"
    bl_label = "Delete"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.delete()
        return {"FINISHED"}


class DuplicateAlongCurve(bpy.types.Operator):
    """Duplicate the selected part along a Blender curve."""

    bl_idname = "object.nms_duplicate_along_curve"
    bl_label = "Duplicate Along Curve"
    bl_options = {"UNDO", "REGISTER"}
    distance_percentage: bpy.props.FloatProperty(
        name="Distance Percentage Between Item."
    )

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.duplicate_along_curve(distance_percentage=self.distance_percentage)
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class Mirror(bpy.types.Operator):
    """Mirror the object local to itself."""

    bl_idname = "object.nms_mirror"
    bl_label = "Mirror"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.mirror()
        return {"FINISHED"}


class MirrorAcrossX(bpy.types.Operator):
    """Mirror the object along the X axis."""

    bl_idname = "object.nms_mirror_across_x"
    bl_label = "Mirror Across X Axis"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.mirror(across_x=True)
        return {"FINISHED"}


class Flip(bpy.types.Operator):
    """Flip the object along the Y axis (Only available on certain Corvette pieces)"""

    bl_idname = "object.nms_flip"
    bl_label = "Flip"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.flip()
        return {"FINISHED"}


class Snap(bpy.types.Operator):
    """Snap the selected object to another selected object."""

    bl_idname = "object.nms_snap"
    bl_label = "Snap"
    bl_options = {"UNDO", "REGISTER"}

    next_source: BoolProperty()
    prev_source: BoolProperty()
    next_target: BoolProperty()
    prev_target: BoolProperty()

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        kwargs = {
            "next_source": self.next_source,
            "prev_source": self.prev_source,
            "next_target": self.next_target,
            "prev_target": self.prev_target,
        }
        nms_tool.snap(**kwargs)
        return {"FINISHED"}
    
    
classes = (
    ToggleRoom,
    Duplicate,
    Delete,
    DuplicateAlongCurve,
    Mirror,
    MirrorAcrossX,
    Flip,
    Snap
)