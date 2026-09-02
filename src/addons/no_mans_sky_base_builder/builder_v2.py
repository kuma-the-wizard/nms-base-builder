import bpy
import os
import time
import mathutils
import math
from . import builder, preset
from .part import Part
from .utils import blend_utils, material, materials_v2, collection_utils
from .part_overrides import parts_override
from .utils import python as python_utils

BUILDER = builder.Builder()

# This is to compensate blender's Z up axis.
X_ROT_90 = mathutils.Matrix.Rotation(math.radians(90.0), 4, "X")

# name of collection to import objects to
IMPORT_COLLECTION_NAME = "Collection"

FILE_PATH = os.path.dirname(os.path.realpath(__file__))

# The high resolution library. One .blend per object id, each holding exactly
# one mesh object with the real game materials and textures on it.
# Textures are referenced relatively from assets/ into textures/, so the whole
# models-high-res folder has to move as a unit.
HIGH_RES_PATH = os.path.join(FILE_PATH, "models-high-res", "assets")

# An earlier build of the library shipped some ids as several style variants,
# named <ID>__<STYLE>.blend, because two styles cannot live in one file without
# breaking the one-object-per-file rule. The current library is flat - one file
# per id, no suffixes - so nothing hits this any more, but it is kept so a
# styled file dropped into the folder still resolves instead of being ignored.
# Order of preference, chosen by matching each variant's bounding box against
# the fbx proxy: Builders won 16 of the 17 pairs tested, Exterior all 3 corvette
# cockpits. An id whose styles are all outside this list is left out of the
# index on purpose and falls back to the fbx proxy - that was the FRE_ROOM_*
# room kits, where no single piece is the room and picking one would be wrong.
STYLE_PRIORITY = ("Builders", "Exterior")

# Appended meshes are cached in bpy.data under this prefix so a second import in
# the same session (or after a reload) reuses them instead of touching the disk.
# The tag written alongside it is what marks a part as belonging to the new
# colour system - it lives in materials_v2 so the old material code can read it.
MESH_PREFIX = "NMS_HR_"
MESH_TAG = materials_v2.MESH_TAG

# Set once per session by get_asset_index().
_asset_index = None


# An optimised way to import objects,
# First exclude view layer from outliner
# then share as much data as possible between the objects we create
#
# Parts that come from the high res library share ONE mesh datablock (and with
# it one set of materials) across every placement of that object id, whatever
# their UserData, because colour lives on the object as four custom properties
# rather than on the material - see utils/materials_v2.py.
# Parts that still fall back to an fbx proxy keep the old behaviour, where the
# mesh has to be copied per (ObjectID, UserData) pair because the colour is
# baked into a flat material.
def deserialise_from_data(data):

    if data is None:
        return

    # High res meshes, keyed by object id. Shared by every placement.
    unique_meshes = {}
    # Fbx fallback objects and their per (object id, user data) mesh copies.
    unique_objects = {}
    unique_materials = {}
    # (object, user data) pairs to colour in one pass at the end.
    to_colour = []
    order = 0

    # Use these only an object requires special steps to be imported
    classes_dict = parts_override.get_override_classes()
    asset_index = get_asset_index()

    # exclude view layer from blender
    # so that importing and updating scene with new objects doesnt get reflected
    # immediately after each disk I/O or object creation
    import_collection = collection_utils.get_collection(IMPORT_COLLECTION_NAME)
    collection_utils.set_collection_visibility(import_collection.name, visible=False)

    # wrapped so a bad part can never leave the collection excluded from the
    # outliner - that would look like the import silently did nothing
    try:
        # local lookups, this loop runs once per placed part
        link_object = import_collection.objects.link
        new_object = bpy.data.objects.new

        objects_data = data.get("Objects", [])
        for part_data in objects_data:
            raw_object_id = part_data.get(Part.PROP_OBJECT_ID, None)
            if raw_object_id is None:
                continue

            object_id = raw_object_id.replace("^", "")
            user_data = part_data.get(Part.PROP_USER_DATA, 0)

            # use override classes only when needed, these are left untouched
            if object_id in classes_dict:
                use_class = classes_dict[object_id]
                use_class.deserialise_from_data(
                    part_data, BUILDER, compensate_normal=True
                )
                continue

            # import object_id from disk when visiting it first time
            if object_id not in unique_meshes:
                unique_meshes[object_id] = load_high_res_mesh(object_id, asset_index)
            high_res_mesh = unique_meshes[object_id]

            if high_res_mesh is not None:
                # a plain new object over the cached mesh - no copy, no ops,
                # and every instance of this id points at the same mesh
                bpy_object = new_object(object_id, high_res_mesh)
                link_object(bpy_object)
                to_colour.append((bpy_object, user_data))
            else:
                bpy_object = build_fbx_part(
                    object_id,
                    user_data,
                    import_collection,
                    unique_objects,
                    unique_materials,
                )
                if bpy_object is None:
                    continue

            # restore matrix world
            restore_params(bpy_object, part_data, object_id)
            bpy_object.matrix_world = deserialise_matrix_world(part_data)

            # provide order
            bpy_object[Part.PROP_ORDER] = order
            order += 1

        # colour every high res part in one pass, so each distinct UserData is
        # only decoded once, then collapse the datablocks the appends duplicated
        materials_v2.apply_many(to_colour)
        materials_v2.dedupe_appended_data()

        # Solid shading colours by MATERIAL out of the box, and high res parts
        # share their materials, so without this a freshly imported base is one
        # flat grey mass until the textures load. Only Solid viewports are
        # touched - anything set to Material Preview or Rendered is left alone.
        materials_v2.use_object_colour_in_viewport()

    finally:
        # include import collection to outliner and update view layer
        collection_utils.set_collection_visibility(import_collection.name, visible=True)
        bpy.context.view_layer.update()

    # Reconstruct presets.
    for preset_data in data.get("Presets", []):
        preset.Preset.deserialise_from_data(
            preset_data, BUILDER, compensate_normal=True
        )

    # Build Rigs.
    BUILDER.build_rigs()
    # Optimise control points.
    BUILDER.optimise_control_points()


