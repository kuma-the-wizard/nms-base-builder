"""Convenient methods to perform common blender related tasks."""

import math

import addon_utils
import bpy


def load_plugin(plugin_name):
    """Load a blender plugin."""
    is_enabled, _ = addon_utils.check(plugin_name)
    if not is_enabled:
        addon_utils.enable(plugin_name)


def add_to_scene(item, collection_name="Collection"):
    """Add an item to the main blender collection.

    A Collection is a concept introduced in Blender 2.8. Which can be seen
    as a group/scene of items.

    By default we should add all new items to the default "Collection".

    Args:
        item (bpy_types.Object): The blender object.
        collection_name(str): The name of the collection to place the item in.
    """
    # Validate collection existence.
    if collection_name not in bpy.data.collections:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

    # Add the item to the collection.
    object_set = bpy.data.collections[collection_name].objects
    if item.name not in object_set:
        object_set.link(item)


def get_item_by_name(item_name):
    """Get a Blender object by specifying the name of the object.

    Args:
        item_name (str): The name of the item.

    Returns:
        bpy_types.Object: The Blender object.
    """
    return bpy.data.objects[item_name]


def item_exists_by_name(item_name):
    """Check for a Blender object by specifying the name of the object.

    Args:
        item_name (str): The name of the item.

    Returns:
        bool: True iff object exists.
    """
    return item_name in bpy.data.objects


def remove_object(name):
    """Remove an item from the scene by specifying it's name.

    Args:
        name (str): The name of the object to remove.
    """
    objs = bpy.data.objects
    if name in objs:
        objs.remove(objs[name], do_unlink=True)


# Force refresh of scene so the matrix values are correct.
def scene_refresh():
    """Force the dependency graph to update.

    This is sometimes required when adding and removing constraints on
    certain objects.
    """
    layer = bpy.context.view_layer
    layer.update()


def set_active_item(item):
    """Set the item to be the active item.

    This is similar to the selected state.

    Args:
        item (bpy_types.Object): The item to set as active.
    """
    bpy.context.view_layer.objects.active = item


def select(selection, add=False):
    """Select an item.

    The add flag determines if the item is appended to the current selection
    or if we should only select that particular item.

    Args:
        selection (bpy_types.Object, list): The item to be selected.
            This can be a singular object or a list of objects.
        add (bool): Appends the selection if `True` else select by itself.
    """
    # Deselect all.
    if not add:
        bpy.ops.object.select_all(action="DESELECT")
        set_active_item(None)

    # Ensure List.
    if not isinstance(selection, list):
        selection = [selection]

    for item in selection:
        # Check if item exists in the active view layer before selecting
        if item is not None and item.name in bpy.context.view_layer.objects:
            item.select_set(True)

    # Make the last item the active one (only if valid)
    if selection and selection[-1] is not None:
        if selection[-1].name in bpy.context.view_layer.objects:
            selection[-1].select_set(True)
            set_active_item(selection[-1])


def get_current_selection():
    """Get the current selected item.

    Returns:
        bpy_types.Object: The selected item.
    """
    selected_objects = [o for o in bpy.context.scene.objects if o.select_get()]
    if selected_objects:
        return selected_objects[-1]


def get_distance_between(matrix1, matrix2):
    """Get the distance between two matrices.

    Args:
        matrix1: First matrix input.
        matrix2: Second matrix input.

    Returns:
        float: The distance between the two.
    """
    translate1 = matrix1.decompose()[0]
    translate2 = matrix2.decompose()[0]
    return math.sqrt(
        (translate2.x - translate1.x) ** 2
        + (translate2.y - translate1.y) ** 2
        + (translate2.z - translate1.z) ** 2
    )


def delete(bpy_object):
    """Remove the item and everything below it."""
    # Deselect all
    #bpy.ops.object.select_all(action="DESELECT")

    # Parent items to control.
    for part in bpy_object.children:
        bpy.data.objects.remove(part, do_unlink=True)

    bpy.data.objects.remove(bpy_object, do_unlink=True)
    
    
