import bpy
import time
import mathutils
import math
from . import builder, part, preset
from .utils import material, collection_utils
from .utils import python as ptyhon_utils

BUILDER = builder.Builder()

# This is to compensate blender's Z up axis.
mat_rot = mathutils.Matrix.Rotation(math.radians(90.0), 4, "X")

def deserialise_from_data(data):
        
        import_collection = collection_utils.get_collection("Collection")
        layer_collection = bpy.context.view_layer.layer_collection.children.get(import_collection.name)
        if layer_collection:
            layer_collection.exclude = True
        
        unique_objects = {}
        unique_materials = {}
        order = 0
        
        override_classes = builder.Builder.override_classes
        classes_dict = {}
        for class_ref, part_list in override_classes.items():
            for part in part_list:
                classes_dict[part] = class_ref
                print("storing", part,"    ",class_ref)
        
        objects_data = data.get("Objects", [])
        for part_data in objects_data:
            object_id = part_data.get("ObjectID", None).replace("^", "")
            user_data = part_data.get("UserData", 0)
            
            message_key = (object_id,message_key)
            material_key = (object_id,user_data)
            
            if object_id is None:
                continue
            
            if object_id in classes_dict:
                use_class = classes_dict[object_id]
                bpy_object = use_class.deserialise_from_data(
                    part_data, BUILDER, compensate_normal=True
                )
                
            else:
                if object_id not in unique_objects:
                    
                    bpy_object = improt_fbx_from_disk(object_id)
                    
                    collection_utils.move_object_into_collection(import_collection, bpy_object)
                    material.restore_material(bpy_object,user_data)
                    restore_params(bpy_object,part_data, object_id)
                    
                    unique_objects[object_id] = bpy_object
                    unique_materials[material_key] = bpy_object.data
                    
                else:
                    unique_obj = unique_objects.get(object_id)
                    bpy_object = bpy.data.objects.new(unique_obj.name, unique_obj.data)
                    for key, value in unique_obj.items():
                        bpy_object[key] = value
                    import_collection.objects.link(bpy_object)
                    
                    if material_key in unique_materials:
                        bpy_object.data = unique_materials.get(material_key)
                    else:
                        bpy_object.data = bpy_object.data.copy()
                        material.restore_material(bpy_object,user_data)
                        unique_materials[material_key] = bpy_object.data
                
                matrix_world = deserialise_matrix_world(part_data)
                bpy_object.matrix_world = matrix_world
                bpy_object["order"] = order
                order += 1
        
        # Reconstruct presets.
        for preset_data in data.get("Presets", []):
            preset.Preset.deserialise_from_data(
                preset_data, BUILDER, compensate_normal=True
            )
        
        # Build Rigs.
        BUILDER.build_rigs()
        # Optimise control points.
        BUILDER.optimise_control_points()
        
        if layer_collection:
            layer_collection.exclude = False
            bpy.context.view_layer.depsgraph.update()
            
            
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

def deserialise_matrix_world(part_data):
    # Get location data.
    pos = part_data.get("Position", [0.0, 0.0, 0.0])
    up = part_data.get("Up", [0.0, 0.0, 0.0])
    at = part_data.get("At", [0.0, 0.0, 0.0])
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
    
    return mat_rot @ mat
                
            
