"""Project standalone NMS decal volumes onto build surfaces.

Only display meshes change. Object IDs, matrices and saved game records remain
on the original objects. Source meshes are retained for quality changes/undo.
"""
import bpy
import numpy as np
from mathutils import Vector
from bpy.app.handlers import persistent

SOURCE = 'bbe_decal_source'
PROJECTED = 'bbe_projected_decal'
_signature = None
_busy = False
_project_signatures = {}
_geometry_revision = 0
_solid_views = {}
SOLID_NODE = 'BBE Solid Reference'
SOLID_PREVIOUS = 'bbe_solid_previous_active'


def is_decal(obj):
    pid = obj.get('ObjectID', '').lstrip('^')
    return obj.type == 'MESH' and pid.startswith(('BUILDDECAL', 'DECAL_', 'EXPD_DECAL', 'SPEC_DECAL'))


def source_mesh(obj):
    if not obj.data.get(PROJECTED) and obj.get(SOURCE) != obj.data:
        obj[SOURCE] = obj.data
    return obj.get(SOURCE, obj.data)


def bounds(points):
    return points.min(axis=0), points.max(axis=0)


def clip(poly, axis, value, sign):
    result = []
    previous = poly[-1]
    pd = sign*(previous[axis]-value)
    for current in poly:
        cd = sign*(current[axis]-value)
        if (cd >= 0) != (pd >= 0):
            result.append(previous+(current-previous)*(pd/(pd-cd)))
        if cd >= 0:
            result.append(current)
        previous, pd = current, cd
    return result


def projector(mesh):
    points = np.array([v.co[:] for v in mesh.vertices], dtype=float)
    if not len(points) or not mesh.uv_layers:
        return None
    lo, hi = bounds(points)
    # The extracted mesh is a thin placement cage, not the renderer's reach.
    # Project into the receiving hull over one artwork radius, allowing decals
    # placed above stepped plates to reach those plates without floating cards.
    lo[1] = min(lo[1], -max(hi[0]-lo[0], hi[2]-lo[2])*.5)
    # Saves can place the projector slightly inside a plate. Reach outward
    # too, while retaining a bounded volume and the front-facing test below.
    hi[1] = max(hi[1], max(hi[0]-lo[0], hi[2]-lo[2])*.25)
    # Native standalone decals project along Y with artwork in X/Z. Derive
    # UV mapping from the authored +Y face, including atlas scale/orientation.
    face = max(mesh.polygons, key=lambda p: p.normal.y)
    if face.normal.y < .5:
        return None
    uv = mesh.uv_layers.active.data
    coords = np.array([[points[mesh.loops[i].vertex_index][0], points[mesh.loops[i].vertex_index][2], 1] for i in face.loop_indices])
    tex = np.array([uv[i].uv[:] for i in face.loop_indices])
    mapping = np.linalg.lstsq(coords, tex, rcond=None)[0]
    return lo, hi, mapping, face.material_index


def surface_components(positions, indices):
    """Weld UV splits to identify separate receiver surfaces (seat vs frame)."""
    parents = list(range(len(indices)))
    owners = {}
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    for i, triangle in enumerate(indices):
        for vertex in triangle:
            key = tuple(np.round(positions[vertex], 5))
            if key in owners:
                parents[root(i)] = root(owners[key])
            else:
                owners[key] = i
    return np.array([root(i) for i in range(len(indices))])


