import os
import sys
import platform
from pathlib import Path


def get_root_save_folder():
    system = platform.system()
    if system == "Windows":
        return (Path.home()/ "AppData/Roaming/HelloGames/NMS" )
    elif system == "Darwin":
        # macOS
        return (Path.home()/ "Library/Application Support/HelloGames/NMS" )
    elif system == "Linux":
        # Proton / Steam Play
        return (Path.home() / ".steam/steam/steamapps/compatdata" )
    else:
        raise RuntimeError(f"Unsupported OS: {system}")
