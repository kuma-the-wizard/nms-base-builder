"""The "Base Builder" dropdown in the 3D viewport header.

The UI it shows is draw_base_builder_menu(), which lives in
base_builder_menu_presentation.py. This module is only the header entry and
the popover that hosts it.
"""

import bpy

from .. import icons

from .base_builder_menu_presentation import draw_base_builder_menu


class VIEW3D_PT_nms_base_builder(bpy.types.Panel):
    """ Quick options related to NMS Base and Corvette Builder"""

    bl_idname = "VIEW3D_PT_nms_base_builder"
    bl_space_type = "VIEW_3D"
    bl_region_type = "HEADER"
    bl_label = "Base Builder"
    # Popovers size themselves from this rather than from their content.
    bl_ui_units_x = 8

    def draw(self, context):
        draw_base_builder_menu(self.layout, context)


def draw_header_menu(self, context):
    """Appended to VIEW3D_MT_editor_menus, which draws the header's menu row.

    Blender calls this with the editor menus instance as self, so the dropdown
    lands in the same row as View / Select / Add / Object rather than being
    drawn somewhere of its own.
    """
    layout = self.layout
    
    pcoll = icons.get_icons_pscroll()
    plugin_icon = pcoll["plugin_icon"]
    
    layout.separator(factor = 5)
    layout.popover(panel=VIEW3D_PT_nms_base_builder.bl_idname, text="Base Builder", icon_value = plugin_icon.icon_id)

classes = (
    VIEW3D_PT_nms_base_builder,
)


def register_menu():
    # Removed first so a re-register - an addon reload, or enable after
    # disable - cannot leave two "Base Builder" entries in the header.
    unregister_menu()
    bpy.types.VIEW3D_MT_editor_menus.append(draw_header_menu)


def unregister_menu():
    try:
        bpy.types.VIEW3D_MT_editor_menus.remove(draw_header_menu)
    except (ValueError, AttributeError, RuntimeError):
        # Not appended in the first place, which is fine - this runs on
        # unregister paths that may not have got as far as adding it.
        pass