def add_part(
    object_id, user_data=None, build_rigs=True, high_res=True, builder_object=None
):
    """Add a single part, the way the asset browser and the build tools do it.

    A drop in replacement for builder.Builder.add_part - it hands back the same
    Part wrapper, so .object, .select(), .snap_to() and .build_rig() all still
    work on the result.

    Args:
        object_id (str): The part to build.
        user_data: The packed UserData value, or None for the part default.
        build_rigs (bool): Passed through to the part class.
        high_res (bool): True to place the models-high-res asset when the id
            has one, False to always place the old fbx proxy instead.
        builder_object (Builder): The builder whose part cache this belongs in.
            Defaults to this module's. Pass the caller's own instance to keep
            its cache the one that gets filled.

    Returns:
        Part: The new part, or whatever the old builder returns for it.
    """
    object_id = object_id.replace("^", "")
    builder_object = builder_object or BUILDER

    # matched before the part exists, same as the old builder, so a new part
    # lands on whatever was selected rather than on itself
    active_object = bpy.context.active_object

    # Use these only when an object requires special steps to be imported.
    # Same override table deserialise_from_data reads, so a part built here and
    # the same part loaded from a save come out of the same class. Checked
    # first, because these parts need their class whether or not the caller
    # asked for the high res library.
    classes_dict = parts_override.get_override_classes()
    if object_id in classes_dict:
        use_class = classes_dict[object_id]
        item = use_class(
            object_id=object_id,
            builder_object=builder_object,
            user_data=user_data,
            build_rigs=build_rigs,
        )
        if active_object is not None:
            item.object.matrix_world = active_object.matrix_world.copy()
        return item

    # with high_res off the caller is explicitly asking for the old proxy, which
    # is the old builder's job - it behaves exactly as it always has
    if not high_res:
        return builder_object.add_part(
            object_id, user_data=user_data, build_rigs=build_rigs
        )

    # ids the high res library doesn't cover fall back to the proxy too
    bpy_object = new_high_res_object(object_id)
    if bpy_object is None:
        return builder_object.add_part(
            object_id, user_data=user_data, build_rigs=build_rigs
        )

    # the same properties Part sets when it builds one from scratch
    bpy_object.hide_select = False
    bpy_object[Part.PROP_OBJECT_ID] = object_id
    bpy_object[Part.PROP_SNAP_ID] = object_id
    bpy_object[Part.PROP_TIMESTAMP] = str(int(time.time()))
    bpy_object[Part.PROP_BELONGS_TO_PRESET] = Part.DEFAULT_BELONGS_TO_PRESET
    bpy_object[Part.PROP_ORDER] = len(bpy.data.objects)

    # colour by object property, so this placement goes on sharing the mesh
    if user_data is None:
        user_data = Part.DEFAULT_USER_DATA
    materials_v2.recolour_from_user_data([bpy_object], user_data)

    # if the asset was appended just now it brought its own copies of textures
    # and of the colourise node group with it. Cheap to call either way - with
    # nothing to collapse this is a scan of bpy.data.images and no more
    materials_v2.dedupe_appended_data()

    # wrap it so callers get the interface they expect from builder.add_part
    item = Part(
        bpy_object=bpy_object, builder_object=builder_object, build_rigs=build_rigs
    )
    item.reset_transforms()

    if active_object is not None:
        item.object.matrix_world = active_object.matrix_world.copy()

    return item