def project(obj, receivers, cache):
    source = source_mesh(obj)
    definition = projector(source)
    if definition is None:
        return False
    lo, hi, mapping, slot = definition
    inverse = obj.matrix_world.inverted_safe()
    verts, faces, uvs = [], [], []
    # Sub-millimetre separation loses depth precision in a ship-sized Solid
    # viewport. This small world-space lift also avoids curved-hull burial.
    offset = max(.003, min(.012, max(abs(v) for v in obj.matrix_world.to_scale())*.003))
    surfaces = []
    contacts = []
    for receiver in receivers:
        transform = inverse @ receiver.matrix_world
        corners = np.array([(transform @ Vector(c))[:] for c in receiver.bound_box])
        rlo, rhi = bounds(corners)
        if np.any(rhi < lo) or np.any(rlo > hi):
            continue
        key = receiver.data.as_pointer()
        if key not in cache:
            mesh = receiver.data
            mesh.calc_loop_triangles()
            positions = np.empty(len(mesh.vertices)*3)
            mesh.vertices.foreach_get('co', positions)
            indices = np.empty(len(mesh.loop_triangles)*3, dtype=np.int32)
            mesh.loop_triangles.foreach_get('vertices', indices)
            cache[key] = positions.reshape(-1,3), indices.reshape(-1,3)
        positions, indices = cache[key]
        mat = np.array(transform)
        points = positions @ mat[:3,:3].T + mat[:3,3]
        triangles = points[indices]
        normals = np.cross(triangles[:,1]-triangles[:,0], triangles[:,2]-triangles[:,0])
        lengths = np.linalg.norm(normals,axis=1)
        keep = ((normals[:,1] > lengths*.05) &
                np.all(triangles.max(axis=1) >= lo,axis=1) &
                np.all(triangles.min(axis=1) <= hi,axis=1))
        triangles, normals = triangles[keep], normals[keep]
        triangle_ids = np.flatnonzero(keep)
        surfaces.append((receiver, triangles, normals, triangle_ids))
        # Locate the surface touching the placement centre, including decals
        # sunk slightly into their receiver. A broad search finds that surface;
        # it must not become the final projection depth through nearby objects.
        for x, z in ((0, 0), (.08, 0), (-.08, 0), (0, .08), (0, -.08)):
            a = triangles[:, 0]
            b, c = triangles[:, 1]-a, triangles[:, 2]-a
            denominator = b[:, 0]*c[:, 2]-b[:, 2]*c[:, 0]
            valid = abs(denominator) > 1e-12
            denominator = np.where(valid, denominator, 1)
            u = ((x-a[:, 0])*c[:, 2]-(z-a[:, 2])*c[:, 0])/denominator
            v = (b[:, 0]*(z-a[:, 2])-b[:, 2]*(x-a[:, 0]))/denominator
            y = a[:, 1]+u*b[:, 1]+v*c[:, 1]
            hit = valid & (u >= 0) & (v >= 0) & (u+v <= 1) & (y >= lo[1]) & (y <= hi[1])
            contacts.extend((float(y[i]), receiver, int(triangle_ids[i])) for i in np.flatnonzero(hit))
    anchor = None
    component = None
    if contacts:
        contact, anchor, triangle_id = min(contacts, key=lambda hit: abs(hit[0]))
        # Corvette hull panels form a continuous assembled receiver. Separate
        # props instead receive the decal on the touched surface only: a seat
        # cushion must not paint its frame, the floor, or neighbouring props.
        structural = anchor.get('ObjectID', '').lstrip('^').startswith('B_')
        if structural:
            anchor = None
        elif anchor.get('ObjectID', '').lstrip('^').startswith('BUILDCHAIR'):
            key = (anchor.data.as_pointer(), 'components')
            if key not in cache:
                cache[key] = surface_components(*cache[anchor.data.as_pointer()])
            component = cache[key] == cache[key][triangle_id]
        # The authored cage thickness supplies a scale-relative depth. Keep
        # adjoining hull plates in this layer, but exclude floors/hammocks
        # behind cushions. Offsetting the layer retains buried placements.
        depth = max(v.co.y for v in source.vertices)-min(v.co.y for v in source.vertices)
        depth = max(depth, (hi[0]-lo[0])*.08)
        lo[1], hi[1] = max(lo[1], contact-depth), min(hi[1], contact+depth)
    receiver_names = []
    for receiver, triangles, normals, triangle_ids in surfaces:
        if anchor is not None:
            if receiver != anchor:
                continue
            if component is not None:
                triangles, normals = triangles[component[triangle_ids]], normals[component[triangle_ids]]
        before = len(faces)
        for tri, normal in zip(triangles, normals):
            poly = list(tri)
            if not (np.all(tri >= lo) and np.all(tri <= hi)):
                for axis in range(3):
                    poly = clip(poly,axis,lo[axis],1) if poly else []
                    poly = clip(poly,axis,hi[axis],-1) if poly else []
            if len(poly) < 3:
                continue
            world_normal = obj.matrix_world.to_3x3().inverted_safe().transposed() @ Vector(normal)
            world_normal.normalize()
            shift = inverse.to_3x3() @ (world_normal*offset)
            start = len(verts)
            verts.extend(Vector(p)+shift for p in poly)
            uvs.extend(np.array([p[0],p[2],1]) @ mapping for p in poly)
            faces.extend((start,start+i,start+i+1) for i in range(1,len(poly)-1))
        if len(faces) > before:
            receiver_names.append(receiver.name)
    mesh = bpy.data.meshes.new('BBE Projected / '+obj.name)
    mesh.from_pydata(verts, [], faces)
    for key in source.keys():
        mesh[key] = source[key]
    mesh[PROJECTED] = True
    mesh['bbe_decal_receivers'] = receiver_names
    for mat in source.materials:
        mesh.materials.append(mat)
    layer = mesh.uv_layers.new(name=source.uv_layers.active.name)
    if faces:
        mesh.polygons.foreach_set('material_index', [slot]*len(faces))
        layer.data.foreach_set('uv', np.array(uvs)[np.array(faces).ravel()].ravel())
    old = obj.data
    obj.data = mesh
    if old.get(PROJECTED) and old.users == 0:
        bpy.data.meshes.remove(old)
    return True


