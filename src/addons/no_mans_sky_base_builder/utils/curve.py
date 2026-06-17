from . import blend_utils
import bpy
from bpy.app.handlers import persistent
import mathutils

from . import curve_utils

def get_curve_children(curve_obj):
    """
    Fast O(1) lookup helper that bypasses iterating over all scene objects.
    Falls back to a scene scan only if the registry needs to be rebuilt.
    """
    names_str = curve_obj.get("curve_children_names", "")
    children = []
    
    if names_str:
        names = names_str.split(",")
        valid_names = []
        for name in names:
            obj = bpy.data.objects.get(name)
            if obj and obj.get("curve_parent") == curve_obj.name:
                children.append(obj)
                valid_names.append(name)
        # Keep registry clean if objects were manually deleted by user
        if len(valid_names) != len(names):
            curve_obj["curve_children_names"] = ",".join(valid_names)
            
    # Rebuild registry fallback (for backward compatibility or first runs)
    if not children and curve_obj.get("has_linked_objects"):
        for obj in bpy.context.scene.objects:
            if obj.get("curve_parent") == curve_obj.name:
                children.append(obj)
        curve_obj["curve_children_names"] = ",".join([o.name for o in children])
        
    return children


def update_curve_children_registry(curve_obj, children_list):
    """Updates the fast-lookup cache on the curve."""
    curve_obj["curve_children_names"] = ",".join([obj.name for obj in children_list])


def update_curve_duplicates(curve_obj, radius_multiplier = None, attaching = False):
    # Only loops over the specific children assigned to this curve
    for obj in get_curve_children(curve_obj):
        curve_utils.update_obj_transformations(obj, curve_obj)
        
        if "detached_rotation_offset" in obj and attaching:
            offset_rot = mathutils.Euler(obj["detached_rotation_offset"]).to_matrix()
            current_rot = obj.rotation_euler.to_matrix()
            final_rot = current_rot @ offset_rot
            obj.rotation_euler = final_rot.to_euler(obj.rotation_mode)


def duplicate_along_curve(builder, object, curve, number_of_duplicates=10, radius_multiplier=1.0):
    register_curve_handler()
    
    
    if curve.get("children_detached"):
        raise RuntimeError(
            f"Cannot modify duplicates on '{curve.name}' while children are temporarily detached. "
            "Call reattach_curve_children() first."
        )
    
    gap_distance = 0.0 if number_of_duplicates <= 1 else 1.0 / (number_of_duplicates - 1)
   
    curve["has_linked_objects"] = True
    curve["gap_distance"] = gap_distance
    curve["original_object"] = object
    curve["radius_multiplier"] = radius_multiplier
    curve["paused"] = False

    existing_objs = [object]
    
    if object.get("curve_parent") != curve.name:
        object["curve_parent"] = curve.name
        object["base_scale"] = (object.scale.x, object.scale.y, object.scale.z)
        
        has_constraint = any(c.type == 'FOLLOW_PATH' and c.target == curve for c in object.constraints)
        if not has_constraint:
            constraint = object.constraints.new(type='FOLLOW_PATH')
            constraint.target = curve
            constraint.use_fixed_location = True
            constraint.use_curve_follow = True

    # Fast gather via registry cache
    for obj in get_curve_children(curve):
        if obj != object:
            existing_objs.append(obj)
            
    existing_objs.sort(key=lambda x: x.get("curve_factor", 0.0))

    object_id = object["ObjectID"]
    user_data = object["UserData"]
    
    current_count = len(existing_objs)
    if number_of_duplicates < current_count:
        for _ in range(current_count - number_of_duplicates):
            obj_to_remove = existing_objs.pop()
            if obj_to_remove == object:
                existing_objs.insert(0, obj_to_remove)
                continue 
            bpy.data.objects.remove(obj_to_remove, do_unlink=True)
            
    elif number_of_duplicates > current_count:
        
        last_object_base_scale = object.get("base_scale")
        scale_x = last_object_base_scale[0]
        
        for _ in range(number_of_duplicates - current_count):
            new_item = builder.add_part(object_id, user_data=user_data)
            new_obj = new_item.object
            
            constraint = new_obj.constraints.new(type='FOLLOW_PATH')
            constraint.target = curve
            constraint.use_fixed_location = True
            constraint.use_curve_follow = True
            
            obj_scale = scale_x#new_obj.scale.x 
            new_obj["base_scale"] = (obj_scale, obj_scale, obj_scale)
            new_obj["curve_parent"] = curve.name
            new_obj["curve_parent_ref"] = curve
            new_obj["new_object"] = True
            
            new_obj.rotation_euler = object.rotation_euler.copy()
            
            existing_objs.append(new_obj)

    # Sync the cache list registry
    update_curve_children_registry(curve, existing_objs)

    for i, obj in enumerate(existing_objs):
        percentage_count = i * gap_distance
        obj.location = (0.0, 0.0, 0.0)
        constraint = next((c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve), None)
        
        if constraint:
            constraint.offset_factor = percentage_count
        obj["curve_factor"] = percentage_count
        
        curve_utils.update_obj_transformations(obj, curve)
        if "detached_rotation_offset" not in obj:
            obj.rotation_euler.x = 0.0
            obj.rotation_euler.z = 0.0
            
        obj.hide_select = True
        obj.lock_location = (True, True, True)
        
        #if i == current_count - 1:
        curve["last_object"] = obj
        
    curve["objects_count"] = len(existing_objs)
            


