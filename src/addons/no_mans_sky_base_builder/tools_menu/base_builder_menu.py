import bpy
from .. import icons
from ..save_editor import save_editor_presentation
from . base_builder_menu_presentation import VIEW3D_PT_nms_base_builder, VIEW3D_PT_nms_io_panel


def draw_header_menu(self, context):
    """Appended to VIEW3D_MT_editor_menus, which draws the header's menu row. """
    layout = self.layout
    save_data = save_editor_presentation.get_save_data(context)
    pcoll = icons.get_icons_pscroll()
    plugin_icon = pcoll["plugin_icon"]
    
    layout.separator(factor = 5)
    menu_row = layout.box().row(align = True)
    menu_row.label(text = "", icon_value = plugin_icon.icon_id)
    menu_row.popover(panel=VIEW3D_PT_nms_base_builder.bl_idname, text="Builder")
    
    layout.separator()
    menu_row = layout.row(align = True)
    
    
    if save_data.pinned_base_check:
        menu_row.operator("object.export_pinned_base", icon="EXPORT", text="Export to Save" )
        menu_row.popover(panel=VIEW3D_PT_nms_io_panel.bl_idname, text="I/O")
    else:
        menu_row.popover(panel=VIEW3D_PT_nms_io_panel.bl_idname, text="I/O")
    
    
    
classes = (
    VIEW3D_PT_nms_base_builder,
    VIEW3D_PT_nms_io_panel
)


def register_menu():
    unregister_menu()
    bpy.types.VIEW3D_MT_editor_menus.append(draw_header_menu)
    
    bpy.types.Scene.enum_assets_quick_access_view_mode = bpy.props.EnumProperty(
        name="View Mode",
        description="Asset QA View Mode",
        items = [
            ("fav", "Favourites", "fav","HEART", 0),
            ("recent", "Recent", "recent","MOD_TIME",1)
        ],
        default = "fav"
    )
       


def unregister_menu():
    try:
        bpy.types.VIEW3D_MT_editor_menus.remove(draw_header_menu)
    except (ValueError, AttributeError, RuntimeError):
        # Not appended in the first place, which is fine - this runs on
        # unregister paths that may not have got as far as adding it.
        pass
    
