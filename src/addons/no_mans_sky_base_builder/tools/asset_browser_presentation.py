import bpy
from .. import icons

def draw_sub_category(pcoll , container, label, elements_list, number_of_columns, icon_size, grid_type = "Grid" ):
            
    sub_category_column = container.column(align = True)
    sub_cat_label_row = sub_category_column.row()
    sub_cat_label_row.label(text = label)
    
    subcategory_row = None

    for index,(obj_id,part_data) in enumerate(elements_list.items()):
        asset_icon_id = pcoll[obj_id].icon_id if obj_id in pcoll else None
        asset_name = part_data["name"]
        if index%number_of_columns == 0:
            subcategory_row = sub_category_column.row(align = True)
        
        has_variants = True if "variants" in part_data and len(part_data["variants"]) > 0 else False
        
        drawing_function = draw_list_element if grid_type == "List" else draw_grid_element
        drawing_function(
            grid = subcategory_row,
            grid_icon_size = icon_size,
            object_id = obj_id,
            asset_name = asset_name,
            operator = "object.nms_asset_browser_object_selected",
            asset_icon_value = asset_icon_id,
            has_variants = has_variants
        )
        
    remaining_rows = number_of_columns - len(elements_list)%number_of_columns
    if subcategory_row and remaining_rows != number_of_columns:
        for _ in range(remaining_rows):
            subcategory_row.column(align = True).label(text = "")

def draw_grid_element( grid, grid_icon_size, object_id, asset_name, operator, asset_icon_value = None, has_variants = False ):
    
    if not asset_name:
        return
    
    asset_column = grid.box().column(align=True)
    try:
        asset_icon_row = asset_column.row(align = True)
        #asset_icon_row.label(text = "", icon = "BLANK1")
        asset_icon_row.template_icon( icon_value = asset_icon_value, scale = grid_icon_size) 
        #add_button = asset_icon_row.operator(operator, text = "", emboss = True, icon = "COLOR" if has_variants else "ADD" )
        #add_button.object_id = object_id
    except:
        enum_items = bpy.types.UILayout.bl_rna.functions['label'].parameters['icon'].enum_items["MONKEY"].value
        asset_column.template_icon( icon_value = enum_items,scale= grid_icon_size)
    
    asset_column_text_row = asset_column.row(align = True)
    asset_column_text_row.scale_y = 0.5
    button = asset_column_text_row.operator(operator, text = asset_name, emboss = False)
    button.object_id = object_id
    
def draw_list_element( grid, grid_icon_size, object_id, asset_name, operator, asset_icon_value = None, has_variants = False  ):
    element_row = grid.box().row(align = True)
    element_icon_row = element_row.row(align = True)
    element_icon_row.scale_x = 1.8
    try:
        element_icon_row.template_icon( icon_value = asset_icon_value, scale = grid_icon_size)
    except:
        enum_items = bpy.types.UILayout.bl_rna.functions['label'].parameters['icon'].enum_items["MONKEY"].value
        element_icon_row.template_icon( icon_value = enum_items,scale= grid_icon_size)
    
    if grid_icon_size == 1:
        element_row_right = element_row.row(align = True)
        element_row_right.label(text = asset_name)
        add_button_row = element_row_right.row(align = True)
        add_button_2 = add_button_row.operator(operator, text = "", emboss = True, icon = "COLOR" if has_variants else "ADD")
        add_button_2.object_id = object_id
        
    else:
        element_row_right = element_row.column(align = True)
        element_row_right.label(text = asset_name)
        for _ in range(grid_icon_size-2):
            element_row_right.label(text = "")
        add_button_row = element_row_right.row(align = True)
        add_button_row.label(text = "")
        add_button_2 = add_button_row.operator(operator, text = "", emboss = True, icon = "ADD")
        add_button_2.object_id = object_id


