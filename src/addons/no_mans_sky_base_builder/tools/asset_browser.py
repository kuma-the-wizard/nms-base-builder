
import bpy
from ..utils import dictionary
from .. import builder
from ..utils.mirror_utils import ShowMessageBox



nice_name_dictionary = dictionary.get_nice_names_diictionary()

class AssetBrowser(bpy.types.PropertyGroup):

    enum_categories = []
    enum_sub_categories = []
    
    check_display_search_results: bpy.props.BoolProperty(
        name = "Display Search Results",
        default = False
    )
    
    asset_broser_search_query: bpy.props.StringProperty(
        name="Search", 
        default="",
        options={'TEXTEDIT_UPDATE'},
        update = lambda self, context: self.on_search_entered()
    )
    
    asset_browser_caterogies: bpy.props.EnumProperty(
        name="Categories",
        description="Catagories",
        items = lambda self, context: self.get_categories(),
        update = lambda self, context: self.on_category_selected(),
        default = 0
    )
    
    asset_browser_sub_caterogies: bpy.props.EnumProperty(
        name="Subcategory",
        description="Subcategory",
        items = lambda self, context: AssetBrowser.enum_sub_categories,
        update=lambda self, context: self.on_sub_category_selected(),
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
    
    categories_data = {}
    search_results = {}
    
    
    def get_grid_size_prop_string(self):
        grid_type = self.enum_asset_browser_mode
        if grid_type == "Grid":
            icon_size_prop = "asset_browser_icon_size"
            number_of_columns_prop = "asset_browser_number_of_columns"
        else :
            icon_size_prop = "asset_browser_icon_size_list"
            number_of_columns_prop = "asset_browser_number_of_columns_list"
        return icon_size_prop, number_of_columns_prop
        
    
    def get_grid_sizes(self):
        grid_type = self.enum_asset_browser_mode
        if grid_type == "Grid":
            icon_size = self.asset_browser_icon_size
            number_of_columns = self.asset_browser_number_of_columns
        else :
            icon_size = self.asset_browser_icon_size_list
            number_of_columns = self.asset_browser_number_of_columns_list
        return icon_size, number_of_columns
    
    
    def get_categories(self):
        if not AssetBrowser.enum_categories:
            categories_data = dictionary.get_category_vise_objects()
            for category in categories_data:
                AssetBrowser.enum_categories.append((category,category,category))
            AssetBrowser.enum_sub_categories = self.extract_enum_sub_categories()
        return AssetBrowser.enum_categories

    def on_category_selected(self):
        AssetBrowser.enum_sub_categories = self.extract_enum_sub_categories()
        self.asset_browser_sub_caterogies = "All"
        
    def get_enum_sub_categories(self):
        return self.extract_enum_sub_categories()
        
    def extract_enum_sub_categories(self):
        prop_caterogies = self.asset_browser_caterogies
        categories_data = dictionary.get_category_vise_objects()
        
        sub_categories = [("All","All","All")]
        
        if not prop_caterogies or prop_caterogies not in categories_data:
            return sub_categories
        
        categories_data_cat = categories_data[prop_caterogies]
        if categories_data_cat:
            for subcategories_name, object_ids in categories_data_cat.items():
                sub_categories.append((subcategories_name,subcategories_name,subcategories_name))
        return sub_categories
        
    def get_categories_data(self):
        if not AssetBrowser.categories_data:
            AssetBrowser.categories_data = dictionary.get_category_vise_objects()
        return AssetBrowser.categories_data
    
    def get_enum_categories_list(self):
        return AssetBrowser.enum_categories
    
    def get_enum_sub_categories_list(self):
            return AssetBrowser.enum_sub_categories
    
    def on_search_entered(self):
        search_filter = self.asset_broser_search_query
        if search_filter and len(search_filter) > 2:
            self.check_display_search_results = True
            categories_data = self.get_categories_data()
            search_results = {}
            for category, sub_categories in categories_data.items():
                for sub_categories, objects_list in sub_categories.items():
                    for obj_id, obj_data in objects_list.items():
                        
                        obj_id_lower = obj_id.lower()
                        name_lower = obj_data["name"].lower()

                        if search_filter in obj_id_lower or search_filter in name_lower:
                            if category not in search_results:
                                search_results[category] = {}
                                
                            search_results[category][obj_id] = obj_data
                        
            AssetBrowser.search_results = search_results
        else:
            self.check_display_search_results = False
            AssetBrowser.search_results = {}
            
    def get_search_results(self):
        return AssetBrowser.search_results