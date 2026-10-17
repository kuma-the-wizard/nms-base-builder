"""Simple proxies stay usable when the optional detailed pack is absent."""
from pathlib import Path
import sys
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, report

hd = module('hd_library')
builder = module('builder_v2')
materials = module('utils.materials_v2')
hd_ui = module('hd_library_ui')
Group = module('group').Group

# A project saved elsewhere can embed detailed geometry whose external
# textures do not exist on the recipient's machine.
saved = builder.add_part('ABAND_BARREL', user_data=0)
saved_obj = saved.object
assert materials.is_high_res(saved_obj)
saved_obj.location.x = 7
group_parts = [builder.add_part(name, user_data=0).object
               for name in ('ABAND_BENCH', 'ABAND_SHELF')]
group_obj = Group.group_objects(group_parts)
assert group_obj and materials.is_high_res(group_obj)
for obj in (saved_obj, group_obj):
    image = next(i for i in builder._mesh_texture_images(obj.data)
                 if i.source == 'FILE' and not i.packed_file)
    image.filepath = 'C:/BBE-test-source-that-does-not-exist/missing.webp'
assert hd_ui._saved_hd_needs_simple_proxies(bpy.context.scene)
assert hd.available(), 'This test needs the locally installed HD pack'
hd_ui._repair_saved_hd_textures()
assert saved_obj == saved.object and saved_obj.location.x == 7
assert not materials.is_high_res(saved_obj)
assert Group.PROP_GROUP_ID in group_obj and not materials.is_high_res(group_obj)
assert not bpy.context.scene.bbe_detailed_proxies

# The same scene should also keep working if the optional pack is removed.
hd.library_root = lambda: None
hd.available = lambda: False
builder.get_asset_index(rebuild=True)

part = builder.add_part('ABAND_BARREL', user_data=0)
assert part and part.object and part.object.type == 'MESH'
assert not materials.is_high_res(part.object)
report('proxy_without_hd_pack', {'part': part.object.get('ObjectID'),
                                 'saved_project_fell_back': not materials.is_high_res(saved_obj),
                                 'saved_group_fell_back': not materials.is_high_res(group_obj),
                                 'mesh': part.object.data.name,
                                 'high_res': materials.is_high_res(part.object)})
