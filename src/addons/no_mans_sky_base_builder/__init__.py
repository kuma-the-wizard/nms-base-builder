import json
import os
import subprocess
import sys
import webbrowser

# Add it to the system path if it isn't already there
addon_dir = os.path.dirname(__file__)
libs_dir = os.path.join(addon_dir, "lib")
if libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)

import bpy
import bpy.ops
import bpy.utils
import bpy.utils.previews
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Panel, PropertyGroup
from numpy import isin

from . import builder, part, preset
from .part_overrides import line
from .utils import blend_utils, curve
from .utils import material as _material
from .utils import python as python_utils
from .utils import mirror_utils
from .save_editor import conversion_utils, save_editor_utils

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
USER_PATH = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")
PRESET_PATH = os.path.join(USER_PATH, "presets")
ASSET_BROWSER_PATH = os.path.join(FILE_PATH, "asset_browser")

BUILDER = builder.Builder()
GHOSTED_JSON = os.path.join(FILE_PATH, "resources", "ghosted.json")
ghosted_reference = python_utils.load_dictionary(GHOSTED_JSON)
GHOSTED_ITEMS = ghosted_reference["GHOSTED"]
NICE_JSON = os.path.join(FILE_PATH, "resources", "nice_names.json")
nice_name_dictionary = python_utils.load_dictionary(NICE_JSON)

from .operators.save_editor_operators import ExportObfuscatedObjectsData, OpenSaveFile
from .addon_state import preview_collections
from .support_methods import ShowMessageBox, part_switch


