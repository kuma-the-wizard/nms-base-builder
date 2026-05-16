import os
import json
import platform
import struct
import lz4.block
from pathlib import Path

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
from ..save_editor import hg_save_file
from ..save_editor.hg_save_file import NMSHGFile


class NMSSaveManager:
    
    def __init__(self, root_dir=None):
        if root_dir is None:
            system = platform.system()
            if system == "Windows":
                root_dir = (Path.home()/ "AppData/Roaming/HelloGames/NMS" )
            elif system == "Darwin":
                # macOS
                root_dir = (Path.home()/ "Library/Application Support/HelloGames/NMS" )
            elif system == "Linux":
                # Proton / Steam Play
                root_dir = (Path.home() / ".steam/steam/steamapps/compatdata" )
            else:
                raise RuntimeError(f"Unsupported OS: {system}")
        self.root_dir = Path(root_dir)

    def decompress_hg(self, filepath):
        with open(filepath, "rb") as f:
            data = f.read()
        size = struct.unpack("<I", data[:4])[0]
        decompressed = lz4.block.decompress(
            data[4:],
            uncompressed_size=size
        )
        return json.loads(decompressed.decode("utf-8"))

    def get_accounts(self):
        #Returns all account folders
    
        accounts = []
        for folder in self.root_dir.iterdir():
            if not folder.is_dir():
                continue
            # Steam/Gamepass account folders
            if folder.name.startswith("st_"):
                accounts.append(folder)
        return accounts

    def get_all_saves(self):

        all_accounts = []
        for account_folder in self.get_accounts():
            account_data = {
                "account_id": account_folder.name,
                "saves": []
            }
            for file in account_folder.glob("save*.hg"):
                account_data["saves"].append({
                    "filepath": str(file),
                    "save_name": file.stem,
                })
                
                
                #print(f"Reading save file: {file}")
                #save_file = NMSHGFile(file)
                #data = save_file.load()
                #common_state_data = hg_save_file.eng_to_obf_translator("CommonStateData")
                #save_name = hg_save_file.eng_to_obf_translator("SaveName")
                #savename_string = data[common_state_data][save_name]
                #print("Save Name:", savename_string)

            #account_data["saves"].sort(
            #    key=lambda x: x["slot"]
            #)
            print(account_data)
            all_accounts.append(account_data)

        return all_accounts