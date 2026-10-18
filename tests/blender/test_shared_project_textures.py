"""Shared project textures are usable before the first frame, with/without HD."""
from pathlib import Path
from unittest.mock import patch
import hashlib, os, sys
import bpy
from bpy.app.handlers import persistent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, report
builder = module('builder_v2')
hd = module('hd_library')
ui = module('hd_library_ui')
materials = module('utils.materials_v2')
progress = module('progress_ui')
source = Path(os.environ.get('BBE_TEST_PROJECT', Path.home() / 'Downloads/TestBed.blend'))
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
no_hd = bool(os.environ.get('BBE_TEST_NO_HD'))
if no_hd:
    hd.library_root = lambda: None
    hd.available = lambda: False

def identities():
    return {obj.name: (obj.get('ObjectID'), obj.get('UserData'),
                       tuple(obj.location), tuple(obj.rotation_euler), tuple(obj.rotation_quaternion),
                       obj.rotation_mode, tuple(obj.scale), tuple(tuple(row) for row in obj.matrix_parent_inverse),
                       obj.parent.name if obj.parent else None)
            for obj in bpy.context.scene.objects if 'ObjectID' in obj}

original = {}
@persistent
def capture(_):
    original.update(identities())
bpy.app.handlers.load_post.insert(0, capture)
try:
    with patch.object(progress.Activity, '_redraw') as redraw:
        bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
        redraw.assert_not_called()
finally:
    bpy.app.handlers.load_post.remove(capture)
assert len(original) == 293 and identities() == original
images = {image for obj in bpy.context.scene.objects if obj.type == 'MESH'
          for image in builder._mesh_texture_images(obj.data)}
for image in images:
    if image.source == 'FILE' and not image.packed_file:
        assert Path(bpy.path.abspath(image.filepath, library=image.library)).is_file(), image.filepath
    # Reading size alone need not decode a lazy file image; touch pixels too.
    assert len(image.pixels) > 0 and image.size[0] > 0, image.name
assert not ui._saved_hd_needs_simple_proxies(bpy.context.scene)
assert sum(materials.is_high_res(obj) for obj in bpy.context.scene.objects) == (0 if no_hd else 293)
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
report('shared_project_textures', dict(version=bpy.app.version_string, no_hd=no_hd,
       images=len(images), missing_textures=0, decoded=True, no_intermediate_redraw=True,
       part_identity_and_transforms_preserved=True, original_file_unchanged=True))
