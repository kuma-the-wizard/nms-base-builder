from . import blend_utils
import bpy
from mathutils import Matrix
from bpy.app.handlers import persistent

from mathutils.geometry import interpolate_bezier
import mathutils

import json


def get_spline_segment_lengths(spline, resolution=12):
    """
    Approximates the length of each segment between control points
    so we can find the true physical distance along the curve.
    """
    points = spline.bezier_points if spline.bezier_points else spline.points
    count = len(points)
    
    if count < 2:
        return [0.0], 0.0

    segment_lengths = []
    total_length = 0.0
    
    # Check if curve is a closed loop (cyclic)
    is_cyclic = spline.use_cyclic_u
    segment_count = count if is_cyclic else count - 1

    for i in range(segment_count):
        p0 = points[i]
        p1 = points[(i + 1) % count]
        
        if spline.type == 'BEZIER':
            # Interpolate points along the bezier curve segment to measure its real length
            segment_pts = interpolate_bezier(
                p0.co, p0.handle_right, p1.handle_left, p1.co, resolution + 1
            )
            # Add up the distances between the interpolated points
            seg_len = sum((segment_pts[j+1] - segment_pts[j]).length for j in range(len(segment_pts) - 1))
        else:
            # For Poly or NURBS (4D coordinates require fallback to 3D)
            v0 = p0.co.xyz if len(p0.co) == 4 else p0.co
            v1 = p1.co.xyz if len(p1.co) == 4 else p1.co
            seg_len = (v0 - v1).length
            
        segment_lengths.append(seg_len)
        total_length += seg_len

    return segment_lengths, total_length

# get rotation and size for indivicual duplicate along curve according to nearest points.
# calculate what radius and tilt should be if object is between points of different radius and tilt
def get_curve_radius_tilt(curve_obj, factor):
    """
    Calculates radius and tilt based on the actual physical arc-length of the curve.
    """
    spline = curve_obj.data.splines[0]
    points = spline.bezier_points if spline.bezier_points else spline.points
    count = len(points)
    
    if count == 0:
        return 1.0, 0.0
    if count == 1:
        return points[0].radius, points[0].tilt

    # Measure the real lengths of the segments
    segment_lengths, total_length = get_spline_segment_lengths(spline, resolution=12)
    
    if total_length == 0:
        return points[0].radius, points[0].tilt
        
    # Find the target physical length based on the 0.0 - 1.0 factor
    target_length = factor * total_length
    
    accumulated_length = 0.0
    for i, seg_len in enumerate(segment_lengths):
        if accumulated_length + seg_len >= target_length or i == len(segment_lengths) - 1:
            # The target length falls exactly inside this segment.
            # Calculate where we are inside THIS specific segment (0.0 to 1.0)
            if seg_len == 0:
                t = 0.0
            else:
                t = (target_length - accumulated_length) / seg_len
                
            p0 = points[i]
            p1 = points[(i + 1) % count]
            
            # Interpolate radius and tilt using the true segment percentage
            radius = (1.0 - t) * p0.radius + t * p1.radius
            tilt = (1.0 - t) * p0.tilt + t * p1.tilt
            
            return radius, tilt
            
        accumulated_length += seg_len

    # Fallback to the last point
    return points[-1].radius, points[-1].tilt

# update tilt and scale of every duplicated object on curve
def update_curve_duplicates(curve_obj):
    curve_name = curve_obj.name
    for obj in bpy.data.objects:
        if obj.get("curve_parent") != curve_name:
            continue

        factor = obj.get("curve_factor")
        if factor is None:
            continue
        
        radius_multiplier = curve_obj.get("radius_multiplier", 1.0)
        
        radius, tilt = get_curve_radius_tilt(curve_obj, factor)
        base_scale = obj.get("base_scale")
        if base_scale:
            # nms objects cannot have non uniform scale
            scale = base_scale[0] * radius * radius_multiplier
            obj.scale.x = scale
            obj.scale.y = scale
            obj.scale.z = scale
        
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler.y = tilt

#handles updating of tilg and scale after creation of duplicates
@persistent
def curve_duplicate_handler(scene, depsgraph):
    updated_curves = set()
    for update in depsgraph.updates:
        id_data = update.id
        if isinstance(id_data, bpy.types.Object):
            if id_data.type == 'CURVE':
                updated_curves.add(id_data)
    for curve in updated_curves:
        update_curve_duplicates(curve)
        

# register handler only once
def register_curve_handler():
    if curve_duplicate_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(
            curve_duplicate_handler
        )
       
