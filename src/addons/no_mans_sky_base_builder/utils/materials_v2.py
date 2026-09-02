"""Colouring for the models-high-res asset library.

The old material system (utils/material.py) paints a part by swapping a flat
coloured material into slot 0. That works for the flat FBX proxies, but it
throws away the real game textures and it forces one material - and therefore
one mesh datablock - per (ObjectID, UserData) pair.

The high-res library works the other way round. Every colourable material in
models-high-res/assets carries an "NMS_Colourise" node group whose four palette
slots are Attribute nodes of type OBJECT, reading the object custom properties
nms_p / nms_s / nms_t / nms_q. So the colour lives on the OBJECT, not on the
material, and colouring a part is four property writes - no material is touched
and nothing has to be duplicated.

That is what makes the whole thing cheap: a thousand placements of the same
part share ONE mesh and ONE set of materials and can still each be a different
colour. Never copy a mesh or a material just to recolour something here.

UserData layout (the same bitfield utils/userdata.py already implements):

    colour index = UserData & 0xFFFFFF      bits 8, 16, 17 are reserved
    finish index = (UserData >> 24) & 0xFF  material/finish, not colour

The colour index indexes resources/colour_palette_by_index.json, extracted from
the game's own basebuildingobjectstable and cross-checked 84/84 against
resources/DT_Palettes.csv. The JSON is the wider of the two - all 115 palettes
with all four slots, against the CSV's 84 with two.

Note the finish index only feeds the readable "Material" label - the library
implements the colour half of the system, not the surface finishes.
"""

import json
import os

import bpy

from ..utils import material
from ..utils import userdata

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
RESOURCES_PATH = os.path.join(FILE_PATH, "..", "resources")

PALETTE_JSON = os.path.join(RESOURCES_PATH, "colour_palette_by_index.json")

# The four object properties the NMS_Colourise node group reads, in slot order
# (primary, secondary, ternary, quaternary). These names are baked into the
# node group inside every asset file, so they cannot be renamed here alone.
SLOT_PROPS = ("nms_p", "nms_s", "nms_t", "nms_q")

# Name prefix of the colourise node group carried by every asset file.
COLOURISE_GROUP = "NMS_Colourise"

# Written onto every mesh appended from models-high-res, holding the object id
# it came from. It marks a part as belonging to the new colour system, which is
# what the old material code checks before deciding to paint a flat material
# over it. It lives here rather than in builder_v2 so that utils/material.py can
# read it without importing the importer.
MESH_TAG = "nms_high_res_id"

# Readable labels, so the viewport overlay keeps showing colour/material names.
PROP_READONLY_COLOUR = "readonly:Colour"
PROP_READONLY_MATERIAL = "readonly:Material"

# Loaded on first use rather than at import time - the addon registers a lot of
# modules and there is no point reading 47KB of JSON for a session that never
# imports a base.
_palette_by_index = None
_colour_labels = None
_finish_labels = None


# Palette data ---
def _load_palettes():
    """Load and cache the palette table and the readable labels.

    Both labels come from DT_Palettes.csv where it has them, because it is what
    the rest of the addon already displays and its names are the real English
    ones. The palette JSON only resolved the 16 LEGACY names when it was
    extracted - the other 99 are still internal keys like SET_FREIGHTER_7 - so
    it is the fallback for the 31 palettes the CSV doesn't cover, not the
    first choice.

    The finish label HAS to come from the CSV. In the game's own material table
    the finish index is only unique within a material group - index 1 is "Rust"
    for the legacy group and "Builders C" for the builders group - and UserData
    carries no group id to tell them apart. The CSV is keyed on the colour AND
    finish index together, which resolves it.

    Returns:
        tuple: (palette by colour index, colour label by colour index,
            finish label by (colour index, finish index))
    """
    global _palette_by_index, _colour_labels, _finish_labels
    if _palette_by_index is not None:
        return _palette_by_index, _colour_labels, _finish_labels

    with open(PALETTE_JSON, "r", encoding="utf-8") as palette_file:
        raw = json.load(palette_file)
    _palette_by_index = {int(key): value for key, value in raw.items()}

    # material.BAKED_COLOURS is the CSV, already parsed once at import time.
    _colour_labels = {}
    _finish_labels = {}
    for row in material.BAKED_COLOURS:
        try:
            colour_index = int(row[3])
            _colour_labels[colour_index] = row[5]
            _finish_labels[(colour_index, int(row[4]))] = row[2]
        except (IndexError, ValueError):
            continue

    return _palette_by_index, _colour_labels, _finish_labels