# Core Settings Class
class NMSSettings(PropertyGroup):
    # Build Array of base part types. (Vanilla Parts - Mods - Presets)
    enum_items = []
    for pack, _ in BUILDER.available_packs:
        enum_items.append((pack, pack, "View {0}...".format(pack)))
    enum_items.append(("PRESETS", "Presets", "View Presets..."))

    # Blender Properties.
    enum_switch: EnumProperty(
        name="enum_switch",
        description="Toggle to display between parts and presets.",
        items=enum_items,
        options={"ENUM_FLAG"},
        default=None,
        update=part_switch,
    )

    material_switch: EnumProperty(
        name="Material Palette",
        description="Decide what type of material to apply",
        items=_material.BAKED_PALETTES_UI,
    )

    line_switch: EnumProperty(
        name="line_switch",
        description="Decide what type of cable to build",
        items=[
            ("POWER", "Electrical Wire", "Electrical Wire"),
            ("TELEPORT", "Teleport Wire", "Teleport Wire"),
            ("BYTEBEAT", "Byte-Beat Cable", "Byte-Beat Cable"),
            ("PIPE", "Pipe", "Pipe"),
        ],
        options={"ENUM_FLAG"},
        default={"POWER"},
    )

    preset_name: StringProperty(
        name="preset_name", description="The of a preset.", default="", maxlen=1024
    )

    string_base: StringProperty(
        name="Base Name",
        description="The name of the base set in game.",
        default="",
        maxlen=1024,
    )

    string_address: StringProperty(
        name="Galactic Address",
        description="The galactic address.",
        default="",
        maxlen=1024,
    )

    string_userdata: StringProperty(
        name="User Data",
        description="User Data - important for corvette bases.",
        default="",
        maxlen=1024,
    )

    string_base_type: StringProperty(
        name="The base type",
        description="Planet or Freighter.",
        default="HomePlanetBase",
        maxlen=1024,
    )

    string_usn: StringProperty(
        name="USN", description="The username attribute.", default="", maxlen=1024
    )

    string_uid: StringProperty(
        name="UID", description="A user ID.", default="", maxlen=1024
    )

    string_lid: StringProperty(
        name="LID", description="Not sure what this is.", default="", maxlen=1024
    )

    string_ptk: StringProperty(
        name="PTK", description="Not sure what this is.", default="", maxlen=1024
    )

    string_ts: StringProperty(
        name="TS",
        description="Timestamp.",
        default="",
        maxlen=1024,
    )

    string_last_ts: StringProperty(
        name="LastUpdatedTimestamp",
        description="Timestamp - last updated timestamp.",
        default="",
        maxlen=1024,
    )

    float_pos_x: FloatProperty(
        name="X", description="The X position of the base in planet space.", default=0.0
    )

    float_pos_y: FloatProperty(
        name="Y", description="The Y position of the base in planet space.", default=0.0
    )

    float_pos_z: FloatProperty(
        name="Z", description="The Z position of the base in planet space.", default=0.0
    )

    float_ori_x: FloatProperty(
        name="X",
        description="The X orientation vector of the base in planet space.",
        default=0.0,
    )

    float_ori_y: FloatProperty(
        name="Y",
        description="The Y orientation vector of the base in planet space.",
        default=0.0,
    )

    float_ori_z: FloatProperty(
        name="Z",
        description="The Z orientation vector of the base in planet space.",
        default=0.0,
    )

    # Unimportant details...
    LastEditedById: StringProperty(
        name="LastEditedByID",
        description="LastEditedByID.",
        default="",
        maxlen=1024,
    )
    LastEditedByUsername_value: StringProperty(
        name="LastEditedByUsername",
        description="LastEditedByUsername.",
        default="",
        maxlen=1024,
    )
    original_base_version: IntProperty(
        name="OriginalBaseVersion", description="OriginalBaseVersion.", default=3
    )

    screenshot_at_x: FloatProperty(
        name="SAX",
        description="The X orientation vector of the screenshot.",
        default=1.0,
    )

    screenshot_at_y: FloatProperty(
        name="SAY",
        description="The Y orientation vector of the screenshot.",
        default=0.0,
    )

    screenshot_at_z: FloatProperty(
        name="SAZ",
        description="The Z orientation vector of the screenshot.",
        default=0.0,
    )

    screenshot_pos_x: FloatProperty(
        name="SPX",
        description="The X pos vector of the screenshot.",
        default=1.0,
    )

    screenshot_pos_y: FloatProperty(
        name="SPY",
        description="The Y pos vector of the screenshot.",
        default=1.0,
    )

    screenshot_pos_z: FloatProperty(
        name="SUZ",
        description="The Z pos vector of the screenshot.",
        default=0.0,
    )

    game_mode: StringProperty(
        name="GameMode", description="GameMode.", default="Unspecified"
    )

    platform_token: StringProperty(
        name="PlatformToken", description="PlatformToken.", default=""
    )

    is_reported: BoolProperty(
        name="IsReported", description="Is Reported.", default=False
    )

    is_featured: BoolProperty(
        name="IsFeatured", description="Is Featured.", default=False
    )

    difficulty_flags: IntProperty(
        name="DifficultyFlags", description="DifficultyFlags.", default=0
    )

    difficulty_preset: StringProperty(
        name="DifficultyPresetType",
        description="DifficultyPresetType.",
        default="Creative",
    )

    auto_power_setting: StringProperty(
        name="AutoPowerSetting", description="AutoPowerSetting.", default="UseDefault"
    )

    room_vis_switch: IntProperty(name="room_vis_switch", default=0)

    def deserialise_from_data(self, nms_data):
        # Start new file
        self.new_file()

        # Start bringing the data in.
        if "GalacticAddress" in nms_data:
            self.string_address = str(nms_data["GalacticAddress"])
        if "UserData" in nms_data:
            self.string_userdata = str(nms_data["UserData"])
        if "BaseType" in nms_data:
            self.string_base_type = str(nms_data["BaseType"]["PersistentBaseTypes"])
        if "Position" in nms_data:
            self.float_pos_x = nms_data["Position"][0]
            self.float_pos_y = nms_data["Position"][1]
            self.float_pos_z = nms_data["Position"][2]
        if "Forward" in nms_data:
            self.float_ori_x = nms_data["Forward"][0]
            self.float_ori_y = nms_data["Forward"][1]
            self.float_ori_z = nms_data["Forward"][2]
        if "Name" in nms_data:
            self.string_base = str(nms_data["Name"])
        if "LastUpdateTimestamp" in nms_data:
            self.string_last_ts = str(nms_data["LastUpdateTimestamp"])
        if "Owner" in nms_data:
            Owner_details = nms_data["Owner"]
            self.string_uid = str(Owner_details.get("UID", ""))
            self.string_ts = str(Owner_details.get("TS", ""))
            self.string_lid = str(Owner_details.get("LID", ""))
            self.string_usn = str(Owner_details.get("USN"))
            self.string_ptk = str(Owner_details.get("PTK"))
        # Extras/Unimportant
        if "LastEditedById" in nms_data:
            self.LastEditedById = str(nms_data["LastEditedById"])
        if "LastEditedByUsername" in nms_data:
            self.LastEditedByUsername_value = str(nms_data["LastEditedByUsername"])
        if "OriginalBaseVersion" in nms_data:
            self.original_base_version = nms_data["OriginalBaseVersion"]
        if "ScreenshotAt" in nms_data:
            self.screenshot_at_x = nms_data["ScreenshotAt"][0]
            self.screenshot_at_y = nms_data["ScreenshotAt"][1]
            self.screenshot_at_z = nms_data["ScreenshotAt"][2]
        if "ScreenshotPos" in nms_data:
            self.screenshot_pos_x = nms_data["ScreenshotPos"][0]
            self.screenshot_pos_y = nms_data["ScreenshotPos"][1]
            self.screenshot_pos_z = nms_data["ScreenshotPos"][2]
        if "GameMode" in nms_data:
            self.game_mode = nms_data["GameMode"]["PresetGameMode"]
        if "PlatformToken" in nms_data:
            self.platform_token = nms_data["PlatformToken"]
        if "IsReported" in nms_data:
            self.is_reported = nms_data["IsReported"]
        if "IsFeatured" in nms_data:
            self.is_featured = nms_data["IsFeatured"]
        if "AutoPowerSetting" in nms_data:
            auto_power_container = nms_data.get("AutoPowerSetting", {})
            self.auto_power_setting = auto_power_container.get(
                "BaseAutoPowerSetting", "UseDefault"
            )
        if "Difficulty" in nms_data:
            difficulty_container = nms_data.get("Difficulty", {})
            sub_difficulty_container = difficulty_container.get("DifficultyPreset")
            self.difficulty_preset = sub_difficulty_container.get(
                "DifficultyPresetType", "Creative"
            )
            self.difficulty_flags = difficulty_container.get(
                "PersistentBaseDifficultyFlags", 0
            )

    def serialise(self, get_presets=False, objects_only=False):
        """Export the data in the blender scene to NMS compatible data.

        This will slot the data into the clip-board so you can easy copy
        and paste data back and forth between the tool.
        """
        # Try making the address an int, if not it should be a string.
        data = {
            "BaseVersion": 5,
            "OriginalBaseVersion": self.original_base_version,
            "GalacticAddress": python_utils.prefer_int(self.string_address),
            "Position": [self.float_pos_x, self.float_pos_y, self.float_pos_z],
            "Forward": [self.float_ori_x, self.float_ori_y, self.float_ori_z],
            "UserData": python_utils.prefer_int(self.string_userdata),
            "LastUpdateTimestamp": python_utils.prefer_int(self.string_last_ts),
            "RID": "",
            "Owner": {
                "UID": self.string_uid,
                "LID": self.string_lid,
                "USN": self.string_usn,
                "PTK": self.string_ptk,
                "TS": python_utils.prefer_int(self.string_ts),
            },
            "Name": self.string_base,
            "BaseType": {"PersistentBaseTypes": self.string_base_type},
            "LastEditedById": self.LastEditedById,
            "LastEditedByUsername": self.LastEditedByUsername_value,
            "ScreenshotAt": [
                self.screenshot_at_x,
                self.screenshot_at_y,
                self.screenshot_at_z,
            ],
            "ScreenshotPos": [
                self.screenshot_pos_x,
                self.screenshot_pos_y,
                self.screenshot_pos_z,
            ],
            "GameMode": {"PresetGameMode": self.game_mode},
            "PlatformToken": self.platform_token,
            "IsReported": self.is_reported,
            "IsFeatured": self.is_featured,
            "Difficulty": {
                "DifficultyPreset": {"DifficultyPresetType": self.difficulty_preset},
                "PersistentBaseDifficultyFlags": self.difficulty_flags,
            },
            "AutoPowerSetting": {"BaseAutoPowerSetting": self.auto_power_setting},
        }
        # Capture Individual Objects
        objects_data = BUILDER.serialise(get_presets=get_presets)
        if objects_only:
            return objects_data["Objects"]

        data.update(objects_data)
        return data
    
    
    def serialise_obfuscated(self, get_presets=False, objects_only=False):
        data = self.serialise(get_presets=get_presets, objects_only=objects_only)
        #obfuscated_data = conversion_utils.obfuscate_dict(data)
        obfuscated_data = conversion_utils.load_save_file()
        return obfuscated_data
    
    def open_savefile(self):
        return ""

    # Import and Export Methods ---
    def import_nms_data(self):
        """Import and build a base based on the contents of user clipboard.

        The clipboard should contain a copy of the base data found in the
        No Man's Sky Save Editor.
        """
        # Read clipboard data.
        clipboard_data = bpy.context.window_manager.clipboard
        try:
            nms_import_data = json.loads(clipboard_data)
        except:
            message = (
                "Could not import base data, are you sure you copied "
                "the data to the clipboard? (Ctrl+C from No Man's Sky Save Editor)"
            )
            ShowMessageBox(message=message, title="Import")
            return

        # Start a new file
        self.deserialise_from_data(nms_import_data)
        BUILDER.deserialise_from_data(nms_import_data)

    def export_nms_data(self, objects_only=False):
        """Generate data and place it into the user's clipboard.

        This generates a flat set of individual base parts for NMS to read.
        All preset information is lost in this process.
        """
        data = self.serialise(objects_only=objects_only)
        bpy.context.window_manager.clipboard = json.dumps(data, indent=4)
        
    def export_obfuscated_nms_data(self, objects_only=False):
        """Generate data and place it into the user's clipboard.

        This generates a flat set of individual base parts for NMS to read.
        All preset information is lost in this process.
        """
        data = self.serialise_obfuscated(False)
        bpy.context.window_manager.clipboard = json.dumps(data, indent=4)

    # Save and Load Methods ---
    def save_nms_data(self, file_path):
        """Generate data and place it into a json file.

        This preserves any presets built in scene.

        Args:
            file_path (str): The path to the json file.
        """
        data = self.serialise(get_presets=True)
        # Add .json if it's not specified.
        if not file_path.endswith(".json"):
            file_path += ".json"
        # Save to file path
        with open(file_path, "w") as stream:
            json.dump(data, stream, indent=4)

    def load_nms_data(self, file_path):
        # First load
        with open(file_path, "r") as stream:
            try:
                save_data = json.load(stream)
            except BaseException:
                message = (
                    "Could not load base data, are you sure you chose the "
                    "correct file? (.json)"
                )
                ShowMessageBox(message=message, title="Import")
                return
        # Build from Data
        self.deserialise_from_data(save_data)
        BUILDER.deserialise_from_data(save_data)

    def new_file(self):
        """Reset's the entire Blender scene to default.

        Note:
            * Removes all base information in the Blender properties.
            * Resets the build part order in the part builder.
            * Removes all items with ObjectID, PresetID and NMS_LIGHT properties.
            * Resets the room visibility switch to default.
        """
        BUILDER.clear_caches()

        # Remove basic blender default items.
        blend_utils.remove_object("Cube")
        blend_utils.remove_object("Light")
        blend_utils.remove_object("Camera")

        self.string_address = ""
        self.string_userdata = ""
        self.string_base = ""
        self.string_lid = ""
        self.string_ts = ""
        self.string_uid = ""
        self.string_usn = ""
        self.string_ptk = ""
        self.float_pos_x = 0
        self.float_pos_y = 0
        self.float_pos_z = 0
        self.float_ori_x = 0
        self.float_ori_y = 0
        self.float_ori_z = 0
        self.string_last_ts = ""
        self.LastEditedById = ""
        self.original_base_version = 3
        self.LastEditedByUsername_value = ""
        self.screenshot_at_x = 1
        self.screenshot_at_y = 0
        self.screenshot_at_z = 0
        self.screenshot_up_x = 0
        self.screenshot_up_y = 1
        self.screenshot_up_z = 0
        self.game_mode = "Unspecified"
        self.platform_token = ""
        self.is_reported = False
        self.is_featured = False
        self.difficulty_preset = "Creative"
        self.difficulty_flags = 0
        self.auto_power_setting = "UseDefault"

        # Remove all no mans sky items from scene.
        # Deselect all
        bpy.ops.object.select_all(action="DESELECT")
        # Select NMS Items
        for bpy_object in bpy.data.objects:
            id_check = "ObjectID" in bpy_object
            preset_check = "PresetID" in bpy_object
            light_check = "NMS_LIGHT" in bpy_object
            rig_check = "rig_item" in bpy_object
            if any([id_check, preset_check, light_check, rig_check]):
                blend_utils.remove_object(bpy_object.name)

        # Reset room vis
        self.room_vis_switch = 0

    def toggle_room_visibility(self):
        """Cycle through room visibilities.

        Note:
            Visibility types are...
                0: Normal
                1: Ghosted
                2: Invisible
        """
        # Increment Room Vis
        if self.room_vis_switch < 2:
            self.room_vis_switch += 1
        else:
            self.room_vis_switch = 0

        # Set Shading.
        if self.room_vis_switch in [0, 1, 2]:
            bpy.context.space_data.shading.type = "SOLID"
            bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"

        # Set Hide
        hidden = True
        if self.room_vis_switch in [0, 1]:
            hidden = False

        # Transparency.
        show_transparent = False
        if self.room_vis_switch in [1]:
            show_transparent = True

        # Hide Select.
        hide_select = False
        if self.room_vis_switch in [1]:
            hide_select = True

        # Iterate materials for transparency.
        # NOTE: Seems in 2.8 you can't set per object alpha toggling anymore :/
        for material in bpy.data.materials:
            if "transparent" in material.name:
                material.diffuse_color[3] = 0.07 if show_transparent else 1.0

        # Iterate object for selection.
        for ob in bpy.data.objects:
            if "ObjectID" in ob:
                if ob["ObjectID"] in GHOSTED_ITEMS:
                    is_preset = ob.get("belongs_to_preset", False)
                    # Normal
                    ob.hide_viewport = hidden
                    # ob.show_transparent = show_transparent
                    if not is_preset:
                        ob.hide_select = hide_select
                    ob.select_set(False)

    def delete(self):
        """Delete the selected object and everything below."""
        # Store selection.
        selected_objects = bpy.context.selected_objects
        # Validate
        if not selected_objects:
            ShowMessageBox(
                message="Select an item to delete from the scene.", title="Delete"
            )
            return

        for item in selected_objects:
            blend_utils.delete(item)

    def duplicate(self):
        """Snaps one object to another based on selection."""
        # Store selection.
        selected_objects = bpy.context.selected_objects

        # Validate
        if not selected_objects:
            ShowMessageBox(
                message="Make sure you have an item selected.", title="Duplicate"
            )
            return

        # Get Selected item.
        target = blend_utils.get_current_selection()

        if "ObjectID" not in target and "PresetID" not in target:
            message = (
                "This item can not be duplicated via the No Man's Sky tool. "
                "Try using Blender hotkey instead (Shift-D)."
            )
            ShowMessageBox(message=message, title="Duplicate")
            return

        # Part
        if "ObjectID" in target:
            object_id = target["ObjectID"]
            user_data = target["UserData"]
            # Build Item.
            new_item = BUILDER.add_part(object_id, user_data=user_data)
            new_item.select()
        if "PresetID" in target:
            preset_id = target["PresetID"]
            # Build Item.
            new_item = BUILDER.add_preset(preset_id)
            new_item.select()

        # Build Rig if need to.
        if hasattr(new_item, "build_rig"):
            new_item.build_rig()
        # Snap.
        target = BUILDER.get_builder_object_from_bpy_object(target)
        new_item.snap_to(target)

    def duplicate_along_curve(self, distance_percentage):
        """Snaps one object to another based on selection."""
        selected_objects = bpy.context.selected_objects

        if len(selected_objects) != 2:
            message = (
                "Make sure you have two items selected. Select the item to"
                " duplicate, then the curve you want to snap to."
            )
            ShowMessageBox(message=message, title="Duplicate Along Curve")
            return {"FINISHED"}

        # Validate gap_distance.
        range_message = "Please choose a value between 0 and 1."
        if distance_percentage <= 0.0:
            ShowMessageBox(message=range_message, title="Duplicate Along Curve")
            return {"FINISHED"}

        if distance_percentage >= 1.0:
            ShowMessageBox(message=range_message, title="Duplicate Along Curve")
            return {"FINISHED"}

        # Figure out selection.
        if "ObjectID" in selected_objects[0] or "PresetID" in selected_objects[0]:
            curve_object = selected_objects[1]
            dup_object = selected_objects[0]
        else:
            curve_object = selected_objects[0]
            dup_object = selected_objects[1]

        # Perform duplication along curve.
        curve.duplicate_along_curve(
            BUILDER, dup_object, curve_object, distance_percentage
        )

    def mirror(self, across_x=False):
        """Mirror the object along X axis (if possible)."""
        # Store selection.
        selected_objects = bpy.context.selected_objects

        # Validate
        if not selected_objects:
            ShowMessageBox(
                message="Make sure you have an item selected.", title="Mirror"
            )
            return

        # Get Selected item.
        new_items = []
        for target in selected_objects:
            # Part
            if "ObjectID" in target:
                object_id = target["ObjectID"]
                mirror_id = part.Part.get_mirror_part_id(object_id)
                new_item = target
                mirror_part_exist = False
                if mirror_id in nice_name_dictionary.keys():
                    # Build Item.
                    new_item = BUILDER.mirror_part(target)
                    mirror_part_exist = True

                # mirror part across x axis
                if across_x:
                    mirrored_matrix_world = mirror_utils.mirror_matrix_world(object_id, new_item.matrix_world,True)
                    new_item.matrix_world = mirrored_matrix_world
                # mirror part on its location
                else:
                    # Apply mirroring fixes on parts that dont have a ingame asset to represent their mirror.
                    if not mirror_part_exist:
                        mirrored_matrix_world = mirror_utils.mirror_matrix_world(object_id, new_item.matrix_world, False)
                        new_item.matrix_world = mirrored_matrix_world
                        
                if hasattr(new_item, "object"):
                    new_items.append(new_item.object)
                else:
                    new_items.append(new_item)
        blend_utils.select(new_items)
        return {"FINISHED"}

    def flip(self):
        """Mirror the object along X axis (if possible)."""
        # Store selection.
        selected_objects = bpy.context.selected_objects
        new_items = []
        # Validate
        if not selected_objects:
            ShowMessageBox(message="Make sure you have an item selected.", title="Flip")
            return

        # Get Selected item.
        for target in selected_objects:
            # Part
            if "ObjectID" in target:
                object_id = target["ObjectID"]
                mirror_id = part.Part.get_flip_part_id(object_id)
                new_item = target
                if mirror_id in nice_name_dictionary.keys():
                    # Build Item.
                    new_item = BUILDER.flip_part(target)
                    new_items.append(new_item)

                if hasattr(new_item, "object"):
                    new_items.append(new_item.object)
                else:
                    new_items.append(new_item)

        blend_utils.select(new_items)

    def apply_colour(self, colour_index=0, material=0):
        """Gives an item a new colour."""
        selected_objects = bpy.context.selected_objects
        if not selected_objects:
            ShowMessageBox(
                message="Make sure you have an item selected.", title="Apply Colour"
            )
            return {"FINISHED"}

        # Apply Colour Material.
        maeterial_index = int(material.split("_")[0])
        for obj in selected_objects:
            _material.assign_material(obj, int(colour_index), int(maeterial_index))

        # Refresh the viewport.
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)

    def apply_default_colour(self):
        """Gives an item a new colour."""
        selected_objects = bpy.context.selected_objects
        if not selected_objects:
            ShowMessageBox(
                message="Make sure you have an item selected.", title="Apply Colour"
            )
            return {"FINISHED"}

        # Apply Colour Material.
        for obj in selected_objects:
            index = 0
            # Figure out default index.
            object_id = obj["ObjectID"]
            if object_id:
                parent_folder = BUILDER.get_obj_parent_folder(object_id)
                if parent_folder:
                    if parent_folder == "alloy_structures":
                        index = 37
                    elif parent_folder == "timber_structures":
                        index = 45
                    elif parent_folder == "stone_structures":
                        index = 23
            _material.assign_default_material(obj, index=index)

        # Refresh the viewport.
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)

    def snap(
        self, next_source=False, prev_source=False, next_target=False, prev_target=False
    ):
        """Snaps one object to another based on selection."""
        selected_objects = bpy.context.selected_objects

        source = None
        target = None
        # If only one item is selected, see if it has a snapped_to variable to
        # use.
        if len(selected_objects) == 1:
            source = bpy.context.view_layer.objects.active
            if "snapped_to" in source:
                target = bpy.data.objects[source["snapped_to"]]
            else:
                message = (
                    "This item has not been snapped to anything. Please select "
                    "the item you want to snap it to"
                )
                ShowMessageBox(message=message, title="Snap")
                return {"FINISHED"}

        # If 2 are selected, use them as the snapping items.
        elif len(selected_objects) == 2:
            target = bpy.context.view_layer.objects.active
            source = [obj for obj in selected_objects if obj != target][0]

        # If otherwise, we should skip and warn the user.
        else:
            message = (
                "Make sure you have two items selected. Select the item you"
                " want to snap to, then the item you want to snap."
            )
            ShowMessageBox(message=message, title="Snap")
            return {"FINISHED"}

        # Perform Snap
        source = BUILDER.get_builder_object_from_bpy_object(source)
        target = BUILDER.get_builder_object_from_bpy_object(target)
        if source and target:
            source.snap_to(
                target,
                next_source=next_source,
                prev_source=prev_source,
                next_target=next_target,
                prev_target=prev_target,
            )


