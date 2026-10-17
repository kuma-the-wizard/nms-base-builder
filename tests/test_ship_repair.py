"""Reviewed replacements must repair only the explicitly chosen destination."""
import copy
import importlib.util
import sys
import types
import unittest
from test_ship_link_resilience import core, fixture, TEMPLATE

package = types.ModuleType('repair_test')
package.__path__ = [str(core.RES.parent / 'save_editor')]
sys.modules['repair_test'] = package
sys.modules['repair_test.ship_core'] = core
spec = importlib.util.spec_from_file_location('repair_test.ship_repair', core.RES.parent/'save_editor/ship_repair.py')
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


def payload():
    return {'ship': copy.deepcopy(TEMPLATE['ship']), 'objects': copy.deepcopy(TEMPLATE['base']['Objects']), 'custom': None}


class RepairTests(unittest.TestCase):
    def test_inventory_comparison_is_read_only_and_covers_unknown_data(self):
        for raw in (False, True):
            root=fixture('wrong_ship')
            root['UnknownRootData']={'Seed':2**63+123,'Text':'星🚀','Values':[1.25,-7]}
            root['BaseContext']['UnknownContextData']={'Keep':[{'Value':99}]}
            if raw:root=core.translate(root,False)
            plan=repair.make_plan(root,'Main',0,payload(),'FULL')
            draft=repair.apply_plan(root,plan)
            core.set_class(draft,'Main',0,'C')
            before,after=copy.deepcopy(root),copy.deepcopy(draft)
            repair.validate_reviewed_draft(root,draft,[plan])
            self.assertEqual(root,before)
            self.assertEqual(draft,after)
            for mutation in (
                lambda r:r['UnknownRootData']['Values'].append(123),
                lambda r:r[core.key(r,'BaseContext')]['UnknownContextData']['Keep'][0].update(Value=100),
                lambda r:core.get(core.player(r,'Main'),'PersistentPlayerBases')[0].update(Unreviewed=True)):
                bad=copy.deepcopy(draft);mutation(bad)
                with self.assertRaises(ValueError):repair.validate_reviewed_draft(root,bad,[plan])
                self.assertEqual(root,before)

    def test_warnings_and_independent_replacement(self):
        for raw in (False, True):
            for problem in ('wrong_ship', 'missing_build', 'duplicate'):
                with self.subTest(raw=raw, problem=problem):
                    source=fixture(problem)
                    p=core.player(source,'Main')
                    freighter={'Name':'Keep Freighter','BaseType':{'PersistentBaseTypes':'FreighterBase'},'Objects':[{'Private':'unchanged'}]}
                    p['PersistentPlayerBases'].append(freighter)
                    # Another invalid build must remain untouched.
                    orphan=copy.deepcopy(TEMPLATE['base']);orphan['UserData']=99
                    p['PersistentPlayerBases'].append(orphan)
                    source['ExpeditionContext']=fixture(context='Season')['ExpeditionContext']
                    if raw:source=core.translate(source,False)
                    before=copy.deepcopy(source)
                    warnings=repair.inspect_slots(source,'Main')
                    self.assertTrue(warnings[0][0]);self.assertTrue(warnings[1])
                    plan=repair.make_plan(source,'Main',0,payload(),'FULL',anchor=0 if problem!='missing_build' else None,replace_duplicates=True)
                    result=repair.apply_plan(source,plan)
                    repair.validate_reviewed_draft(source,result,[plan])
                    self.assertFalse(repair.inspect_slots(result,'Main')[0][0])
                    self.assertEqual(result[core.key(result,'ExpeditionContext')],source[core.key(source,'ExpeditionContext')])
                    self.assertEqual(core.ships(result,'Main')[1:],core.ships(source,'Main')[1:])
                    remaining=core.translate(core.get(core.player(result,'Main'),'PersistentPlayerBases'))
                    self.assertIn(freighter,remaining);self.assertIn(orphan,remaining)
                    self.assertEqual(source,before)

    def test_duplicate_requires_reviewed_anchor_and_confirmation(self):
        root=fixture('duplicate')
        for anchor,confirm in ((None,False),(0,False),(None,True),(9,True)):
            with self.assertRaises(ValueError):repair.make_plan(root,'Main',0,payload(),'FULL',anchor,confirm)
        plan=repair.make_plan(root,'Main',0,payload(),'FULL',1,True)
        result=repair.apply_plan(root,plan)
        self.assertEqual(len(core.get(core.player(result,'Main'),'PersistentPlayerBases')),1)

    def test_objects_only_preserves_ownership_and_rejects_ambiguous_slots(self):
        root=fixture();data=payload();data['objects']=data['objects'][:1]
        plan=repair.make_plan(root,'Main',0,data,'OBJECTS')
        result=repair.apply_plan(root,plan)
        repair.validate_reviewed_draft(root,result,[plan])
        self.assertEqual(core.ships(result,'Main'),core.ships(root,'Main'))
        for problem in ('wrong_ship','missing_build','duplicate'):
            with self.assertRaises(ValueError):repair.make_plan(fixture(problem),'Main',0,data,'OBJECTS')

    def test_bad_payload_cannot_mutate_source(self):
        root=fixture('wrong_ship');before=copy.deepcopy(root)
        bad=[]
        p=payload();p['objects']=[];bad.append(p)
        p=payload();p['objects'][0]['Position']=[float('nan'),0,0];bad.append(p)
        p=payload();p['ship']['Resource']['Filename']='SHUTTLE';bad.append(p)
        p=payload();p['ship']['Inventory']['Width']=0;bad.append(p)
        for p in bad:
            with self.assertRaises(ValueError):repair.make_plan(root,'Main',0,p,'FULL')
        self.assertEqual(root,before)

    def test_unreviewed_changes_blocked_in_previously_broken_context(self):
        root=fixture('wrong_ship');plan=repair.make_plan(root,'Main',0,payload(),'FULL')
        good=repair.apply_plan(root,plan)
        for mutate in (lambda r:r['BaseContext']['SpawnStateData'].update(Evil=True),
                       lambda r:core.ships(r,'Main')[1].update(Name='unauthorized'),
                       lambda r:core.player(r,'Main').update(FreighterInventory={'Changed':True}),
                       lambda r:r['CommonStateData'].update(SaveName='unauthorized')):
            result=copy.deepcopy(good);mutate(result)
            with self.assertRaises(ValueError):repair.validate_reviewed_draft(root,result,[plan])
        core.set_class(good,'Main',0,'C')
        repair.validate_reviewed_draft(root,good,[plan])

    def test_stale_record_list_rejected(self):
        root=fixture('wrong_ship');plan=repair.make_plan(root,'Main',0,payload(),'FULL')
        core.get(core.player(root,'Main'),'PersistentPlayerBases').append(copy.deepcopy(TEMPLATE['base']))
        with self.assertRaises(ValueError):repair.apply_plan(root,plan)

    def test_primary_ship_and_appearance_sync(self):
        root=fixture('wrong_ship');p=core.player(root,'Main')
        p.update(CurrentShip={'Old':True},ShipInventory={'Old':True},ShipLayout={'Old':True},
                 CharacterCustomisationData=[{'Keep':i} for i in range(23)],ShipUsesLegacyColours=[True]*12)
        data=payload();data['custom']=copy.deepcopy(TEMPLATE['custom'])
        plan=repair.make_plan(root,'Main',0,data,'FULL')
        result=repair.apply_plan(root,plan);r=core.player(result,'Main')
        self.assertEqual(r['CurrentShip'],data['ship']['Resource'])
        self.assertEqual(r['ShipInventory'],data['ship']['Inventory'])
        self.assertEqual(r['CharacterCustomisationData'][3],data['custom'])
        self.assertEqual(r['CharacterCustomisationData'][4:],p['CharacterCustomisationData'][4:])
        self.assertFalse(r['ShipUsesLegacyColours'][0]);self.assertTrue(all(r['ShipUsesLegacyColours'][1:]))
        repair.validate_reviewed_draft(root,result,[plan])

    def test_keep_build_repair_preserves_ship_data_without_adding_cockpit(self):
        for ctx in ('Main', 'Season'):
            for raw in (False, True):
                root = fixture('wrong_ship', context=ctx)
                p = core.player(root, ctx)
                p['CharacterCustomisationData'] = [copy.deepcopy(TEMPLATE['custom']) for _ in range(23)]
                p['ShipUsesLegacyColours'] = [True] * 12
                p['ShipOwnership'][0]['UnknownShipStat'] = {'Keep': 1234}
                p['ShipOwnership'][0]['Name'] = 'Keep my ship name'
                inv = p['ShipOwnership'][0]['Inventory_TechOnly']
                inv['BaseStatValues'][0]['Value'] = 777
                inv['SpecialSlots'] = [{'Index': {'X': 4, 'Y': 2}, 'Type': {'InventorySpecialSlotType': 'TechBonus'}}]
                objects = p['PersistentPlayerBases'][0]['Objects']
                objects[:] = [o for o in objects if not o['ObjectID'].startswith('^B_COK_')]
                objects[0]['UnknownPartField'] = {'Colors': [1, 2, 3]}
                objects[0]['Position'] = [19.25, -14, 6]
                if raw: root = core.translate(root, False)
                before = copy.deepcopy(root)
                data, resets = repair.rebuild_payload(root, ctx, 0, 0)
                self.assertEqual(resets, [])
                plan = repair.make_plan(root, ctx, 0, data, 'FULL', 0)
                out = repair.apply_plan(root, plan)
                repair.validate_reviewed_draft(root, out, [plan])
                old_ship, new_ship = core.ships(root, ctx)[0], core.ships(out, ctx)[0]
                self.assertEqual(core.get(new_ship, 'Name'), 'Keep my ship name')
                for field in ('Inventory', 'Inventory_Cargo', 'Inventory_TechOnly', 'InventoryLayout', 'UnknownShipStat'):
                    self.assertEqual(core.get(old_ship, field), core.get(new_ship, field), field)
                self.assertEqual(core.get(core.player(out, ctx), 'PersistentPlayerBases')[0][core.key(core.get(core.player(out, ctx), 'PersistentPlayerBases')[0], 'Objects')],
                                 core.get(core.get(core.player(root, ctx), 'PersistentPlayerBases')[0], 'Objects'))
                self.assertEqual(core.get(core.player(out, ctx), 'CharacterCustomisationData'), core.get(core.player(root, ctx), 'CharacterCustomisationData'))
                self.assertEqual(core.get(core.player(out, ctx), 'ShipUsesLegacyColours'), [True]*12)
                self.assertFalse(repair.inspect_slots(out, ctx, include_warnings=False)[0][0])
                self.assertIn('unflyable', repair.inspect_slots(out, ctx)[0][0][0])
                self.assertEqual(root, before)

    def test_new_slot_contains_only_scene_parts_and_preserves_existing_ships(self):
        for ctx in ('Main', 'Season'):
            root = fixture(context=ctx)
            objects = copy.deepcopy(TEMPLATE['base']['Objects'][:1])  # Deliberately no cockpit.
            data, resets = repair.rebuild_payload(root, ctx, 5, objects=objects, name='New design', new=True)
            plan = repair.make_plan(root, ctx, 5, data, 'FULL')
            out = repair.apply_plan(root, plan)
            repair.validate_reviewed_draft(root, out, [plan])
            self.assertEqual(core.ships(out, ctx)[:5], core.ships(root, ctx)[:5])
            self.assertEqual(core.ships(out, ctx)[6:], core.ships(root, ctx)[6:])
            base = core.get(core.player(out, ctx), 'PersistentPlayerBases')[-1]
            self.assertEqual(core.get(base, 'Objects'), objects)
            self.assertEqual(core.get(base, 'UserData'), 5)
            self.assertTrue(core.corvette(core.ships(out, ctx)[5]))
            self.assertEqual(resets, [])
            with self.assertRaises(ValueError): repair.rebuild_payload(out, ctx, 5, objects=objects, new=True)
            core.ships(root, ctx)[0] = copy.deepcopy(TEMPLATE['empty'])
            self.assertNotIn(0, repair.empty_ship_slots(root, ctx))  # Orphan build reserves slot.
            for i in range(12):
                core.ships(root, ctx)[i] = copy.deepcopy(TEMPLATE['ship'])
            self.assertEqual(repair.empty_ship_slots(root, ctx), [])

    def test_unreadable_inventory_reset_is_reported_and_other_data_preserved(self):
        root = fixture('wrong_ship')
        old = core.ships(root, 'Main')[0]
        old['Inventory_TechOnly']['Width'] = 0
        data, resets = repair.rebuild_payload(root, 'Main', 0)
        self.assertEqual(len(resets), 1)
        self.assertIn('Inventory_TechOnly', resets[0])
        self.assertEqual(data['ship']['Inventory'], old['Inventory'])
        self.assertEqual(data['ship']['Inventory_Cargo'], old['Inventory_Cargo'])
        repair.validate_payload(data, 'FULL')

    def test_rebuild_rejects_invalid_destination_indices(self):
        root = fixture()
        for index in (-1, 12, True, '0'):
            with self.assertRaises(ValueError): repair.rebuild_payload(root, 'Main', index)

    def test_empty_slot_and_multiple_replacements(self):
        root=fixture('wrong_ship');draft=root;plans=[]
        for index in (0,2,0):
            plan=repair.make_plan(draft,'Main',index,payload(),'FULL')
            draft=repair.apply_plan(draft,plan);plans.append(plan)
        repair.validate_reviewed_draft(root,draft,plans)
        self.assertFalse(core.inspect_links(draft)['Main'])


if __name__=='__main__':unittest.main()