def is_bezier_or_nurbs_path(curve):
    if not curve or curve.type != 'CURVE':
        return False
    for spline in curve.data.splines:
        if spline.type in {'BEZIER', 'NURBS'}:
            return True
    return False


def delete_duplicated_objects(curve):
    if not is_bezier_or_nurbs_path(curve):
        return

    # Delete directly via cached collection
    for obj in get_curve_children(curve):
        bpy.data.objects.remove(obj, do_unlink=True)

    curve["has_linked_objects"] = False
    curve["children_detached"] = False
    curve["curve_children_names"] = ""
    
        
def apply_curve_transforms_and_detach(curve):
    if not is_bezier_or_nurbs_path(curve):
        raise TypeError("Please provide a valid curve object.")
    
    detached_count = 0
    duplicates = get_curve_children(curve)
    
    bpy.context.view_layer.update()
    
    for obj in duplicates:
        constraints_to_remove = [c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve]
        if "curve_parent_ref" in obj:
            del obj["curve_parent_ref"]
            
        if constraints_to_remove:
            baked_matrix = obj.matrix_world.copy()
            for c in constraints_to_remove:
                obj.constraints.remove(c)
            obj.matrix_world = baked_matrix
            detached_count += 1
            
        obj.hide_select = False
        obj.lock_location = (False, False, False)
    
    blend_utils.select(duplicates)
    curve["has_linked_objects"] = False
    return detached_count


def temporarily_detach_curve_children(curve):
    if not is_bezier_or_nurbs_path(curve):
        raise TypeError("Please provide a valid curve object.")

    if curve.get("children_detached"):
        return 0

    bpy.context.view_layer.update()
    detached_count = 0

    for obj in get_curve_children(curve):
        constraints_to_remove = [c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve]
        if not constraints_to_remove:
            continue

        baked_matrix = obj.matrix_world.copy()
        for c in constraints_to_remove:
            obj.constraints.remove(c)

        obj.matrix_world = baked_matrix
        obj["temp_detached"] = True
        obj.hide_select = False
        
        detached_count += 1

    curve["children_detached"] = True
    curve["paused"] = True
    return detached_count


def reattach_curve_children(curve):
    """Optimized: Processes all structural data first, batches into ONE view_layer update."""
    if not is_bezier_or_nurbs_path(curve):
        raise TypeError("Please provide a valid curve object.")

    if not curve.get("children_detached"):
        return 0

    children = get_curve_children(curve)
    detached_matrices = {}
    reattach_objs = []

    # Loop 1: Fast tracking setups (No dependency calculations here)
    for obj in children:
        if not obj.get("temp_detached"):
            continue

        detached_matrices[obj] = obj.matrix_world.copy()
        reattach_objs.append(obj)

        constraint = obj.constraints.new(type='FOLLOW_PATH')
        constraint.target = curve
        constraint.use_fixed_location = True
        constraint.use_curve_follow = True
        constraint.offset_factor = obj.get("curve_factor", 0.0)

        obj.location = (0.0, 0.0, 0.0)
        obj.rotation_euler = (0.0, 0.0, 0.0)
        obj.hide_select = True

    if reattach_objs:
        # BATCHED UPDATE: Evaluates the entire array's native track alignments simultaneously
        bpy.context.view_layer.update()

        # Loop 2: Read evaluation matrices instantly from the single update cache
        for obj in reattach_objs:
            native_curve_rot = obj.matrix_world.to_3x3().normalized()
            user_detached_rot = detached_matrices[obj].to_3x3().normalized()
            
            rotation_offset_matrix = native_curve_rot.inverted() @ user_detached_rot
            obj["detached_rotation_offset"] = rotation_offset_matrix.to_euler()

            curve_utils.update_obj_transformations(obj, curve)
            del obj["temp_detached"]

    curve["children_detached"] = False
    curve["paused"] = False

    update_curve_duplicates(curve, attaching = True)
    bpy.context.view_layer.update()

    return len(reattach_objs)


def select_parent_curve(object):
    parent_curve = object.get("curve_parent_ref", None)
    if parent_curve:
        blend_utils.select(parent_curve)
            
def select_children_of_curve(curve):
    if not is_bezier_or_nurbs_path(curve):
        return
    blend_utils.select(get_curve_children(curve))
    
    
def edit_radius_multiplier(curve, new_radius_multiplier):
    if not is_bezier_or_nurbs_path(curve):
        return
    curve["radius_multiplier"] = new_radius_multiplier
    update_curve_duplicates(curve)
    
    
@persistent
def curve_duplicate_handler(scene, depsgraph):
    updated_curves = set()
    for update in depsgraph.updates:
        id_data = update.id
        if isinstance(id_data, bpy.types.Object) and id_data.type == 'CURVE':
            updated_curves.add(id_data)
            
    for curve in updated_curves:
        if curve.get("children_detached") or curve.get("paused"):
            continue
        update_curve_duplicates(curve)
        

def register_curve_handler():
    if curve_duplicate_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(curve_duplicate_handler)