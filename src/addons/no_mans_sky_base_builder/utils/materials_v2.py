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

The finish index is handled too, but read the FINISHES_BY_LABEL note below
before trusting what it looks like - the names are the game's, the surface
values are ours.
"""

import contextlib
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

# Object properties carrying the surface finish, read by the nodes
# ensure_finish_nodes() splices into each colourable material. Both are
# offsets onto whatever the part's own texture maps say, so 0 - which is what
# an Attribute node reports for an object that has neither - means "exactly as
# the textures have it". That keeps every part that predates this unchanged.
PROP_FINISH_ROUGHNESS = "nms_finish_rough"
PROP_FINISH_METALLIC = "nms_finish_metal"

# A colour the finish multiplies over the part, and how strongly.
# Kept as two properties rather than one RGBA so the "no tint" default needs
# no assumption about what an Attribute node reports for a missing alpha:
# a missing mix reads as 0, which is no tint at all.
PROP_FINISH_TINT = "nms_finish_tint"
PROP_FINISH_TINT_MIX = "nms_finish_tint_mix"

# Marks a material whose node tree has already had the finish nodes spliced
# in, so a second import does not stack a second copy on top.
FINISH_NODES_TAG = "nms_finish_nodes"

# The palette slots in their normal order. "Inverted" is the one finish that
# reorders them, which is why it is also the only one that shows up under
# Solid viewport shading - it is a colour difference, not a surface one.
SLOT_ORDER = ("p", "s", "t", "q")
SLOT_ORDER_INVERTED = ("s", "p", "q", "t")

# What each finish does to a part's look.
#
# Keyed on the readable label rather than the raw index, because the index is
# only meaningful inside its own material group: index 1 is "Inverted Gloss
# Finish" on a corvette palette and plain "Rust" on a legacy one. The labels
# come straight from resources/DT_Palettes.csv, which is also what the colour
# picker shows, so what you choose in the UI is what is looked up here.
#
# The VALUES are ours, not the game's. What No Man's Sky actually does to its
# shader for each finish was never worked out - the extracted
# material_finishes.json carries names and indices and nothing else - so these
# are chosen to tell the finishes apart in the direction their names point,
# for previewing in Blender. Correct them here; nothing else reads them.
#
# None of this touches the saved UserData. The finish index is written and
# read back exactly as before, so the game stays the authority on how a base
# really looks - this only changes what Blender draws.
#
#   roughness / metallic: added to the texture value, clamped to 0..1
#   tint / tint_mix: a colour multiplied over the part, and how strongly.
#     Being a multiply, these are brighter than the colour you want out:
#     a rust of (0.55, 0.26, 0.14) lands as dark oxide over a light hull.
#   invert: swap the palette slots as above

# What rust multiplies a surface by. Reads as a dark oxide over a light hull
# while leaving the panel lines and decals showing through.
RUST_TINT = (0.42, 0.17, 0.07)

GLOSS = {"roughness": 0.40}
GLOSS_INVERTED = {"roughness": 0.40, "invert": True}
RUSTED = {"roughness": 0.80, "tint": (0.58, 0.53, 0.46), "tint_mix": 0.75}
METALLIC = {"roughness": 0.25, "metallic": 5.0}

FINISHES_BY_LABEL = {
    # Corvette - the four the picker offers for a BIGGS palette.
    # These panels are painted, so their maps are already fairly smooth; a
    # negative offset here goes straight past "shiny" into mirror, which is why
    # gloss sits slightly ROUGHER than the texture rather than smoother. Think
    # moulded plastic, not a showroom floor.
    "Corvette - Gloss Finish": GLOSS,
    "Corvette - Inverted Gloss Finish": GLOSS_INVERTED,
    # grimy rather than bleached: dulled right down and darkened towards a warm
    # grey, but still recognisably the same paint underneath
    "Corvette - Weathered Finish": RUSTED,
    # Metal, but a painted piece of it. Metallic kills the diffuse term, so
    # pushing it high turns the part into a dark mirror and the palette colour
    # stops reading at all - kept low enough that the colour still comes
    # through, with the roughness doing the work of making it look like metal.
    "Corvette - Metallic Finish": METALLIC,

    # Legacy - the original four building materials
    "Legacy - Concrete": GLOSS,
    "Legacy - Rust": GLOSS_INVERTED,
    "Legacy - Stone": RUSTED,
    "Legacy - Wood": METALLIC,

    # the later material groups, all polished/worn pairs
    "Stone - Polished Stone": {"roughness": 0.10},
    "Stone - Aged Stone": {"roughness": 0.45},
    "Timber - Polished Timber": {"roughness": 0.10},
    "Timber - Weathered Timber": {"roughness": 0.45,
                                  "tint": (0.74, 0.68, 0.60), "tint_mix": 0.50},
    "Fiberglass - Polished Alloy": {"roughness": 0.10, "metallic": 0.25},
    "Fiberglass - Rusted Alloy": {"roughness": 0.85, "tint": RUST_TINT,
                                  "tint_mix": 1.0},
    "Salvaged - Polished Salvage": {"roughness": 0.10, "metallic": 0.25},
    "Salvaged - Rusted Salvage": {"roughness": 0.85, "tint": RUST_TINT,
                                  "tint_mix": 1.0},

    "Freighter": {"roughness": 0.15, "metallic": 0.30},
}

# Used for a finish that is not in the table - leaves the part exactly as its
# textures make it.
FINISH_NEUTRAL = {}

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
def get_finish(user_data_value):
    """The finish behaviour for a UserData value.

    Args:
        user_data_value: The packed UserData value.

    Returns:
        dict: An entry from FINISHES_BY_LABEL, or FINISH_NEUTRAL. Never None.
    """
    finish_name = get_nice_names(user_data_value)[1]
    return FINISHES_BY_LABEL.get(finish_name, FINISH_NEUTRAL)


def apply_palette(bpy_object, palette, finish=None):
    """Write the four palette slots and the surface finish onto an object.

    Args:
        bpy_object (bpy.types.Object): The object to colour.
        palette (dict): A palette entry with p/s/t/q RGBA lists.
        finish (dict): An entry from FINISHES_BY_LABEL. Defaults to neutral.
    """
    finish = finish if finish is not None else FINISH_NEUTRAL

    slots = SLOT_ORDER_INVERTED if finish.get("invert") else SLOT_ORDER
    for prop_name, slot in zip(SLOT_PROPS, slots):
        bpy_object[prop_name] = tuple(palette[slot])
    primary = tuple(palette[slots[0]])

    # Offsets rather than absolute values, so a part keeps the surface detail
    # its own maps give it. 0 is "unchanged", which is also what the shader
    # reads for an object that has never been given a finish.
    bpy_object[PROP_FINISH_ROUGHNESS] = float(finish.get("roughness", 0.0))
    bpy_object[PROP_FINISH_METALLIC] = float(finish.get("metallic", 0.0))
    bpy_object[PROP_FINISH_TINT] = tuple(finish.get("tint", (0.0, 0.0, 0.0)))
    bpy_object[PROP_FINISH_TINT_MIX] = float(finish.get("tint_mix", 0.0))

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

    apply_palette(bpy_object, palette, get_finish(user_data_value))
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
            names = get_nice_names(key)
            cache[key] = (get_palette(key), names,
                          FINISHES_BY_LABEL.get(names[1], FINISH_NEUTRAL))
        palette, names, finish = cache[key]

        if palette is None:
            unresolved += 1
            continue

        apply_palette(bpy_object, palette, finish)
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

    # A base saved before finishes were handled has materials with no finish
    # nodes in them, so the offsets below would land on nothing. Cheap to call
    # again - materials that already have them carry a marker - so the first
    # recolour after opening such a file quietly brings it up to date.
    ensure_finish_nodes()

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
    finish = FINISHES_BY_LABEL.get(finish_name, FINISH_NEUTRAL)
    value = str(user_data_value)

    # see recolour() - keeps an older file working the moment it is touched
    ensure_finish_nodes()

    for bpy_object in objects:
        bpy_object["UserData"] = value
        apply_palette(bpy_object, palette, finish)
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
def _splice_finish_offset(node_tree, socket, attribute_name, label):
    """Add an object attribute onto whatever already feeds `socket`.

    The Principled BSDF's Roughness and Metallic are driven by the part's own
    texture maps, and those maps are shared by every placement of that part - so
    the finish cannot be baked into them any more than the colour can. This adds
    the object property on top instead, the same trick the colour slots use, and
    clamps the result back into 0..1.

    Args:
        node_tree (bpy.types.NodeTree): The material's node tree.
        socket (bpy.types.NodeSocket): The Principled input to drive.
        attribute_name (str): The object property carrying the offset.
        label (str): Label for the added nodes, so they are findable by hand.
    """
    nodes = node_tree.nodes
    links = node_tree.links

    attribute = nodes.new("ShaderNodeAttribute")
    attribute.attribute_type = 'OBJECT'
    attribute.attribute_name = attribute_name
    attribute.label = label
    attribute.location = (socket.node.location.x - 600,
                          socket.node.location.y - 400)

    add = nodes.new("ShaderNodeMath")
    add.operation = 'ADD'
    add.use_clamp = True
    add.label = label
    add.location = (socket.node.location.x - 300,
                    socket.node.location.y - 400)

    # whatever was feeding the socket becomes the first term - a texture, or the
    # value that was typed into it if nothing was linked
    existing = socket.links[0].from_socket if socket.is_linked else None
    if existing is not None:
        links.new(existing, add.inputs[0])
    else:
        add.inputs[0].default_value = socket.default_value

    links.new(attribute.outputs["Fac"], add.inputs[1])
    links.new(add.outputs["Value"], socket)


def _splice_finish_tint(node_tree, socket):
    """Wash a finish colour over whatever already feeds Base Color.

    Rust is a colour as much as a roughness, and the part's own diffuse map
    cannot carry it - that map is shared by every placement. So the tint goes
    on as a mix at the end of the chain, driven by two object properties, the
    same way the palette and the roughness are.

    Args:
        node_tree (bpy.types.NodeTree): The material's node tree.
        socket (bpy.types.NodeSocket): The Principled Base Color input.
    """
    nodes = node_tree.nodes
    links = node_tree.links

    colour = nodes.new("ShaderNodeAttribute")
    colour.attribute_type = 'OBJECT'
    colour.attribute_name = PROP_FINISH_TINT
    colour.label = "NMS Finish Tint"
    colour.location = (socket.node.location.x - 900, socket.node.location.y + 300)

    amount = nodes.new("ShaderNodeAttribute")
    amount.attribute_type = 'OBJECT'
    amount.attribute_name = PROP_FINISH_TINT_MIX
    amount.label = "NMS Finish Tint Mix"
    amount.location = (socket.node.location.x - 900, socket.node.location.y + 120)

    mix = nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    # MULTIPLY, not MIX. Mixing towards a flat colour washes the panel lines,
    # decals and paint straight off the part - 60% towards a rust brown turned
    # a hull into a smooth terracotta shape. Multiplying darkens and shifts the
    # hue while every bit of that detail survives underneath.
    mix.blend_type = 'MULTIPLY'
    mix.clamp_factor = True
    mix.label = "NMS Finish Tint"
    mix.location = (socket.node.location.x - 300, socket.node.location.y + 220)

    existing = socket.links[0].from_socket if socket.is_linked else None
    if existing is not None:
        links.new(existing, mix.inputs["A"])
    else:
        mix.inputs["A"].default_value = socket.default_value

    links.new(amount.outputs["Fac"], mix.inputs["Factor"])
    links.new(colour.outputs["Color"], mix.inputs["B"])
    links.new(mix.outputs["Result"], socket)


# Bulk builds ---
#
# dedupe_appended_data() and the no-argument form of ensure_finish_nodes() both
# walk every material node tree in the file. That is the right cost to pay once
# at the end of an import, and the wrong one to pay per part: builder_v2's
# add_part() calls all of them for every single part it places, so a scene wide
# rebuild - a proxy quality switch, a batch replace - spends most of its time
# rescanning a library that only the last pass could have changed.
#
# Inside defer_shared_data() they record that they were wanted and return
# immediately, and leaving the block runs each of them once.
_defer_depth = 0
_defer_pending = False


@contextlib.contextmanager
def defer_shared_data():
    """Collapse the whole-library passes inside a bulk build into one each.

    Nests: only the outermost block runs the deferred passes, so a caller can
    wrap a batch without caring whether something inside it does the same.

    Nothing is deferred that a caller asked for explicitly - passing a
    materials list to ensure_finish_nodes() still does exactly that work, since
    that form is already scoped to what changed.
    """
    global _defer_depth, _defer_pending
    _defer_depth += 1
    try:
        yield
    finally:
        _defer_depth -= 1
        if _defer_depth == 0 and _defer_pending:
            _defer_pending = False
            # dedupe first, so the surviving shared materials are the ones
            # that get the finish nodes rather than copies about to be thrown
            # away - the same order deserialise_from_data uses.
            dedupe_appended_data()
            ensure_finish_nodes()


def _defer():
    """Record that a deferred pass was wanted. True if it should be skipped."""
    global _defer_pending
    if not _defer_depth:
        return False
    _defer_pending = True
    return True


def note_appended_data():
    """Record that an asset was appended, for whatever tidy up comes next.

    Appending brings its own copies of the asset's textures and of the
    colourise node group with it, and both have to be collapsed onto the ones
    already in the file before the finish nodes are spliced in. Inside
    defer_shared_data() this is what schedules that single pass at the end.

    Outside one it deliberately does nothing: the callers that append without
    deferring - builder_v2.add_part, builder_v2.deserialise_from_data - already
    run the passes themselves, and running them here as well would put the per
    asset cost back that deferring exists to remove.
    """
    _defer()


def ensure_finish_nodes(materials=None):
    """Give materials the nodes that let a finish change their surface.

    Idempotent and cheap to call again: a material that already carries the
    nodes is skipped by its marker, so re-importing an asset does not stack a
    second copy of them.

    Args:
        materials (iterable): Materials to fix up. Defaults to all of them.

    Returns:
        int: How many materials were changed.
    """
    if materials is None and _defer():
        return 0

    materials = materials if materials is not None else bpy.data.materials

    changed = 0
    for mat in materials:
        if mat is None or mat.get(FINISH_NODES_TAG) or not mat.node_tree:
            continue

        # Only the materials that carry the colourise group. That keeps this off
        # the flat proxy materials and off anything of the user's own, and it
        # also leaves a part's non-paintable materials - its lights and its glass
        # - alone, which is right: a weathered finish should dull the hull, not
        # the lamps set into it.
        if not any(node.type == 'GROUP' and node.node_tree
                   and node.node_tree.name.startswith(COLOURISE_GROUP)
                   for node in mat.node_tree.nodes):
            continue

        principled = next((node for node in mat.node_tree.nodes
                           if node.type == 'BSDF_PRINCIPLED'), None)
        if principled is None:
            # not a shaded material - nothing a finish could act on
            continue

        _splice_finish_offset(mat.node_tree, principled.inputs["Roughness"],
                              PROP_FINISH_ROUGHNESS, "NMS Finish Roughness")
        _splice_finish_offset(mat.node_tree, principled.inputs["Metallic"],
                              PROP_FINISH_METALLIC, "NMS Finish Metallic")
        _splice_finish_tint(mat.node_tree, principled.inputs["Base Color"])

        mat[FINISH_NODES_TAG] = True
        changed += 1

    return changed


def dedupe_appended_data():
    """Collapse the datablocks the appends duplicated.

    Call this once, after a whole batch of assets is appended, never per asset
    - the cost is one walk over every material node tree, so doing it once for
    100 assets is 100x cheaper than doing it as they arrive.

    Returns:
        tuple: (images removed, node groups removed)
    """
    if _defer():
        return 0, 0

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
