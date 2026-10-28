"""Render clean browser icons when the game's shipped icon has a red X.

Run with Blender in background mode.  The meshes, UVs, and materials come from
the native 7.10 extraction; this changes browser artwork only.
"""

from pathlib import Path
import shutil
import bpy
from mathutils import Vector


ADDON = Path(__file__).resolve().parents[2] / "src/addons/no_mans_sky_base_builder"
ROOT = Path(r"C:\Users\kengo\OneDrive\Desktop\NMS\outputs\nms-update-20261028\built")
OUTPUT = ADDON / "images/asset_icons"


def render(pid):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(ROOT / "assets" / (pid + ".blend")), link=False) as (source, loaded):
        loaded.objects = source.objects
    obj = loaded.objects[0]
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()

    # Native icons for these two families are marked with a red X.  A neutral
    # studio material shows the game mesh clearly at thumbnail size without
    # depending on the game's parallax shader or colour palette.
    clay = bpy.data.materials.new("Native rim icon")
    clay.diffuse_color = (0.68, 0.71, 0.75, 1)
    clay.use_nodes = True
    shader = clay.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = clay.diffuse_color
    shader.inputs["Metallic"].default_value = 0.15
    shader.inputs["Roughness"].default_value = 0.5
    obj.data.materials.clear()
    obj.data.materials.append(clay)

    for image in bpy.data.images:
        native_name = image.get("bbe_native_texture")
        if native_name:
            image.filepath = str(ROOT / "textures" / native_name)

    minimum = [min((obj.matrix_world @ v.co)[axis] for v in obj.data.vertices) for axis in range(3)]
    maximum = [max((obj.matrix_world @ v.co)[axis] for v in obj.data.vertices) for axis in range(3)]
    center = Vector([(a + b) / 2 for a, b in zip(minimum, maximum)])
    extent = max(b - a for a, b in zip(minimum, maximum))

    bpy.ops.object.camera_add(location=center + Vector((1.2, -1.5, 0.35)).normalized() * extent * 3)
    camera = bpy.context.object
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = extent * 1.8

    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.render.film_transparent = True
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world = bpy.data.worlds.new("Icon studio")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.8, 0.8, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    for offset, power, size in [((1, -2, 3), 5000, 6), ((-2, 1, 1), 3000, 5)]:
        bpy.ops.object.light_add(type="AREA", location=center + Vector(offset) * extent)
        light = bpy.context.object
        light.data.energy = power
        light.data.shape = "DISK"
        light.data.size = size * extent
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.view_settings.view_transform = "AgX"
    scene.render.filepath = str(OUTPUT / (pid + ".png"))
    bpy.ops.render.render(write_still=True)


for root in ("B_STR_AH_NETB", "B_STR_AI_NETB", "B_WNG_Y"):
    render(root)
    if "NETB" in root:
        family = root.replace("NETB", "")
        siblings = [path.stem for path in (ROOT / "assets").glob(f"{family}*.blend")
                    if path.stem.startswith(family + "NETB") or path.stem.startswith(family + "NWTB")]
    else:
        siblings = [root + suffix for suffix in ("", "_B", "_R", "_T")]
    for pid in siblings:
        if pid != root:
            shutil.copy2(OUTPUT / (root + ".png"), OUTPUT / (pid + ".png"))
