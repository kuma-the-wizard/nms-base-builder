import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty,
                       PointerProperty, StringProperty)

from .save_editor import save_editor_utils

ADDON_ID = __package__

class NMSAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    nms_save_folder_path: StringProperty(
        name="Save Directory",
        description="Folder where save files are stored",
        subtype='DIR_PATH',
        default = str(save_editor_utils.get_default_save_folder())
    )
    
    nms_check_show_properties : BoolProperty(
        name = "Display details in viewport",
        description = "Display some details like Part Count or active-object details on bottom left side of 3-d viewport",
        default = True
    )
    
    nms_check_show_active_object_properties : BoolProperty(
        name = "Display details in viewport",
        description = "Display some details like Part Count or active-object details on bottom left side of 3-d viewport",
        default = True
    )
    
    nms_active_object_properties_position: EnumProperty(
        name="Active-Object poroperties locatino",
        description="Location in 3d viewport where object properties are to be displayed",
        items = [
            ("Top", "Top", "Display properties at top"),
            ("Bottom", "Bottom", "Display properties at bottom"),
        ],
        default = "Bottom"
    )
    
    nms_check_show_part_count : BoolProperty(
        name = "Display details in viewport",
        description = "Display some details like Part Count or active-object details on bottom left side of 3-d viewport",
        default = True
    )
    
    nms_part_count_position: EnumProperty(
        name="Place where part count is to be shown",
        description="Location in 3d viewport where properties are to be displayed",
        items = [
            ("Top", "Top", "Display properties at top"),
            ("Bottom", "Bottom", "Display properties at bottom"),
        ],
        default = "Bottom"
    )