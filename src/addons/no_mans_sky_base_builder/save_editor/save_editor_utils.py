import os
import platform
from pathlib import Path
from ..utils import python as python_utils
from .. import platforms_manager

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
SAVE_MAP_JSON_FILE = os.path.join(FILE_PATH, "save_map_dictionary.json")

"""
#########################
In this file anything with obf in it means obfuscated, since json keys from imported save file are obfuscated during compressing for reducing size.
eng here means human readable translations of those keys.
#########################
"""

# two copies, one in reverse and one normal are kept to optimise search
save_map_dictionary_reversed = python_utils.load_dictionary(SAVE_MAP_JSON_FILE)
save_map_dictionary = {v: k for k, v in save_map_dictionary_reversed.items()}

# lambda functions to call to translate simple string values
eng_to_obf_translator = lambda k: save_map_dictionary.get(k, k)
obf_to_eng_translator = lambda k: save_map_dictionary_reversed.get(k, k)

#hignly used obfuscated strings for traversing save file
base_context = eng_to_obf_translator("BaseContext")
player_state_data = eng_to_obf_translator("PlayerStateData")
persistent_player_bases = eng_to_obf_translator("PersistentPlayerBases")
base_name = eng_to_obf_translator("Name")
base_type = eng_to_obf_translator("BaseType")
persistent_base_types = eng_to_obf_translator("PersistentBaseTypes")
galactic_address = eng_to_obf_translator("GalacticAddress")


#this function recursively replaces keys according to mapping provided by translator
def translate_data(obj,translator):
    if isinstance(obj, dict):
        new_dict = {} 
        for key, value in obj.items():
            # Translate the key if it exists in the map, otherwise keep the original
            new_key = translator(key)
            # Recursively process the value (to handle nested dicts/lists)
            new_dict[new_key] = translate_data(value, translator)
            
        return new_dict
    elif isinstance(obj, list):
        # if child is a list, process every item in it
        return [translate_data(item, translator) for item in obj]
    else:
        return obj
    

def translate_to_eng_data(data):
    return translate_data(data,obf_to_eng_translator)

def translate_to_obf_data(data):
    return translate_data(data,eng_to_obf_translator)

    
#Returns all account folders
def get_accounts_list():
    accounts_list = []
    root_dir = platforms_manager.get_root_save_folder()
    for folder in root_dir.iterdir():
        if not folder.is_dir():
            continue
        # Steam/Gamepass account folders
        if folder.name.startswith("st_"):
            accounts_list.append(folder)
    return accounts_list


def get_save_slots_list(account):
    hg_files_list = []
    for file in Path(account).glob("save*.hg"):
        hg_files_list.append(file)
    
    save_slots = []
    prev_slot = None
    for file in hg_files_list:
        file_number = file.name[4]  # Assuming the format is "save*.hg"
        if file_number.isdigit():
            number = int(file_number)
            if number%2 == 0:
                save_slot_number = number//2
                saves_links = [str(prev_slot), str(file)]
                save_slots.append({
                    "slot": save_slot_number,
                    "saves": saves_links
                })
        prev_slot = file
    return save_slots  

def get_bases_list(save_slot):
    
    save_location = save_slot["saves"][0]
    print("getting bases list for save slot:", save_slot)
    
    from .hg_save_file import HGFile
    save_file = HGFile(save_location)
    
    data = save_file.load()
    bases_list = []
    for index, base in enumerate(data[base_context][player_state_data][persistent_player_bases]):
        bases_list.append({
            "index": index,
            "name": base[eng_to_obf_translator("Name")],
            "base_type": base[eng_to_obf_translator("BaseType")][eng_to_obf_translator("PersistentBaseTypes")],
        })
    return bases_list

def get_persistent_player_bases(save_slot):
    save_location = get_lastes_save_file_location(save_slot)
    
    from .hg_save_file import HGFile
    save_file = HGFile(save_location)
    
    data = save_file.load()
    obfuscated_persistent_base_data = data[base_context][player_state_data][persistent_player_bases]
    
    return obfuscated_persistent_base_data

def get_lastes_save_file_location(save_slot):
    saves = save_slot["saves"]
    
    save_1 = Path(saves[0])
    save_2 = Path(saves[1])
    
    m_time_save_1 = os.path.getmtime(save_1)
    m_time_save_2 = os.path.getmtime(save_2)
    
    return save_1 if m_time_save_1 > m_time_save_2 else save_2

def matches_base(base, identifier):
    return (
        base[base_name] == identifier["base_name"]
        and base[base_type][persistent_base_types] == identifier["base_type"]
        and base[galactic_address] == identifier["galactic_address"]
    )

    
def save_base_to_save_file(objects_data, base_identifier,  save_slot):
    save_location = get_lastes_save_file_location(save_slot)
    
    from .hg_save_file import HGFile
    save_file = HGFile(save_location)
    
    data = save_file.load()
    
    base_list = data[base_context][player_state_data][persistent_player_bases]
    
    try:
        in_base = base_list[base_identifier["base_index"]]
    except IndexError:
        print("base not found")
        return
    
    base_found = matches_base(in_base,base_identifier)
    
    if not base_found:
        for base in base_list:
            if matches_base(base, base_identifier):
                in_base = base
                base_found = True
                    
    if not base_found:
        return
    
    key_objects = eng_to_obf_translator("Objects")
    obf_objects_data = translate_to_obf_data(objects_data)
    in_base[key_objects] = obf_objects_data
    
    save_file.make_backup()
    save_file.save()
    
        
