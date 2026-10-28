"""Discard a disabled add-on's cached children before loading an updated root.

Blender reloads __init__.py when an installed ZIP changes, but Python's
ordinary relative imports can still return the previous release's modules.
Only this package is cleared; dependencies and other add-ons are untouched.
"""
import sys


def prepare_package(namespace):
    name = namespace['__name__']
    prefix = name + '.'
    children = [key for key in sys.modules if key.startswith(prefix) and key != __name__]
    if not children:
        return
    if namespace.get('__addon_enabled__') or namespace.get('_core_registered'):
        raise RuntimeError('Close and reopen Blender before updating BBE; its previous version is still running')
    for key in sorted(children, key=lambda item: item.count('.'), reverse=True):
        child = sys.modules.pop(key)
        parent_name, _, attribute = key.rpartition('.')
        parent = sys.modules.get(parent_name)
        if parent is not None and getattr(parent, attribute, None) is child:
            delattr(parent, attribute)
