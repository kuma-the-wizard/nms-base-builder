"""The UI drawn inside the "Base Builder" dropdown.

Kept apart from base_builder_menu.py the same way the save manager splits its
panel registration from its draw code, so the popover stays a thin host.
"""

import bpy


def get_nms_main(context):
    """The addon's main property group, or None if it is not registered yet.

    A draw can run at awkward moments - during registration, or after the addon
    is disabled while the header is still on screen - so nothing here assumes
    the scene properties exist.
    """
    return getattr(context.scene, "nms_main", None)


def draw_base_builder_menu(layout, context):
    """Draw the Base Builder dropdown's contents into `layout`."""

    nms_main = get_nms_main(context)

    # Clipboard: the same three controls as the clipboard box in the
    # Import/Export panel. The box frames them as a section of their own,
    # so further sections can be added below without running together.
    clipboard_box = layout.column(align=True)
    clipboard_box.label(text="Clipboard")
    clipboard_box.separator()
    clipboard_column = clipboard_box.column(align=False)
    clipboard_column.operator("object.nms_import_nms_data", icon="PASTEDOWN")
    clipboard_export_column = clipboard_column.column(align=True)
    if nms_main is not None:
        # The export operator reads this off the scene when it runs, so
        # this checkbox and the panel's are the one setting.
        clipboard_export_column.prop(nms_main, "check_export_objects_only", text="Objects Only")

    clipboard_export_column.operator("object.nms_export_nms_data", icon="COPYDOWN")

    # Proxy Quality: switch every placed part in the scene between the
    # models-high-res library and the old fbx proxies.
    proxy_box = layout.column(align=True)
    proxy_box.separator()
    proxy_box.label(text="Proxy Quality")
    proxy_box.separator()
    proxy_column = proxy_box.column(align=True)
    proxy_column.operator("object.nms_switch_proxies_to_low", icon="MESH_CUBE")
    proxy_column.operator("object.nms_switch_proxies_to_high", icon="MESH_MONKEY")
