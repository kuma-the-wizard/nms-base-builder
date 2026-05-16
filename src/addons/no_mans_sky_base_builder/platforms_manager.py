import os
import sys
import platform
from pathlib import Path

def get_platform_folder():
    system = platform.system()
    machine = platform.machine().lower()

    if system == "Windows":
        return "win_amd64"

    elif system == "Linux":
        return "linux_x86_64"

    elif system == "Darwin":

        if machine == "arm64":
            return "macos_arm64"

        return "macos_x86_64"

    raise RuntimeError(f"Unsupported platform: {system}")

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
    

def get_lib_directory():
    addon_dir = os.path.dirname(__file__)
    
    # Blender python version
    python_version = f"cp{sys.version_info.major}{sys.version_info.minor}"
    print("python version in blender is  : ",python_version)
    
    libs_dir = os.path.join(
        addon_dir,
        "libs",
        python_version,
        get_platform_folder()
    )
    return libs_dir