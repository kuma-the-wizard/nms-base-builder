import bpy
import time
import math

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


def update_obj_transformations(obj, curve_obj, eval_data, total_length):
    """
    Optimized transformation update with early returns and inline calculations.
    """
    factor = obj.get("curve_factor")
    update_object_factor(obj , curve_obj, factor)
    
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
    
def update_object_factor(obj , curve_obj, factor):
    constraint = next(( c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve_obj), None)
    if constraint:
        constraint.offset_factor = factor
    obj["curve_factor"] = factor

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
                    
def get_control_points(curve_obj):
    if not curve_obj or not curve_obj.type == 'CURVE':
        return None

    curve_data = curve_obj.data
    # A curve can contain multiple splines
    spline = curve_data.splines[0]
    
    # 1. Bezier Curves store points in 'bezier_points'
    if spline.type == 'BEZIER':
        return spline.bezier_points
    # 2. Poly or NURBS Curves store points in 'points'
    elif spline.type in {'POLY', 'NURBS'}:
        return spline.points
            
    return None


def get_nearest_control_point_factor(control_points, target_factor):
    """
    Returns the curve factor (0.0 to 1.0) and the index of the nearest 
    control point relative to a target factor.
    
    :param control_points: List of Vector, tuple/list coords, or Blender point objects
    :param target_factor: Float between 0.0 and 1.0
    :return: Tuple (nearest_factor: float, nearest_index: int)
    """
    if not control_points:
        return 0.0, 0
    if len(control_points) == 1:
        return 0.0, 0

    # Extract 3D coordinates (handles Vector, tuple, or Blender point objects)
    def extract_co(p):
        if hasattr(p, 'co'):
            return Vector(p.co.xyz)
        return Vector(p[:3])

    coords = [extract_co(p) for p in control_points]

    # 1. Calculate cumulative segment lengths between consecutive control points
    cum_lengths = [0.0]
    total_length = 0.0
    
    for i in range(1, len(coords)):
        dist = (coords[i] - coords[i - 1]).length
        total_length += dist
        cum_lengths.append(total_length)

    # If all points overlap at the exact same location
    if total_length == 0.0:
        return 0.0, 0

    # 2. Convert cumulative lengths to normalized factors (0.0 to 1.0)
    cp_factors = [l / total_length for l in cum_lengths]

    # 3. Clamp target_factor between 0.0 and 1.0
    target_factor = max(0.0, min(1.0, target_factor))

    # 4. Find index of the control point closest to target_factor
    nearest_index = min(range(len(cp_factors)), key=lambda i: abs(cp_factors[i] - target_factor))
    
    return cp_factors[nearest_index], nearest_index


def get_segment_midpoint_factor(control_points, target_factor):
    """
    Finds which control point segment the target_factor falls into and 
    returns the factor representing the exact midpoint of that segment.
    
    :param control_points: List of Vector, tuple/list coords, or Blender point objects
    :param target_factor: Float between 0.0 and 1.0
    :return: Float factor between 0.0 and 1.0 (midpoint of the segment)
    """
    if not control_points or len(control_points) < 2:
        return 0.0

    # Helper to extract 3D Vector position
    def extract_co(p):
        if hasattr(p, 'co'):
            return Vector(p.co.xyz)
        return Vector(p[:3])

    coords = [extract_co(p) for p in control_points]

    # Calculate cumulative length at each control point
    cum_lengths = [0.0]
    total_length = 0.0
    
    for i in range(1, len(coords)):
        dist = (coords[i] - coords[i - 1]).length
        total_length += dist
        cum_lengths.append(total_length)

    if total_length == 0.0:
        return 0.0

    # Clamp target_factor between 0.0 and 1.0
    target_factor = max(0.0, min(1.0, target_factor))
    target_length = target_factor * total_length

    # Identify the segment [i-1, i] containing target_length
    for i in range(1, len(cum_lengths)):
        start_len = cum_lengths[i - 1]
        end_len = cum_lengths[i]

        # Check if target falls in this segment
        if start_len <= target_length <= end_len:
            # Midpoint length of this segment
            mid_length = (start_len + end_len) / 2.0
            # Return midpoint as a 0.0 - 1.0 factor of total curve length
            return mid_length / total_length

    # Fallback for edge cases
    last_seg_mid = (cum_lengths[-2] + cum_lengths[-1]) / 2.0
    return last_seg_mid / total_length


def smoothstep(t):
    return t * t * (3.0 - 2.0 * t)

