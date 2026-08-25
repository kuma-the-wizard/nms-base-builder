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
    bl_label = "Object_selected"
    bl_description = "Show tips on how to use curve tool"

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
                #dummy_obj.use_fake_user = True
                    
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
    bl_label = "Object_selected"

    object_id: bpy.props.StringProperty()
    has_variants : bpy.props.BoolProperty(
        default = False
    )
    variants : bpy.props.StringProperty()
    
    @classmethod
    def description(cls, context, properties):
        return f"ObjectID : {properties.object_id}"
    
    
    def execute(self, context):
        variants = self.variants
        
        if self.has_variants:
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
                self.report({'INFO'}, f"Added {self.object_id} to scene")
            else:
                self.report({'ERROR'}, f"Could not add {self.object_id} to scene")
        return {'FINISHED'}
    
class AssetBrowserCategorySelected(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_category_selected"
    bl_label = "Object_selected"
    bl_description = "Show tips on how to use curve tool"

    category: bpy.props.StringProperty()
    
    def execute(self, context):
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        asset_browser.asset_browser_caterogies = self.category
        return {'FINISHED'}
    
class AssetBrowserCategoryFavourite(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_category_favourite"
    bl_label = "Object_selected"
    bl_description = "Show tips on how to use curve tool"

    category: bpy.props.StringProperty()
    
    def execute(self, context):
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        asset_browser.asset_browser_caterogies = self.category
        return {'FINISHED'}
    
class AssetBrowserCategorySubSelected(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_sub_category_selected"
    bl_label = "Object_selected"
    bl_description = "Show tips on how to use curve tool"

    sub_category: bpy.props.StringProperty()
    
    def execute(self, context):
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        asset_browser.asset_browser_sub_caterogies = self.sub_category
        return {'FINISHED'}
    


class AssetBrowserListSettings(bpy.types.Operator):
    """Group parts together into"""

    bl_idname = "object.nms_asset_browser_list_settings"
    bl_label = "List Settingsr"
    bl_options = {'REGISTER', 'UNDO'}
    
    grid_type : bpy.props.StringProperty(
        default = "Other"
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self,
            title="List Settings",
        )

    def execute(self, context):
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
        
classes = (
    LaunchAssetBrowserWindow,
    AssetBrowserObjectSelected,
    AssetBrowserListSettings,
    AssetBrowserCategorySelected,
    AssetBrowserCategorySubSelected,
    AssetBrowserCategoryFavourite
    
)