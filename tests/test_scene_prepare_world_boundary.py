"""A world clock cannot unlock scene-order-selected facts for a POV."""
import json
from pathlib import Path
import tempfile
import unittest

import test_story_roots as story_roots
from scripts import scene_prepare


class ScenePreparationWorldBoundaryTests(unittest.TestCase):
    read = staticmethod(story_roots.StoryRootTests.read)
    write = staticmethod(story_roots.StoryRootTests.write)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.root = story_roots.StoryRootTests.fixture(self, 'synthetic', 'BOUNDARY')
        self._add_later_narrative_facts()

    def tearDown(self):
        self.temp.cleanup()

    def _add_later_narrative_facts(self):
        scenes = self.read(self.root / 'data/scenes.json')
        # Keep this fixture focused on temporal disclosure, not prerequisite
        # gate construction; the explicit history still carries a sentinel.
        for scene in scenes['scenes']:
            scene['requires_flags'] = []
        for scene in scenes['scenes'][:2]:
            scene['status'] = 'APPROVED'
            source = self.root / scene['draft_path']
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(
                f'{scene["id"]} NARRATIVE_SOURCE_SENTINEL\n', encoding='utf-8')
        self.write(self.root / 'data/scenes.json', scenes)

        characters = self.read(self.root / 'data/characters.json')
        characters['characters'][0]['knowledge'].append({
            'after_scene': 'SC-002', 'knows': 'NARRATIVE_LATER_KNOWLEDGE_SENTINEL',
        })
        self.write(self.root / 'data/characters.json', characters)

        inventory = self.read(self.root / 'data/inventory_ledger.json')
        inventory['entries'][0].update(
            scene_id='SC-002', quantity=7319, status='APPROVED',
            notes='NARRATIVE_LATER_INVENTORY_SENTINEL')
        self.write(self.root / 'data/inventory_ledger.json', inventory)

        threads = self.read(self.root / 'data/threads.json')
        threads['threads'][0].update(
            title='NARRATIVE_LATER_THREAD_SENTINEL', setup_scene_id='SC-002')
        self.write(self.root / 'data/threads.json', threads)

        state = self.read(self.root / 'data/story_state.json')
        state.update(phase='NARRATIVE_SNAPSHOT_STATE_SENTINEL',
                     fixture_metadata='NARRATIVE_SNAPSHOT_EXTENSION_SENTINEL')
        self.write(self.root / 'data/story_state.json', state)

        history = {
            'schema_version': 1,
            'baseline': {
                'before_scene': 'SC-001', 'status': 'APPROVED',
                'evidence_path': 'bible/INITIAL_STATE.md',
                'state': {'flags': {}, 'marker': 'NARRATIVE_HISTORY_STATE_SENTINEL'},
            },
            'deltas': [
                {'id': f'DELTA-{number:03}', 'scene_id': f'SC-{number:03}',
                 'status': 'APPROVED', 'changes': []}
                for number in (1, 2)
            ],
        }
        (self.root / 'bible/INITIAL_STATE.md').write_text(
            'Synthetic baseline evidence sentinel; no narrative prose.\n', encoding='utf-8')
        self.write(self.root / 'data/state_history.json', history)

    def test_explicit_earlier_world_cursor_withholds_all_narrative_order_facts(self):
        cursor = {
            'clock_id': 'CLOCK-FLASHBACK', 'tick': 1,
            'suborder': 0, 'boundary': 'BEFORE',
        }
        report = scene_prepare.build(
            self.root, 'SC-003', house_id='LOC-001', world_cursor=cursor)
        serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)

        for sentinel in (
            'NARRATIVE_SOURCE_SENTINEL',
            'NARRATIVE_LATER_KNOWLEDGE_SENTINEL',
            'NARRATIVE_LATER_INVENTORY_SENTINEL',
            'NARRATIVE_LATER_THREAD_SENTINEL',
            'NARRATIVE_SNAPSHOT_STATE_SENTINEL',
            'NARRATIVE_SNAPSHOT_EXTENSION_SENTINEL',
            'NARRATIVE_HISTORY_STATE_SENTINEL',
        ):
            with self.subTest(sentinel=sentinel):
                self.assertNotIn(sentinel, serialized)

        self.assertNotIn('7319', serialized)
        self.assertEqual(report['world_cursor'], cursor)
        self.assertEqual(report['cursor_mapping'], 'UNKNOWN_NO_AUTOMATIC_MAPPING')
        self.assertEqual(report['world_preview']['result']['availability'], 'UNKNOWN')
        self.assertEqual(report['world_preview']['audience'], 'AUTHOR_ONLY_NOT_POV_KNOWLEDGE')
        self.assertIn('BOUNDARY_STYLE', report['author_planning_context']['content'])
        self.assertIn('AUTHOR-ONLY SELECTED SCENE PLAN', report['author_planning_context']['content'])
        self.assertEqual(report['pov_knowledge']['availability'], 'UNKNOWN')
        self.assertEqual(report['pov_knowledge']['entries'], [])
        self.assertEqual(report['scene_references']['inventory']['current_balance'], 'UNKNOWN')
        self.assertEqual(report['scene_references']['inventory']['earlier_local_approved_events'], [])
        self.assertEqual(report['scene_references']['open_threads']['eligible_registry_references'], [])
        self.assertEqual(report['scene_references']['open_threads']['historical_open_state'], 'UNKNOWN')
        self.assertEqual(report['house_reference']['availability'], 'UNKNOWN')
        self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')
        self.assertFalse(report['canon_change_authorized'])
        self.assertFalse(report['ledger_apply_authorized'])

    def test_missing_world_model_stays_unknown_and_partial_cursor_is_rejected(self):
        report = scene_prepare.build(self.root, 'SC-003', world_cursor={
            'clock_id': 'CLOCK-NOT-IN-MODEL', 'tick': 800,
            'suborder': 3, 'boundary': 'AFTER',
        })
        result = report['world_preview']['result']
        self.assertEqual(result['availability'], 'UNKNOWN')
        self.assertNotEqual(result['availability'], 'PASS')
        with self.assertRaisesRegex(ValueError, 'World cursor requires'):
            scene_prepare.build(self.root, 'SC-003', world_cursor={
                'clock_id': 'CLOCK-FLASHBACK', 'tick': 1,
            })

    def test_without_world_cursor_legacy_narrative_boundary_remains(self):
        report = scene_prepare.build(self.root, 'SC-003')
        self.assertIsNone(report['world_cursor'])
        self.assertEqual(report['pov_knowledge']['availability'], 'LOCAL_EVIDENCE')
        self.assertIn('NARRATIVE_LATER_KNOWLEDGE_SENTINEL',
                      json.dumps(report, ensure_ascii=False))
        self.assertIn('NARRATIVE_LATER_INVENTORY_SENTINEL',
                      json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    unittest.main()