def decode_user_data(user_data_value):
    """Split a UserData value into its colour and finish indices.

    Args:
        user_data_value: The packed UserData value, int or numeric string.

    Returns:
        tuple: (colour index, finish index), or None if the value isn't a number.
    """
    try:
        value = int(user_data_value)
    except (TypeError, ValueError):
        return None
    return userdata.get_colour(value), userdata.get_material(value)


def get_palette(user_data_value):
    """Resolve a UserData value to its palette entry.

    Args:
        user_data_value: The packed UserData value.

    Returns:
        dict: {id, name_en, p, s, t, q} or None if the colour index is unknown.
    """
    indices = decode_user_data(user_data_value)
    if indices is None:
        return None
    palettes = _load_palettes()[0]
    return palettes.get(indices[0])


def get_nice_names(user_data_value):
    """Get the readable colour and finish names for a UserData value.

    Args:
        user_data_value: The packed UserData value.

    Returns:
        tuple: (colour name, finish name). Either can be None.
    """
    indices = decode_user_data(user_data_value)
    if indices is None:
        return None, None

    palettes, colour_labels, finish_labels = _load_palettes()
    colour_name = colour_labels.get(indices[0])
    if colour_name is None:
        palette = palettes.get(indices[0])
        colour_name = palette.get("name_en") if palette else None

    return colour_name, finish_labels.get(indices)


# Applying colour ---
def apply_palette(bpy_object, palette):
    """Write the four palette slots onto an object.

    Args:
        bpy_object (bpy.types.Object): The object to colour.
        palette (dict): A palette entry with p/s/t/q RGBA lists.
    """
    primary = tuple(palette["p"])
    bpy_object["nms_p"] = primary
    bpy_object["nms_s"] = tuple(palette["s"])
    bpy_object["nms_t"] = tuple(palette["t"])
    bpy_object["nms_q"] = tuple(palette["q"])

    # Solid viewport shading set to Object colour draws this, so parts can still
    # be told apart at a glance without waiting for textures. The old flat
    # material system did the same job through material.diffuse_color, but a
    # high res part shares its materials with every other placement of that id,
    # so the viewport colour has to live on the object - the same reason the
    # palette slots do. Primary is the part's body colour, so it is the one
    # that reads as "what colour is this part".
    bpy_object.color = primary


def apply(bpy_object, user_data_value, tag=True):
    """Colour a single object from a UserData value.

    Args:
        bpy_object (bpy.types.Object): The object to colour.
        user_data_value: The packed UserData value.
        tag (bool): Flag the object for a depsgraph re-evaluation. Skip this
            while bulk building - one view layer update at the end is enough.

    Returns:
        dict: The palette that was applied, or None if it didn't resolve, in
            which case the object is left untouched.
    """
    palette = get_palette(user_data_value)
    if palette is None:
        return None

    apply_palette(bpy_object, palette)
    colour_name, finish_name = get_nice_names(user_data_value)
    bpy_object[PROP_READONLY_COLOUR] = colour_name or ""
    bpy_object[PROP_READONLY_MATERIAL] = finish_name or ""
    if tag:
        bpy_object.update_tag()
    return palette


def apply_many(pairs, tag=False, update=False):
    """Colour a lot of objects at once.

    Each distinct UserData value is resolved once and reused, so the per object
    cost is just the four property writes.

    Args:
        pairs (iterable): An iterable of (bpy object, UserData value).
        tag (bool): Flag each object for re-evaluation as it goes.
        update (bool): Push a single view layer update when finished.

    Returns:
        tuple: (number coloured, number whose UserData didn't resolve)
    """
    cache = {}
    applied = 0
    unresolved = 0

    for bpy_object, user_data_value in pairs:
        key = str(user_data_value)
        if key not in cache:
            cache[key] = (get_palette(key), get_nice_names(key))
        palette, names = cache[key]

        if palette is None:
            unresolved += 1
            continue

        apply_palette(bpy_object, palette)
        bpy_object[PROP_READONLY_COLOUR] = names[0] or ""
        bpy_object[PROP_READONLY_MATERIAL] = names[1] or ""
        if tag:
            bpy_object.update_tag()
        applied += 1

    if update:
        bpy.context.view_layer.update()

    return applied, unresolved


def recolour(objects, colour_index=None, material_index=None, tag=True):
    """Repaint objects, writing the new indices into their UserData first.

    This is the replacement for material.assign_material on a high res part.
    Nothing is copied and no material is touched, so a hundred selected parts
    stay on the meshes they were already sharing - which is the whole point of
    the object property approach.

    Every bit of UserData outside the colour and finish fields is preserved,
    including the reserved ones, exactly as utils/userdata.py intends.

    Args:
        objects (iterable): The objects to repaint.
        colour_index (int): The new colour index, or None to leave it alone.
        material_index (int): The new finish index, or None to leave it alone.
        tag (bool): Flag each object for a depsgraph re-evaluation.

    Returns:
        tuple: (number coloured, number whose UserData didn't resolve)
    """
    pairs = []
    for bpy_object in objects:
        try:
            current = int(bpy_object.get("UserData", 0) or 0)
        except (TypeError, ValueError):
            current = 0

        value = userdata.update_colour_material(
            current, colour_index=colour_index, material_index=material_index
        )
        bpy_object["UserData"] = str(value)
        pairs.append((bpy_object, value))

    return apply_many(pairs, tag=tag)