def duplicate_along_curve(builder, object, curve, number_of_duplicates=10, radius_multiplier=1.0):
    """
    Duplicate object around a curve dynamically.
    Includes the original object, and zeros out local transforms to prevent curve offsets.
    """
    register_curve_handler()

    # 1. Setup the original object and make it the start of our pool
    existing_objs = [object]
    
    # Give the original object the required properties and constraints if it doesn't have them
    if object.get("curve_parent") != curve.name:
        object["curve_parent"] = curve.name
        object["base_scale"] = (object.scale.x, object.scale.y, object.scale.z)
        
        # Check for existing constraint, add if missing
        has_constraint = any(c.type == 'FOLLOW_PATH' and c.target == curve for c in object.constraints)
        if not has_constraint:
            constraint = object.constraints.new(type='FOLLOW_PATH')
            constraint.target = curve
            constraint.use_fixed_location = True
            constraint.use_curve_follow = True

    # Gather the rest of the previously generated duplicates
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve.name and obj != object:
            existing_objs.append(obj)
            
    # Sort them by their current position on the curve
    existing_objs.sort(key=lambda x: x.get("curve_factor", 0.0))

    object_id = object["ObjectID"]
    user_data = object["UserData"]
    
    current_count = len(existing_objs)
    
    # 2. Adjust the object count 
    if number_of_duplicates < current_count:
        # We have too many objects. Delete excess from the end.
        for _ in range(current_count - number_of_duplicates):
            obj_to_remove = existing_objs.pop()
            
            # Failsafe: NEVER delete the original object
            if obj_to_remove == object:
                existing_objs.insert(0, obj_to_remove) # Put it back
                continue 
                
            bpy.data.objects.remove(obj_to_remove, do_unlink=True)
            
    elif number_of_duplicates > current_count:
        # We need more objects, spawn the missing amount
        for _ in range(number_of_duplicates - current_count):
            new_item = builder.add_part(object_id, user_data=user_data)
            new_obj = new_item.object
            
            constraint = new_obj.constraints.new(type='FOLLOW_PATH')
            constraint.target = curve
            constraint.use_fixed_location = True
            constraint.use_curve_follow = True
            
            obj_scale = new_obj.scale.x 
            new_obj["base_scale"] = (obj_scale, obj_scale, obj_scale)
            new_obj["curve_parent"] = curve.name
            
            existing_objs.append(new_obj)

    # 3. Update positions, scales, and tilts for ALL objects
    if number_of_duplicates <= 1:
        gap_distance = 0.0
    else:
        gap_distance = 1.0 / (number_of_duplicates - 1)

    for i, obj in enumerate(existing_objs):
        percentage_count = i * gap_distance
        
        # CRITICAL FIX: Reset local location to (0,0,0) so the constraint has no offset
        obj.location = (0.0, 0.0, 0.0)
        
        constraint = next((c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve), None)
        if constraint:
            constraint.offset_factor = percentage_count
            
        obj["curve_factor"] = percentage_count
        
        radius, tilt = get_curve_radius_tilt(curve, percentage_count)

        # Update Scale
        base_scale = obj.get("base_scale")
        if base_scale:
            scale = base_scale[0] * radius * radius_multiplier
            obj.scale.x = scale
            obj.scale.y = scale
            obj.scale.z = scale
            
        # CRITICAL FIX: Reset X and Z rotations to 0, and only apply the curve tilt to Y
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler.x = 0.0
        obj.rotation_euler.y = tilt
        obj.rotation_euler.z = 0.0

    # Update curve metadata
    curve["has_linked_objects"] = True
    curve["gap_distance"] = gap_distance
    curve["original_object"] = object
    curve["radius_multiplier"] = radius_multiplier
    
          
# check if selected object is a suported curve or not
def is_bezier_or_nurbs_path(curve):
    if not curve:
        return False

    if curve.type != 'CURVE':
        return False

    for spline in curve.data.splines:
        if spline.type in {'BEZIER', 'NURBS'}:
            return True

    return False


def delete_duplicated_objects(curve):
    if not is_bezier_or_nurbs_path(curve):
        return
    
    bpy.context.view_layer.update()
    #Iterate through all objects in the scene
    for obj in bpy.context.scene.objects:
        for constraint in obj.constraints:
            # Look for Follow Path constraints targeting our specific curve
            if constraint.type == 'FOLLOW_PATH' and constraint.target == curve:
                bpy.data.objects.remove(obj, do_unlink=True)
                
    curve["has_linked_objects"] = False
    
        
        
def apply_curve_transforms_and_detach(curve):
    """
    Finds all objects constrained to the given curve via FOLLOW_PATH,
    applies their visual transformations so they stay exactly in place,
    and removes the constraint.
    """
    #if not curve
    if not is_bezier_or_nurbs_path(curve):
        raise TypeError("Please provide a valid curve object.")
    
    detached_count = 0
    duplicates = []
    
    #Update the view layer to ensure all matrices (Ctrl+T / Alt+S math) are 100% up to date
    bpy.context.view_layer.update()
    
    #Iterate through all objects in the scene
    for obj in bpy.context.scene.objects:
        
        # Look for Follow Path constraints targeting our specific curve
        constraints_to_remove = [
            c for c in obj.constraints 
            if c.type == 'FOLLOW_PATH' and c.target == curve
        ]
        
        if constraints_to_remove:
            #Capture the exact visual transform (location/rotation/scale) generated by the curve
            baked_matrix = obj.matrix_world.copy()
            #Remove the constraint(s)
            for c in constraints_to_remove:
                obj.constraints.remove(c)
            #Paste the captured transform directly into the object's permanent data
            obj.matrix_world = baked_matrix
            duplicates.append(obj)
            detached_count += 1
    
    blend_utils.select(duplicates)
    curve["has_linked_objects"] = False
            
    return detached_count

def select_parent_curve(object):
    for constraint in object.constraints:
        if constraint.type == 'FOLLOW_PATH':
            parent_curve = constraint.target
            blend_utils.select(parent_curve)
            
def select_children_of_curve(curve):
    children = []
    if not is_bezier_or_nurbs_path(curve):
        return
    
    bpy.context.view_layer.update()
    
    #Iterate through all objects in the scene
    for obj in bpy.context.scene.objects:
        for constraint in obj.constraints:
            # Look for Follow Path constraints targeting our specific curve
            if constraint.type == 'FOLLOW_PATH' and constraint.target == curve:
                children.append(obj)
                
    blend_utils.select(children)
    
    
def edit_radius_multiplier(curve, new_radius_multiplier):
    #Updates the radius multiplier for all objects linked to the specified curve.
    if not is_bezier_or_nurbs_path(curve):
        return

    # Update the multiplier property stored on the curve
    curve["radius_multiplier"] = new_radius_multiplier
    
    # Trigger the update function to recalculate the scale for all linked objects
    update_curve_duplicates(curve)
    
    
