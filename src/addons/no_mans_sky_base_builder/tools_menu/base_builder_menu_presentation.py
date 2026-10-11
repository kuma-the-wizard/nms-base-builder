"""The UI drawn inside the "Base Builder" dropdown."""

import bpy
from ..tools import asset_browser_presentation
from ..save_editor import save_editor_presentation
from .. import icons, hd_library, hd_library_ui

class VIEW3D_PT_nms_io_panel(bpy.types.Panel):
    """ Save Files Browser """

    bl_idname = "VIEW3D_PT_nms_io_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "HEADER"
    bl_label = "I/O"
    # Popovers size themselves from this rather than from their content.
    bl_ui_units_x = 24
    

    def draw(self, context):
        layout = self.layout
        layout.label(text="Save Manager", icon="FILE_TICK")
        save_editor_presentation.draw_save_manager(layout, context)
        if not context.scene.nms_save_data.check_plugin_enabled:
            layout.label(text="Enable to choose a save and access its tools.", icon="INFO")
       
        


class VIEW3D_PT_nms_base_builder(bpy.types.Panel):
    """ Quick options related to NMS Base and Corvette Builder"""

    bl_idname = "VIEW3D_PT_nms_base_builder"
    bl_space_type = "VIEW_3D"
    bl_region_type = "HEADER"
    bl_label = "Base Builder Extended"
    bl_description = "Proxy quality, Asset Browser, and quick access to parts"
    # Popovers size themselves from this rather than from their content.
    bl_ui_units_x = 13
    

    def draw(self, context):
        """Draw the Base Builder dropdown's contents into `layout`."""
        layout = self.layout
        
        asset_browser = context.scene.nms_asset_browser
        enum_assets_quick_access_view_mode = context.scene.enum_assets_quick_access_view_mode
        pcoll = icons.get_asset_icons_pcoll()
        
        
        proxy_box = layout.column(align=True)
        proxy_box.label(text="Switch Proxy Quality")
        proxy_column = proxy_box.row(align=False)
        detailed = hd_library_ui.detailed_enabled(context.scene)
        proxy_column.operator("object.nms_switch_proxies_to_low", icon="MESH_CUBE", text="Simple Proxies", depress=not detailed)
        proxy_column.operator("object.nms_switch_proxies_to_high", icon="MESH_MONKEY", text="Detailed Proxies", depress=detailed)
        remove_column = proxy_column.row(align=True)
        remove_column.alignment = 'RIGHT'
        remove_column.operator_context = 'INVOKE_DEFAULT'
        remove_column.operator('bbe.hd_remove', text='', icon='TRASH')
        if detailed:
            proxy_box.prop(context.scene, 'bbe_solid_decals')
        if hd_library.STATE['busy']:
            # Blender caches an open popover's layout. Keep live progress in
            # the viewport header/sidebar, where timer redraws are supported.
            proxy_box.label(text="Downloading: progress in top bar", icon='IMPORT')
            proxy_box.operator('bbe.hd_cancel', text='Cancel Download', icon='CANCEL')
    
        
        layout.separator()
        asset_browser_box = layout.column(align=True)
        asset_browser_box.label(text="Asset Browser")
        asset_browser_box.operator(
            "object.nms_launch_asset_browser_window", text="Launch Asset Browser", icon="ASSET_MANAGER"
        )
        
        layout.separator()
        quick_access_column = layout.column(align = True)
        quick_access_column.label(text = "Quick Access")
        quick_access_column.row(align = True).prop(context.scene,"enum_assets_quick_access_view_mode", expand = True)
        quick_access_column.separator()
        
        
        def draw_assets(asset_data):
            if asset_data:
                row = quick_access_column.row(align = True)
                for subcategories, object_ids in asset_data.items():
                    asset_browser_presentation.draw_sub_category(
                        pcoll = pcoll, 
                        container = row, 
                        label = subcategories,
                        elements_list = object_ids, 
                        number_of_columns = 4,
                        icon_size = 2,
                        grid_type = "Other",
                        show_title = False
                    )
                
        
        recent_data = asset_browser.get_recent_objects_data()
        if enum_assets_quick_access_view_mode == "recent":
            if recent_data:
                recent_first_four = dict(list(recent_data.items())[:4])
                recent_dict = {"Recent Objects": recent_first_four}
    
                draw_assets(recent_dict)
        else:
            fav_data = asset_browser.get_favourite_objects_data()
            if fav_data:
                fav_first_four = dict(list(fav_data.items())[:4])
                fav_dict = {"Favourite Objects": fav_first_four}
                draw_assets(fav_dict)
        
        layout.separator()
        search_colun = layout.column(align = True)
        search_colun.label(text = "Search Items")
        search_colun.prop(asset_browser, "asset_broser_search_query", text="", icon='VIEWZOOM')
        
        if asset_browser.enum_asset_browser_what_to_display == "search":
            search_data = asset_browser.get_search_results()
            draw_assets(search_data)


def _draw_toolbar_group(self, context):
    """Reuse the original controls; no second implementation to drift."""
    from .. import (
        NMS_PT_build_panel, NMS_PT_nms_legacy_asset_browser,
        NMS_PT_logic_panel,
    )
    from ..tools.properties_presentation import NMS_PT_transformation_panel
    from ..tools.build_tool_presentation import NMS_PT_tools_panel
    from ..tools.batch_tool_presentation import NMS_PT_batch_tools_panel
    group = self.toolbar_group
    sources = {
        "parts": (NMS_PT_build_panel, NMS_PT_nms_legacy_asset_browser),
        "transform": (NMS_PT_transformation_panel,),
        "builder_tools": (NMS_PT_tools_panel,),
        "batch": (NMS_PT_batch_tools_panel,),
        "cables": (NMS_PT_logic_panel,),
    }
    for source in sources[group]:
        if hasattr(source, "poll") and not source.poll(context):
            if group == "transform":
                self.layout.label(text="Select a part to edit its transform.", icon="INFO")
            continue
        if len(sources[group]) > 1:
            self.layout.label(text=source.bl_label)
        source.draw(self, context)


def _toolbar_panel(identifier, label, group, width):
    return type(
        "VIEW3D_PT_bbe_toolbar_" + identifier,
        (bpy.types.Panel,),
        {
            "bl_idname": "VIEW3D_PT_bbe_toolbar_" + identifier,
            "bl_label": label,
            "bl_description": "Open " + label + " controls",
            "bl_space_type": "VIEW_3D",
            "bl_region_type": "HEADER",
            "bl_ui_units_x": width,
            "toolbar_group": group,
            "draw": _draw_toolbar_group,
        },
    )


TOOLBAR_GROUPS = tuple(
    (_toolbar_panel(identifier, label, group, width), icon)
    for identifier, label, group, width, icon in (
        ("transform", "Transformations", "transform", 26, "ORIENTATION_GIMBAL"),
        ("cables", "Cables & Logic", "cables", 24, "CURVE_PATH"),
        ("builder_tools", "Builder Tools", "builder_tools", 27, "TOOL_SETTINGS"),
        ("batch", "Batch Tools", "batch", 27, "MOD_ARRAY"),
        ("parts", "Parts & Prefabs", "parts", 26, "ASSET_MANAGER"),
    )
)
                        


    
    
    