# build the {object_id: blend file} lookup for the high res library, once
def get_asset_index(rebuild=False):
    global _asset_index

    if _asset_index is not None and not rebuild:
        return _asset_index

    _asset_index = {}
    if not os.path.isdir(HIGH_RES_PATH):
        return _asset_index

    # collect every candidate first, then resolve the styled ones, so the
    # answer doesn't depend on the order the folder happens to list in
    candidates = {}
    for filename in os.listdir(HIGH_RES_PATH):
        if not filename.endswith(".blend"):
            continue
        object_id, separator, style = filename[:-6].partition("__")
        candidates.setdefault(object_id, []).append(
            (style if separator else None, os.path.join(HIGH_RES_PATH, filename))
        )

    for object_id, styles in candidates.items():
        if len(styles) == 1 and styles[0][0] is None:
            _asset_index[object_id] = styles[0][1]
            continue

        # a multi style id is only usable if one of its styles is one we chose
        for preferred in STYLE_PRIORITY:
            for style, path in styles:
                if style == preferred:
                    _asset_index[object_id] = path
                    break
            if object_id in _asset_index:
                break

    return _asset_index


def new_high_res_object(object_id, asset_index=None):
    """Make a bare object over the shared high res mesh for an id.

    Everything the high res library places goes through here, including the
    fossil bones, which build their own object rather than going through
    add_part - see part_overrides/bone.py.

    No properties are set and nothing is coloured; that is the caller's job,
    because Part sets its own when it builds one and add_part sets them itself.

    Args:
        object_id (str): The part to build.
        asset_index (dict): Optional prebuilt index, to skip the lookup.

    Returns:
        bpy.types.Object: The new object, or None when the library doesn't
            cover the id, so the caller can fall back to the fbx proxy.
    """
    mesh = load_high_res_mesh(object_id, asset_index)
    if mesh is None:
        return None

    # a plain new object over the shared mesh - adding the tenth copy of a part
    # costs an object datablock and nothing else
    bpy_object = bpy.data.objects.new(object_id, mesh)
    blend_utils.add_to_scene(bpy_object)
    return bpy_object


# get the shared mesh datablock for an object id, appending it on first use
def load_high_res_mesh(object_id, asset_index=None):
    asset_index = asset_index if asset_index is not None else get_asset_index()

    blend_path = asset_index.get(object_id)
    if blend_path is None:
        return None

    # the cache lives in bpy.data rather than in a module level dict, so it
    # survives a new file, a module reload and a scene the user already saved
    mesh_name = MESH_PREFIX + object_id
    cached = bpy.data.meshes.get(mesh_name)
    if cached is not None and cached.get(MESH_TAG) == object_id:
        return cached

    # every library file holds exactly one mesh object. We only want its mesh -
    # the object datablock is thrown away and each placement gets a fresh one
    with bpy.data.libraries.load(blend_path, link=False) as (source, target):
        target.objects = list(source.objects)

    mesh = None
    for appended_object in target.objects:
        if appended_object is None:
            continue
        if mesh is None and appended_object.type == "MESH":
            mesh = appended_object.data
        bpy.data.objects.remove(appended_object)

    if mesh is None:
        return None

    mesh.name = mesh_name
    mesh[MESH_TAG] = object_id
    return mesh


