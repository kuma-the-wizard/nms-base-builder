import os
import bpy

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
LIBRARY_PATH = os.path.join(FILE_PATH,"..","native_asset_browser")
LIBRARY_NAME = "NMS Parts"



def check_new_import(obj):
    if "ObjectID" in obj and obj.get("is_native_asset", False):
        if obj.asset_data is None:
            obj.name = obj.get("ObjectID")
            
def add_asset_library_to_blender():
    library_path = os.path.abspath(LIBRARY_PATH)
    asset_libraries = bpy.context.preferences.filepaths.asset_libraries
    
    if LIBRARY_NAME in asset_libraries:
        print(f"Asset library '{LIBRARY_NAME}' already exists.")
    else:
        new_lib = asset_libraries.new(name=LIBRARY_NAME)
        new_lib.path = library_path
        bpy.ops.wm.save_userpref()
        print(f"Successfully added asset library: {LIBRARY_NAME} -> {library_path}")
        
        
def open_and_switch_asset_browser():
    target_library_name = LIBRARY_NAME

    bpy.ops.wm.window_new()
    new_window = bpy.context.window_manager.windows[-1]

    def find_area():
        return next(
            (a for a in new_window.screen.areas if a.type == 'VIEW_3D'),
            new_window.screen.areas[0]
        )

    target_area = find_area()
    target_area.type = 'FILE_BROWSER'
    space = target_area.spaces.active
    space.browse_mode = 'ASSETS'

    def wait_for_params():
        if space.params is None:
            return 0.05  # keep polling
        available_libs = bpy.context.preferences.filepaths.asset_libraries
        if target_library_name in available_libs or target_library_name == "LOCAL":
            space.params.asset_library_reference = target_library_name
            print(f"Switched library to: {target_library_name}")
        else:
            print(f"Library '{target_library_name}' not found in preferences.")
        target_area.tag_redraw()
        return None  # stop polling

    bpy.app.timers.register(wait_for_params, first_interval=0.05)
