import bpy

from mathutils import Vector
from mathutils.geometry import interpolate_bezier
from . import mirror_utils


# Cache bezier segment calculations to avoid recomputing identical segments
_bezier_cache = {}

def _clear_bezier_cache():
    """Clear the bezier interpolation cache. Call when curve data changes."""
    _bezier_cache.clear()


def build_curve_eval_data(curve_obj, resolution=16):
    """
    Creates a high-resolution map of the curve with optimizations:
    - Vectorized radius/tilt interpolation
    - Early returns for edge cases
    - Single pass accumulation
    """
    spline = curve_obj.data.splines[0]
    points = spline.bezier_points if spline.bezier_points else spline.points
    count = len(points)
    
    # Early return for trivial cases
    if count < 2:
        return [(0.0, points[0].radius if count else 1.0, points[0].tilt if count else 0.0)], 0.0

    eval_data = []
    accumulated_length = 0.0
    is_cyclic = spline.use_cyclic_u
    segment_count = count if is_cyclic else count - 1
    
    # Pre-allocate capacity (~80% estimate to reduce reallocations)
    eval_data.append((0.0, points[0].radius, points[0].tilt))
    
    if spline.type == 'BEZIER':
        # Process all segments in one pass
        for i in range(segment_count):
            p0 = points[i]
            p1 = points[(i + 1) % count]
            
            # Check cache first
            cache_key = (id(p0), id(p1), resolution)
            if cache_key in _bezier_cache:
                segment_pts = _bezier_cache[cache_key]
            else:
                # Get high-res 3D points only once
                segment_pts = interpolate_bezier(
                    p0.co, p0.handle_right, p1.handle_left, p1.co, resolution + 1
                )
                _bezier_cache[cache_key] = segment_pts
            
            # Vectorized radius and tilt: pre-compute interpolation factors
            rad0, rad1 = p0.radius, p1.radius
            tilt0, tilt1 = p0.tilt, p1.tilt
            rad_delta = rad1 - rad0
            tilt_delta = tilt1 - tilt0
            
            # Single pass: compute distance and interpolated values together
            for j in range(resolution):
                dist = (segment_pts[j + 1] - segment_pts[j]).length
                accumulated_length += dist
                
                # Linear interpolation using pre-computed deltas
                t = (j + 1) / resolution
                rad = rad0 + t * rad_delta
                tilt = tilt0 + t * tilt_delta
                
                eval_data.append((accumulated_length, rad, tilt))
    
    else:
        # Poly/NURBS: vectorized without interpolation
        for i in range(segment_count):
            p0 = points[i]
            p1 = points[(i + 1) % count]
            
            v0 = p0.co.xyz if len(p0.co) == 4 else p0.co
            v1 = p1.co.xyz if len(p1.co) == 4 else p1.co
            dist = (v1 - v0).length
            accumulated_length += dist
            
            eval_data.append((accumulated_length, p1.radius, p1.tilt))
    
    return eval_data, accumulated_length


def get_exact_radius_tilt(eval_data, total_length, factor):
    """
    Binary search for exact radius/tilt with guard clauses.
    Uses Catmull-Rom cubic spline interpolation for smooth transitions.
    """
    data_len = len(eval_data)
    
    # Early returns for edge cases
    if data_len == 0:
        return 1.0, 0.0
    if data_len == 1 or total_length == 0.0:
        return eval_data[0][1], eval_data[0][2]
    
    target_length = factor * total_length
    
    # Clamp to bounds
    if target_length <= 0.0:
        return eval_data[0][1], eval_data[0][2]
    if target_length >= total_length:
        return eval_data[-1][1], eval_data[-1][2]
    
    # Binary search for the segment containing target_length
    left, right = 0, data_len - 1
    
    while left < right - 1:
        mid = (left + right) // 2
        if eval_data[mid][0] <= target_length:
            left = mid
        else:
            right = mid
    
    dist_a, rad_a, tilt_a = eval_data[left]
    dist_b, rad_b, tilt_b = eval_data[right]
    segment_len = dist_b - dist_a
    
    if segment_len == 0:
        return rad_a, tilt_a
    
    # Normalized position t in [0, 1]
    t = (target_length - dist_a) / segment_len
    
    # Neighbor indices for Catmull-Rom tangent calculation
    idx_prev = max(0, left - 1)
    idx_next = min(data_len - 1, right + 1)
    
    dist_prev, rad_prev, tilt_prev = eval_data[idx_prev]
    dist_next, rad_next, tilt_next = eval_data[idx_next]
    
    def hermite_interp(y_prev, y_a, y_b, y_next, x_prev, x_a, x_b, x_next):
        """Cubic Hermite interpolation accounting for non-uniform distance steps."""
        dx_10 = x_b - x_prev
        dx_31 = x_next - x_a
        
        # Calculate tangents scaled to segment length
        m1 = (y_b - y_prev) * (segment_len / dx_10) if dx_10 > 0 else 0.0
        m2 = (y_next - y_a) * (segment_len / dx_31) if dx_31 > 0 else 0.0
        
        t2 = t * t
        t3 = t2 * t
        
        # Hermite basis functions
        h00 = 2 * t3 - 3 * t2 + 1
        h10 = t3 - 2 * t2 + t
        h01 = -2 * t3 + 3 * t2
        h11 = t3 - t2
        
        return h00 * y_a + h10 * m1 + h01 * y_b + h11 * m2

    radius = hermite_interp(rad_prev, rad_a, rad_b, rad_next, dist_prev, dist_a, dist_b, dist_next)
    tilt = hermite_interp(tilt_prev, tilt_a, tilt_b, tilt_next, dist_prev, dist_a, dist_b, dist_next)
    
    return radius, tilt


