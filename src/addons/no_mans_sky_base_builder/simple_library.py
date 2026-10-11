"""Bundled geometry for parts without a legacy FBX. Never requires HD assets."""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parent / "models-simple"


def load_mesh(object_id):
    path = ROOT / (object_id + ".blend")
    if not path.is_file():
        return None
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        target.meshes = list(source.meshes)
    meshes = [mesh for mesh in target.meshes if mesh is not None]
    if len(meshes) != 1 or not meshes[0].vertices:
        raise ValueError("Invalid bundled simple model: " + object_id)
    return meshes[0]


def new_object(object_id):
    # Use the common cache so browser placement, imports and quality switches
    # all resolve the same geometry.
    from . import builder_v2
    mesh = builder_v2.load_proxy_mesh(object_id)
    return bpy.data.objects.new(object_id, mesh.copy()) if mesh is not None else None
