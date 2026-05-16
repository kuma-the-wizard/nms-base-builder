import bpy
from . import builder

BUILDER = builder.Builder()

# Setting Support Methods ---
def ShowMessageBox(message="", title="Message Box", icon="INFO"):
    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def part_switch(self, context):
    """Toggle method for switching between parts and presets."""
    scene = context.scene
    part_list = "presets" if self.enum_switch == {"PRESETS"} else "parts"

    if self.enum_switch not in [{"PRESETS"}]:
        refresh_ui_part_list(scene, part_list, pack=list(self.enum_switch)[0])
    else:
        refresh_ui_part_list(scene, part_list)


def get_line_type_from_enum(context):
    line_object = "U_POWERLINE"
    scene = context.scene
    nms_tool = scene.nms_base_tool
    line_value = list(nms_tool.line_switch)[0]
    if line_value == "TELEPORT":
        line_object = "U_PORTALLINE"
    elif line_value == "PIPE":
        line_object = "U_PIPELINE"
    elif line_value == "BYTEBEAT":
        line_object = "U_BYTEBEATLINE"
    return line_object

def create_sublists(input_list, n=3):
    """Create a list of sub-lists with n elements."""
    if not input_list:
        return []
    total_list = [input_list[x : x + n] for x in range(0, len(input_list), n)]
    # Fill in any blanks.
    last_list = total_list[-1]
    while len(last_list) < n:
        last_list.append("")
    return total_list


def generate_ui_list_data(item_type="parts", pack=None):
    """Generate a list of Blender UI friendly data of categories and parts.

    When we retrieve presets we just want an item name.

    For parts I am doing a trick where I am grouping sets of 3 parts in order
    to make a grid in each UIList entry.

    Args:
        item_type (str): The type of items we want to retrieve
            options - "presets", "parts".

    Return:
        list: tuple (str, str): Label and Description of items for the UIList.
    """
    ui_list_data = []
    # Presets
    if "presets" in item_type:
        preset_categories = BUILDER.get_preset_categories()
        for category in preset_categories:
            presets = BUILDER.get_presets_from_category(category)
            if presets:
                ui_list_data.append((category, ""))
                for _preset in sorted(presets):
                    ui_list_data.append(("", _preset))
        # Uncategorized.
        presets = BUILDER.get_uncategorized_presets()
        if presets:
            ui_list_data.append(("Uncategorized Presets", ""))
            for _preset in sorted(presets):
                ui_list_data.append(("", _preset))
    else:
        # Packs/Parts
        for category in BUILDER.get_categories(pack=pack):
            ui_list_data.append((category, ""))
            category_parts = BUILDER.get_parts_from_category(category, pack=pack)
            category_parts = sorted(category_parts, key=BUILDER.get_nice_name)
            new_parts = create_sublists(category_parts)
            for part in new_parts:
                joined_list = ",".join(part)
                ui_list_data.append(("", joined_list))
    return ui_list_data

def refresh_ui_part_list(scene, item_type="parts", pack=None):
    """Refresh the UI List.

    Args:
        item_type: The type of items we want to retrieve.
            options - "presets", "parts".
    """
    # Clear the scene col.
    try:
        scene.col.clear()
    except:
        pass

    # Get part data based on
    ui_list_data = generate_ui_list_data(item_type=item_type, pack=pack)
    # Create items with labels and descriptions.
    for i, (label, description) in enumerate(ui_list_data, 1):
        item = scene.col.add()
        item.title = label.title().replace("_", " ")
        item.description = description
        item.item_type = item_type
        item.name = " ".join((str(i), label, description))