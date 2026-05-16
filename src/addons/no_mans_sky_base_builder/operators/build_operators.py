import os
import bpy
import subprocess

from .. import builder
from .. import preset
from ..utils import blend_utils

from bpy.props import ( StringProperty)

from ..support_methods import ShowMessageBox, refresh_ui_part_list

BUILDER = builder.Builder()
FILE_PATH = os.path.dirname(os.path.realpath(__file__))
USER_PATH = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")
PRESET_PATH = os.path.join(USER_PATH, "presets")
ASSET_BROWSER_PATH = os.path.join(FILE_PATH, "asset_browser")


class PresetsMenu(bpy.types.Menu):
    bl_idname = "OBJECT_MT_nms_get_more_presets_menu"
    bl_label = "Get More Presets..."

    def draw(self, context):
        layout = self.layout
        layout.operator("object.nms_visit_prefab_community")
        layout.operator("object.nms_visit_github")
        
class OpenPresetFolder(bpy.types.Operator):
    """Open the folder containing your presets."""

    bl_idname = "object.nms_open_preset_folder"
    bl_label = "Open Preset Folder"

    def execute(self, context):
        # Load web page.
        # FIXME: Mac OS
        if hasattr(os, "startfile"):
            # Windows
            os.startfile(PRESET_PATH)
        else:
            # Linux etc. (requires XDG tools)
            subprocess.call(["xdg-open", PRESET_PATH])
        return {"FINISHED"}
    
class GetMorePresets(bpy.types.Operator):
    """Load the No Man's Sky Presets web page to find more community presets."""

    bl_idname = "object.nms_get_more_presets"
    bl_label = "Get More Presets..."

    def execute(self, context):
        # Load web page.
        bpy.ops.wm.call_menu(name=PresetsMenu.bl_idname)
        return {"FINISHED"}
    
    
class SaveAsPreset(bpy.types.Operator):
    """Save the current scene contents as a new Preset"""

    bl_idname = "object.nms_save_as_preset"
    bl_label = "Save As Preset"
    preset_name: bpy.props.StringProperty(name="Preset Name")

    def execute(self, context):
        # Save Preset.
        BUILDER.save_preset_to_file(self.preset_name)
        # Refresh Preset List.
        scene = context.scene
        nms_tool = scene.nms_base_tool
        if nms_tool.enum_switch == {"PRESETS"}:
            refresh_ui_part_list(scene, "presets")
        # Reset string variable.
        self.preset_name = ""
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class LoadFancyUI(bpy.types.Operator):
    """Launch the standalone asset browser."""

    bl_idname = "object.nms_launch_asset_browser"
    bl_label = "Launch Asset Browser..."

    def execute(self, context):
        from ..asset_browser import check_dependencies

        valid = check_dependencies.check_dependencies()
        if not valid:
            ShowMessageBox(
                message="Could not load Asset Browser. See Window > Toggle System Console for detials.",
                title="Asset Browser",
            )
            return {"FINISHED"}
        from ..asset_browser import main as asset_browser_main

        asset_browser_main.load()
        return {"FINISHED"}
    
    
# List Operators ---
class ListBuildOperator(bpy.types.Operator):
    """Build the specified item."""

    bl_idname = "object.list_build_operator"
    bl_label = "Simple Object Operator"
    bl_options = {"UNDO", "REGISTER"}
    part_id: StringProperty()
    tooltip: StringProperty()

    @classmethod
    def description(cls, context, operator):
        return operator.tooltip

    def execute(self, context):
        # Get Selection
        selection = blend_utils.get_current_selection()

        # Build item
        if self.part_id in preset.Preset.get_presets():
            new_item = BUILDER.add_preset(self.part_id)
        else:
            new_item = BUILDER.add_part(self.part_id)
            if hasattr(new_item, "build_rig"):
                new_item.build_rig()

        # Make this item the selected.
        new_item.select()

        # If there was a previous selection, snap the new item to it.
        if selection:
            builder_selection = BUILDER.get_builder_object_from_bpy_object(selection)
            if builder_selection:
                new_item.snap_to(builder_selection)
        return {"FINISHED"}


class ListEditOperator(bpy.types.Operator):
    """Edit the specified preset."""

    bl_idname = "object.list_edit_operator"
    bl_label = "Edit Preset"
    bl_options = {"UNDO", "REGISTER"}
    part_id: StringProperty()

    def execute(self, context):
        nms_tool = context.scene.nms_base_tool
        if self.part_id in preset.Preset.get_presets():
            nms_tool.new_file()
            preset.Preset(
                preset_id=self.part_id,
                builder_object=BUILDER,
                create_control=False,
                apply_shader=False,
                build_rigs=True,
            )
            BUILDER.build_rigs()
            BUILDER.optimise_control_points()
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class ListDeleteOperator(bpy.types.Operator):
    """Delete the specified preset."""

    bl_idname = "object.list_delete_operator"
    bl_label = "Delete"
    part_id: StringProperty()

    def execute(self, context):
        scene = context.scene
        nms_tool = context.scene.nms_base_tool
        if self.part_id in preset.Preset.get_presets():
            preset.Preset.delete_preset(self.part_id)
            if nms_tool.enum_switch == {"PRESETS"}:
                refresh_ui_part_list(scene, "presets")
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
    
classes = (
    GetMorePresets,
    OpenPresetFolder,
    SaveAsPreset,
    LoadFancyUI,
    ListBuildOperator,
    ListEditOperator,
    ListDeleteOperator
)