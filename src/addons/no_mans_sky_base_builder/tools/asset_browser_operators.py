import bpy
import json
from ..utils import blend_utils,dictionary
from ..builder import Builder
import ctypes
from ctypes import wintypes

BUILDER = Builder()
ADDON_ID = __package__.rsplit(".", 1)[0]

    
class LaunchAssetBrowserWindow(bpy.types.Operator):
    bl_idname = "object.nms_launch_asset_browser_window"
    bl_label = "Asset Browser"
    bl_description = "Launch an Asset Browser in new Window"

    target_width: bpy.props.IntProperty(default=1200)
    target_height: bpy.props.IntProperty(default=900)

    def execute(self, context):
        
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        asset_browser.asset_browser_number_of_columns_other = 8
        
        bpy.ops.wm.window_new()
        wm = context.window_manager
        if not wm.windows:
            return {'CANCELLED'}
        new_window = wm.windows[-1]
        try:
            areas = new_window.screen.areas
            if not areas:
                return {'CANCELLED'}
            target_area = areas[0]
            target_area.type = 'PROPERTIES'
        except (ReferenceError, RuntimeError, TypeError):
            return {'CANCELLED'}
        
        attempts_count = 0
        
        def get_timeout():
            nonlocal attempts_count
            attempts_count +=1
            if attempts_count >= 20:
                return None
            return 0.02
        
        def configure_areas():
            try:
                window_exists = any(w == new_window for w in wm.windows)
                if not window_exists:
                    return None
                if len(new_window.screen.areas) < 2:
                    return get_timeout()

                areas_sorted = sorted(new_window.screen.areas, key=lambda a: a.x)
                left_area, right_area = areas_sorted[0], areas_sorted[1]

                prev_dummy_obj = bpy.data.objects.get("Asset Browser Window",None)
                if prev_dummy_obj is not None:
                    bpy.data.objects.remove(prev_dummy_obj, do_unlink=True)
                    
                bpy.ops.mesh.primitive_cube_add(size=0.1, location=(0, 0, 0))
                dummy_obj = context.active_object
                dummy_obj.name = "Asset Browser Window"
                
                for area, ctx_type in ((left_area, 'CONSTRAINT'), (right_area, 'MODIFIER')):
                    area.type = 'PROPERTIES'
                    space = area.spaces.active
                    space.context = ctx_type
                    space.show_region_header = False
                    space.use_pin_id = True
                    space.pin_id = dummy_obj
                    
                for collection in list(dummy_obj.users_collection):
                    collection.objects.unlink(dummy_obj)
                dummy_obj.use_fake_user = True
                    
                return None
            except (ReferenceError, RuntimeError, TypeError, AttributeError):
                return get_timeout()

        def switch_tab():
            try:
                window_exists = any(w == new_window for w in wm.windows)
                if not window_exists:
                    return None

                if target_area.type != 'PROPERTIES':
                    return get_timeout()
                space = target_area.spaces.active
                if space is None or space.type != 'PROPERTIES':
                    return get_timeout()

                nav_region = None
                window_region = None
                for region in target_area.regions:
                    if region.type == 'NAVIGATION_BAR':
                        nav_region = region
                    elif region.type == 'WINDOW':
                        window_region = region

                if window_region is None:
                    return get_timeout()

                if nav_region and nav_region.width > 1:
                    with bpy.context.temp_override(window=new_window, area=target_area, region=nav_region):
                        bpy.ops.screen.region_toggle(region_type='NAVIGATION_BAR')

                with bpy.context.temp_override(window=new_window, area=target_area, region=window_region):
                    bpy.ops.screen.area_split(direction='VERTICAL', factor=0.2)

                bpy.app.timers.register(configure_areas, first_interval=0.02)
                return None
            except (ReferenceError, RuntimeError, TypeError, AttributeError):
                return get_timeout()

        bpy.app.timers.register(switch_tab, first_interval=0.02)

        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                user32.SetWindowTextW(hwnd, "Asset Browser")
                rect = wintypes.RECT()
                if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    user32.MoveWindow(hwnd, rect.left, rect.top, self.target_width, self.target_height, True)
        except Exception:
            pass

        return {'FINISHED'}
    
    
