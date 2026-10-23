"""Static writer-reference consistency; no damage, raid or engine simulation."""
import json
from pathlib import Path
import unittest

PACKAGE = Path(__file__).resolve().parents[1]/'stories/last-island-active/design/proposals/house-atlas-v1'


class EnvelopeReferenceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((PACKAGE/'defensive_envelope_reference.json').read_text(encoding='utf-8'))
        self.parts = {p['part_id']: p for p in self.data['part_registry']}

    def test_strength_claims_keep_exact_comparators_and_unknown_values(self):
        claims = self.data['user_reported_strength_claims']
        self.assertEqual(claims[0]['claim_text_th_exact'], 'ประตูหินมีความหนาเท่ากับกำแพงไม้')
        self.assertEqual(claims[1]['claim_text_th_exact'], 'ประตูเหล็กมีความหนาเท่ากับประตูหิน')
        self.assertEqual(claims[1]['comparison_as_written'], 'iron door compared with stone door')
        self.assertEqual(claims[1]['clarification_status'], 'AMBIGUOUS_PENDING_CONFIRMATION')
        for claim in claims:
            self.assertEqual(claim['verification'], 'UNVERIFIED')
            self.assertEqual(claim['attribute_ref'], 'symbolic_strength_tier')
            self.assertEqual(claim['intended_meaning_after_user_clarification'], 'SYMBOLIC_STRENGTH_LEVEL_IN_GAME')
            self.assertIsNone(claim['symbolic_strength_tier_value'])
            self.assertIsNone(claim['geometric_thickness_value'])
        self.assertEqual(self.data['strength_layer_addition'], 'UNKNOWN_NO_ADDITION_RULE_ASSUMED')

    def test_layers_and_unknown_vertical_levels_are_independent_of_game_strength(self):
        self.assertEqual(len(self.parts), len(self.data['part_registry']))
        barriers = [p for p in self.parts.values() if p['kind'] == 'BARRIER_SEGMENT']
        self.assertEqual({(p['side'],p['layer_index']) for p in barriers},
                         {(s,n) for s in ['N','S','E','W','TOP'] for n in [1,2,3]})
        for part in self.parts.values():
            self.assertEqual(part['material_tier'], 'UNKNOWN')
            self.assertIsNone(part['geometric_thickness'])
            self.assertIsNone(part['symbolic_strength_tier'])
            self.assertIsNone(part['floor_index'])
            self.assertIsNone(part['completion_world_time'])
        self.assertIsNone(self.data['design_direction']['fixed_build_schedule'])
        self.assertIsNone(self.data['design_direction']['automatic_level_rule'])

    def test_snapshot_declarations_keep_future_layers_unknown_and_breach_local(self):
        # Resolve only explicit fixture inheritance to compare static declarations.
        # This helper is confined to this test; no engine replay is implemented.
        states, ticks = {}, {}
        for snapshot in self.data['synthetic_snapshots']:
            name, parent = snapshot['snapshot_id'], snapshot['as_built_inherits']
            tick = snapshot['world_time_bounds']['start']
            if parent:
                self.assertIn(parent, states)
                self.assertLess(ticks[parent], tick)
                state = {key: dict(value) for key,value in states[parent].items()}
            else:
                default = snapshot['default_state_for_unlisted_parts']
                state = {key: dict(default) for key in self.parts}
            overrides = snapshot['as_built_overrides']
            self.assertEqual(len({p['part_id'] for p in overrides}), len(overrides))
            for part in overrides:
                self.assertIn(part['part_id'], self.parts)
                state[part['part_id']] = {k:v for k,v in part.items() if k != 'part_id'}
            states[name], ticks[name] = state, tick
            self.assertIsNone(snapshot['story_scene_ref'])
            self.assertEqual(snapshot['pov_knowledge'], 'UNKNOWN')
        for side in ['N','S','E','W','TOP']:
            self.assertEqual(states['SYN-ENV-A']['SYN-ENV-L2-'+side]['construction'], 'UNKNOWN')
            self.assertEqual(states['SYN-ENV-B']['SYN-ENV-L2-'+side]['construction'], 'COMPLETED')
            self.assertEqual(states['SYN-ENV-C']['SYN-ENV-L3-'+side]['construction'], 'UNKNOWN')
        changed = {key for key in self.parts if states['SYN-ENV-C'][key] != states['SYN-ENV-B'][key]}
        self.assertEqual(changed, {'SYN-ENV-L1-N'})
        self.assertEqual(states['SYN-ENV-C']['SYN-ENV-L1-N']['damage_repair'], 'DAMAGED_BREACHED')
        for part in self.parts.values():
            if part['kind'] == 'DOOR_SYMBOL':
                self.assertEqual(states['SYN-ENV-C'][part['part_id']]['usability'], 'UNKNOWN')

    def test_serial_door_labels_resolve_but_do_not_claim_walkability(self):
        route = self.data['symbolic_route_example']
        nodes, crossings = route['sequence_of_symbolic_nodes'], route['door_crossings']
        self.assertEqual(len(crossings), len(nodes)-1)
        registered = {'EXTERIOR', self.data['design_direction']['inner_house_ref'], *self.data['symbolic_buffer_refs']}
        self.assertTrue(set(nodes) <= registered)
        for i,crossing in enumerate(crossings):
            door = self.parts[crossing['door_id']]
            self.assertEqual(door['from_ref'], nodes[i])
            self.assertEqual(door['to_ref'], nodes[i+1])
            self.assertIn(crossing['crosses_boundary_ref'], self.parts)
        self.assertFalse(route['barrier_parts_are_nodes_or_rooms'])
        self.assertFalse(route['buffer_labels_are_rooms'])
        self.assertFalse(route['scene_specific_route'])
        self.assertEqual(route['walkability'], 'UNKNOWN')
        self.assertEqual(route['route_optimization'], 'NOT_PERFORMED')

    def test_optional_writer_package_does_not_adopt_or_apply_state(self):
        self.assertEqual(self.data['namespace'], 'SYNTHETIC-NOT-STORY')
        self.assertEqual(self.data['adoption'], 'NOT_ADOPTED')
        self.assertEqual(self.data['human_editorial_approval'], 'UNVERIFIED')
        for key in ['canon_change_authorized','ledger_apply_authorized','runtime_or_engine_promise']:
            self.assertIs(self.data[key], False)
        self.assertIn('IMMUTABLE_SNAPSHOTS', self.data['history_policy'])
        card = json.loads((PACKAGE/'writer_reference_card.json').read_text(encoding='utf-8'))
        ref = card['optional_writer_reference_documents']
        self.assertFalse(ref['runtime_loaded'])
        self.assertTrue((PACKAGE/ref['protective_envelope']).is_file())


if __name__ == '__main__':
    unittest.main()