class NMS_UL_actions_list(bpy.types.UIList):
    previous_layout = None

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname
    ):
        self.use_filter_show = True
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            # Add a category item if the title is specified.
            if item.title:
                layout.label(text=item.title)

            # Draw Parts
            if item.item_type == "parts" and item.description:
                all_parts = [x for x in item.description.split(",") if x]
                part_row = layout.column_flow(columns=3)
                for part in all_parts:
                    operator = part_row.operator(
                        "object.list_build_operator",
                        text=BUILDER.get_nice_name(part),
                    )
                    operator.part_id = part
                    operator.tooltip = (
                        f"Name: {BUILDER.get_nice_name(part)}\nID: ({part})"
                    )

            # Draw Presets
            if item.item_type == "presets":
                if item.description in preset.Preset.get_presets():
                    # Create Sub layuts
                    build_area = layout.split(factor=0.7)
                    operator = build_area.operator(
                        "object.list_build_operator", text=item.description
                    )
                    edit_area = build_area.split(factor=0.6)
                    edit_operator = edit_area.operator(
                        "object.list_edit_operator", text="Edit"
                    )
                    delete_operator = edit_area.operator(
                        "object.list_delete_operator", text="X"
                    )
                    operator.part_id = item.description
                    edit_operator.part_id = item.description
                    delete_operator.part_id = item.description
                    operator.tooltip = "Place this preset in the scene."


