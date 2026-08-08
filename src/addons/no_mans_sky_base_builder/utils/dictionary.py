import os
from . import python as python_utils

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
NICE_JSON = os.path.join(FILE_PATH,"..","resources","nice_names.json")

nice_name_dictionary = python_utils.load_dictionary(NICE_JSON)

def get_nice_names_diictionary():
    return nice_name_dictionary