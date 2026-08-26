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
    
    asset_browser_icon_size_other: bpy.props.IntProperty(
        name="Size",
        description="Icons Size",
        default = 4,
        min = 1,
        max = 10,
        options={'TEXTEDIT_UPDATE'}
    )
    
    asset_browser_number_of_columns_other: bpy.props.IntProperty(
        name="Nomber of Columns",
        description="Number of elements to display in each row",
        default = 10,
        min = 4,
        max = 15,
        options={'TEXTEDIT_UPDATE'}
    )
    
    asset_browser_icon_size_list: bpy.props.IntProperty(
        name="Size",
        description="Icons Size",
        default = 2,
        min = 1,
        max = 10,
        options={'TEXTEDIT_UPDATE'}
    )
    
    asset_browser_number_of_columns_list: bpy.props.IntProperty(
        name="Nomber of Columns",
        description="Number of elements to display in each row",
        default = 3,
        min = 1,
        max = 16,
        options={'TEXTEDIT_UPDATE'}
    )
    
    asset_browser_icon_size: bpy.props.IntProperty(
        name="Size",
        description="Icons Size",
        default = 3,
        min = 1,
        max = 10,
        options={'TEXTEDIT_UPDATE'}
    )
    
    asset_browser_number_of_columns: bpy.props.IntProperty(
        name="Nomber of Columns",
        description="Number of elements to display in each row",
        default = 3,
        min = 1,
        max = 10,
        options={'TEXTEDIT_UPDATE'}
    )
    
    enum_asset_browser_mode: bpy.props.EnumProperty(
        name="View Mode",
        description="Asset Browser View Mode",
        items = [
            ("List", "List", "List","ALIGN_LEFT", 0),
            ("Grid", "Grid", "Grid","LIGHTPROBE_VOLUME",1)
        ],
        default = "Grid"
    )
    
    favourite_categories: bpy.props.StringProperty(
        name = "Favourite Categories",
        description = "List of Categories that are marked as Favourite",
        default = ""
    )
    
    favourite_objects: bpy.props.StringProperty(
        name = "Favourite Objects",
        description = "List of Objects that are marked as Favourite",
        default = ""
    )
    
    recent_objects: bpy.props.StringProperty(
        name = "Recent Objects",
        description = "List of Objects that have been recently added",
        default = ""
    )