# Global Save path for to persiste across blend files                 
class SaveFilePath(bpy.types.AddonPreferences):
    # This must match your addon folder name
    bl_idname = __package__

    # Define the data you want to persist
    nms_save_folder_path: bpy.props.StringProperty(
        name="Save Dir",
        description="Folder where save files are stored",
        default="/"
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="NMS .hg save location:")
        layout.prop(self, "nms_save_folder_path")
        
#save data to persist within blend files.
class SaveData(bpy.types.PropertyGroup):
    
    #this will populate the enum property
    save_slots_enum_list = []
    #this stores data related to save slot like paths etd
    save_slots_data = []
    #this stores list of bases
    base_enum_list = []
    #this is cache for PersistentPlayerBases data
    persistent_base_data = {}

    # there can be miltiple accounts on same device
    nms_account_selected: bpy.props.EnumProperty(
        name="account",
        description="account from which save file will be loaded",
        items = lambda self, context: self.get_accounts_list(),
        update = lambda self, context: self.on_account_list_change(),
    )
    
    #save slot for that account
    nms_save_slot: bpy.props.EnumProperty(
        name="save slot",
        description="Folder where save files are stored",
        items = lambda self, context: SaveData.save_slots_enum_list,
        update = lambda self, context: self.on_save_slot_list_change(),
    )
    
    # Index of base imorted, this is index of base inside PersistentPlayerBase array
    nms_base : bpy.props.EnumProperty(
        name="base index",
        description="Index of the base in the save file.",
        items = lambda self, context: SaveData.base_enum_list,
        update = lambda self, context: self.on_base_selected(context),
    )
    
    # base can be a corvette or a normal base
    nms_base_type: bpy.props.EnumProperty(
        name="base type",
        description="Type of the base.",
        items = [
            ("PlayerShipBase", "Corvette", "show list of corvettes and freighters"),
            ("HomePlanetBase", "Base", "show list of bases"),
        ],
        update = lambda self, context: self.on_base_type_selected()
    )
    
    

    def on_account_list_change(self):
        SaveData.save_slots_enum_list = self.get_save_slots_list()
        #self.nms_save_slot = SaveData.save_slots_enum_list[0][0]
        #SaveData.persistent_base_data = {}
        #SaveData.base_enum_list = [("","","")]
    
    def get_accounts_list(self):
        default_account_list_item = ("Select Account", "Select Account", "No account selected")
        accounts_list = save_editor_utils.get_accounts_list()
        accounts_enum_list = [(str(account), account.name, "") for account in accounts_list]
        accounts_enum_list.insert(0, default_account_list_item)
        return accounts_enum_list
    
    def on_save_slot_list_change(self):
        #SaveData.persistent_base_data = {}
        print("save slot selected is  ", self.nms_save_slot)
        if not self.nms_save_slot == "Select Save Slot":
            save_slot_data = {}
            for slot in SaveData.save_slots_data:
                print("slot data  : ",slot)
                if str(slot["slot"]) == self.nms_save_slot:
                    save_slot_data = slot
                    SaveData.save_slots_data = slot
                    break
            SaveData.persistent_base_data = save_editor_utils.get_persistent_player_bases(save_slot_data)
            SaveData.base_enum_list = self.get_bases_list()
        #self.on_base_type_selected()
    
    def get_save_slots_list(self):
        default_save_slot_list_item = ("Select Save Slot", "Select Save Slot", "No save slot selected")
        account_selected = self.nms_account_selected 
        if not account_selected == "Select Account":
            print("account selected", account_selected)
            save_slots = save_editor_utils.get_save_slots_list(account_selected)
            SaveData.save_slots_data = save_slots
            save_slots_enum_list = [(str(slot["slot"]), "Save Slot " + str(slot["slot"]), "save slot for importing base/corvette") for slot in save_slots]
            save_slots_enum_list.insert(0, default_save_slot_list_item)
            return save_slots_enum_list
        return default_save_slot_list_item
    
    def on_base_type_selected(self):
        if not self.nms_save_slot == "Select Save Slot":
            SaveData.base_enum_list = self.get_bases_list()
            
    def on_base_selected(self,context):
        print()

    def get_bases_list(self):
        default_base_list_item = (
            "Select Corvette" if self.nms_base_type == "PlayerShipBase" else "Select Base", 
            "Select Corvette" if self.nms_base_type == "PlayerShipBase" else "Select Base", 
            "No base selected"
        )
        
        key_base_type = save_editor_utils.eng_to_obf_translator("BaseType")
        key_persistent_base_types = save_editor_utils.eng_to_obf_translator("PersistentBaseTypes")
        key_name = save_editor_utils.eng_to_obf_translator("Name")
        
        base_enum_list = []
        for index, base in enumerate(SaveData.persistent_base_data):
            if(base[key_base_type][key_persistent_base_types] == self.nms_base_type):
                item_tuple = (str(index), str(base[key_name]), "")
                base_enum_list.append(item_tuple)
        base_enum_list.insert(0, default_base_list_item)
        return base_enum_list
    
    def imort_base_from_save_file(self,context):
        base_selected_intex = self.nms_base
        obf_base_data = SaveData.persistent_base_data[int(base_selected_intex)]
        translated_base_data = save_editor_utils.translate_to_eng_data(obf_base_data)
        
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
        
        key_base_type = save_editor_utils.eng_to_obf_translator("BaseType")
        key_persistent_base_types = save_editor_utils.eng_to_obf_translator("PersistentBaseTypes")
        key_name = save_editor_utils.eng_to_obf_translator("Name")
        
        base_index = self.nms_base
        base_type = self.nms_base_type
        base = SaveData.persistent_base_data[int(base_index)]
        base_name = base[key_name]
        
        save_slot = SaveData.save_slots_data
        
        base_identifiers = {
            "base_index": int(base_index),
            "base_name" : base_name,
            "base_type" : base_type
        }
        
        print("base index :", int(base_index))
        print("base name :", base_name)
        print("base type :", base_type)
        
        save_editor.save_editor_utils.save_base_to_save_file(serialised_base_objects_data, base_identifiers, save_slot)
        
        
    