def get_density(density_map,factor):
    if len(density_map) == 1:
        return density_map[0]
    position = factor * (len(density_map) - 1)
    index = min(int(position), len(density_map) - 2)
    t = position - index
    # Smooth transition between control points
    t = smoothstep(t)
    a = density_map[index]
    b = density_map[index + 1]

    return a + (b - a) * t

def factor_from_density(cumulative_density, sample_factors , target):
    low = 0
    high = len(cumulative_density) - 1

    while low < high:
        mid = (low + high) // 2
        if cumulative_density[mid] < target:
            low = mid + 1
        else:
            high = mid

    index = max(1, low)
    d0 = cumulative_density[index - 1]
    d1 = cumulative_density[index]
    f0 = sample_factors[index - 1]
    f1 = sample_factors[index]

    if d1 == d0:
        return f0
    
    t = (target - d0) / (d1 - d0)
    return f0 + (f1 - f0) * t

def calculate_curve_factors(curve, existing_objs):
    
    density_map = get_density_map(curve)
    
    # Sample the density curve
    sample_count = max(128, len(existing_objs) * 16)
    sample_factors = []
    sample_density = []

    for i in range(sample_count):
        factor = i / (sample_count - 1)
        sample_factors.append(factor)
        sample_density.append(get_density(density_map,factor))
    # Integrate density along the curve
    cumulative_density = [0.0]
    for i in range(1, sample_count):
        dx = sample_factors[i] - sample_factors[i - 1]
        density = ( sample_density[i - 1] + sample_density[i]) * 0.5
        cumulative_density.append( cumulative_density[-1] + density * dx)

    total_density = cumulative_density[-1]

    # Calculate object positions
    object_count = len(existing_objs)
    if object_count == 1:
        existing_objs[0]["curve_factor"] = 0.0
    else:
        for index, obj in enumerate(existing_objs):
            position = index / (object_count - 1)
            target_density = position * total_density
            factor = factor_from_density(cumulative_density,sample_factors,target_density)
            obj["curve_factor"] = factor


def get_total_curve_density(curve, object_count=10):
    density_map = get_density_map(curve)
    sample_count = max(128, object_count * 16)
    sample_factors = [i / (sample_count - 1) for i in range(sample_count)]
    
    cumulative_density = 0.0
    for i in range(1, sample_count):
        dx = sample_factors[i] - sample_factors[i - 1]
        density_a = get_density(density_map, sample_factors[i - 1])
        density_b = get_density(density_map, sample_factors[i])
        density = (density_a + density_b) * 0.5
        cumulative_density += density * dx
        
    return cumulative_density            
            
            
def exponential_scale(x: float, steepness: float = 5.0) -> float:
    return math.exp(steepness * (x - 0.5))
            
def get_density_map(curve):
    control_points = get_control_points(curve)
    density_map = []
    for point in control_points:
        weight = exponential_scale(point.weight_softbody)
        density_map.append(weight)
    return density_map

def half_the_weight_points(curve):
    control_points = get_control_points(curve)
    for point in control_points:
        point.weight_softbody = 0.5
        

def evaluate_curve_density(curve_obj, t):
    """
    Evaluates density at curve factor t (0.0 to 1.0).
    Extract this from your existing smoothstep / weight math in get_total_curve_density().
    """
    # Retrieve curve density bounds / parameters from object
    edge0 = curve_obj.get("density_start", 0.0)
    edge1 = curve_obj.get("density_end", 1.0)
    
    if edge1 == edge0:
        return 1.0
        
    # Clamp factor to bounds
    x = max(0.0, min(1.0, (t - edge0) / (edge1 - edge0)))
    
    # Smoothstep interpolation weight
    return x * x * (3 - 2 * x)
        

def build_density_cdf(curve_obj, samples=64):
    """Pre-computes cumulative density array (CDF) in a single pass."""
    cdf = [0.0]
    total_density = 0.0
    dt = 1.0 / samples
    
    for i in range(samples):
        t = i * dt
        density = evaluate_curve_density(curve_obj, t)
        total_density += density * dt
        cdf.append(total_density)
        
    return total_density, cdf

def get_factor_from_cdf(cdf, target_val):
    """Fast binary search lookup on pre-computed CDF array."""
    if not cdf or cdf[-1] == 0:
        return 0.0
    
    normalized_target = target_val * cdf[-1]
    low, high = 0, len(cdf) - 1
    
    while low < high:
        mid = (low + high) // 2
        if cdf[mid] < normalized_target:
            low = mid + 1
        else:
            high = mid
            
    return low / (len(cdf) - 1)