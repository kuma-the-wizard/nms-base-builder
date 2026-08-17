import os
import csv
import re
from . import python as python_utils

FILE_PATH = os.path.dirname(os.path.realpath(__file__))

RESOURCES_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__),"..", "resources")
)

NICE_JSON = os.path.join(RESOURCES_DIR,"nice_names.json")
nice_name_dictionary = {}


PART_DEFINITION = os.path.join(RESOURCES_DIR, "DT_PartDefinition.csv")
part_definition_dictionary = {}

def to_title_case(text):
    parts = re.split(r'(\([^)]*\))', text)
    return ''.join(
        part if part.startswith('(') else part.title()
        for part in parts
    )

def get_nice_names_diictionary():
    global nice_name_dictionary
    
    if not nice_name_dictionary:
        nice_name_dictionary = python_utils.load_dictionary(NICE_JSON)
        
    return nice_name_dictionary

def get_parts_definition():
    global part_definition_dictionary
    
    if not part_definition_dictionary:
        with open(PART_DEFINITION, "r", encoding="utf-16") as csv_file:
            csv_reader = csv.reader((x.replace("\0", "") for x in csv_file), delimiter=",")
            for index, row in enumerate(csv_reader):
                if not row or index == 0:
                    continue
                
                m_obj_id = row[0]
                part_definition_dictionary[m_obj_id] = row
                
    return part_definition_dictionary

def get_category_vise_objects():
    categories_list = {}
    part_definition = get_parts_definition()
    
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
        
        nice_name = to_title_case(nice_name)
        
        
        if category not in categories_list:
            categories_list[category] = {}
        
        if sub_category not in categories_list[category]:
            categories_list[category][sub_category] = {}
            
        sub_cat = categories_list[category][sub_category]
        
        
        
        if varaint_of == "None":
            if object_id not in sub_cat:
                sub_cat[object_id] = {}
                
            sub_cat[object_id]["name"] = nice_name
        else:
            if varaint_of not in sub_cat:
                sub_cat[varaint_of] = {
                    "name" : nice_name
                }
                
            if "variants" not in sub_cat[varaint_of]:
                sub_cat[varaint_of]["variants"] = []
            
            sub_cat[varaint_of]["variants"].append(object_id)
            
            
    return categories_list
        
    