class PartCollection(bpy.types.PropertyGroup):
    title: bpy.props.StringProperty()
    description: bpy.props.StringProperty()
    item_type: bpy.props.StringProperty()


# Plugin Registration ---
from .operators import build_operators, color_operators, file_operators, socials_operators, tool_operators, wiring_operators,save_editor_operators
from .presentation import ui_classes

operator_classes = (
    build_operators.classes +
    color_operators.classes +
    file_operators.classes +
    socials_operators.classes +
    tool_operators.classes +
    wiring_operators.classes +
    save_editor_operators.classes
)

classes = (
    NMSSettings,
    PartCollection,
    NMS_UL_actions_list,
    SaveFilePath,
    SaveData
)

combined_classes = classes + ui_classes  + operator_classes



def register():

    # Ensure User data folder structure exists
    for data_path in [USER_PATH, PRESET_PATH]:
        if not os.path.exists(data_path):
            os.makedirs(data_path)

    # Load Icons.
    pcoll = bpy.utils.previews.new()

    # Load Colours
    colours_dir = os.path.join(os.path.dirname(__file__), "images", "colours")
    colour_files = os.listdir(colours_dir)
    for colour_file in colour_files:
        file_name = os.path.splitext(colour_file)[0]
        pcoll.load(
            file_name,
            os.path.join(colours_dir, colour_file),
            "IMAGE",
        )

    preview_collections["main"] = pcoll

    # Register Plugin
    for _class in combined_classes:
        bpy.utils.register_class(_class)
    bpy.types.Scene.nms_base_tool = PointerProperty(type=NMSSettings)
    bpy.types.Scene.col = bpy.props.CollectionProperty(type=PartCollection)
    bpy.types.Scene.col_idx = bpy.props.IntProperty(default=0)
    bpy.types.Scene.nms_save_data = bpy.props.PointerProperty(type=SaveData)


def unregister():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

    for _class in reversed(combined_classes):
        bpy.utils.unregister_class(_class)
    del bpy.types.Scene.nms_base_tool


if __name__ == "__main__":
    register()
