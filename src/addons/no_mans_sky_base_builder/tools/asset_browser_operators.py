import bpy
from ..utils import blend_utils,dictionary
from ..builder import Builder


import ctypes
from ctypes import wintypes

BUILDER = Builder()

    
class LaunchAssetBrowserWindow(bpy.types.Operator):
    bl_idname = "object.nms_launch_asset_browser_window"
    bl_label = "Object_selected"
    bl_description = "Show tips on how to use curve tool"
    
    
    target_width: bpy.props.IntProperty(default = 1200)
    target_height: bpy.props.IntProperty(default = 900)

    
    def execute(self, context):
        # Create the new Blender window
        bpy.ops.wm.window_new()
        # Get the newly created window.
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

        created_objects = set()
        # finished creating the new window.
        def switch_tab():
            try:
                # Check that the window still exists.
                window_exists = False
                for window in wm.windows:
                    if window == new_window:
                        window_exists = True
                        break
                    
                if not window_exists:
                    return None

                if target_area.type != 'PROPERTIES':
                    return 0.05
                space = target_area.spaces.active
                if space is None or space.type != 'PROPERTIES':
                    return 0.05

                nav_region = None
                for region in target_area.regions:
                    if region.type == 'NAVIGATION_BAR':
                        nav_region = region
                        break
                    
                # Hide navigation bar
                if nav_region and nav_region.width > 1:
                    with bpy.context.temp_override( window=new_window, area=target_area, region=nav_region):
                        bpy.ops.screen.region_toggle(region_type='NAVIGATION_BAR')
                        
                        
                bpy.ops.mesh.primitive_cube_add(
                    size=2,
                    location=(0, 0, 0)
                )
                if created_objects:
                    for obj in created_objects:
                        bpy.data.objects.remove(obj, do_unlink=True)
                        
                dummy_obj = context.active_object
                dummy_obj.name = "Asset Browser Window"
                created_objects.add(dummy_obj)
                
                # Configure Properties editor
                space.context = 'MODIFIER'
                space.show_region_header = False
                space.use_pin_id = True
                space.pin_id = dummy_obj
                
                bpy.ops.object.delete()
     
                return None
            except (ReferenceError, RuntimeError, TypeError, AttributeError):
                # Try again later.
                return 0.05

        bpy.app.timers.register(
            switch_tab,
            first_interval=0.1
        )

        # Resize the native Windows window
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                user32.SetWindowTextW(hwnd, "Asset Browser")
                rect = wintypes.RECT()
                if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    user32.MoveWindow( hwnd, rect.left, rect.top, self.target_width, self.target_height, True)
        except Exception:
            pass

        return {'FINISHED'}
    
    
class AssetBrowserObjectSelected(bpy.types.Operator):
    bl_idname = "object.nms_asset_browser_object_selected"
    bl_label = "Object_selected"
    bl_description = "Show tips on how to use curve tool"

    object_id: bpy.props.StringProperty()
    
    def execute(self, context):
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
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self,
            title="List Settings",
        )

    def execute(self, context):
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        
        scene = context.scene
        asset_browser = scene.nms_asset_browser
        
        icon_size_prop, number_of_columns_prop = asset_browser.get_grid_size_prop_string()
        
        layout.prop(asset_browser, icon_size_prop,text = "Icon Size")
        layout.separator()
        layout.prop(asset_browser, number_of_columns_prop, text = "Columns")
        
classes = (
    LaunchAssetBrowserWindow,
    AssetBrowserObjectSelected,
    AssetBrowserListSettings,
    AssetBrowserCategorySelected,
    AssetBrowserCategorySubSelected
    
)