import os
from ..utils import python as python_utils
from .hg_save_file import NMSHGFile

FILE_PATH = os.path.dirname(os.path.realpath(__file__))

SAVE_MAP_JSON_FILE = os.path.join(FILE_PATH, "save_map_dictionary.json")
save_map_dictionary_reversed = python_utils.load_dictionary(SAVE_MAP_JSON_FILE)

TESTING_HG_FILE = os.path.join(FILE_PATH,"testing", "save.hg")

save_map_dictionary = {v: k for k, v in save_map_dictionary_reversed.items()}

eng_to_obf_translator = lambda k: save_map_dictionary.get(k, k)
obf_to_eng_translator = lambda k: save_map_dictionary_reversed.get(k, k)

#Recursively replaces keys from one form to another
def translate_data(obj,translator):
    if isinstance(obj, dict):
        new_dict = {} 
        for key, value in obj.items():
            # Translate the key if it exists in the map, otherwise keep the original
            new_key = translator(key)
            # Recursively process the value (to handle nested dicts/lists)
            print("replacing key:", key, "with:", new_key)
            new_dict[new_key] = translate_data(value, translator)
            
        return new_dict
    elif isinstance(obj, list):
        # Process every item in a list (like coordinates)
        return [translate_data(item, translator) for item in obj]
    else:
        # Return the value as-is if it's not a container
        return obj
        
def load_save_file():
    save_file = NMSHGFile(os.path.join(FILE_PATH, "testing", "save.hg"))
    data = save_file.load()
    
    base_context = eng_to_obf_translator("BaseContext")
    player_state_data = eng_to_obf_translator("PlayerStateData")
    persistent_player_bases = eng_to_obf_translator("PersistentPlayerBases")
    name = eng_to_obf_translator("Name")
    
    
    #print(data[translator(key_base_context)][translator(key_player_state_data)][translator(key_persistent_player_bases)])
    bases = data[base_context][player_state_data][persistent_player_bases]  
    for base in bases:
        print(base[name], base["CVX"])
    return "This is a test string from load_save_file() in conversion_utils.py"