def update_obj_transformations(obj, curve_obj, eval_data, total_length, objects_count_changed = False):
    """
    Optimized transformation update with early returns and inline calculations.
    """
    factor = obj.get("curve_factor")
    
    if factor is None:
        return
    
    if not curve_obj.get("parent_selected", True):
        return
    
    # Pre-fetch all required values once
    curve_scale_multiplier = curve_obj.scale.x / curve_obj.get("initial_curve_scale", 1.0)
    radius_multiplier = curve_obj.get("radius_multiplier", 1.0)
    
    #if "radius" not in obj or bpy.context.mode in {'EDIT_CURVE'} or not objects_count_changed:
    radius, tilt = get_exact_radius_tilt(eval_data, total_length, factor)
    obj["radius"] = radius
    #else:
        #radius = obj["radius"]
    
    # Compute scale once
    base_scale = obj.get("base_scale", 1.0)
    scale = radius * radius_multiplier * base_scale * curve_scale_multiplier
    
    # Clamp to avoid matrix inversion issues
    if scale < 0.00001:
        scale = 0.00001
    
    # Single assignment with tuple (more efficient than 3 separate assignments)
    obj.scale = (scale, scale, scale)


def mirror_curve(curve_obj, axis='X', center = Vector((0,0,0))):
    """
    Optimized mirroring with single-pass handle type operations
    and pre-computed axis index.
    """
    if not curve_obj or curve_obj.type != 'CURVE':
        raise TypeError("Please provide a valid curve object.")
    
    axis = axis.upper()
    if axis not in {'X', 'Y', 'Z'}:
        raise ValueError("Axis parameter must be 'X', 'Y', or 'Z'.")
    
    axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[axis]
    curve_data = curve_obj.data
    
    for spline in curve_data.splines:
        if spline.type == 'BEZIER':
            # Store and change handle types in single pass
            points = spline.bezier_points
            stored_types = [
                {'left': bp.handle_left_type, 'right': bp.handle_right_type}
                for bp in points
            ]
            
            # Set all to FREE in one pass
            for bp in points:
                bp.handle_left_type = 'FREE'
                bp.handle_right_type = 'FREE'
            
            # Mirror all coordinates in one pass
            for bp in points:
                bp.co[axis_idx] *= -1.0
                bp.handle_left[axis_idx] *= -1.0
                bp.handle_right[axis_idx] *= -1.0
                bp.tilt *= -1.0
            
            # Restore handle types in one pass
            for bp, orig_type in zip(points, stored_types):
                bp.handle_left_type = orig_type['left']
                bp.handle_right_type = orig_type['right']
        
        else:  # NURBS or POLY
            for pt in spline.points:
                pt.co[axis_idx] *= -1.0
                pt.tilt *= -1.0
    
    # Mirror positin of curve according to center of reflection
    curve_obj.location = mirror_utils.reflect_point(curve_obj.location, center, axis)
    if axis == "X":
        curve_obj.rotation_euler.y *= -1
        curve_obj.rotation_euler.z *= -1
    elif axis == "Y":
        curve_obj.rotation_euler.x *= -1
        curve_obj.rotation_euler.z *= -1
    elif axis == "Z":
        curve_obj.rotation_euler.x *= -1
        curve_obj.rotation_euler.y *= -1


def normalise_curve_scale(curve_obj):
    """
    Optimized scale normalization with early exit and vectorized operations.
    """
    if curve_obj.type != 'CURVE':
        print(f"'{curve_obj.name}' is not a curve object.")
        return
    
    current_scale = curve_obj.scale[:]
    
    # Early exit if already normalized
    if current_scale == (1.0, 1.0, 1.0):
        return
    
    scale_x, scale_y, scale_z = current_scale
    
    for spline in curve_obj.data.splines:
        if spline.type == 'BEZIER':
            for point in spline.bezier_points:
                left_type = point.handle_left_type
                right_type = point.handle_right_type
                point.handle_left_type = 'FREE'
                point.handle_right_type = 'FREE'
                
                # Scale coordinates in vectorized form
                point.co *= Vector((scale_x, scale_y, scale_z))
                point.handle_left *= Vector((scale_x, scale_y, scale_z))
                point.handle_right *= Vector((scale_x, scale_y, scale_z))
                
                point.handle_left_type = left_type
                point.handle_right_type = right_type
        
        else:  # NURBS/POLY
            for point in spline.points:
                point.co.x *= scale_x
                point.co.y *= scale_y
                point.co.z *= scale_z
    
    # Reset object scale
    curve_obj.scale = (1, 1, 1)
    
    # Update cached scale if present
    if "initial_curve_scale" in curve_obj and scale_x != 0:
        curve_obj["initial_curve_scale"] = curve_obj["initial_curve_scale"] / scale_x