def recolour_from_user_data(objects, user_data_value, tag=True):
    """Repaint objects to an exact UserData value.

    The replacement for material.restore_material on a high res part - used
    when the value is already known, such as the colour picker copying one
    part's look onto another.

    A value that doesn't resolve to a palette - None, or an index outside the
    table - leaves every object completely untouched, rather than stamping an
    unusable value into their UserData.

    Args:
        objects (iterable): The objects to repaint.
        user_data_value: The packed UserData value to apply wholesale.
        tag (bool): Flag each object for a depsgraph re-evaluation.

    Returns:
        tuple: (number coloured, number whose UserData didn't resolve)
    """
    objects = list(objects)

    # one value for all of them, so resolve it once and bail if it is no good
    palette = get_palette(user_data_value)
    if palette is None:
        return 0, len(objects)

    colour_name, finish_name = get_nice_names(user_data_value)
    value = str(user_data_value)

    for bpy_object in objects:
        bpy_object["UserData"] = value
        apply_palette(bpy_object, palette)
        bpy_object[PROP_READONLY_COLOUR] = colour_name or ""
        bpy_object[PROP_READONLY_MATERIAL] = finish_name or ""
        if tag:
            bpy_object.update_tag()

    return len(objects), 0


def clear(bpy_object):
    """Strip the colour properties, returning an object to its raw textures.

    An absent slot property reads as black inside the node group, so removing
    them also clears any stale colour rather than leaving it half applied.

    Args:
        bpy_object (bpy.types.Object): The object to clear.
    """
    for prop in SLOT_PROPS:
        if prop in bpy_object:
            del bpy_object[prop]
    bpy_object.update_tag()


def use_object_colour_in_viewport(enable=True, only_solid=True):
    """Point Solid viewport shading at the per object colour.

    Blender's Solid mode defaults to colouring by MATERIAL, which is what made
    the old flat material system readable - every part had its own material
    carrying its diffuse_color. High res parts share their materials, so under
    MATERIAL they all draw the same and the scene turns into one grey mass.
    OBJECT reads object.color instead, which both libraries now set.

    Textured and Rendered shading are unaffected either way - this only changes
    what Solid mode paints with.

    Args:
        enable (bool): True for OBJECT colour, False back to MATERIAL.
        only_solid (bool): Skip viewports that aren't in Solid shading, so a
            viewport somebody has deliberately put in Material Preview or
            Rendered is left alone.

    Returns:
        int: How many viewports were changed. Zero in background mode, which
            has no windows.
    """
    colour_type = "OBJECT" if enable else "MATERIAL"
    changed = 0

    window_manager = getattr(bpy.context, "window_manager", None)
    if window_manager is None:
        return 0

    for window in window_manager.windows:
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type != "VIEW_3D":
                    continue
                shading = space.shading
                if only_solid and shading.type != "SOLID":
                    continue
                if shading.color_type != colour_type:
                    shading.color_type = colour_type
                    changed += 1
    return changed


def is_high_res(bpy_object):
    """Check whether an object came out of the models-high-res library.

    This is the test the old material code uses to decide whether it may paint
    a flat material over something. It asks where the part came from rather
    than whether it happens to be colourable, because a high res part with no
    colourable material still must not be flattened - in game those parts just
    cannot be recoloured.

    Args:
        bpy_object (bpy.types.Object): The object to test.

    Returns:
        bool: True if its mesh carries the high res marker.
    """
    data = getattr(bpy_object, "data", None)
    return data is not None and MESH_TAG in data


def is_colourable(bpy_object):
    """Check whether an object actually responds to the colour properties.

    Args:
        bpy_object (bpy.types.Object): The object to test.

    Returns:
        bool: True if any of its materials carries the colourise node group.
    """
    for slot in bpy_object.material_slots:
        material_data = slot.material
        if material_data is None or material_data.node_tree is None:
            continue
        for node in material_data.node_tree.nodes:
            if node.type != "GROUP" or node.node_tree is None:
                continue
            if node.node_tree.name.startswith(COLOURISE_GROUP):
                return True
    return False


