import bpy
import bmesh
import mathutils
import json
import math
import time
from mathutils import Matrix, Vector
import uuid

from . import blend_utils

PROP_CHILD_CACHE = "child_cache"
PROP_GROUP_ID = "GroupID"



def cache_relative_matrices(parent_obj, object_list):
    """
    Calculates the local matrices of a list of objects relative to a parent_obj
    as if they were parented, without actually changing their hierarchy.
    
    Returns a JSON-serialized string of the cache data.
    """
    cache_data = {}

    # Get the inverse of the parent's world matrix once to optimize performance
    parent_matrix_inverted = parent_obj.matrix_world.inverted()

    for obj in object_list:
        # Skip the parent object if it accidentally ended up in the list
        if obj == parent_obj:
            continue
            
        # Ensure the object has the required identifier
        if "ObjectID" in obj:
            
            # Math behind the magic: 
            # Local Matrix = (Parent World Matrix Inverse) @ (Child World Matrix)
            matrix_local = parent_matrix_inverted @ obj.matrix_world
            
            # Convert Blender's mathutils.Matrix to a JSON-serializable list of lists
            matrix_list = [list(row) for row in matrix_local]
            
            object_id = obj["ObjectID"]
            user_data = obj.get("UserData",0)
            time_stamp = obj.get("TimeStamp",int(time.time()))
            
            cache = {
                "ObjectID": object_id,
                "UserData": user_data,
                "TimeStamp": time_stamp,
                "matrix_local": matrix_list
            }
            
            #if "Message" in obj:
            #    cache["Message"] = obj.get("Message","")
            
            # Store using the object's name as the key
            cache_data[obj.name] = cache

    return json.dumps(cache_data)
    

def extract_child_data(parent_obj):
    """
    Reads the custom property from parent_obj and returns a dictionary
    mapping child names to actual mathutils.Matrix objects.
    """
    global PROP_CHILD_CACHE
    
    if PROP_CHILD_CACHE not in parent_obj:
        print(f"No cache found on '{parent_obj.name}'.")
        return None

    try:
        # Load the string back into a Python dictionary
        cache_data = json.loads(parent_obj[PROP_CHILD_CACHE])
        return cache_data
    except Exception as e:
        print(f"Failed to parse cache on '{parent_obj.name}': {e}")
        return None
    
def group_objects(objects_list, origin_vector = None):
    global PROP_GROUP_ID
    global PROP_CHILD_CACHE
    
    for obj in objects_list:
        if PROP_GROUP_ID in obj:
            return None
    
    if origin_vector is None:
        active_object = bpy.context.active_object
        if active_object is not None:
            mesh_origin = active_object.location
        else:
            # calculate median of positinos of all objects and use that as mesh origin
            total_location = Vector((0.0, 0.0, 0.0))
            for obj in objects_list:
                # Use matrix_world.translation to get the actual world position safely
                total_location += obj.matrix_world.translation
            # Divide by the total number of objects to get the average (median)
            mesh_origin = total_location / len(objects_list)
    else:
        mesh_origin = origin_vector
    
    
    merged_object = blend_utils.merge_objects(objects_list, "Grouped_Objects" )
    prev_position = Vector(merged_object.location)
    
    # set origin of merged object here
    local_origin = merged_object.matrix_world.inverted() @ mesh_origin
    # Shift all vertices backward by that local offset
    for vertex in merged_object.data.vertices:
        vertex.co -= local_origin
        
    # Move the object's world location to the custom coordinate
    merged_object.location = mesh_origin
    merged_object.data.update()

    # Get the difference in origin, before and after shifting mesh
    new_location = Vector(merged_object.location)
    origin_difference = prev_position - new_location
    
    # Convert the difference into the merged object's local space and store it
    local_difference = merged_object.matrix_world.to_3x3().inverted() @ origin_difference
    merged_object["origin_offset"] = local_difference
    
    # cache all combined objects so that they can be reproduced
    child_cache = cache_relative_matrices(merged_object,objects_list)
    merged_object[PROP_CHILD_CACHE] = child_cache
    merged_object[PROP_GROUP_ID] = str(uuid.uuid4())
    # delete all objects
    for obj in objects_list:
        bpy.data.objects.remove(obj, do_unlink=True)
    

