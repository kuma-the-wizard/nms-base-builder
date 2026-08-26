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
        
    icon_dir = os.path.join(os.path.dirname(__file__), "images","plugin_icon.png")
    pcoll.load("plugin_icon", icon_dir, 'IMAGE')
        
    # Store the collection in our global dictionary under a specific key
    return pcoll


def get_asset_icons_pcol():
    """
    Directly imports the compiled Qt resource module and populates
    a Blender preview collection.
    """
    # Ensure Qt bindings are available
    try:
        from PySide6 import QtCore
    except ImportError:
        try:
            from PyQt6 import QtCore
        except ImportError:
            raise ImportError("PySide6 or PyQt6 must be installed in Blender's environment.")
    from .asset_browser.icons import icons
    
    # Extract resource data from Qt's virtual filesystem (:/)
    pcoll = bpy.utils.previews.new()
    addon_cache_dir = os.path.join(tempfile.gettempdir(), "blender_addon_icons")
    os.makedirs(addon_cache_dir, exist_ok=True)
    iterator = QtCore.QDirIterator(":/", QtCore.QDirIterator.IteratorFlag.Subdirectories)

    while iterator.hasNext():
        resource_path = iterator.next()
        if resource_path.startswith(":/qt-project.org") or resource_path.startswith(":/qt/"):
            continue

        qfile = QtCore.QFile(resource_path)
        if qfile.open(QtCore.QIODevice.OpenModeFlag.ReadOnly):
            file_data = qfile.readAll().data()
            qfile.close()

            clean_rel_path = resource_path.lstrip(":/")
            icon_key = os.path.splitext(clean_rel_path)[0].replace("/", "_")
            if not icon_key:
                icon_key = os.path.basename(resource_path).rsplit('.', 1)[0]

            if icon_key in pcoll:
                continue

            cache_file_path = os.path.join(addon_cache_dir, f"{icon_key}.png")
            if not os.path.exists(cache_file_path):
                with open(cache_file_path, "wb") as f:
                    f.write(file_data)

            pcoll.load(icon_key, cache_file_path, 'IMAGE')

    return pcoll

def load_asset_icons():
    """
    Scans a folder for PNGs and loads them into a Blender preview collection.
    """
    # Create a new preview collection
    pcoll = bpy.utils.previews.new()
    
    directory_path = os.path.realpath(
        os.path.join(os.path.dirname(__file__), "images","asset_icons")
    )
    
    
    if not os.path.exists(directory_path):
        print(f"Directory not found: {directory_path}")
        return None

    # Loop through the directory and find all PNGs
    for filename in os.listdir(directory_path):
        if filename.lower().endswith(".png"):
            filepath = os.path.join(directory_path, filename)
            
            # Use the filename without the .png extension as the icon identifier
            icon_name = os.path.splitext(filename)[0]
            
            # Load the image into the preview collection
            # 'IMAGE' type is required for UI icons
            pcoll.load(icon_name, filepath, 'IMAGE')

    return pcoll

def get_asset_icons_pcoll():
    return preview_collections["asset_icons"]

def get_icons_pscroll():
    return preview_collections["ui_icons"]

def register_icons():
    pcoll = extract_pcoll()
    asset_pcoll = load_asset_icons()
    
    preview_collections["ui_icons"] = pcoll
    if asset_pcoll:
        preview_collections["asset_icons"] = asset_pcoll


def unregister_icons():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()