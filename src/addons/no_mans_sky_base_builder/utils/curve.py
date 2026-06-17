from . import blend_utils
import bpy
from bpy.app.handlers import persistent
import mathutils
import math

from . import curve_utils

def update_curve_duplicates(curve_obj, radius_multiplier = None, attaching = False):
    
    if not curve_obj.get("has_linked_objects"):
        return
    
    spline = curve_obj.data.splines[0]
    segment_lengths, total_length = (curve_utils.get_spline_segment_lengths(spline))
    
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve_obj.name:
            curve_utils.update_obj_transformations(obj, curve_obj, segment_lengths, total_length)


def duplicate_along_curve(builder, object, curve, number_of_duplicates=10, radius_multiplier=1.0):
    curve["has_linked_objects"] = True
    curve["radius_multiplier"] = radius_multiplier
    
    register_curve_handler()
    
    gap_distance = 0.0 if number_of_duplicates <= 1 else 1.0 / (number_of_duplicates - 1)

    existing_objs = []
    
    if object.get("curve_parent") != curve.name:
        object["curve_parent"] = curve.name
        curve["original_object"] = object
        
        #object.hide_select = True
        #object.lock_location = (True, True, True)
        
        has_constraint = any(c.type == 'FOLLOW_PATH' and c.target == curve for c in object.constraints)
        if not has_constraint:
            constraint = object.constraints.new(type='FOLLOW_PATH')
            constraint.target = curve
            constraint.use_fixed_location = True
            constraint.use_curve_follow = True
            
            
            
        object.rotation_euler = ( math.pi/2 ,0,0)

    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve.name:
            existing_objs.append(obj)
    

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
        for _ in range(number_of_duplicates - current_count):
            new_item = builder.add_part(object_id, user_data=user_data)
            new_obj = new_item.object
            
            constraint = new_obj.constraints.new(type='FOLLOW_PATH')
            constraint.target = curve
            constraint.use_fixed_location = True
            constraint.use_curve_follow = True
            
            new_obj["curve_parent"] = curve.name
            new_obj["curve_parent_ref"] = curve
            
            obj.rotation_euler = object.rotation_euler.copy()
            existing_objs.append(new_obj)

    
    spline = curve.data.splines[0]
    segment_lengths, total_length = (curve_utils.get_spline_segment_lengths(spline) )

    for i, obj in enumerate(existing_objs):
        percentage_count = i * gap_distance
        
        constraint = next((c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve), None)
        if constraint:
            constraint.offset_factor = percentage_count
            
        obj["curve_factor"] = percentage_count
        
        curve_utils.update_obj_transformations(obj, curve, segment_lengths, total_length)
        
    curve["objects_count"] = len(existing_objs)
            


def is_bezier_or_nurbs_path(curve):
    if not curve or curve.type != 'CURVE':
        return False
    for spline in curve.data.splines:
        if spline.type in {'BEZIER', 'NURBS'}:
            return True
    return False

        
def apply_curve_transforms_and_detach(curve):
    
    if not is_bezier_or_nurbs_path(curve):
        raise TypeError("Please provide a valid curve object.")
    
    detached_count = 0
    duplicates = []
    
    bpy.context.view_layer.update()
    
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve.name:
            constraints_to_remove = [c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve]
            
            if "curve_parent_ref" in obj:
                del obj["curve_parent_ref"]
                
            del obj["curve_parent"]
                
            if constraints_to_remove:
                baked_matrix = obj.matrix_world.copy()
                for c in constraints_to_remove:
                    obj.constraints.remove(c)
                obj.matrix_world = baked_matrix
                detached_count += 1
                
            obj.hide_select = False
            obj.lock_location = (False, False, False)
            duplicates.append(obj)
    
    blend_utils.select(duplicates)
    curve["has_linked_objects"] = False
    return detached_count

def lock_all_objects(curve_obj):
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve_obj.name:
            obj.hide_select = True
            obj.lock_location = (True, True, True)
            
            
def unlock_all_objects(curve_obj):
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve_obj.name:
            obj.hide_select = False
            obj.lock_location = (False, False, False)


def select_parent_curve(object):
    parent_curve = object.get("curve_parent_ref", None)
    if parent_curve:
        parent_curve.hide_select = False
        for obj in bpy.context.scene.objects:
            if obj.get("curve_parent") == parent_curve.name:
                obj.hide_select = True
        blend_utils.select(parent_curve)
            
def select_children_of_curve(curve):
    if not is_bezier_or_nurbs_path(curve):
        return
    
    children = []
    
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve.name:
            obj.hide_select = False
            children.append(obj)
    
    curve.hide_select = True
    blend_utils.select(children)
    
    
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
        update_curve_duplicates(curve)
        

def register_curve_handler():
    if curve_duplicate_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(curve_duplicate_handler)