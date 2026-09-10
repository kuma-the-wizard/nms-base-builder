"""The UI drawn inside the "Base Builder" dropdown."""

import bpy
from ..tools import asset_browser_presentation
from ..save_editor import save_editor_presentation
from .. import icons

class VIEW3D_PT_nms_io_panel(bpy.types.Panel):
    """ Save Files Browser """

    bl_idname = "VIEW3D_PT_nms_io_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "HEADER"
    bl_label = "I/O"
    # Popovers size themselves from this rather than from their content.
    bl_ui_units_x = 14
    

    def draw(self, context):
        layout = self.layout
        nms_main = getattr(context.scene, "nms_main", None)
        
        clipboard_box = layout.box().column(align=True)
        clipboard_box.label(text="Clipboard")
        clipboard_column = clipboard_box.row(align=False)
        clipboard_column.operator("object.nms_import_nms_data", icon="PASTEDOWN")
        clipboard_export_column = clipboard_column.column(align=True)
        clipboard_export_column.operator("object.nms_export_nms_data", icon="COPYDOWN")
        clipboard_export_column.prop(nms_main, "check_export_objects_only", text="Objects Only")
            
        layout.separator()
        save_editor_presentation.draw_save_manager(layout, context)
       
        


class VIEW3D_PT_nms_base_builder(bpy.types.Panel):
    """ Quick options related to NMS Base and Corvette Builder"""

    bl_idname = "VIEW3D_PT_nms_base_builder"
    bl_space_type = "VIEW_3D"
    bl_region_type = "HEADER"
    bl_label = "Base Builder"
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
        proxy_column.operator("object.nms_switch_proxies_to_low", icon="MESH_CUBE", text = "Simple Proxies")
        proxy_column.operator("object.nms_switch_proxies_to_high", icon="MESH_MONKEY", text = "High-res Proxies")
    
        
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
                        


    
    
    