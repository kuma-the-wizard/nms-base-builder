"""Read saved Forge point layouts without registering or changing Forge objects."""

import math
import time

from mathutils import Matrix, Quaternion


def export_cache(obj):
    """Return transient group records for a procedural Forge shape, or None.

    Forge stores the visible placements on its mesh, not in child_cache.
    Reading those attributes also works when Forge is not installed/enabled.
    Never fill the real child_cache: it belongs to Forge's editing workflow.
    """
    if obj.type != 'MESH' or 'GroupID' not in obj:
        return None
    modifiers = [m for m in obj.modifiers if m.type == 'NODES' and m.node_group
                 and m.node_group.name.startswith('Charon Forge')]
    if not modifiers:
        return None

    def invalid(detail):
        raise ValueError(f'{obj.name}: cannot export this Forge shape ({detail}). '
                         'Open it in Forge and use Split to export individual parts.')

    if len(modifiers) != 1:
        invalid('multiple procedural layouts')
    nodes = modifiers[0].node_group.nodes
    part = nodes.get('Part')
    copies = nodes.get('Copies')
    if (part is None or part.bl_idname != 'GeometryNodeObjectInfo' or
            copies is None or copies.bl_idname != 'GeometryNodeInstanceOnPoints'):
        invalid('unrecognized placement nodes')
    source = part.inputs['Object'].default_value
    mesh = getattr(source, 'data', None)
    object_id = mesh.get('nms_id', mesh.get('nms_high_res_id')) if mesh else None
    if not isinstance(object_id, str) or not object_id.strip('^'):
        invalid('missing source part ID')
    object_id = object_id.lstrip('^')

    points = obj.data
    count = len(points.vertices)
    rotations = points.attributes.get('charon_rotation')
    scales = points.attributes.get('charon_scale')
    for attribute, kind in ((rotations, 'QUATERNION'), (scales, 'FLOAT')):
        if (attribute is None or attribute.data_type != kind or
                attribute.domain != 'POINT' or len(attribute.data) != count):
            invalid('missing or incompatible placement attributes')

    stamp = int(time.time())
    cache = {}
    for index, vertex in enumerate(points.vertices):
        rotation = Quaternion(rotations.data[index].value)
        scale = scales.data[index].value
        if not all(math.isfinite(v) for v in (*vertex.co, *rotation, scale)):
            invalid('non-finite placement')
        if scale <= 0 or rotation.magnitude < 1e-8:
            invalid('invalid placement scale or rotation')
        matrix = Matrix.LocRotScale(vertex.co, rotation.normalized(), (scale,) * 3)
        cache[f'{object_id}.{index:04d}'] = {
            'ObjectID': object_id,
            'UserData': obj.get('UserData', 0),
            'Timestamp': stamp,
            'matrix_local': [list(row) for row in matrix],
        }
    return cache
