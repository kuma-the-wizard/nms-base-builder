"""A copied Steam slot preserves its source save identity."""
import importlib.util
import pathlib
import struct
import unittest


SAVE_EDITOR = pathlib.Path(__file__).resolve().parents[1] / 'src/addons/no_mans_sky_base_builder/save_editor'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SAVE_EDITOR / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load('ship_core')
metadata = load('steam_metadata')


class DuplicateIdentityTests(unittest.TestCase):
    def test_copy_preserves_slot_identity_and_changes_requested_name(self):
        old_id = '0x0123456789ABCDEF'
        ships = [{'Resource': {'Filename': 'MODELS/SHIP.FBX'}, 'Name': 'Kept Ship'}]
        ships += [{'Resource': {'Filename': ''}} for _ in range(11)]
        source = {
            'CommonStateData': {'SaveName': 'Original', 'SaveUniversalId': old_id},
            'BaseContext': {'PlayerStateData': {
                'ShipOwnership': ships, 'PersistentPlayerBases': [], 'PrimaryShip': 0,
            }},
        }
        copied = core.clean_copy(source, 'New Copy', {'Main': [0]}, {})
        self.assertEqual(copied['CommonStateData']['SaveUniversalId'], old_id)
        self.assertEqual(copied['CommonStateData']['SaveName'], 'New Copy')
        self.assertEqual(source['CommonStateData'], {'SaveName': 'Original', 'SaveUniversalId': old_id})
        self.assertEqual(copied['BaseContext']['PlayerStateData']['ShipOwnership'][0], ships[0])

    def test_new_slot_metadata_keeps_source_identity(self):
        plain = bytearray(432)
        struct.pack_into('<I', plain, 0, 0xeeeeeebe)
        struct.pack_into('<Q', plain, 348, 0x0123456789ABCDEF)
        source = metadata.crypt(plain, metadata.storage_number('mf_save9.hg'))
        copied = metadata.rebuild(source, 'mf_save9.hg', 'mf_save23.hg', 1234, 5678,
                                  'New Copy')
        decoded = metadata.decode(copied, 'mf_save23.hg')
        self.assertEqual(struct.unpack_from('<Q', decoded, 348)[0], 0x0123456789ABCDEF)
        self.assertEqual(decoded[88:96], b'New Copy')
        self.assertEqual(metadata.decode(source, 'mf_save9.hg')[348:356], plain[348:356])


if __name__ == '__main__':
    unittest.main()
