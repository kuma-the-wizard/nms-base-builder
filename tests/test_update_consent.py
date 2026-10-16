"""Persisted update choices must gate automatic network activity."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / 'src/addons/no_mans_sky_base_builder/furby_updates.py'
spec = importlib.util.spec_from_file_location('updates_under_test', path)
updates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updates)


class UpdateConsentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def client(self, version='18.1.63', consent=True):
        return updates.UpdateClient('bbe', version, state=self.root, require_consent=consent)

    def assert_no_check(self, client):
        calls = []
        client.start = lambda: calls.append('network')
        client.maybe_check()
        self.assertEqual(calls, [])

    def test_new_install_waits_for_consent(self):
        c = self.client()
        self.assertTrue(c.needs_auto_consent)
        self.assertFalse(c.settings['auto_check'])
        self.assert_no_check(c)

    def test_decline_survives_restart_and_upgrade(self):
        self.client().set_auto(False)
        c = self.client('18.1.64')
        self.assertFalse(c.needs_auto_consent)
        self.assertFalse(c.settings['auto_check'])
        self.assert_no_check(c)

    def test_accept_survives_restart_and_upgrade(self):
        self.client().set_auto(True)
        c = self.client('18.1.64')
        self.assertFalse(c.needs_auto_consent)
        self.assertTrue(c.settings['auto_check'])
        calls = []
        c.start = lambda: calls.append('check')
        c.maybe_check()
        self.assertEqual(calls, ['check'])

    def test_legacy_default_on_must_ask(self):
        (self.root / 'bbe.json').write_text(json.dumps({'auto_check':True, 'last_checked':123}))
        c = self.client()
        self.assertTrue(c.needs_auto_consent)
        self.assert_no_check(c)

    def test_legacy_disabled_setting_is_respected(self):
        (self.root / 'bbe.json').write_text(json.dumps({'auto_check':False}))
        c = self.client()
        self.assertFalse(c.needs_auto_consent)
        self.assert_no_check(c)

    def test_other_products_keep_existing_behavior(self):
        c = self.client(consent=False)
        self.assertTrue(c.settings['auto_check'])
        self.assertFalse(c.needs_auto_consent)

    def test_corrupt_settings_do_not_enable_checks(self):
        (self.root / 'bbe.json').write_text('{broken')
        c = self.client()
        self.assertTrue(c.needs_auto_consent)
        self.assert_no_check(c)


if __name__ == '__main__':
    unittest.main()
