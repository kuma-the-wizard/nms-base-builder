import bpy
from .. import builder
from ..part_overrides import line
from ..utils import blend_utils

from ..support_methods import ShowMessageBox, get_line_type_from_enum



BUILDER = builder.Builder()
# Logic Operators ---
class Point(bpy.types.Operator):
    """Create a new point controller used to create logic cables.\nSelect this twice to create a cables between 2 points."""

    bl_idname = "object.nms_point"
    bl_label = "New Point"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        # Get current selection.
        selection = blend_utils.get_current_selection()

        # Don't stack multiple for multiple clicks
        if selection and context.scene.cursor.location == selection.location:
            return {"CANCELLED"}

        # Create a new point at the cursor.
        point = line.Line.create_point(BUILDER, name="ARBITRARY_POINT")
        point.location = context.scene.cursor.location

        # If another powerline was already selected, connect it
        if selection and "rig_item" in selection:
            line_object = selection.get("power_line", "U_POWERLINE").split(".")[0]
            power_line = BUILDER.add_part(line_object, build_rigs=False)
            # Create controls.
            power_line.build_rig(start=selection, end=point)

        # Now select the new point.
        blend_utils.select(point)
        return {"FINISHED"}


class Connect(bpy.types.Operator):
    """Form a cable between 2 objects that have cable connections."""

    bl_idname = "object.nms_connect"
    bl_label = "Connect"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        # Validate selection.
        selected_objects = [
            BUILDER.get_builder_object_from_bpy_object(o)
            for o in bpy.context.selected_objects
        ]
        selected_objects = [o for o in selected_objects if o.has_snap_point("POWER")]
        if len(selected_objects) < 2:
            message = "Make sure you have two or more electric points selected."
            ShowMessageBox(message=message, title="Connect")
            return {"FINISHED"}

        # Test this after selection for better error reporting
        if not bpy.context.active_object:
            message = "Make sure one object is the active object (shift select the object to connect everything to)."
            ShowMessageBox(message=message, title="Connect")
            return {"FINISHED"}

        active_object = BUILDER.get_builder_object_from_bpy_object(
            bpy.context.active_object
        )
        if not active_object.has_snap_point("POWER"):
            message = "Make sure the active object supports electrical connections."
            ShowMessageBox(message=message, title="Connect")
            return {"FINISHED"}

        for selected_object in selected_objects:
            if selected_object is active_object:
                continue
            if selected_object.name == active_object.name:
                continue
            # Build and perform connection.
            start_point, end_point = line.Line.generate_control_points(
                active_object, selected_object, BUILDER
            )
            if not start_point or not end_point:
                # should have been tested by filtering selected_objects above
                continue

            # Re-obtain objects
            start_point = blend_utils.get_item_by_name(start_point.name)
            end_point = blend_utils.get_item_by_name(end_point.name)

            # Create new power line.
            line_object_id = get_line_type_from_enum(context)

            # if "power_line" in start_point:
            #     line_object_id = start_point["power_line"].split(".")[0]
            power_line = BUILDER.add_part(line_object_id, build_rigs=False)
            # Create controls.
            power_line.build_rig(start=start_point, end=end_point)

        return {"FINISHED"}


class Divide(bpy.types.Operator):
    """Divide a selected cable into 2 cables."""

    bl_idname = "object.nms_divide"
    bl_label = "Divide"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        # Get Selected item.
        target = blend_utils.get_current_selection()

        # Validate
        invalid_message = "Make sure you have a powerline item selected."
        title = "Divide"
        if not target:
            ShowMessageBox(message=invalid_message, title=title)
            return {"FINISHED"}
        if "ObjectID" not in target:
            ShowMessageBox(message=invalid_message, title=title)
            return {"FINISHED"}
        valid_parts = ["U_POWERLINE", "U_PIPELINE", "U_PORTALLINE", "U_BYTEBEATLINE"]
        if target["ObjectID"] not in valid_parts:
            ShowMessageBox(message=invalid_message, title=title)
            return {"FINISHED"}

        # Perform split.
        power_line = BUILDER.get_builder_object_from_bpy_object(target)
        power_line.divide()
        return {"FINISHED"}