def signature(scene):
    return tuple((o.as_pointer(), o.data.as_pointer(), tuple(v for row in o.matrix_world for v in row),
                  o.hide_viewport, o.hide_render, len(o.data.vertices), len(o.data.polygons))
                 for o in scene.objects if o.type == 'MESH' and o.get('ObjectID'))


def refresh(scene=None, force=False):
    global _signature, _busy
    scene = scene or bpy.context.scene
    if _busy or bpy.context.mode != 'OBJECT':
        return 0
    current = signature(scene)
    if not force and current == _signature:
        return 0
    _busy = True
    count = 0
    try:
        decals = [o for o in scene.objects if is_decal(o)]
        receivers = [o for o in scene.objects if o.type == 'MESH' and o.get('ObjectID')
                     and not is_decal(o) and not o.hide_render and not o.hide_viewport]
        cache = {}
        for obj in decals:
            # Low-detail proxies remain editable simple objects.
            if not getattr(scene, 'bbe_detailed_proxies', True):
                if obj.data.get(PROJECTED):
                    obj.data = source_mesh(obj)
                _project_signatures.pop(obj.as_pointer(), None)
                continue
            source = source_mesh(obj)
            definition = projector(source)
            if definition is None:
                continue
            lo, hi, _, _ = definition
            inverse = obj.matrix_world.inverted_safe()
            nearby = []
            for receiver in receivers:
                transform = inverse @ receiver.matrix_world
                corners = np.array([(transform @ Vector(c))[:] for c in receiver.bound_box])
                rlo, rhi = bounds(corners)
                if not (np.any(rhi < lo) or np.any(rlo > hi)):
                    nearby.append(receiver)
            stamp = (source.as_pointer(), _geometry_revision,
                     tuple(v for row in obj.matrix_world for v in row),
                     tuple((r.as_pointer(), r.data.as_pointer(), tuple(v for row in r.matrix_world for v in row)) for r in nearby))
            if force or not obj.data.get(PROJECTED) or stamp != _project_signatures.get(obj.as_pointer()):
                count += int(project(obj, nearby, cache))
                _project_signatures[obj.as_pointer()] = stamp
        _signature = signature(scene)
    finally:
        _busy = False
    return count


def tick():
    try:
        if not bpy.app.is_job_running('RENDER'):
            refresh()
            solid_references()
    except Exception as exc:
        print('BBE decal projection:', exc)
    return 1.0