# fbx fallback for the 169 ids the high res index doesnt cover yet (of 2090 in
# models/, 1921 are served from models-high-res).
# these still colour by swapping a flat material in, so objects can only share a
# mesh when their ObjectID AND UserData match
def build_fbx_part(
    object_id, user_data, import_collection, unique_objects, unique_materials
):
    material_key = (object_id, user_data)

    # import object from disk when visiting that object_id for first time
    if object_id not in unique_objects:
        bpy_object = improt_fbx_from_disk(object_id)
        if bpy_object is None:
            return None

        collection_utils.move_object_into_collection(import_collection, bpy_object)
        material.restore_material(bpy_object, user_data)

        # store it in temp cache
        unique_objects[object_id] = bpy_object
        unique_materials[material_key] = bpy_object.data
        return bpy_object

    # if object is already visited, check if a same object with same userdata exists
    # this is to avoid creating data block for each object with same object_ids
    bpy_object = unique_objects[object_id].copy()
    import_collection.objects.link(bpy_object)

    # choose to either create new material or use existing one if it exists
    if material_key in unique_materials:
        bpy_object.data = unique_materials[material_key]
    else:
        bpy_object.data = bpy_object.data.copy()
        material.restore_material(bpy_object, user_data)
        unique_materials[material_key] = bpy_object.data

    return bpy_object


def improt_fbx_from_disk(object_id):
    fbx_path = BUILDER.get_obj_path(object_id)

    objects_before = set(bpy.data.objects)
    if fbx_path is None:
        bpy.ops.mesh.primitive_cube_add()
    else:
        bpy.ops.import_scene.fbx(filepath=fbx_path)
    new_objects = list(set(bpy.data.objects) - objects_before)

    if not new_objects:
        return None

    bpy_object = bpy.data.objects[new_objects[0].name]
    bpy_object.name = object_id
    bpy_object.data.materials.clear()
    bpy_object.select_set(False)

    return bpy_object

# copy params from part json to bpy_object
def restore_params(part, part_data, object_id):

    user_data = part_data.get(Part.PROP_USER_DATA, "")
    time_stamp = str(part_data.get(Part.PROP_TIMESTAMP, int(time.time())))
    message = part_data.get(Part.PROP_MESSAGE, None)

    # Apply metadata
    part[Part.PROP_OBJECT_ID] = object_id
    part[Part.PROP_SNAP_ID] = object_id
    part[Part.PROP_USER_DATA] = str(user_data)
    part[Part.PROP_TIMESTAMP] = time_stamp
    part[Part.PROP_BELONGS_TO_PRESET] = False

    if message:
        part[Part.PROP_MESSAGE] = message

    return part

# convert position, up and at to matrix world for blender object
def deserialise_matrix_world(part_data):
    # Get location data.
    pos = part_data.get("Position", [0.0, 0.0, 0.0])
    up = part_data.get("Up", [0.0, 0.0, 0.0])
    at = part_data.get("At", [0.0, 0.0, 0.0])

    # combine three vectors above to constrict matrix world
    return create_matrix_from_vectors(pos, up, at)


def create_matrix_from_vectors(pos, up, at):
    """Create a world space matrix given by an Up and At vector.

    Args:
        pos (list): 3 element list/vector representing the x,y,z position.
        up (list): 3 element list/vector representing the up vector.
        at (list): 3 element list/vector representing the aim vector.
    """
    up_vector = mathutils.Vector(up)
    at_vector = mathutils.Vector(at)

    # Compute right vector and normalize
    right_vector = at_vector.cross(up_vector)
    right_vector.normalize()
    right_vector *= -1

    # Get the up length once
    up_length = up_vector.length
    right_vector.length = up_length
    at_vector.length = up_length

    # Build matrix directly without intermediate list construction
    mat = mathutils.Matrix((
        (right_vector[0], up_vector[0], at_vector[0], pos[0]),
        (right_vector[1], up_vector[1], at_vector[1], pos[1]),
        (right_vector[2], up_vector[2], at_vector[2], pos[2]),
        (0.0, 0.0, 0.0, 1.0),
    ))

    return X_ROT_90 @ mat
