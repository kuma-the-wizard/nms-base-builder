import bpy
import os
import bmesh
import mathutils
import json
import math
import time
from mathutils import Matrix, Vector
import uuid

from .utils import blend_utils, materials_v2, mirror_utils, dictionary
from .part import Part

nice_name_dictionary = dictionary.get_nice_names_diictionary()


"""
    Manages grouping and ungrouping of NMS objects with safe caching.
    Handles relative matrix calculations, serialization, and restoration.
"""


def _builder_v2():
    """The high res importer, imported on use rather than at module level.

    builder_v2 imports builder, which imports this module, so importing it up
    top would be a cycle.
    """
    from . import builder_v2
    return builder_v2

class Group:
    
    # object properties
    PROP_OBJECT_ID = Part.PROP_OBJECT_ID
    PROP_USER_DATA = Part.PROP_USER_DATA
    PROP_TIMESTAMP = Part.PROP_TIMESTAMP
    PROP_MESSAGE = Part.PROP_TIMESTAMP
    
    # curve properties
    PROP_CHILD_CACHE = "child_cache"
    PROP_GROUP_ID = "GroupID"
    PROP_ORIGIN_OFFSET = "origin_offset"
    PROP_ORIGIN_MATRIX = "origin_matrix"
    PROP_PART_COUNT = "part_count"
    PROP_IS_MIRROR = "is_mirror"
    
    PROP_MATRIX_LOCAL = "matrix_local"

    def __init__(self):
        """Initialize the Groups manager."""
        pass


    @staticmethod
    def cache_relative_matrices( parent_obj, object_list ) :
        """
        Calculates the local matrices of objects relative to a parent, without
        actually changing their hierarchy.

        Args:
            parent_obj: The reference parent object
            object_list: List of objects to cache

        Returns:
            JSON-serialized string of cache data
        """
        cache_data = {}
        parent_matrix_inverted = parent_obj.matrix_world.inverted()

        for obj in object_list:
            if obj == parent_obj or Group.PROP_OBJECT_ID not in obj:
                continue

            matrix_local = parent_matrix_inverted @ obj.matrix_world
            matrix_list = [list(row) for row in matrix_local]

            cache = {
                Group.PROP_OBJECT_ID: obj[Group.PROP_OBJECT_ID],
                Group.PROP_USER_DATA: obj.get(Group.PROP_USER_DATA, 0),
                Group.PROP_TIMESTAMP: obj.get(Group.PROP_TIMESTAMP, int(time.time())),
                Group.PROP_MATRIX_LOCAL: matrix_list,
            }

            cache_data[obj.name] = cache

        return json.dumps(cache_data)
        

    @staticmethod
    def extract_cached_data(parent_obj) :
        """
        Reads the custom property cache from parent_obj and returns a dictionary
        mapping child names to cached data.

        Args:
            parent_obj: The parent object containing the cache

        Returns:
            Dictionary of cached child data, or None if not found or invalid
        """
        if Group.PROP_CHILD_CACHE not in parent_obj:
            return None, None

        try:
            cache_child_data = json.loads(parent_obj[Group.PROP_CHILD_CACHE])
            origin_matrix_str = parent_obj.get(Group.PROP_ORIGIN_MATRIX)
            origin_matrix = Group.str_to_matrix(origin_matrix_str) if origin_matrix_str else None
            return cache_child_data, origin_matrix
        except (json.JSONDecodeError, Exception):
            return None, None


    @staticmethod
    def group_objects(objects_to_group, target_matrix=None):
        """
        Groups multiple objects into a single merged object.
        Applies the location and local rotation axes from the provided target_matrix.

        Args:
            objects_list (list[bpy.types.Object]): A list of Blender objects to be grouped.
            target_matrix (mathutils.Matrix, optional): A 4x4 transformation matrix defining the 
                origin location and local rotation axes for the new grouped object. 
                If None, the median position of all objects is used with a default global rotation.

        Returns:
            bpy.types.Object | None: Lis of objects if sucessful or None
        """
        if objects_to_group is None or len(objects_to_group) == 0:
            return None

        objects_list = []
        # Check if any object already has a GroupID
        for obj in objects_to_group:
            if Group.PROP_GROUP_ID in obj:
                return None
            if "ObjectID" in obj:
                objects_list.append(obj)

        # Keep location, rotation, and scale from the target matrix
        if target_matrix is not None:
            clean_matrix = target_matrix.copy()
        else:
            # Fallback: Calculate median position if no matrix is given
            clean_matrix = Matrix.Identity(4)
            total_location = Vector((0.0, 0.0, 0.0))
            for obj in objects_list:
                total_location += obj.matrix_world.translation
            clean_matrix.translation = total_location / len(objects_list)

        # Merge objects
        merged_object = blend_utils.merge_objects(objects_list, "Grouped_Objects")

        # this check used to sit after the write below, so a failed merge threw
        # a TypeError on None instead of returning None the way it says it does
        if merged_object is None:
            return None

        target_matrix_cache = json.dumps([list(row) for row in target_matrix]) if target_matrix is not None else None
        merged_object[Group.PROP_ORIGIN_MATRIX] = target_matrix_cache

        prev_position = merged_object.matrix_world.translation.copy()

        # Transform vertices so they do not visually move when we apply the new matrix.
        # Mesh.transform rather than a python loop over the vertices: it is the
        # difference between 30 ms and 1 ms on a small group, and it also carries
        # the custom split normals round with the geometry, which the loop left
        # pointing the old way.
        current_matrix = merged_object.matrix_world.copy()
        transform_matrix = clean_matrix.inverted() @ current_matrix

        merged_object.data.transform(transform_matrix)

        # Apply the clean matrix (this sets the new location and local axes)
        merged_object.matrix_world = clean_matrix
        merged_object.data.update()

        # Calculate origin difference for the cache
        new_location = merged_object.matrix_world.translation.copy()
        origin_difference = prev_position - new_location

        # Convert difference to local space and store
        local_difference = merged_object.matrix_world.to_3x3().inverted() @ origin_difference
        merged_object[Group.PROP_ORIGIN_OFFSET] = local_difference

        # Cache all combined objects
        child_cache = Group.cache_relative_matrices(merged_object, objects_list)
        #child_cache[Group.PROP_ORIGIN_MATRIX] = target_matrix_cache
        number_of_objects_grouped = len(objects_list)
        merged_object[Group.PROP_CHILD_CACHE] = child_cache
        merged_object[Group.PROP_GROUP_ID] = str(uuid.uuid4())
        merged_object[Group.PROP_PART_COUNT] = number_of_objects_grouped
        merged_object[Group.PROP_IS_MIRROR] = False

        # Carry a colour onto the group.
        # merge_objects strips every custom property off the merged object, and
        # an absent palette slot reads as black in the colourise node group, so
        # a group of high res parts would otherwise come out with all of its
        # paintable regions blacked out.
        group_user_data = Group.get_representative_user_data(objects_list)
        if group_user_data is not None:
            # Only the palette properties, never UserData - ungroup treats a
            # UserData on the group as a master colour to force onto every
            # child, and that should only happen when the user has actually
            # recoloured the group, not just because they grouped it.
            materials_v2.apply(merged_object, group_user_data)

        # Delete original objects - in one batch, because a remove() per object
        # re-syncs the whole scene each time and costs about 4 ms a piece on a
        # big base
        bpy.data.batch_remove([obj for obj in objects_to_group if obj is not None])

        return merged_object

    @staticmethod
    def get_representative_user_data(objects_list):
        """Pick the one colour a merged group should show.

        A group is a single object, and colour lives on the object, so it can
        only carry one. The most common colour among the parts is the closest
        match to what was just grouped - a wall of ten white panels with one red
        door should read as white. Ties go to whichever was seen first.

        Only high res parts get a vote. The old proxies keep their colour in
        their material, which survives the merge on its own.

        Args:
            objects_list (list): The objects being grouped.

        Returns:
            The UserData value to show, or None if nothing needs one.
        """
        counts = {}
        for obj in objects_list:
            if not materials_v2.is_high_res(obj):
                continue
            user_data = obj.get(Part.PROP_USER_DATA)
            if user_data is None:
                continue
            user_data = str(user_data)
            counts[user_data] = counts.get(user_data, 0) + 1

        if not counts:
            return None
        return max(counts, key=counts.get)

    @staticmethod
    def ungroup_objects( builder, parent_obj):
        """
        Restores grouped objects back to their original state from cache.

        Args:
            builder: The builder instance (with add_part method)
            parent_obj: The grouped parent object to ungroup

        Returns:
            List of restored objects, or None if operation fails
        """
        cached_child_data, origin_matrix = Group.extract_cached_data(parent_obj)
        if not cached_child_data:
            return None
        
        master_user_data = parent_obj.get("UserData",None)
        
        restored_objects = []

        for child_name, cache_data in cached_child_data.items():

            object_id = cache_data[Group.PROP_OBJECT_ID]
            if master_user_data is not None:
                user_data = master_user_data 
            else:
                user_data = cache_data.get(Group.PROP_USER_DATA, 0) 
            time_stamp = cache_data.get(Group.PROP_TIMESTAMP, int(time.time()))

            # Add part via builder - the caller's builder is passed through so
            # its part cache stays the one that gets filled
            new_part = _builder_v2().add_part(
                object_id, user_data, builder_object=builder
            )
            if new_part is None or not hasattr(new_part, "object"):
                continue

            new_obj = new_part.object

            # Restore properties
            new_obj[Group.PROP_TIMESTAMP] = time_stamp
            if Group.PROP_MESSAGE in cache_data:
                new_obj[Group.PROP_MESSAGE] = cache_data[Group.PROP_MESSAGE]

            # Restore transform
            matrix_local_data = cache_data.get("matrix_local")
            if not matrix_local_data:
                continue

            new_obj.matrix_world = Group.restore_matrix_world(parent_obj, cache_data)
            restored_objects.append(new_obj)

        # Delete parent object
        bpy.data.objects.remove(parent_obj, do_unlink=True)
        return restored_objects


    @staticmethod
    def serialise(parent_obj):
        """
        Converts grouped objects to serialized format for No Man's Sky savefile.

        Args:
            parent_obj: The group_object object to serialize, these obejcts have "GroupID" property attached to them

        Returns:
            List of serialized object dictionaries, or None if operation fails
        """
        cached_child_data, origin_matrix = Group.extract_cached_data(parent_obj)
        if not cached_child_data:
            return None
        
        master_user_data = parent_obj.get("UserData",None)

        serialized_objects = []
        for child_name, cache_data in cached_child_data.items():

            object_id = cache_data[Group.PROP_OBJECT_ID]
            if master_user_data is not None:
                user_data = master_user_data 
            else:
                user_data = cache_data.get(Group.PROP_USER_DATA, 0) 
            time_stamp = cache_data.get(Group.PROP_TIMESTAMP, int(time.time()))
            message = cache_data.get(Group.PROP_MESSAGE)

            # Build world matrix
            matrix_world = Group.restore_matrix_world(parent_obj, cache_data)
            if matrix_world is None:
                continue
            
            pos, up, at = Group.extract_pos_up_at(matrix_world)
            
            data = {
                Part.PROP_TIMESTAMP: int(time_stamp),
                Part.PROP_OBJECT_ID: f"^{object_id}",
                Part.PROP_USER_DATA: int(user_data),
                Part.PROP_POSITION: [pos[0], pos[1], pos[2]],
                Part.PROP_UP: [up[0], up[1], up[2]],
                Part.PROP_AT: [at[0], at[1], at[2]],
            }

            if message is not None:
                data[Part.PROP_MESSAGE] = message

            serialized_objects.append(data)

        return serialized_objects
    
    @staticmethod
    def deserialise_to_group(builder,child_cache, origin_matrix = None):
        """
        Deserialise string to group
        Args:
            builder: The builder instance (with add_part method)
            child_cache: string containing data related to grouped object
        Returns:
            merged_group: object that is a merged group
        """
        
        if origin_matrix is None:
            origin_matrix = Group.get_default_origin_matrix()
        
        try:
            cached_child_data = json.loads(child_cache)
        except (json.JSONDecodeError, Exception) as error:
            print("Error deserialise_to_group ", error)
            return None
        
        restored_objects = []
        for child_name, cache_data in cached_child_data.items():

            object_id = cache_data[Group.PROP_OBJECT_ID]
            user_data = cache_data.get(Group.PROP_USER_DATA, 0)
            time_stamp = cache_data.get(Group.PROP_TIMESTAMP, int(time.time()))

            # Add part via builder - the caller's builder is passed through so
            # its part cache stays the one that gets filled
            new_part = _builder_v2().add_part(
                object_id, user_data, builder_object=builder
            )
            if new_part is None or not hasattr(new_part, "object"):
                continue

            new_obj = new_part.object

            # Restore properties
            new_obj[Group.PROP_TIMESTAMP] = time_stamp
            if Group.PROP_MESSAGE in cache_data:
                new_obj[Group.PROP_MESSAGE] = cache_data[Group.PROP_MESSAGE]

            # Restore transform
            matrix_local_data = cache_data.get("matrix_local")
            if not matrix_local_data:
                continue
            # multiply the current world matrix by the local matrix.
            matrix_local = mathutils.Matrix(matrix_local_data)
            new_obj.matrix_world = origin_matrix@ matrix_local
            restored_objects.append(new_obj)
        
        merged_group = Group.group_objects(restored_objects,origin_matrix)
        return merged_group
    
    @staticmethod
    def deserialise_to_objects(builder,child_cache, origin_matrix = None, overall_userdata = None):
        """
        Deserialise string to ungrouped obejcts
        Args:
            builder: The builder instance (with add_part method)
            child_cache: string containing data related to grouped object
        Returns:
            merged_group: list of ungrouped objects
        """
        
        if origin_matrix is None:
            origin_matrix = Group.get_default_origin_matrix()
        
        try:
            cached_child_data = json.loads(child_cache)
        except (json.JSONDecodeError, Exception) as error:
            print("Error deserialise_to_group ", error)
            return None 
        
        restored_objects = []
        for child_name, cache_data in cached_child_data.items():

            object_id = cache_data[Group.PROP_OBJECT_ID]
            user_data = cache_data.get(Group.PROP_USER_DATA, 0)
            time_stamp = cache_data.get(Group.PROP_TIMESTAMP, int(time.time()))

            # Add part via builder - the caller's builder is passed through so
            # its part cache stays the one that gets filled
            new_part = _builder_v2().add_part(
                object_id, user_data, builder_object=builder
            )
            if new_part is None or not hasattr(new_part, "object"):
                continue

            new_obj = new_part.object

            # Restore properties
            new_obj[Group.PROP_TIMESTAMP] = time_stamp
            if Group.PROP_MESSAGE in cache_data:
                new_obj[Group.PROP_MESSAGE] = cache_data[Group.PROP_MESSAGE]

            # Restore transform
            matrix_local_data = cache_data.get("matrix_local")
            if not matrix_local_data:
                continue
            # multiply the current world matrix by the local matrix.
            matrix_local = mathutils.Matrix(matrix_local_data)
            new_obj.matrix_world = origin_matrix@ matrix_local
            restored_objects.append(new_obj)
            
        return restored_objects
    
    @staticmethod
    def restore_matrix_world(parent_obj, child_cache_data):
        matrix_local_data = child_cache_data.get("matrix_local")
        if not matrix_local_data:
            return None
        
        # multiply the parent's current world matrix by the local matrix.
        matrix_local = mathutils.Matrix(matrix_local_data)
        matrix_world = parent_obj.matrix_world @ matrix_local
        
        return matrix_world
    
    @staticmethod
    def extract_pos_up_at(matrix_world):
        # Bring the matrix from Blender Z-Up spoace into standard Y-up space.
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
        
        return pos, up, at
    
    @staticmethod
    def get_all_groups():
        """  Returns all groups presetin inside view_layer"""
        groups = []
        for obj in bpy.context.view_layer.objects:
            try:
                if obj is not None:
                    if Group.PROP_GROUP_ID in obj:
                        groups.append(obj)
            except ReferenceError:
                continue
        return groups
    
    @staticmethod
    def find_mirror_group(target, groups_list = None):
        """ 
        Return first group found in scene that is mirror of target object 
        Args:
            target: object who's mirror needs to be found,
            groups_list (optional) : list of groups in which search will take place, if None, all other groups will be used
        
        Returns:
            First mirror group found or None if no match was found
        """
        existing_groups = Group.get_all_groups() if groups_list is None else groups_list
        is_target_mirror = target.get(Group.PROP_IS_MIRROR, False)   
        
        for obj in existing_groups:
            try:
                # validate obj
                if obj is None or Group.PROP_GROUP_ID not in obj:
                    continue
                # check if target is not equal to obj
                if obj.name == target.name:
                    continue
                
                # check if their GroupIDs are equal
                if obj[Group.PROP_GROUP_ID] != target[Group.PROP_GROUP_ID]:
                    continue
                
                # Mirror of groups with same GroupIDs is needed so obj need to opposite "is_mirror" value than target object
                if obj[Group.PROP_IS_MIRROR] != is_target_mirror:
                    # return after all conditions are met because only first match is needed
                    return obj
            except ReferenceError:
                continue
        return None
    
    @staticmethod
    def extract_origin_matrix(group_obj):
        target_matrix_cache = group_obj[Group.PROP_ORIGIN_MATRIX]
        return Group.str_to_matrix(target_matrix_cache)
    
    @staticmethod
    def str_to_matrix(json_string):
        
        if not json_string:
            return None
        
        
        try:
            return Matrix(json.loads(json_string))
        except (json.JSONDecodeError, Exception):
            print("error deconding json string : ", json_string)
            return None
        
    @staticmethod
    def get_default_origin_matrix():
        return mathutils.Matrix.Identity(4)
    
    @staticmethod
    def mirror_cache_data(child_cache, origin_matrix, axis, center):
        """Mirror a group's cached children without building any of them.

        curve.mirror_curve used to deserialise the whole group into real
        objects, mirror those with the build tool, merge them back into a mesh
        and then delete the mesh - all to end up with two strings. Every step of
        that is matrix arithmetic on the cache, so this does the arithmetic.

        The maths is deliberately step for step what the long way round did:
        each child's world matrix is rebuilt from the origin, mirrored exactly
        as build_tool.mirror would mirror the object (same axis mapping, same
        per part corrections, keyed on the id before the swap), then expressed
        relative to the mirrored origin - which is what cache_relative_matrices
        would have recorded off the regrouped object.

        Args:
            child_cache (str): The group's serialised child cache.
            origin_matrix (mathutils.Matrix): The group's origin, or None.
            axis (str): Mirror axis, "X", "Y" or "Z".
            center: Centre of reflection.

        Returns:
            tuple: (new child cache json, new origin matrix) or (None, None).
        """
        try:
            cached_child_data = json.loads(child_cache)
        except (json.JSONDecodeError, Exception) as error:
            print("Error mirroring group cache: ", error)
            return None, None

        if origin_matrix is None:
            origin_matrix = Group.get_default_origin_matrix()

        new_origin = mirror_utils.mirror_matrix_world_universal(
            None, origin_matrix, axis, center
        )
        new_origin_inverted = new_origin.inverted()

        # build_tool.mirror is only ever handed X or Z for the parts themselves
        tool_axis = "Z" if axis == "Z" else "X"

        new_child_cache = {}
        for child_name, cache_data in cached_child_data.items():
            matrix_local_data = cache_data.get(Group.PROP_MATRIX_LOCAL)
            if not matrix_local_data:
                continue

            new_cache_data = dict(cache_data)
            object_id = cache_data[Group.PROP_OBJECT_ID]

            # a part whose mirrored twin is its own model gets swapped for it,
            # and that changes how the transform has to be corrected
            mirror_part_id = Part.get_mirror_part_id(object_id)
            mirror_part_exist = mirror_part_id in nice_name_dictionary

            matrix_world = origin_matrix @ mathutils.Matrix(matrix_local_data)
            # the correction is keyed on the id the part had going in, which is
            # what build_tool.mirror passes too
            matrix_world = mirror_utils.mirror_matrix_world_universal(
                object_id, matrix_world, tool_axis, center,
                mirror_part_exist=mirror_part_exist
            )
            matrix_local = new_origin_inverted @ matrix_world

            if mirror_part_exist:
                new_cache_data[Group.PROP_OBJECT_ID] = mirror_part_id
            new_cache_data[Group.PROP_MATRIX_LOCAL] = [
                list(row) for row in matrix_local
            ]
            new_child_cache[child_name] = new_cache_data

        return json.dumps(new_child_cache), new_origin

    @staticmethod
    def mirror_group_cache(group_obj, axis, center):
        """
        Directly mirrors the cached child data and origin matrix of a group object
        without needing to unpack and repack the geometry in the scene.
        """
        cached_child_data, origin_matrix = Group.extract_cached_data(group_obj)

        if cached_child_data is None:
            print("Error mirroring group cache: child cache is None")
            return None, None

        # This used to carry its own copy of the mirror maths, which was never
        # called and did not match what mirroring a group actually does. It now
        # goes through the one implementation that is checked against the long
        # build/mirror/regroup route.
        new_child_cache, new_origin_matrix = Group.mirror_cache_data(
            group_obj[Group.PROP_CHILD_CACHE], origin_matrix, axis, center
        )
        if new_child_cache is None:
            return None, None

        if new_origin_matrix is not None:
            group_obj[Group.PROP_ORIGIN_MATRIX] = json.dumps(
                [list(row) for row in new_origin_matrix]
            )
        group_obj[Group.PROP_CHILD_CACHE] = new_child_cache

        return json.loads(new_child_cache), new_origin_matrix