class AssetBrowserObjectSelected(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_object_selected"
    bl_label = "Add Object"
    bl_description = "Click to add this obejct to scene"
    bl_options = {'REGISTER', 'UNDO'}

    object_id: bpy.props.StringProperty()
    has_variants : bpy.props.BoolProperty( default = False )
    variants : bpy.props.StringProperty()
    is_preset : bpy.props.BoolProperty( default = False )
    
    @classmethod
    def description(cls, context, properties):
        return f"ObjectID : {properties.object_id}"
    
    
    def execute(self, context):
        variants = self.variants
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        
        if self.is_preset:
            item_id = self.object_id
            new_item = BUILDER.add_preset(item_id)
            if new_item:
                new_item.select()
        elif self.has_variants:
            def draw_popup(self, context):
                layout = self.layout
                nice_names = dictionary.get_nice_names_diictionary()
                layout.label(text="Select Variants")
                variants_list = json.loads(variants)
                for variant_obj_id in variants_list:
                    if variant_obj_id in nice_names:
                        variant_name = nice_names[variant_obj_id]
                        button = layout.operator("object.nms_asset_browser_object_selected", text = variant_name)
                        button.object_id = variant_obj_id
                        button.has_variants = False
            context.window_manager.popup_menu(draw_popup)
        else:
            if self.object_id in dictionary.get_nice_names_diictionary():
                item = BUILDER.add_part(self.object_id)
                bpy_obj = item.object
                blend_utils.select(bpy_obj)
                asset_browser.add_to_recents_list(self.object_id)
                self.report({'INFO'}, f"Added {self.object_id} to scene")
            else:
                self.report({'ERROR'}, f"Could not add {self.object_id} to scene")
        return {'FINISHED'}
    
class AssetBrowserObjectMoreOptions(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_more_options"
    bl_label = "Add Object"
    bl_description = "Click to add this obejct to scene"

    object_id: bpy.props.StringProperty()
    is_fav : bpy.props.BoolProperty(default = False)
    
    @classmethod
    def description(cls, context, properties):
        return f"Show more optiosn for {properties.object_id}"
    
    
    def execute(self, context):
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        
        is_fav = self.is_fav
        object_id = self.object_id
        
        def draw_popup(self, context):
            layout = self.layout
            layout.label(text=f"{object_id} Options", icon = "COLLAPSEMENU")
            layout.separator()
            layout.separator()
            
            fav_button_label = "Remove from Favourites" if is_fav else "Add to Favourite"
            fav_button_icon = "FUND" if is_fav else "HEART"
            fav_button = layout.operator("object.nms_asset_browser_object_favourite", text = fav_button_label, icon = fav_button_icon)
            fav_button.object_id = object_id
            
            replace_button_label = f"Replace Selected Objects"
            replace_button = layout.operator("object.nms_asset_browser_batch_replace", text = replace_button_label, icon = "GROUP_VERTEX")
            replace_button.object_id = object_id
        context.window_manager.popup_menu(draw_popup)
        return {'FINISHED'}
    
class AssetBrowserCategorySelected(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_category_selected"
    bl_label = "Category Selected"
    bl_description = "Category of objects"

    category: bpy.props.StringProperty()
    
    def execute(self, context):
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        asset_browser.asset_browser_caterogies = self.category
        return {'FINISHED'}
    
class AssetBrowserCategoryFavourite(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_category_favourite"
    bl_label = "Mark Favourite"
    bl_description = "Mark this category favourite"

    category: bpy.props.StringProperty()
    
    def execute(self, context):
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        prefs = context.preferences.addons[ADDON_ID].preferences
        
        fav_cats_str = prefs.favourite_categories
        try:
            fav_cats = json.loads(fav_cats_str) if fav_cats_str else []
        except json.JSONDecodeError:
            fav_cats = []
            
        if self.category in fav_cats:
            fav_cats.remove(self.category)
        else:
            fav_cats.append(self.category)
            
        prefs.favourite_categories = json.dumps(fav_cats)
        asset_browser.set_favourite_categories(fav_cats)
        
        bpy.ops.wm.save_userpref()
        
        return {'FINISHED'}
    

class AssetBrowserObjectFavourite(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_object_favourite"
    bl_label = "Mark Favourite"
    bl_description = "Mark this Object favourite"

    object_id: bpy.props.StringProperty()
    
    def execute(self, context):
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        prefs = context.preferences.addons[ADDON_ID].preferences
        
        fav_obj_str = prefs.favourite_objects
        try:
            fav_objs = json.loads(fav_obj_str) if fav_obj_str else []
        except json.JSONDecodeError:
            fav_objs = []
            
        if self.object_id in fav_objs:
            fav_objs.remove(self.object_id)
        else:
            fav_objs.append(self.object_id)
            
        prefs.favourite_objects = json.dumps(fav_objs)
        asset_browser.set_favourite_objects(fav_objs)
        bpy.ops.wm.save_userpref()
        
        for area in context.window.screen.areas:
            area.tag_redraw()
        
        return {'FINISHED'}
    
class AssetBrowserCategorySubSelected(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_sub_category_selected"
    bl_label = "Sub Cagetory Selected"
    bl_description = "Sub Category of Objects"

    sub_category: bpy.props.StringProperty()
    
    def execute(self, context):
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        asset_browser.asset_browser_sub_caterogies = self.sub_category
        return {'FINISHED'}
    
class AssetBrowserCategoryShowFavItems(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_show_fav_items"
    bl_label = "Favourite Items"
    bl_description = "Show Favourite Items"
    def execute(self, context):
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        asset_browser.show_favourite_obejcts()
        
        for area in context.window.screen.areas:
            area.tag_redraw()
        
        return {'FINISHED'}
    
class AssetBrowserCategoryShowRecentItems(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_show_recent_items"
    bl_label = "Recent Items"
    bl_description = "Show Recent Items"
    def execute(self, context):
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        asset_browser.show_recent_objects()
        
        for area in context.window.screen.areas:
            area.tag_redraw()
        
        return {'FINISHED'}
    
class AssetBrowserCategoryShowPresets(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_show_presets"
    bl_label = "Presets"
    bl_description = "Show Presets"
    def execute(self, context):
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        asset_browser.show_presets()
        
        for area in context.window.screen.areas:
            area.tag_redraw()
        
        return {'FINISHED'}
    


class AssetBrowserListSettings(bpy.types.Operator):
    """Adjust size of icons and number of columns"""

    bl_idname = "object.nms_asset_browser_list_settings"
    bl_label = "List Settings"
    
    grid_type : bpy.props.StringProperty(
        default = "Other"
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self,
            title="List Settings",
        )

    def execute(self, context):
        bpy.ops.wm.save_userpref()
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        prefs = context.preferences.addons[ADDON_ID].preferences
        
        grid_type = self.grid_type
        if grid_type == "Grid":
            icon_size_prop = "asset_browser_icon_size"
            number_of_columns_prop = "asset_browser_number_of_columns"
        elif grid_type == "List":
            icon_size_prop = "asset_browser_icon_size_list"
            number_of_columns_prop = "asset_browser_number_of_columns_list"
        else:
            icon_size_prop = "asset_browser_icon_size_other"
            number_of_columns_prop = "asset_browser_number_of_columns_other"
        
        layout.prop(prefs, icon_size_prop,text = "Icon Size")
        layout.separator()
        layout.prop(prefs, number_of_columns_prop, text = "Columns")
        

class AssetBrowserBatchReplace(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_batch_replace"
    bl_label = "Batch Replace"
    bl_description = "Batch replace selected objects with this item"
    bl_options = {'REGISTER', 'UNDO'}
    
    object_id: bpy.props.StringProperty()
    
    def execute(self, context):
        scene = context.scene
        batch_tool = scene.nms_batch_tool
        selected_objects = context.selected_objects
        if selected_objects:
            batch_tool.batch_replace_with_object_id(self.object_id, selected_objects)
        
        return {'FINISHED'}
        
        
classes = (
    LaunchAssetBrowserWindow,
    AssetBrowserObjectSelected,
    AssetBrowserListSettings,
    AssetBrowserCategorySelected,
    AssetBrowserCategorySubSelected,
    AssetBrowserCategoryFavourite,
    AssetBrowserCategoryShowFavItems,
    AssetBrowserObjectFavourite,
    AssetBrowserCategoryShowRecentItems,
    AssetBrowserCategoryShowPresets,
    AssetBrowserBatchReplace,
    AssetBrowserObjectMoreOptions
)