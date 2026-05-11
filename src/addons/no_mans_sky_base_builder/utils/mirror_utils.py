import json
import math
from pathlib import Path

from mathutils import Matrix, Euler, Vector

MIRROR_CORRECTIONS_PATH = (
    Path(__file__).resolve().parents[1] / "resources" / "mirror_corrections.json"
)


def load_mirror_corrections():
    with open(MIRROR_CORRECTIONS_PATH, "r", encoding="utf-8") as stream:
        return json.load(stream)


MIRROR_CORRECTIONS = load_mirror_corrections()
LOCAL_Y_180_ROTATION_PARTS = set(MIRROR_CORRECTIONS["local_y_180_rotation_parts"])
MIRROR_Z_180_IDENTIFIERS = set(MIRROR_CORRECTIONS["mirror_z_180_identifiers"])
POSITION_OFFSETS = {
    part: Vector(offset)
    for part, offset in MIRROR_CORRECTIONS["position_offsets"].items()
}


# This function mirrors matrix world across x axis
def mirror_matrix_world(object_id, old_matrix_world, across_x=True):

    # extract location,rotation and scale values from matrix world
    location, rotation_quaternion, scale = old_matrix_world.decompose()

    # mirror location  if across x is selected
    new_location = -location.x if across_x else location.x
    position_values = (new_location, location.y, location.z)
    position_matrix = Matrix.Translation(Vector(position_values))

    # mirror rotation across x axis
    current_euler = rotation_quaternion.to_euler("XYZ")
    rotation_values = (current_euler.x, -current_euler.y, -current_euler.z)
    rotation_euler = Euler(rotation_values, "XYZ")
    rotation_matrix = rotation_euler.to_matrix().to_4x4()

    # creating scale matrix
    scale_matrix = Matrix.Scale(scale.x, 4)

    # multiplying all the matrix
    matrix_world = position_matrix @ rotation_matrix @ scale_matrix

    # correct anomalies in mirroring
    matrix_world = mirror_correction(object_id, matrix_world)

    return matrix_world


# This function provides additional corrections after mirroring object
def mirror_correction(object_id, matrix_world):
    # All triangular floor tiles
    if any(identifier in object_id for identifier in MIRROR_Z_180_IDENTIFIERS):
        angle = math.pi  # 180 degrees
        z_rot_180 = Matrix.Rotation(angle, 4, "Z")
        return matrix_world @ z_rot_180

    # Apply per-part position offset corrections
    if object_id in POSITION_OFFSETS:
        translation_matrix = Matrix.Translation(POSITION_OFFSETS[object_id])
        return matrix_world @ translation_matrix

    # Parts that need rotation by 180 on local Y axis
    if object_id in LOCAL_Y_180_ROTATION_PARTS:
        angle = math.pi  # 180 degrees
        y_rot_180 = Matrix.Rotation(angle, 4, "Y")
        return matrix_world @ y_rot_180

    return matrix_world
