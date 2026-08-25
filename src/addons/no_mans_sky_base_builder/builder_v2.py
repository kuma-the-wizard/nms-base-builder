import bpy
import time
import mathutils
import math
from . import builder, preset
from .utils import material, collection_utils
from .part_overrides import parts_override

BUILDER = builder.Builder()

# This is to compensate blender's Z up axis.
X_ROT_90 = mathutils.Matrix.Rotation(math.radians(90.0), 4, "X")

# name of collection to import objects to
IMPORT_COLLECTION_NAME = "Collection"


# An optimised way to import objects,
# First exclude view layer from outliner
# then collect each unique material and unique object and restore their duplicates from that cache while traversing objects in json
def deserialise_from_data(data):
    
    if data is None:
        return

    unique_objects = {}
    unique_materials = {}
    order = 0
    
    # Use these only an object requires special steps to be imported
    classes_dict = parts_override.get_override_classes()
    
    # exclude view layer from blender 
    # so that importing and updating scene witn new objects doesnt get reflected immidieatly 
    # after each disk I/O or object creation
    import_collection = collection_utils.get_collection(IMPORT_COLLECTION_NAME)
    collection_utils.set_collection_visibility(import_collection.name, visible = False)
    
    objects_data = data.get("Objects", [])
    for part_data in objects_data:
        object_id = part_data.get("ObjectID", None).replace("^", "")
        user_data = part_data.get("UserData", 0)
            
        material_key = ( object_id, user_data )
        
        if object_id is None:
            continue
        
        # use override clases only when needed
        if object_id in classes_dict:
            use_class = classes_dict[object_id]
            bpy_object = use_class.deserialise_from_data(
                part_data, BUILDER, compensate_normal=True
            )
            
        # import object_id from disk when visiting it first time
        else:
            
            if object_id not in unique_objects:
                # import object from disk when visiting that object_id for fiest time
                bpy_object = improt_fbx_from_disk(object_id)
                if bpy_object is not None:
                    collection_utils.move_object_into_collection(import_collection, bpy_object)
                    material.restore_material(bpy_object,user_data)
                    
                    # store it in temp cache
                    unique_objects[object_id] = bpy_object
                    unique_materials[material_key] = bpy_object.data
                    
            # if object is already visited, check if a same object with same userdata exists
            # this is to avoid creating data block for each object with same object_ids 
            else:
                
                unique_obj = unique_objects.get(object_id)
                bpy_object = bpy.data.objects.new(unique_obj.name, unique_obj.data)
                import_collection.objects.link(bpy_object)
                for key, value in unique_obj.items():
                    bpy_object[key] = value
                
                # choose to either create new material or use existing one if it exists
                if material_key in unique_materials:
                    bpy_object.data = unique_materials.get(material_key)
                else:
                    bpy_object.data = bpy_object.data.copy()
                    material.restore_material(bpy_object,user_data)
                    unique_materials[material_key] = bpy_object.data
            
            # restore matrix world
            restore_params(bpy_object,part_data, object_id)
            matrix_world = deserialise_matrix_world(part_data)
            bpy_object.matrix_world = matrix_world
            
            # provide order
            bpy_object["order"] = order
            order += 1
    
    
    # include import collection to outliner and update view layer
    collection_utils.set_collection_visibility(import_collection.name, visible = True)
    bpy.context.view_layer.depsgraph.update()
        
    
    # Reconstruct presets.
    for preset_data in data.get("Presets", []):
        preset.Preset.deserialise_from_data(
            preset_data, BUILDER, compensate_normal=True
        )
        
    # Build Rigs.
    BUILDER.build_rigs()
    # Optimise control points.
    BUILDER.optimise_control_points()

            
def improt_fbx_from_disk(object_id):
    fbx_path = BUILDER.get_obj_path(object_id)
    
    objects_before = set(bpy.data.objects)
    if fbx_path is None:
        bpy.ops.mesh.primitive_cube_add()
    else:
        bpy.ops.import_scene.fbx(filepath=fbx_path)
    new_objects = list(set(bpy.data.objects) - objects_before)
    
    bpy_object = bpy.data.objects[new_objects[0].name]
    bpy_object.name = object_id
    bpy_object.data.materials.clear()
    bpy_object.select_set(False)
    
    return bpy_object

# copy params from part json to bpy_object
def restore_params(part, part_data, object_id):
    # Apply metadata
    part["ObjectID"] = object_id
    part["SnapID"] = object_id
    try:
        part["UserData"] = part_data.get("UserData", 0)
    except Exception:
        part["UserData"] = 0
    part["Timestamp"] = str(part_data.get("Timestamp", int(time.time())))
    part["belongs_to_preset"] = False
    
    if "Message" in part_data:
        part["Message"] = part_data.get("Message", "")
        
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
                
            