class Split(bpy.types.Operator):
    """Divide a selected cable into 2 cables with a gap between them."""

    bl_idname = "object.nms_split"
    bl_label = "Split"

    def execute(self, context):
        # Get Selected item.
        target = blend_utils.get_current_selection()

        # Validate
        invalid_message = "Make sure you have a powerline item selected."
        title = "Split"
        if not target:
            ShowMessageBox(message=invalid_message, title=title)
            return {"FINISHED"}
        if "ObjectID" not in target:
            ShowMessageBox(message=invalid_message, title=title)
            return {"FINISHED"}
        valid_parts = ["U_POWERLINE", "U_PIPELINE", "U_PORTALLINE", "U_BYTEBEATLINE"]
        if target["ObjectID"] not in valid_parts:
            ShowMessageBox(message=invalid_message, title=title)
            return {"FINISHED"}

        # Perform split.
        power_line = BUILDER.get_builder_object_from_bpy_object(target)
        power_line.split()
        return {"FINISHED"}


class SelectConnected(bpy.types.Operator):
    """Select all objects that are connected to the selected cable."""

    bl_idname = "object.nms_select_connected"
    bl_label = "Select Connected"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        selected_objects = [
            BUILDER.get_builder_object_from_bpy_object(o)
            for o in bpy.context.selected_objects
        ]

        newly_selected = set()
        for o in selected_objects:
            newly_selected.update(o.get_connected_snapped_objects("POWER"))
        for o in newly_selected:
            o.object.select_set(True)
        return {"FINISHED"}


class SelectFloating(bpy.types.Operator):
    """Select free-floating cable points."""

    bl_idname = "object.nms_select_floating"
    bl_label = "Select Floating"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        for part in BUILDER.get_all_parts(include_lines=True):
            if not "SnapID" in part:
                continue
            part = BUILDER.get_builder_object_from_bpy_object(part)
            if part.snap_id != "POWER_CONTROL":
                continue
            is_connected_to_object = False
            num_line_connections = 0
            for target in part.get_connected_snapped_objects(
                "POWER", include_lines=False
            ):
                if not hasattr(target, "start_control"):
                    is_connected_to_object = True
                    break
                else:
                    num_line_connections += 1

            if not is_connected_to_object and num_line_connections < 2:
                part.object.select_set(True)

        return {"FINISHED"}


class LogicButton(bpy.types.Operator):
    """Add a Logic Button to the scene."""

    bl_idname = "object.nms_logic_button"
    bl_label = "BTN"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        # Build button.
        button = BUILDER.add_part("U_SWITCHBUTTON")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)

        # Select new item.
        button.select()
        return {"FINISHED"}


class LogicWallSwitch(bpy.types.Operator):
    """Add a Logic Switch to the scene."""

    bl_idname = "object.nms_logic_wall_switch"
    bl_label = "SWITCH"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        button = BUILDER.add_part("U_SWITCHWALL")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)
        # Select new item.
        button.select()
        return {"FINISHED"}


class LogicProxSwitch(bpy.types.Operator):
    """Add a Logic Proximity Sensor to the scene."""

    bl_idname = "object.nms_logic_prox_switch"
    bl_label = "PROX"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        button = BUILDER.add_part("U_SWITCHPROX")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)
        # Select new item.
        button.select()
        return {"FINISHED"}


class LogicInvSwitch(bpy.types.Operator):
    """Add a Logic Inverter to the scene."""

    bl_idname = "object.nms_logic_inv_switch"
    bl_label = "INV"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        button = BUILDER.add_part("U_TRANSISTOR1")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)
        # Select new item.
        button.select()
        return {"FINISHED"}


class LogicAutoSwitch(bpy.types.Operator):
    """Add a Logic Auto to the scene."""

    bl_idname = "object.nms_logic_auto_switch"
    bl_label = "AUTO"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        button = BUILDER.add_part("U_TRANSISTOR2")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)
        # Select new item.
        button.select()
        return {"FINISHED"}


class LogicFloorSwitch(bpy.types.Operator):
    """Add a Logic Floor Switch to the scene."""

    bl_idname = "object.nms_logic_floor_switch"
    bl_label = "FLOOR"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        button = BUILDER.add_part("U_SWITCHPRESS")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)
        # Select new item.
        button.select()
        return {"FINISHED"}


class LogicBeatSwitch(bpy.types.Operator):
    """Add a Logic ByteBeat switch to the scene."""

    bl_idname = "object.nms_logic_beat_switch"
    bl_label = "BEAT"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        button = BUILDER.add_part("BYTEBEATSWITCH")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)
        # Select new item.
        button.select()
        return {"FINISHED"}
    
    
classes = (
    LogicWallSwitch,
    LogicProxSwitch,
    LogicInvSwitch,
    LogicAutoSwitch,
    LogicFloorSwitch,
    LogicBeatSwitch,
    Point,
    Connect,
    Divide,
    Split,
    SelectConnected,
    SelectFloating,
    LogicButton
    
)