# Datablock sharing ---
#
# Appending is per file, and Blender has no idea that two asset files reference
# the same texture on disk or carry the same node group - it just appends both
# copies and renames the second one .001. Over a whole base that is the single
# biggest source of wasted memory, because textures are ~98% of the scene.
#
# Measured on 100 distinct assets / 6000 placed parts:
#   without dedupe   692 images, 67 node groups, 2580 MB, 6.96s to load textures
#   with dedupe      333 images,  1 node group,  1092 MB, 2.51s to load textures
#
# So it is worth roughly 2.4x the RAM and 2.8x the texture load time, for about
# a second of work at the end of an import. Materials are deliberately left
# alone - they are cheap once they share their images, and two same named
# materials from different assets are not guaranteed to be identical.
def dedupe_appended_data():
    """Collapse the datablocks the appends duplicated.

    Call this once, after a whole batch of assets is appended, never per asset
    - the cost is one walk over every material node tree, so doing it once for
    100 assets is 100x cheaper than doing it as they arrive.

    Returns:
        tuple: (images removed, node groups removed)
    """
    image_map = _plan_image_dedupe()
    group_map = _plan_node_group_dedupe()

    if not image_map and not group_map:
        return 0, 0

    _repoint_nodes(image_map, group_map)

    # one batch_remove for both - see _remove_dead
    dead_images = _collect_dead(image_map)
    dead_groups = _collect_dead(group_map)
    bpy.data.batch_remove(dead_images + dead_groups)
    return len(dead_images), len(dead_groups)


def dedupe_images():
    """Collapse image datablocks that point at the same file on disk.

    Returns:
        int: How many duplicate image datablocks were removed.
    """
    image_map = _plan_image_dedupe()
    if not image_map:
        return 0
    _repoint_nodes(image_map, None)
    return _remove_dead(image_map)


def dedupe_node_groups():
    """Collapse every appended copy of the colourise node group into one.

    Every asset file carries its own copy, so appending N assets leaves
    NMS_Colourise.001 ... .00N behind. They are identical by construction.

    Returns:
        int: How many duplicate groups were removed.
    """
    group_map = _plan_node_group_dedupe()
    if not group_map:
        return 0
    _repoint_nodes(None, group_map)
    return _remove_dead(group_map)


def _plan_image_dedupe():
    """Build {duplicate image: canonical image} for images sharing a file."""
    canonical_by_path = {}
    duplicates = {}

    for image in bpy.data.images:
        filepath = image.filepath
        if not filepath:
            continue
        key = os.path.normcase(bpy.path.abspath(filepath))
        canonical = canonical_by_path.get(key)
        if canonical is None:
            canonical_by_path[key] = image
        else:
            duplicates[image] = canonical

    return duplicates


def _plan_node_group_dedupe(prefix=COLOURISE_GROUP):
    """Build {duplicate group: canonical group} for the colourise copies."""
    groups = sorted(
        (group for group in bpy.data.node_groups if group.name.startswith(prefix)),
        key=lambda group: group.name,
    )
    if len(groups) < 2:
        return {}

    canonical = groups[0]
    return {group: canonical for group in groups[1:]}


def _repoint_nodes(image_map, group_map):
    """Swap every duplicate reference in every material for its canonical.

    One pass handles images and node groups together, because the walk itself
    is the expensive part - the node trees of a hundred appended assets are a
    few thousand nodes and every attribute read crosses into Blender.
    """
    for material_data in bpy.data.materials:
        node_tree = material_data.node_tree
        if node_tree is None:
            continue
        for node in node_tree.nodes:
            node_type = node.type
            if image_map and node_type == "TEX_IMAGE":
                canonical = image_map.get(node.image)
                if canonical is not None:
                    node.image = canonical
            elif group_map and node_type == "GROUP":
                canonical = group_map.get(node.node_tree)
                if canonical is not None:
                    node.node_tree = canonical


def _collect_dead(duplicate_map):
    """List the duplicates nothing points at any more.

    Anything the node walk didn't reach - a fake user, a reference from
    somewhere outside the material trees - is handed to user_remap first, so a
    datablock is never dropped while something still needs it.
    """
    dead = []
    for duplicate, canonical in duplicate_map.items():
        if duplicate.users:
            duplicate.user_remap(canonical)
        if duplicate.users == 0:
            dead.append(duplicate)
    return dead


def _remove_dead(duplicate_map):
    """Drop every duplicate nothing points at any more.

    batch_remove() rather than a remove() per datablock: removing one at a time
    rescans the whole file for users each time, which costs 0.54s for the ~400
    duplicates a 100 asset base leaves behind, against 0.006s for the batch.

    Returns:
        int: How many datablocks were removed.
    """
    if not duplicate_map:
        return 0
    dead = _collect_dead(duplicate_map)
    bpy.data.batch_remove(dead)
    return len(dead)