def draw_asset_browser(asset_browser_box, scene):
    
    asset_browser = scene.nms_asset_browser
    grid_type = asset_browser.enum_asset_browser_mode
    
    ab_category = asset_browser.asset_browser_caterogies
    ab_sub_category = asset_browser.asset_browser_sub_caterogies
    
    icon_size, number_of_columns = asset_browser.get_grid_sizes()
    
    
    show_serch_results = asset_browser.check_display_search_results
    
    pcoll = icons.get_asset_icons_pcoll()
    categories_data = asset_browser.get_categories_data()
    
    search_row = asset_browser_box.row(align=True)
    search_row.prop(asset_browser, "asset_broser_search_query", text="", icon='VIEWZOOM')
    search_row.separator()
    grid_options_row = search_row.row(align = True)
    grid_options_row.scale_x = 0.3
    grid_options_row.prop(asset_browser,"enum_asset_browser_mode", text = "View type", expand = True)
    search_row.operator("object.nms_asset_browser_list_settings", icon = "SETTINGS", text = "")
    
    if grid_type == "Grid":
        main_split = asset_browser_box.split(factor=0.13)
        left_col = main_split.column(align=True)
        right_box = main_split.column(align = True)
        
        left_col.label(text = "Asset Browser", icon='ASSET_MANAGER')
        left_col.separator()
        
        categories_col = left_col.column(align = True)
        categories_col.enabled = not asset_browser.check_display_search_results
        categories_col.label(text="Categories" )
        categories_col.prop(asset_browser,"asset_browser_caterogies", expand = True)
        categories_col.scale_y = 1.5
        
    else:
        right_box = asset_browser_box.column(align = True)
    
    right_box.separator()
    top_category_row = right_box.row(align = True)
    
    if show_serch_results:
        sub_cat_dict = asset_browser.get_search_results()
    elif not ab_sub_category or ab_sub_category == "All":
        sub_cat_dict = categories_data[ab_category]
    else:
        cat_dict = categories_data[ab_category][ab_sub_category]
        sub_cat_dict = {ab_sub_category: cat_dict}
    
    if show_serch_results:
        right_box.separator()
        result_row = right_box.row(align = True)
        if sub_cat_dict:
            result_row.alert = False
            result_row.label(text = f"Showing search results ( {len(sub_cat_dict)} found ) ...")
        else:
            result_row.alert = True
            result_row.label(text = f"No matching parts found")
    else:
        if grid_type == "Grid":
            sub_category_column = top_category_row.column(align = True)
            sub_category_column.label(text = "Sub-Category")
            sub_categories_row = sub_category_column.row(align = True)
            sub_categories_row.scale_y = 1.5
            sub_categories_row.prop( asset_browser, "asset_browser_sub_caterogies", expand = True)
        elif grid_type == "List":
            top_category_column = top_category_row.column(align = True)
            top_category_column.label(text = "Category")
            top_categories_row = top_category_column.row(align = True)
            top_categories_row.prop(asset_browser,"asset_browser_caterogies", expand = False, text = "" ) 
            sub_category_column = top_category_row.column(align = True)
            sub_category_column.label(text = "Sub-Category")
            sub_categories_row = sub_category_column.row(align = True)
            sub_categories_row.prop( asset_browser, "asset_browser_sub_caterogies", expand = False, text = "" )
        else:
            top_category_column = top_category_row.column(align = True)
            top_category_column.label(text = "Categories")
            cats_per_row = 4
            cat_row = None
            for index, category in enumerate(categories_data):
                if index % cats_per_row == 0:
                    cat_row = top_category_column.row(align = True)
                cat_button = cat_row.operator(
                    "object.nms_asset_browser_category_selected",
                    text = category,
                    depress = category == ab_category
                )
                cat_button.category = category
            remaining_rows = cats_per_row - len(categories_data)%cats_per_row
            if cat_row and remaining_rows != cats_per_row:
                for _ in range(remaining_rows):
                    cat_row.column(align = True).label(text = "")
            
            top_category_column.separator()
            top_category_column.label(text = "Sub-Categories")
            cat_row = None
            sub_cats_enum = asset_browser.get_enum_sub_categories_list()
            for index, sub_cat in enumerate(sub_cats_enum):
                sub_category = sub_cat[0]
                if index % cats_per_row == 0:
                    cat_row = top_category_column.row(align = True)
                cat_button = cat_row.operator(
                    "object.nms_asset_browser_sub_category_selected",
                    text = sub_category,
                    depress = sub_category == ab_sub_category
                )
                cat_button.sub_category = sub_category
            remaining_rows = cats_per_row - len(sub_cats_enum)%cats_per_row
            if cat_row and remaining_rows != cats_per_row:
                for _ in range(remaining_rows):
                    cat_row.column(align = True).label(text = "")

    
    for subcategories, object_ids in sub_cat_dict.items():
        right_box.separator()
        draw_sub_category(
            pcoll = pcoll, 
            container = right_box, 
            label = subcategories,
            elements_list = object_ids, 
            number_of_columns = number_of_columns,
            icon_size = icon_size,
            grid_type = grid_type
        )



class NMS_PT_asset_browser_properties_panel(bpy.types.Panel):
    bl_label       = "Asset Browser"
    bl_idname      = "MY_PT_asset_browser_properties_panel"
    bl_space_type  = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context     = 'modifier'
    bl_order       = 0 
    
    def draw(self, context):
        layout = self.layout     
        scene = context.scene
        draw_asset_browser(layout, scene)


class NMS_PT_asset_browser_panel(bpy.types.Panel):
    bl_label       = "Asset Browser"
    bl_idname      = "MY_PT_asset_browser_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "NMS Asset Browser"
    bl_context = "objectmode"
    

    def draw(self, context):
        layout = self.layout     
        scene = context.scene
        draw_asset_browser(layout, scene)
        
