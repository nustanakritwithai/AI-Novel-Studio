"""Local declared state evidence tests; fixtures are not real prose or approval."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import state_replay


class StateReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.root, self.db, self.history = self.fixture('branch-a', 'A_ONLY')

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    def fixture(self, directory, token):
        root = self.workspace / directory
        (root / 'data').mkdir(parents=True)
        (root / 'bible').mkdir()
        (root / 'drafts').mkdir()
        self.write(root / 'story.json', {
            'schema_version': 1, 'slug': 'same-story', 'title': 'Synthetic metadata',
            'extensions': {'gameplay': False}, 'rules': [],
        })
        (root / 'bible/INITIAL_STATE.md').write_text(
            '# Synthetic initial-state metadata fixture; no real human approval.\n', encoding='utf-8')
        db = {
            'episodes': {'schema_version': 1, 'episodes': [
                {'id': 'EP-Z', 'scene_ids': ['SC-Z', 'SC-A']},
                {'id': 'EP-A', 'scene_ids': ['SC-B']},
            ]},
            'scenes': {'schema_version': 1, 'scenes': [
                {'id': 'SC-B', 'episode_id': 'EP-A', 'order': 1, 'status': 'APPROVED', 'draft_path': 'drafts/SC-B.md'},
                {'id': 'SC-A', 'episode_id': 'EP-Z', 'order': 2, 'status': 'APPROVED', 'draft_path': 'drafts/SC-A.md'},
                {'id': 'SC-Z', 'episode_id': 'EP-Z', 'order': 1, 'status': 'APPROVED', 'draft_path': 'drafts/SC-Z.md'},
            ]},
        }
        for scene in db['scenes']['scenes']:
            (root / scene['draft_path']).write_text(
                '# Synthetic source metadata fixture, not actual narrative or GitHub approval.\n', encoding='utf-8')
        history = {
            'schema_version': 1,
            'baseline': {'before_scene': 'SC-Z', 'status': 'APPROVED',
                         'evidence_path': 'bible/INITIAL_STATE.md',
                         'state': {'flags': {'gate': False}, 'character': {'location': 'INITIAL_FIXTURE'},
                                   'inventory': {}, 'branch_marker': token}},
            'deltas': [
                {'id': 'DELTA-Z', 'scene_id': 'SC-Z', 'status': 'APPROVED', 'changes': [
                    {'path': ['flags', 'gate'], 'operation': 'SET', 'before_exists': True, 'before': False, 'value': True}]},
                {'id': 'DELTA-A', 'scene_id': 'SC-A', 'status': 'APPROVED', 'changes': [
                    {'path': ['character', 'location'], 'operation': 'SET', 'before_exists': True,
                     'before': 'INITIAL_FIXTURE', 'value': token + '_AFTER_TWO'}]},
                {'id': 'DELTA-B', 'scene_id': 'SC-B', 'status': 'APPROVED', 'changes': [
                    {'path': ['flags', 'gate'], 'operation': 'SET', 'before_exists': True, 'before': True, 'value': False}]},
            ],
        }
        self.write(root / 'data/state_history.json', history)
        return root, db, history

    def replay(self, target='SC-B'):
        self.write(self.root / 'data/state_history.json', self.history)
        return state_replay.replay_before(self.root, target, self.db)

    def scene(self, sid):
        return next(scene for scene in self.db['scenes']['scenes'] if scene['id'] == sid)

    def assert_unknown(self, result):
        self.assertEqual(result['availability'], 'UNKNOWN')
        self.assertNotIn('state', result)
        self.assertNotIn('applied_delta_ids', result)
        self.assertEqual(result['approval_basis'], state_replay.APPROVAL_BASIS)

    def test_absent_history_uses_legacy_fallback_only(self):
        (self.root / 'data/state_history.json').unlink()
        self.assertIsNone(state_replay.replay_before(self.root, 'SC-B', self.db))
        self.assertEqual(state_replay.validate(self.root, self.db), [])

    def test_replay_strict_scene_start_and_episode_order(self):
        before_first = self.replay('SC-Z')
        self.assertEqual(before_first['state']['flags']['gate'], False)
        self.assertEqual(before_first['applied_delta_ids'], [])
        second = self.replay('SC-A')
        self.assertIs(second['state']['flags']['gate'], True)
        self.assertEqual(second['state']['character']['location'], 'INITIAL_FIXTURE')
        third = self.replay('SC-B')
        self.assertEqual(third['state']['character']['location'], 'A_ONLY_AFTER_TWO')
        self.assertIs(third['state']['flags']['gate'], True)
        self.assertEqual(third['applied_delta_ids'], ['DELTA-Z', 'DELTA-A'])
        self.assertEqual(third['as_of_scene'], 'SC-A')
        self.assertEqual(self.replay('EP-A'), third)
        self.assertEqual(self.replay('EP-Z')['applied_delta_ids'], [])

    def test_future_delta_values_and_beforeconditions_are_not_used(self):
        self.history['deltas'][2]['changes'][0].update(before='INCONSISTENT_FUTURE', value='FUTURE_SENTINEL')
        text = json.dumps(self.replay())
        self.assertNotIn('FUTURE_SENTINEL', text)
        self.assertNotIn('INCONSISTENT_FUTURE', text)
        self.assertEqual(state_replay.validate(self.root, self.db), [])

    def test_baseline_cannot_use_future_or_unapproved_scene_evidence(self):
        for status in ('APPROVED', 'PLANNED'):
            with self.subTest(source_status=status):
                self.scene('SC-B')['status'] = status
                self.history['baseline']['evidence_path'] = 'drafts/SC-B.md'
                with self.assertRaisesRegex(ValueError, 'independent state evidence'):
                    self.replay('SC-Z')
                self.assertTrue(any('independent state evidence' in error
                                    for error in state_replay.validate(self.root, self.db)))

    def test_baseline_cannot_alias_scene_source_outside_drafts(self):
        source = 'bible/scene-source.md'
        (self.root / source).write_text('Synthetic scene evidence metadata only.', encoding='utf-8')
        self.scene('SC-B')['draft_path'] = source
        self.history['baseline']['evidence_path'] = source
        with self.assertRaisesRegex(ValueError, 'independent state evidence'):
            self.replay('SC-Z')

    def test_baseline_cannot_reinterpret_live_snapshot_or_ledger_as_earlier_evidence(self):
        for relative in ('data/story_state.json', 'scenes/SC-B.md', 'ledger/index.json'):
            with self.subTest(evidence=relative):
                path = self.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{"approved_through_scene":"SC-B"}', encoding='utf-8')
                self.history['baseline']['evidence_path'] = relative
                with self.assertRaisesRegex(ValueError, 'independent state evidence'):
                    self.replay('SC-Z')

    def test_unapproved_delta_is_excluded_without_partial_state(self):
        self.history['deltas'][1]['status'] = 'PROPOSED'
        self.assert_unknown(self.replay())

    def test_unapproved_scene_is_excluded_even_when_delta_label_is_approved(self):
        self.scene('SC-A')['status'] = 'PLANNED'
        self.assert_unknown(self.replay())

    def test_missing_segment_is_unknown_and_never_skipped(self):
        del self.history['deltas'][0]
        result = self.replay()
        self.assert_unknown(result)
        self.assertIn('SC-Z', result['reason'])

    def test_empty_changes_are_explicit_no_change_evidence(self):
        self.history['deltas'][1]['changes'] = []
        result = self.replay()
        self.assertEqual(result['state']['character']['location'], 'INITIAL_FIXTURE')
        self.assertEqual(result['applied_delta_ids'], ['DELTA-Z', 'DELTA-A'])

    def test_missing_or_proposed_baseline_is_unknown(self):
        original = copy.deepcopy(self.history['baseline'])
        for baseline in (None, {**original, 'status': 'PROPOSED'}):
            with self.subTest(baseline=baseline):
                self.history['baseline'] = baseline
                self.assert_unknown(self.replay())

    def test_later_explicit_baseline_does_not_reconstruct_earlier_state(self):
        self.history['baseline']['before_scene'] = 'SC-A'
        del self.history['deltas'][0]
        self.assert_unknown(self.replay('SC-Z'))
        self.assertEqual(self.replay('SC-A')['applied_delta_ids'], [])

    def test_contradictory_relevant_before_value_fails(self):
        self.history['deltas'][1]['changes'][0]['before'] = 'NOT_THE_BASELINE'
        with self.assertRaisesRegex(ValueError, 'inconsistent before condition'):
            self.replay()

    def test_booleans_cannot_satisfy_numeric_before_values(self):
        self.history['deltas'][0]['changes'][0]['before'] = 0
        with self.assertRaisesRegex(ValueError, 'inconsistent before condition'):
            self.replay()
        self.history['deltas'][0]['changes'][0]['before'] = False
        self.history['baseline']['state']['inventory']['nested'] = {'known': True}
        self.history['deltas'][1]['changes'] = [{
            'path': ['inventory', 'nested'], 'operation': 'SET', 'before_exists': True,
            'before': {'known': 1}, 'value': {},
        }]
        with self.assertRaisesRegex(ValueError, 'inconsistent before condition'):
            self.replay()

    def test_explicit_missing_leaf_set_and_remove(self):
        self.history['deltas'][0]['changes'].append({
            'path': ['inventory', 'fixture_item'], 'operation': 'SET', 'before_exists': False, 'value': None,
        })
        self.history['deltas'][1]['changes'].append({
            'path': ['inventory', 'fixture_item'], 'operation': 'REMOVE', 'before_exists': True, 'before': None,
        })
        self.assertIsNone(self.replay('SC-A')['state']['inventory']['fixture_item'])
        self.assertNotIn('fixture_item', self.replay()['state']['inventory'])

    def test_missing_parents_are_not_invented(self):
        self.history['deltas'][0]['changes'].append({
            'path': ['absent_parent', 'value'], 'operation': 'SET', 'before_exists': False, 'value': 'MUST_NOT_APPEAR',
        })
        with self.assertRaisesRegex(ValueError, 'missing/object parent'):
            self.replay()

    def test_chronological_duplicates_and_unknown_scene_rejected(self):
        original = copy.deepcopy(self.history)
        mutations = [
            lambda h: h['deltas'].reverse(),
            lambda h: h['deltas'].append(copy.deepcopy(h['deltas'][0])),
            lambda h: h['deltas'][0].update(scene_id='SC-MISSING'),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.history = copy.deepcopy(original)
                mutate(self.history)
                self.write(self.root / 'data/state_history.json', self.history)
                self.assertTrue(state_replay.validate(self.root, self.db))
                with self.assertRaises(ValueError):
                    state_replay.replay_before(self.root, 'SC-B', self.db)

    def test_schema_invalid_and_version_mismatch_fail_clearly(self):
        original = copy.deepcopy(self.history)
        mutations = [
            lambda h: h.update(schema_version=2),
            lambda h: h.update(schema_version=True),
            lambda h: h['deltas'][0]['changes'][0].update(path=[]),
            lambda h: h['deltas'][0]['changes'][0].update(before_exists='true'),
            lambda h: h['deltas'][0]['changes'][0].update(operation='GUESS'),
            lambda h: h['deltas'][0]['changes'][0].update(before_exists=False),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.history = copy.deepcopy(original)
                mutate(self.history)
                self.write(self.root / 'data/state_history.json', self.history)
                errors = state_replay.validate(self.root, self.db)
                self.assertTrue(errors)
                self.assertTrue(any('state_history' in error for error in errors), errors)
                with self.assertRaises(ValueError):
                    state_replay.replay_before(self.root, 'SC-B', self.db)

    def test_non_json_numeric_constants_are_rejected(self):
        (self.root / 'data/state_history.json').write_text(
            '{"schema_version":1,"baseline":null,"deltas":[],"bad":NaN}', encoding='utf-8')
        self.assertTrue(any('not valid JSON' in error for error in state_replay.validate(self.root, self.db)))

    def test_local_evidence_must_exist_be_nonblank_and_story_bounded(self):
        source = self.root / self.scene('SC-A')['draft_path']
        source.write_text(' \n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'source evidence'):
            self.replay()
        self.assertTrue(state_replay.validate(self.root, self.db))
        source.write_text('# Synthetic fixture metadata only.\n', encoding='utf-8')
        self.history['baseline']['evidence_path'] = '../branch-b/bible/INITIAL_STATE.md'
        with self.assertRaisesRegex(ValueError, 'escapes selected story'):
            self.replay()

    def test_no_state_or_history_is_mutated_by_replay(self):
        original_db = copy.deepcopy(self.db)
        original_history = copy.deepcopy(self.history)
        result = self.replay()
        result['state']['flags']['gate'] = 'CLIENT_MUTATION'
        self.assertEqual(self.db, original_db)
        self.assertEqual(self.history, original_history)
        self.assertIs(self.replay()['state']['flags']['gate'], True)
        self.assertEqual(json.loads((self.root / 'data/state_history.json').read_text()), original_history)

    def test_story_and_checkout_roots_do_not_share_state(self):
        other_root, other_db, _ = self.fixture('branch-b', 'B_ONLY')
        first = self.replay()
        second = state_replay.replay_before(other_root, 'SC-B', other_db)
        self.assertIn('A_ONLY', json.dumps(first))
        self.assertNotIn('B_ONLY', json.dumps(first))
        self.assertIn('B_ONLY', json.dumps(second))
        self.assertNotIn('A_ONLY', json.dumps(second))
        self.assertEqual(first['approval_basis'], 'LOCAL_RECORDS_NOT_GITHUB_AUTHENTICATED')


if __name__ == '__main__':
    unittest.main()
