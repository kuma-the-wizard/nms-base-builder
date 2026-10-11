"""Packaging guard: optional HD assets must never be the only model for a part."""
from pathlib import Path
import json
import unittest

ADDON = Path(__file__).resolve().parents[1] / 'src/addons/no_mans_sky_base_builder'

class ModelCoverageTests(unittest.TestCase):
    def test_every_optional_hd_part_has_bundled_geometry(self):
        spec = json.loads((ADDON / 'resources/hd_library.json').read_text())
        detailed = {Path(p).stem.split('__')[0] for p in spec['files'] if p.startswith('assets/')}
        bundled = {p.stem for p in (ADDON / 'models').rglob('*.fbx')}
        bundled.update(p.stem for p in (ADDON / 'models-simple').glob('*.blend'))
        self.assertFalse(detailed - bundled, sorted(detailed - bundled))

    def test_stag_is_available_without_optional_library(self):
        self.assertGreater((ADDON / 'models-simple/STA_45.blend').stat().st_size, 1000)

if __name__ == '__main__':
    unittest.main()
