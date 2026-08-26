
import bpy
import json
from ..utils import dictionary
from ..utils.mirror_utils import ShowMessageBox
from ..preset import Preset




ADDON_ID = __package__.rsplit(".", 1)[0]


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
        items = lambda self, context: self.get_categories(context),
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
    
    enum_asset_browser_what_to_display: bpy.props.EnumProperty(
        name="Dislay What",
        description="Choose what type of data to display",
        items = [
            ("asset", "asset", "asset"),
            ("search", "search", "search"),
            ("fav", "fav", "fav"),
            ("recent", "recent", "recent"),
            ("preset", "preset", "preset")
        ],
        default = "asset"
    )
    
    favourite_categories = []
    favourite_objects_data = {}
    recent_objects_data = {}
    presets_data = {}
    
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
    
    
    def get_categories(self, context):
        if not AssetBrowser.enum_categories:
            categories_data = self.get_category_vise_objects()
            for category in categories_data:
                AssetBrowser.enum_categories.append((category,category,category))
            
            AssetBrowser.presets_data = self.get_presets_data()
            AssetBrowser.enum_sub_categories = self.extract_enum_sub_categories()
            AssetBrowser.favourite_categories = self.get_favourite_categories(context)
            
        return AssetBrowser.enum_categories

    def on_category_selected(self):
        self.enum_asset_browser_what_to_display = "asset"
        AssetBrowser.enum_sub_categories = self.extract_enum_sub_categories()
        self.asset_browser_sub_caterogies = "All"
        

    def on_sub_category_selected(self):
        self.enum_asset_browser_what_to_display = "asset"
        AssetBrowser.enum_sub_categories = self.extract_enum_sub_categories()
        
    def get_enum_sub_categories(self):
        return self.extract_enum_sub_categories()
        
    def extract_enum_sub_categories(self):
        prop_caterogies = self.asset_browser_caterogies
        categories_data = self.get_category_vise_objects()
        
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
            AssetBrowser.categories_data = self.get_category_vise_objects()
            
            prefs = bpy.context.preferences.addons[ADDON_ID].preferences
            try:
                fav_obj_str = prefs.favourite_objects
                fav_objs = json.loads(fav_obj_str) if fav_obj_str else []
                self.set_favourite_objects(fav_objs)
            except json.JSONDecodeError:
                pass
            
            try:
                recent_obj_str = prefs.recent_objects
                recent_objs = json.loads(recent_obj_str) if recent_obj_str else []
                self.set_recent_objects(recent_objs)
            except json.JSONDecodeError:
                pass

            
        return AssetBrowser.categories_data
    
    def get_enum_categories_list(self):
        return AssetBrowser.enum_categories
    
    def get_enum_sub_categories_list(self):
            return AssetBrowser.enum_sub_categories
    
    def on_search_entered(self):
        search_filter = self.asset_broser_search_query
        if search_filter and len(search_filter) > 2:
            self.check_display_search_results = True
            self.enum_asset_browser_what_to_display = "search"
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
            self.enum_asset_browser_what_to_display = "asset"
            AssetBrowser.search_results = {}
            
    def get_search_results(self):
        return AssetBrowser.search_results
    
    
    def get_category_vise_objects(self):
        
        categories_list = {}
        fav_obejcts_data = {}
        part_definition = dictionary.get_parts_definition()
        
        prefs = bpy.context.preferences.addons[ADDON_ID].preferences
        fav_obj_str = prefs.favourite_objects
        try:
            fav_objs = json.loads(fav_obj_str) if fav_obj_str else []
        except json.JSONDecodeError:
            fav_objs = []
        
        for _, part in part_definition.items():
            
            object_id = part[0].replace("^","")
            category = part[2]
            sub_category = part[4]
            nice_name = part[7]
            varaint_of = part[9].replace("^","")
            
            if not object_id or not nice_name:
                continue
            
            if object_id not in nice_name_dictionary:
                continue
            
            nice_name = dictionary.to_title_case(nice_name)
            
            if category not in categories_list:
                categories_list[category] = {}
            if sub_category not in categories_list[category]:
                categories_list[category][sub_category] = {}
                
            sub_cat = categories_list[category][sub_category]
            if varaint_of == "None":
                if object_id not in sub_cat:
                    sub_cat[object_id] = {}
                sub_cat[object_id]["name"] = nice_name
                
                if fav_objs and object_id in fav_objs:
                    sub_cat[object_id]["is_fav"] = True
                    fav_obejcts_data[object_id] = sub_cat[object_id]
                else:
                    sub_cat[object_id]["is_fav"] = False
                
            else:
                if varaint_of not in sub_cat:
                    sub_cat[varaint_of] = { "name" : nice_name }
                if "variants" not in sub_cat[varaint_of]:
                    sub_cat[varaint_of]["variants"] = []
                sub_cat[varaint_of]["variants"].append(object_id)
                
        return categories_list
    
    def set_favourite_categories(self, favourite_categories):
        AssetBrowser.favourite_categories = favourite_categories
                
    def get_favourite_categories(self, context = bpy.context):
        if not AssetBrowser.favourite_categories and context is not None:
            prefs = context.preferences.addons[ADDON_ID].preferences
            fav_cats_str = prefs.favourite_categories
            try:
                fav_cats = json.loads(fav_cats_str) if fav_cats_str else []
            except json.JSONDecodeError:
                fav_cats = []
            AssetBrowser.favourite_categories = fav_cats
        return AssetBrowser.favourite_categories
    
    def set_favourite_objects(self, new_favourite_objects):
        categories_data = self.get_categories_data()
        fav_obejcts_data = {}
        for category, sub_categories in categories_data.items():
            for sub_categories, objects_list in sub_categories.items():
                for obj_id, obj_data in objects_list.items():
                    is_fav = obj_id in new_favourite_objects
                    obj_data["is_fav"] = is_fav
                    if is_fav:
                        fav_obejcts_data[obj_id] = obj_data
                        
        AssetBrowser.favourite_objects_data = fav_obejcts_data
        
    
    def get_favourite_objects_data(self):
        return AssetBrowser.favourite_objects_data
    
    def show_favourite_obejcts(self):
        self.enum_asset_browser_what_to_display = "fav"
        
        
    def set_recent_objects(self, new_recent_objects):
        categories_data = self.get_categories_data()
        all_objects = {
            obj_id: obj_data
            for sub_cats in categories_data.values()
            for objects_list in sub_cats.values()
            for obj_id, obj_data in objects_list.items()
        }

        recent_objects_data = {
            obj_id: all_objects[obj_id]
            for obj_id in new_recent_objects
            if obj_id in all_objects
        }
                        
        AssetBrowser.recent_objects_data = recent_objects_data
        
    def get_recent_objects_data(self):
            return AssetBrowser.recent_objects_data
        
    def show_recent_objects(self):
            self.enum_asset_browser_what_to_display = "recent"
            
    def add_to_recents_list(self, object_id):
        prefs = bpy.context.preferences.addons[ADDON_ID].preferences
        try:
            recent_obj_str = prefs.recent_objects
            recent_objs = json.loads(recent_obj_str) if recent_obj_str else []
        except json.JSONDecodeError:
            recent_objs = []
        
        if recent_objs and object_id in recent_objs:
            recent_objs.remove(object_id)
        recent_objs.insert(0,object_id)
        
        prefs.recent_objects = json.dumps(recent_objs)
        
        if recent_objs:
            self.set_recent_objects(recent_objs)
        bpy.ops.wm.save_userpref()
        
    def get_presets_data(self):
        presets_list = Preset.get_presets()
        data = {}
        for preset_name, preset_link in presets_list.items():
            preset_element = {
                "name":preset_name,
                "link": preset_link,
                "is_preset" : True
            }
            data[preset_name] = preset_element
        
        return data
    
    def show_presets(self):
        self.enum_asset_browser_what_to_display = "preset"
        
    def get_preset_data(self):
        return AssetBrowser.presets_data
        