def find_duplicates(decimals = 4):
    """
    Removes duplicate objects based on:
        - name
        - world location
        - world rotation
        - world scale

    Keeps the first found object unselected and select subsequent duplicates.
    """

    seen_objects = {}
    duplicates = []

    for obj in bpy.context.view_layer.objects:
        location_vector, rotation_quaternion, scale_vector = obj.matrix_world.decompose()
        
        location = (
            round(location_vector.x,decimals),
            round(location_vector.y,decimals),
            round(location_vector.z,decimals)
        )
        
        rotation_euler = rotation_quaternion.to_euler("XYZ")
        rotation = (
            round(rotation_euler.x, decimals),
            round(rotation_euler.y, decimals),
            round(rotation_euler.z, decimals)
        )
        
        scale = round(scale_vector.x, decimals)
        object_key = (
            obj.get("ObjectID",obj.name),
            location,
            rotation,
            scale,
        )
        
        if object_key in seen_objects:
            duplicates.append(obj.get("object", obj))
        else:
            seen_objects[object_key] = obj

    # select duplicates
    for obj in duplicates:
            select(duplicates)

    print(f"Selected {len(duplicates)} duplicate objects")
    return len(duplicates)

def duplicate_part(target):
    """ Duplicate an object and place it in same collection as original object
        Return duplicated object
    """
    new_item = target.copy()
    if new_item.data:
        new_item.data = target.data.copy()
    for collection in target.users_collection:
        collection.objects.link(new_item)
    return new_item

def parent_objects(parent, children):
    """
    Parent one or more objects to a parent object without moving them.
    Args:
        parent (bpy.types.Object):
            The parent object.
        children (bpy.types.Object | Iterable[bpy.types.Object]):
            A single object or a list of objects to parent.
    """

    # Allow a single object to be passed.
    if isinstance(children, bpy.types.Object):
        children = [children]

    for child in children:

        # Skip the parent itself.
        if child == parent:
            continue

        # Save the current world transform.
        world_matrix = child.matrix_world.copy()

        # Set the parent.
        child.parent = parent

        # Keep the child in the same position.
        child.matrix_parent_inverse = parent.matrix_world.inverted()
        child.matrix_world = world_matrix
        
def unparent_objects(parent):
    """
    Unparent all direct children of an object without moving them.
    Args:
        parent (bpy.types.Object): The parent object.
    Returns:
        list[bpy.types.Object]: A list of the objects that were unparented.
    """
    # Force evaluation of children into a static list.
    # Otherwise, modifying child.parent alters parent.children mid-loop!
    children_list = list(parent.children)

    for child in parent.children:
        # Save the current world transform so it doesn't jump
        world_matrix = child.matrix_world.copy()

        # Clear the parent
        child.parent = None

        # Reapply the world transform in global space
        child.matrix_world = world_matrix

    return children_list
        
def change_object_visibility(objects, is_visibe = False):
    """
    Hide or show one or more objects in the viewport and renders.

    Args:
        objects (bpy.types.Object | Iterable[bpy.types.Object]):
            A single object or a list of objects.

        hide (bool):
            True to hide the objects, False to show them.
    """

    # Allow a single object to be passed.
    if isinstance(objects, bpy.types.Object):
        objects = [objects]

    for obj in objects:
        obj.hide_set(not is_visibe)      # Hide in viewport
        obj.hide_render = not is_visibe  # Hide in renders
        
def merge_objects(objects, object_name):
    """
    Using Blender's APIs merge the given mesh objects into a new object while leaving the originals
    untouched.

    Parameters:
        objects (list[bpy.types.Object]): Objects to merge.
        object_name (str): Name of the merged object.

    Returns:
        bpy.types.Object | None
    """

    context = bpy.context
    view_layer = context.view_layer

    # Filter mesh objects
    objects = [obj for obj in objects if obj and obj.type == 'MESH']

    if not objects:
        print("No objects to merge")
        return None

    try:
        
        bpy.ops.object.select_all(action='DESELECT')
        
        for obj in objects:
            obj.select_set(True)

        view_layer.objects.active = objects[0]

        # Duplicate and join
        bpy.ops.object.duplicate(linked=False)
        duplicates = context.selected_objects[:]

        view_layer.objects.active = duplicates[0]
        bpy.ops.object.join()

        merged = view_layer.objects.active
        merged.name = object_name
        
        # delete unnecessary custom properties 
        for key in list(merged.keys()):
            del merged[key]

        # Force Blender to update the viewport and geometry cache
        merged.data.update()
        print("Group created : ", merged.name)
        return merged

    except Exception as error:
        print("Error Occured while grouping objects : ", str(error))
        return None 