def ungroup_objects(BUILDER ,parent_obj):
    
    cached_child_data = extract_child_data(parent_obj)
    if not cached_child_data:
        return

    restored_ojects = []
    parent_matrix_world = parent_obj.matrix_world.copy()
    parent_transform = parent_matrix_world.to_3x3()
    local_offset = Vector(parent_obj["origin_offset"])
    
    # rotate and scale the offset vector to match the parent's current orientation
    rotated_offset = parent_transform @ local_offset
    
    for child_name, cache_data in cached_child_data.items():
        
        object_id = cache_data["ObjectID"]
        user_data = cache_data["UserData"]
        new_part = BUILDER.add_part(object_id, user_data)
        new_obj = new_part.object
        
        new_obj["TimeStamp"] = cache_data.get("TimeStamp",int(time.time()))
        new_obj["Message"] = cache_data.get("Message","")
        
        matrix_local = mathutils.Matrix(cache_data["matrix_local"])
        new_obj.matrix_world = parent_matrix_world @ matrix_local 
        new_obj.matrix_world.translation += rotated_offset
        
        restored_ojects.append(new_obj)
            
    bpy.data.objects.remove(parent_obj, do_unlink=True)
    return restored_ojects
        
def serialise(parent_obj):
    
    cached_child_data = extract_child_data(parent_obj)
    if not cached_child_data:
        return

    serialised_objects = []
    parent_matrix_world = parent_obj.matrix_world.copy()
    parent_transform = parent_matrix_world.to_3x3()
    local_offset = Vector(parent_obj["origin_offset"])
    
    # rotate and scale the offset vector to match the parent's current orientation
    rotated_offset = parent_transform @ local_offset
    
    for child_name, cache_data in cached_child_data.items():
        
        object_id = "^"+cache_data["ObjectID"]
        user_data = cache_data["UserData"]
        time_stamp = cache_data.get("TimeStamp",int(time.time()))
        message = cache_data.get("Message")
        
        matrix_local = mathutils.Matrix(cache_data["matrix_local"])
        matrix_world = parent_matrix_world @ matrix_local 
        matrix_world.translation += rotated_offset
        
        # Bring the matrix from Blender Z-Up soace into standard Y-up space.
        z_compensate = mathutils.Matrix.Rotation(math.radians(-90.0), 4, "X")
        world_matrix_offset = z_compensate @ matrix_world
        # Retrieve Position, Up and At vectors.
        pos = world_matrix_offset.decompose()[0]
        up = [
            world_matrix_offset[0][1],
            world_matrix_offset[1][1],
            world_matrix_offset[2][1],
        ]
        at = [
            world_matrix_offset[0][2],
            world_matrix_offset[1][2],
            world_matrix_offset[2][2],
        ]

        data =  {
            "ObjectId": object_id,
            "UserData": user_data,
            "TimeStamp": time_stamp,
            "Position": [pos[0], pos[1], pos[2]],
            "Up": [up[0], up[1], up[2]],
            "At": [at[0], at[1], at[2]],
        }
        
        if message is not None:
            data["Message"] = message
            
        serialised_objects.append(data)
        
    return serialised_objects

def extract_pos_up_at(matrix_world):
    # Bring the matrix from Blender Z-Up soace into standard Y-up space.
        z_compensate = mathutils.Matrix.Rotation(math.radians(-90.0), 4, "X")
        world_matrix_offset = z_compensate @ matrix_world
        # Retrieve Position, Up and At vectors.
        pos = world_matrix_offset.decompose()[0]
        up = [
            world_matrix_offset[0][1],
            world_matrix_offset[1][1],
            world_matrix_offset[2][1],
        ]
        at = [
            world_matrix_offset[0][2],
            world_matrix_offset[1][2],
            world_matrix_offset[2][2],
        ]