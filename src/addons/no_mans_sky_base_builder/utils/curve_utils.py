from . import blend_utils
import bpy

from mathutils.geometry import interpolate_bezier

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
def get_curve_radius_tilt(curve_obj, factor, segment_lengths, total_length):
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


def update_obj_transformations(
    obj, 
    curve_obj,
    segment_lengths,
    total_length,
):
    radius_multiplier = curve_obj.get("radius_multiplier", 1.0)
    factor = obj.get("curve_factor")
    if factor is None:
        return
    
    radius, tilt = get_curve_radius_tilt(curve_obj, factor, segment_lengths, total_length)
    scale = radius * radius_multiplier 
    
    #print(f" scale is {scale},    radius is {radius} , radius multiplier is {radius_multiplier}")
    
    obj.scale.x = scale
    obj.scale.y = scale
    obj.scale.z = scale
    
    obj.rotation_euler.x = 0.0
    obj.rotation_euler.y = 0.0
    obj.rotation_euler.z = 0.0
    
    obj.location = (0.0, 0.0, 0.0)
    