import importlib
import os
import site
import subprocess
import sys

# Check and install dependencies.
PYTHON_EXE_PATH = sys.executable


# target_dir = os.path.join(sys.exec_prefix, "lib", "site-packages")

for p in site.getusersitepackages().split(os.pathsep):
    if p not in sys.path:
        sys.path.append(p)


def install_pip():
    command = [PYTHON_EXE_PATH, "-m", "ensurepip", "--upgrade"]
    subprocess.run(command)


def install_package(package_name):
    command = [PYTHON_EXE_PATH, "-m", "pip", "install", package_name]
    subprocess.run(command)


def check_dependencies():
    try:
        import pip

        print("Pip found.")
    except:
        install_pip()
        importlib.reload(site)

    try:
        import PySide6

        print("PySide6 found.")
    except:
        install_package("PySide6_Essentials")
        importlib.reload(site)

    return True
