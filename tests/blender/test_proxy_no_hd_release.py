"""The public extension works with no separately installed detailed pack."""
from pathlib import Path
import os
import sys

# A ZIP extraction has no bundled models-high-res. Keep this test isolated from
# any HD pack installed for the developer's normal Blender profile.
os.environ['BBE_ASSET_LIBRARY_ROOT'] = str(Path(__file__).resolve().parents[1] /
                                            '.artifacts' / 'empty_hd_library')
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_support import module, report

hd = module('hd_library')
builder = module('builder_v2')
materials = module('utils.materials_v2')
assert not hd.available()
part = builder.add_part('ABAND_BARREL', user_data=0)
assert part and part.object and part.object.type == 'MESH'
assert not materials.is_high_res(part.object)
report('proxy_no_hd_release', {'pack_available': hd.available(),
                               'part': part.object.get('ObjectID'),
                               'simple_proxy': not materials.is_high_res(part.object)})
