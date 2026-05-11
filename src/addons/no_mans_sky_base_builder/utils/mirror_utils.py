import math
import mathutils
from mathutils import Matrix, Euler, Vector

#parts that need 180 degress rotation across local Y axis
y_180_local_correction_parts = {"S_SAIL0","BASE_CAVE3"}


#This function mirrors matrix world across x axis
def mirror_matrix_world(object_id,old_matrix_world, across_x = True):
    
    #extract location,rotation and scale values from matrix world
    location, rotation_quaternion, scale = old_matrix_world.decompose()
    
    #mirror location  if across x is selected
    new_location = -location.x if across_x else location.x 
    position_values = (new_location, location.y, location.z)
    position_matrix = Matrix.Translation(Vector(position_values))
    
    #mirror rotation across x axis
    current_euler = rotation_quaternion.to_euler('XYZ')
    rotation_values = (current_euler.x, -current_euler.y, -current_euler.z)
    rotation_euler = Euler(rotation_values, 'XYZ')
    rotation_matrix = rotation_euler.to_matrix().to_4x4()
    
    #creating scale matrix
    scale_matrix = Matrix.Scale(scale.x, 4)
    
    #multiplying all the matrix
    matrix_world = position_matrix @ rotation_matrix @ scale_matrix
    
    #correct anomalies in mirroring
    matrix_world = mirror_correction(object_id,matrix_world)
    
    return matrix_world

# This function provides additional corrctions after mirroring object
def mirror_correction(object_id,matrix_world):
    
    # All triangular floor tiles
    if "TRIFLOOR" in object_id:
        angle = math.pi # 180 degrees
        z_rot_180 = Matrix.Rotation(angle, 4, 'Z')
        return matrix_world @ z_rot_180
    
    # Storage panel is off centered by 0.05444555 units of measurement
    elif object_id == "STORAGEPANEL":
        storage_panel_offset = 0.05444555
        local_offset = mathutils.Vector((storage_panel_offset, 0.0, 0.0))
        translation_matrix = mathutils.Matrix.Translation(local_offset)
        return matrix_world @ translation_matrix
    
    # Parts that need rotation by 180 on y axis locally go here
    elif object_id in y_180_local_correction_parts:
        angle = math.pi # 180 degrees
        y_rot_180 = Matrix.Rotation(angle, 4, 'Y')
        return matrix_world @ y_rot_180
        
    return matrix_world