def solid_references(force_disable=False):
    """Use Workbench's alpha-tested textures only for decal reference artwork.

    Disconnected one-pixel textures keep BBE hulls in their ordinary solid
    colours. They never enter the material shader or enable scene lighting.
    """
    wanted = {}
    active_views = set()
    for window in bpy.context.window_manager.windows:
        scene = window.scene
        enabled = (not force_disable and getattr(scene, 'bbe_solid_decals', True) and
                   getattr(scene, 'bbe_detailed_proxies', True) and
                   any(is_decal(o) and o.data.get(PROJECTED) for o in scene.objects))
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            space = area.spaces.active
            key = space.as_pointer()
            if enabled:
                active_views.add(key)
                if key not in _solid_views:
                    _solid_views[key] = (space, space.shading.color_type)
                    space.shading.color_type = 'TEXTURE'
                    area.tag_redraw()
            elif key in _solid_views:
                saved, previous = _solid_views.pop(key)
                if space.shading.color_type == 'TEXTURE':
                    space.shading.color_type = previous
                    area.tag_redraw()
        if enabled:
            for obj in scene.objects:
                if obj.type == 'MESH' and obj.get('ObjectID'):
                    for mat in obj.data.materials:
                        if mat and mat.use_nodes:
                            wanted[mat] = wanted.get(mat, False) or is_decal(obj)
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        nodes = mat.node_tree.nodes
        if mat not in wanted:
            if SOLID_PREVIOUS in mat:
                nodes.active = nodes.get(mat[SOLID_PREVIOUS])
                del mat[SOLID_PREVIOUS]
                if nodes.get(SOLID_NODE):
                    nodes.remove(nodes[SOLID_NODE])
            continue
        if SOLID_PREVIOUS not in mat:
            mat[SOLID_PREVIOUS] = nodes.active.name if nodes.active else ''
        if wanted[mat]:
            tex = nodes.get('Diffuse')
            if not tex or tex.type != 'TEX_IMAGE' or not tex.image:
                tex = next((n for n in nodes if n.type == 'TEX_IMAGE' and n.image), None)
        else:
            tex = nodes.get(SOLID_NODE)
            if tex is None:
                tex = nodes.new('ShaderNodeTexImage')
                tex.name = SOLID_NODE
                tex.label = 'Solid viewport only (not connected)'
                color = tuple(round(v, 4) for v in mat.diffuse_color[:3]) + (1.0,)
                name = 'BBE Solid ' + str(color)
                im = bpy.data.images.get(name)
                if im is None:
                    im = bpy.data.images.new(name, width=1, height=1)
                    im.pixels[:] = color
                    im.pack()
                tex.image = im
                tex.hide = True
                tex.location = (-1000, -1000)
        if tex is not None and nodes.active != tex:
            nodes.active = tex
    for key in set(_solid_views)-active_views:
        space, previous = _solid_views.pop(key)
        try:
            if space.shading.color_type == 'TEXTURE':
                space.shading.color_type = previous
        except ReferenceError:
            pass


@persistent
def loaded(_):
    global _signature
    _signature = None
    _project_signatures.clear()
    _solid_views.clear()


@persistent
def before_render(scene, *_):
    refresh(scene)


@persistent
def changed(scene, depsgraph):
    global _signature, _geometry_revision
    if _busy:
        return
    changed_meshes = {update.id.original.as_pointer() for update in depsgraph.updates
                      if isinstance(update.id, bpy.types.Mesh) and update.is_updated_geometry}
    if not changed_meshes:
        return
    # Lighting helpers and preview pads are not decal receivers. Rebuilding
    # them must not invalidate every projected decal in the ship.
    receivers = {o.data.as_pointer() for o in scene.objects
                 if o.type == 'MESH' and o.get('ObjectID') and not o.data.get(PROJECTED)}
    receivers.update(o[SOURCE].as_pointer() for o in scene.objects
                     if o.type == 'MESH' and o.get(SOURCE))
    if changed_meshes & receivers:
        _signature = None
        _geometry_revision += 1


def register():
    bpy.types.Scene.bbe_solid_decals = bpy.props.BoolProperty(
        name='Decals in Solid', default=True,
        description='Show decal artwork over plain hull colours in Solid view, without rendered lighting')
    if not bpy.app.timers.is_registered(tick):
        bpy.app.timers.register(tick, first_interval=1, persistent=True)
    for handlers, callback in ((bpy.app.handlers.load_post, loaded), (bpy.app.handlers.render_pre, before_render),
                               (bpy.app.handlers.depsgraph_update_post, changed)):
        if callback not in handlers:
            handlers.append(callback)


def unregister():
    if bpy.app.timers.is_registered(tick):
        bpy.app.timers.unregister(tick)
    for handlers, callback in ((bpy.app.handlers.load_post, loaded), (bpy.app.handlers.render_pre, before_render),
                               (bpy.app.handlers.depsgraph_update_post, changed)):
        if callback in handlers:
            handlers.remove(callback)
    for obj in bpy.data.objects:
        if is_decal(obj) and obj.data.get(PROJECTED) and obj.get(SOURCE):
            obj.data = obj[SOURCE]
    solid_references(force_disable=True)
    del bpy.types.Scene.bbe_solid_decals
