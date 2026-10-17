"""Inspect texture resolution while a detailed model is appended."""
from pathlib import Path
import sys
import bpy
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, report

builder = module('builder_v2')
materials = module('utils.materials_v2')
hd = module('hd_library')


def images_for(mesh):
    images = set()
    seen = set()
    pending = [mat.node_tree for mat in mesh.materials if mat and mat.use_nodes]
    while pending:
        tree = pending.pop()
        if tree in seen:
            continue
        seen.add(tree)
        for node in tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                images.add(node.image)
            elif node.type == 'GROUP' and node.node_tree:
                pending.append(node.node_tree)
    return images


mesh = builder.load_high_res_mesh('ABAND_BARREL')
assert mesh is not None
root = hd.library_root()
before = [dict(name=i.name, filepath=i.filepath,
               exists=Path(bpy.path.abspath(i.filepath)).is_file())
          for i in images_for(mesh) if i.source == 'FILE' and not i.packed_file]
assert before and all(i['exists'] and Path(i['filepath']).is_relative_to(root) for i in before), before
materials.dedupe_appended_data()
after = [dict(name=i.name, filepath=i.filepath,
              exists=Path(bpy.path.abspath(i.filepath)).is_file())
         for i in images_for(mesh) if i.source == 'FILE' and not i.packed_file]
image = next(i for i in images_for(mesh) if i.source == 'FILE' and not i.packed_file)
original_path = image.filepath
image.filepath = 'C:/BBE-test-source-that-does-not-exist/missing.webp'
with patch.object(hd, 'relink_texture_images', return_value=0):
    assert not builder._relink_mesh_textures(mesh)
    assert 'texture is missing' in hd.STATE['error']
image.filepath = original_path
hd.STATE['error'] = ''
report('proxy_loading_textures', dict(before=before[:2], after=after[:2],
                                      missing_before=sum(not i['exists'] for i in before),
                                      missing_after=sum(not i['exists'] for i in after),
                                      corrupt_texture_rejected=True))
