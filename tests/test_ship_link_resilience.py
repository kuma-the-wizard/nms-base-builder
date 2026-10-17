"""Save-local edits remain safe when pre-existing Corvette links are uncertain."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ship_core', ROOT / 'src/addons/no_mans_sky_base_builder/save_editor/ship_core.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
TEMPLATE = json.loads((core.RES / 'minimal_corvette.json').read_text())


def fixture(problem=None, context='Main', raw=False):
    ship = copy.deepcopy(TEMPLATE['ship'])
    base = copy.deepcopy(TEMPLATE['base'])
    base['UserData'] = 0
    bases = [base]
    if problem == 'duplicate':
        bases.append(copy.deepcopy(base))
    elif problem == 'wrong_ship':
        ship['Resource']['Filename'] = 'MODELS/COMMON/SPACECRAFT/FIGHTER.SCENE.MBIN'
    elif problem == 'missing_build':
        bases = []
    elif problem == 'malformed_build':
        bases.append(None)
    elif problem is not None:
        base['UserData'] = problem
    root = {'BaseContext' if context == 'Main' else 'ExpeditionContext': {
        'PlayerStateData': {'ShipOwnership': [ship] + [copy.deepcopy(TEMPLATE['empty']) for _ in range(11)],
                            'PersistentPlayerBases': bases, 'PrimaryShip': 0},
        'SpawnStateData': {'LastKnownPlayerState': 'OnFoot'}},
        'CommonStateData': {'SaveName': 'Test source'}}
    return core.translate(root, False) if raw else root


class LinkResilienceTests(unittest.TestCase):
    def test_known_failures_can_be_inspected_without_mutation(self):
        for problem in ('duplicate', 'wrong_ship', 'missing_build', 'malformed_build', -1, 12, '0', True):
            for raw in (False, True):
                with self.subTest(problem=problem, raw=raw):
                    root = fixture(problem, raw=raw)
                    before = copy.deepcopy(root)
                    self.assertTrue(core.inspect_links(root)['Main'])
                    self.assertEqual(root, before)

    def test_inventory_and_class_edits_preserve_uncertain_links(self):
        for problem in ('duplicate', 'wrong_ship', 'missing_build', -1, '0'):
            for raw in (False, True):
                with self.subTest(problem=problem, raw=raw):
                    original = fixture(problem, raw=raw)
                    snapshot = copy.deepcopy(original)
                    draft = copy.deepcopy(original)
                    core.set_class(draft, 'Main', 0, 'C')
                    inv = core.inventory(draft, 'Main', 0, 'Inventory_TechOnly')
                    core.unlock(inv, tech=True)
                    core.set_inventory(draft, 'Main', 0, 'Inventory_TechOnly', inv)
                    core.validate_draft(original, draft)
                    self.assertEqual(original, snapshot)
                    self.assertEqual(core.get(core.player(original, 'Main'), 'PersistentPlayerBases'),
                                     core.get(core.player(draft, 'Main'), 'PersistentPlayerBases'))

    def test_items_stats_and_existing_hyperslots_remain_editable(self):
        for raw in (False, True):
            original = fixture('duplicate')
            tech = core.inventory(original, 'Main', 0, 'Inventory_TechOnly')
            tech['SpecialSlots'] = [{'Index': {'X': 0, 'Y': 0},
                                     'Type': {'InventorySpecialSlotType': 'TechBonus'}}]
            core.set_inventory(original, 'Main', 0, 'Inventory_TechOnly', tech)
            if raw:original = core.translate(original, False)
            draft = copy.deepcopy(original)
            tech = core.inventory(draft, 'Main', 0, 'Inventory_TechOnly')
            core.move_item(tech, (0, 0), (1, 0))
            core.move_supercharge(tech, (0, 0), (1, 0))
            core.set_inventory(draft, 'Main', 0, 'Inventory_TechOnly', tech)
            cargo = core.inventory(draft, 'Main', 0, 'Inventory')
            cargo['BaseStatValues'][0]['Value'] += 1
            cargo['Slots'].append({'Index': {'X': 0, 'Y': 0}, 'Id': '^FUEL1',
                                   'Type': {'InventoryType': 'Product'}, 'Amount': 1, 'MaxAmount': 9999})
            core.set_inventory(draft, 'Main', 0, 'Inventory', cargo)
            core.validate_draft(original, draft)
            self.assertEqual(len(tech['SpecialSlots']), 1)
            self.assertEqual(tech['SpecialSlots'][0]['Index'], {'X': 1, 'Y': 0})

    def test_bad_expedition_does_not_block_healthy_main_reordering(self):
        original = fixture()
        original.update({k: v for k, v in fixture('duplicate', 'Season').items() if k == 'ExpeditionContext'})
        draft = copy.deepcopy(original)
        core.reorder(draft, 'Main', [1, 0] + list(range(2, 12)))
        core.validate_draft(original, draft)
        self.assertEqual(original['ExpeditionContext'], draft['ExpeditionContext'])
        self.assertEqual(draft['BaseContext']['PlayerStateData']['PersistentPlayerBases'][0]['UserData'], 1)

    def test_uncertain_context_rejects_ownership_changes_at_commit(self):
        changes = [
            lambda p: p['ShipOwnership'].reverse(),
            lambda p: p['ShipOwnership'][0]['Resource'].update(Filename='OTHER'),
            lambda p: p['PersistentPlayerBases'].pop(),
            lambda p: p['PersistentPlayerBases'][0].update(UserData=3),
            lambda p: p.update(PrimaryShip=1),
            lambda p: p['ShipOwnership'][1].update(Inventory=copy.deepcopy(TEMPLATE['ship']['Inventory'])),
        ]
        for change in changes:
            with self.subTest(change=change):
                original = fixture('duplicate')
                draft = copy.deepcopy(original)
                change(core.player(draft, 'Main'))
                with self.assertRaises(ValueError):core.validate_draft(original, draft)

    def test_surrounding_context_and_save_metadata_stay_protected(self):
        for field in ('spawn', 'name', 'context'):
            original = fixture('duplicate'); draft = copy.deepcopy(original)
            if field == 'spawn':draft['BaseContext']['SpawnStateData']['LastKnownPlayerState'] = 'InShip'
            elif field == 'name':draft['CommonStateData']['SaveName'] = 'Unexpected'
            else:draft['ExpeditionContext'] = copy.deepcopy(draft['BaseContext'])
            with self.subTest(field=field), self.assertRaises(ValueError):core.validate_draft(original, draft)

    def test_bad_inventory_does_not_pass_the_new_save_guard(self):
        original = fixture('duplicate'); draft = copy.deepcopy(original)
        core.player(draft, 'Main')['ShipOwnership'][0]['Inventory']['Width'] = 100
        with self.assertRaises(ValueError):core.validate_draft(original, draft)

    def test_new_link_errors_remain_blocked(self):
        original = fixture(); draft = copy.deepcopy(original)
        core.player(draft, 'Main')['PersistentPlayerBases'].append(copy.deepcopy(TEMPLATE['base']))
        core.player(draft, 'Main')['PersistentPlayerBases'][-1]['UserData'] = 0
        with self.assertRaises(ValueError):core.validate_draft(original, draft)

    def test_structural_commands_still_refuse_uncertain_links(self):
        original = fixture('duplicate'); draft = copy.deepcopy(original)
        with self.assertRaises(ValueError):core.reorder(draft, 'Main', list(reversed(range(12))))
        with self.assertRaises(ValueError):core.add_minimal(draft, 'Main', 1, 'New Corvette')
        with self.assertRaises(ValueError):core.clean_copy(draft, 'Copy', {'Main': [0]}, {})
        self.assertEqual(original, draft)


if __name__ == '__main__':
    unittest.main()
