import bpy
import bpy.utils.previews
import os
import json

import sys
import tempfile
import importlib

preview_collections = {}

def extract_pcoll():
    """Reads the JSON file and loads icons into the Blender preview collection."""
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir,"resources","icons.json")
    
    # Initialize a new preview collection
    pcoll = bpy.utils.previews.new()
    
    # Load the JSON data
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    base_path = data['base_path']
    icons = data['icons']
    
    # Resolve the absolute path to the icons directory
    icons_dir = os.path.normpath(os.path.join(current_dir,"images","icons"))
    
    # Iterate through the JSON and load each icon
    for icon_name, icon_filename in icons.items():
        icon_path = os.path.join(icons_dir, icon_filename)
        
        # Safety check to ensure the file exists before loading
        if not os.path.exists(icon_path):
            print(f"Warning: Icon not found at {icon_path}")
            continue
            
        # Load the image into the preview collection
        pcoll.load(icon_name, icon_path, 'IMAGE')
        
    # Store the collection in our global dictionary under a specific key
    return pcoll

def get_icons_pscroll():
    return preview_collections["ui_icons"]




def load_asset_icons(icons_py_path=None):
    """
    Imports a compiled Qt resource file (icons.py) from a direct file path
    and loads its embedded images directly into a Blender preview collection.
    
    :param icons_py_path: Optional full file path to icons.py. If None, defaults to relative path.
    """
    
    # 0. Fallback to default relative path if no path argument is provided
    if not icons_py_path:
        BASE_DIR = os.path.dirname(__file__)
        icons_py_path = os.path.join(BASE_DIR, "asset_browser", "icons", "icons.py")
    
    # 1. Ensure the file exists
    if not os.path.isfile(icons_py_path):
        raise FileNotFoundError(f"Specified icons file does not exist: {icons_py_path}")

    # 2. Ensure Qt bindings are available in Blender
    try:
        from PySide6 import QtCore
    except ImportError:
        try:
            from PyQt6 import QtCore
        except ImportError:
            raise ImportError("PySide6 or PyQt6 must be installed in Blender's Python environment.")

    # 3. Dynamically import module from explicit file path
    dir_path = os.path.dirname(icons_py_path)
    module_name = os.path.splitext(os.path.basename(icons_py_path))[0]

    if dir_path not in sys.path:
        sys.path.insert(0, dir_path)

    spec = importlib.util.spec_from_file_location(module_name, icons_py_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec from: {icons_py_path}")

    qt_rc_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qt_rc_module)  # Executes code & registers qInitResources()

    # 4. Extract resource binary data into a Blender Preview Collection
    pcoll = bpy.utils.previews.new()
    root_path = ":/"
    iterator = QtCore.QDirIterator(root_path, QtCore.QDirIterator.IteratorFlag.Subdirectories)
    
    # Create a persistent cache directory for icons (not deleted after loading)
    addon_cache_dir = os.path.join(tempfile.gettempdir(), "blender_addon_icons")
    os.makedirs(addon_cache_dir, exist_ok=True)

    while iterator.hasNext():
        resource_path = iterator.next()

        # CHANGE 1: Filter out built-in Qt resources (e.g. Qt system icons/assets)
        if resource_path.startswith(":/qt-project.org") or resource_path.startswith(":/qt/"):
            continue

        qfile = QtCore.QFile(resource_path)

        if qfile.open(QtCore.QIODevice.OpenModeFlag.ReadOnly):
            file_data = qfile.readAll().data()
            qfile.close()

            # CHANGE 2: Build a unique key from relative path (e.g., ":/icons/item.png" -> "icons_item")
            clean_rel_path = resource_path.lstrip(":/")
            icon_key = os.path.splitext(clean_rel_path)[0].replace("/", "_")

            if not icon_key:
                icon_key = os.path.basename(resource_path).rsplit('.', 1)[0]

            # CHANGE 3: Prevent crashing if duplicate keys exist
            if icon_key in pcoll:
                continue

            # Write to persistent cache (not deleted after loading)
            cache_file_path = os.path.join(addon_cache_dir, f"{icon_key}.png")
            
            # Only write if not already cached (avoids repeated writes)
            if not os.path.exists(cache_file_path):
                with open(cache_file_path, "wb") as f:
                    f.write(file_data)

            # Register with Blender UI (file persists, so icon stays visible)
            pcoll.load(icon_key, cache_file_path, 'IMAGE')

    return pcoll

def get_asset_icons_pcoll():
    return preview_collections["asset_icons"]



def register_icons():
    pcoll = extract_pcoll()
    
    icon_dir = os.path.join(os.path.dirname(__file__), "images","plugin_icon.png")
    pcoll.load("plugin_icon", icon_dir, 'IMAGE')
    
    asset_pcoll = load_asset_icons()
    
    
    preview_collections["ui_icons"] = pcoll
    preview_collections["asset_icons"] = asset_pcoll


def unregister_icons():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()