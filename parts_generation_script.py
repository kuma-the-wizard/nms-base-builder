
""" 
HOW TO USE THIS SCRIPT:

 - Open parts.blend file present in src\addons\no_mans_sky_base_builder\native_asset_browser folder
 - switch to "Scripting"workspace from above.
 - paste this file there and run it
 - Apply rotation transformation so that to newly generated obejcts with ctrl + a

"""

import bpy
import csv
import os
import uuid
import re
import json

#nice names json
nice_name_json_path_str = "E:\\Base Builder Plugin 2\\nms-base-builder\\src\\addons\\no_mans_sky_base_builder\\resources\\nice_names.json"
NICE_NAMES_PATH = os.path.normpath(nice_name_json_path_str)
nice_name_dictionary = {}
with open(NICE_NAMES_PATH, "r") as stream:
    nice_name_dictionary = json.load(stream)

# builder object
from bl_ext.user_default.no_mans_sky_base_builder import builder
BUILDER = builder.Builder()

#parts definition
parts_definition_path = "E:\\Base Builder Plugin 2\\nms-base-builder\\src\\addons\\no_mans_sky_base_builder\\resources\\DT_PartDefinition.csv"
PART_DEFINITION = os.path.normpath(parts_definition_path)

#Edit this file to add new catalogs/ sub-catalogs
library_catalogues_path = "E:\\Base Builder Plugin 2\\nms-base-builder\\src\\addons\\no_mans_sky_base_builder\\native_asset_browser\\blender_assets.cats.txt"
CATS = os.path.normpath(library_catalogues_path)

# Folder containing icons, name of icon should be same as "ObjectID" it is representing
icon_path = "E:\\Experiment\\icon extraction\\icons_with_id\\"

# convert uppercase text to title case
def beaufity_name(text):
    parts = re.split(r'(\([^)]*\))', text)
    return ''.join(
        part if part.startswith('(') else part.title()
        for part in parts
    )

def read_parts_definition():
    existing_rows = {}
    if not os.path.exists(PART_DEFINITION):
        print(f"File not found: {PART_DEFINITION}")
        return existing_rows
        
    with open(PART_DEFINITION, "r", encoding="utf-16") as csv_file:
        csv_reader = csv.reader((x.replace("\0", "") for x in csv_file), delimiter=",")
        for idx, row in enumerate(csv_reader):
            if (not row) or (idx == 0):
                continue
            id = row[0]
            existing_rows[id] = row
    return existing_rows

def read_cats():
    existing_catalogues = {}
    if not os.path.exists(CATS):
        print(f"File not found: {PART_DEFINITION}")
        return {}
    
    with open(CATS, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines, comments, and the version header
            if not line or line.startswith("#") or line.startswith("VERSION"):
                continue
            
            # The format is "catalogue name ": "UUID"
            parts = line.split(":")
            if len(parts) >= 2:
                existing_catalogues[parts[1]] = parts[0]      
    return existing_catalogues

# add new unique parts to scene that dont exist
def add_new_parts(part_definitions):
    new_parts = {}
    for obj_id, value in part_definitions.items():
        object_id = str(value[0])[1:]
        if object_id in nice_name_dictionary:
            nice_name = nice_name_dictionary[object_id]
            new_asset_name = beaufity_name(nice_name)
            new_item =  BUILDER.add_part(object_id)
            new_asset = new_item.object
            new_parts.name = new_asset_name
            # this marks this object as native asset
            new_parts["is_native_asset"] = True
            new_parts[object_id] = new_asset
            
            
            
# mark give parts as assets
def mark_parts_as_assets(new_parts, assign_icons = True):
    for obj_id, value in part_definitions.items():
        object_id = str(value[0])[1:]
        if object_id not in new_parts:
            continue
        
        part = new_parts.get(object_id,None)
        if part is not None:
            continue
        
        # catalog name is category_name/subcategory_name
        catalogue_name = value[2]+"/"+value[4]
        # mark a asset with a catalog's UUID
        catalogue_uuid = catalogues.get(catalogue_name,None)
        if catalogue_uuid is None:
            continue
        
        # mark an object in file as asset
        part.asset_mark()
        # assign catalog as categories and sub categories defined in PT_ParDefinition
        part.asset_data.catalog_id = catalogue_uuid
        
        # folder path + object_id.png
        preview_icon_path = icon_path +object_id +".png"
        if assign_icons:
            if os.path.exists(preview_icon_path):
                with bpy.context.temp_override(id=part):
                    bpy.ops.ed.lib_id_load_custom_preview(filepath=preview_icon_path)
                print(f"Successfully loaded preview for {part.name}")
            else:
                print("Error: Image path does not exist.")
            
            
catalogues = read_cats()
part_definitions = read_parts_definition()
new_parts = add_new_parts(part_definitions)
mark_parts_as_assets(new_parts)


# Deselect everything first
bpy.ops.object.select_all(action='DESELECT')

# Select all Mesh objects in the scene
for obj in new_parts:
    if obj.type == 'MESH':
        obj.select_set(True)
        # Set the last found mesh as the active object
        bpy.context.view_layer.objects.active = obj
