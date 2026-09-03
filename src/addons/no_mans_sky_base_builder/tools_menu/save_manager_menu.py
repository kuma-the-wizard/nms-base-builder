"""The "Save Manager" dropdown in the 3D viewport header.

The UI it shows is draw_save_manager(), which lives with the rest of the save
editor in save_editor/save_editor_presentation.py. This module is only the
header entry and the popover that hosts it.
"""

import bpy

from ..save_editor import save_editor_presentation


class VIEW3D_PT_nms_save_manager(bpy.types.Panel):
    """The dropdown itself.

    bl_region_type = "HEADER" keeps it out of the sidebar - it exists only to
    be opened by layout.popover(), so it is not a panel anyone can dock.
    """

    bl_idname = "VIEW3D_PT_nms_save_manager"
    bl_space_type = "VIEW_3D"
    bl_region_type = "HEADER"
    bl_label = "Save Manager"
    # Popovers size themselves from this rather than from their content.
    bl_ui_units_x = 11

    def draw(self, context):
        save_editor_presentation.draw_save_manager(self.layout, context)


def draw_header_menu(self, context):
    """Appended to VIEW3D_MT_editor_menus, which draws the header's menu row.

    Blender calls this with the editor menus instance as self, so the dropdown
    lands in the same row as View / Select / Add / Object rather than being
    drawn somewhere of its own.
    """
    layout = self.layout
    save_data = save_editor_presentation.get_save_data(context)
    if save_data.pinned_base_check:
        layout.operator(
            "object.export_pinned_base", icon="EXPORT", text="Export to Save"
        )
        layout.popover(
            panel=VIEW3D_PT_nms_save_manager.bl_idname, text=""
        )
    else:
        layout.popover(
            panel=VIEW3D_PT_nms_save_manager.bl_idname, text="Save Manager", icon = "FILE_TICK"
        )


classes = (
    VIEW3D_PT_nms_save_manager,
)


def register_menu():
    # Removed first so a re-register - an addon reload, or enable after
    # disable - cannot leave two "Save Manager" entries in the header.
    unregister_menu()
    bpy.types.VIEW3D_MT_editor_menus.append(draw_header_menu)


def unregister_menu():
    try:
        bpy.types.VIEW3D_MT_editor_menus.remove(draw_header_menu)
    except (ValueError, AttributeError, RuntimeError):
        # Not appended in the first place, which is fine - this runs on
        # unregister paths that may not have got as far as adding it.
        pass
