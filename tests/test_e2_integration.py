"""End-to-end E2 commands using synthetic metadata, never real approval/prose."""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_story_roots as story_roots
from scripts import novelctl, state_replay, story_engine


ENGINE_ROOT = Path(__file__).resolve().parents[1]
STATE_HEADING = '## APPROVED WORLD STATE BEFORE TARGET (INITIAL BASELINE IF NO PROSE APPROVED)'


class E2IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.alpha = story_roots.StoryRootTests.fixture(self, 'alpha', 'ALPHA_ONLY')
        self.beta = story_roots.StoryRootTests.fixture(self, 'beta', 'BETA_ONLY')
        self.write(self.workspace / 'studio.json', {'schema_version': 1, 'default_story': 'alpha'})
        self.history = self.add_local_history(self.alpha, 'ALPHA_HISTORY')

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def run_cli(self, script, *args):
        return subprocess.run(
            [sys.executable, str(ENGINE_ROOT / 'scripts' / script), *map(str, args)],
            cwd=self.workspace, env=dict(os.environ, PYTHONIOENCODING='utf-8'),
            capture_output=True, text=True, encoding='utf-8', timeout=30,
        )

    def add_local_history(self, root, token):
        """Local fixture labels supply test evidence, not authenticated review."""
        scenes = self.read(root / 'data/scenes.json')
        for scene in scenes['scenes'][:2]:
            scene['status'] = 'APPROVED'
            source = root / scene['draft_path']
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(
                '# Synthetic source metadata fixture\n'
                'Local APPROVED label is only test input; no narrative or human review.\n',
                encoding='utf-8',
            )
        self.write(root / 'data/scenes.json', scenes)
        snapshot = self.read(root / 'data/story_state.json')
        snapshot.update(approved_through_scene='SC-002', phase='LOCAL_FIXTURE_STATE')
        self.write(root / 'data/story_state.json', snapshot)
        (root / 'bible/INITIAL_STATE.md').write_text(
            '# Synthetic baseline metadata fixture; no real approval.\n', encoding='utf-8')
        history = {
            'schema_version': 1,
            'baseline': {
                'before_scene': 'SC-001', 'status': 'APPROVED',
                'evidence_path': 'bible/INITIAL_STATE.md',
                'state': {'fixture_owner': token, 'location': token + '_INITIAL',
                          'flags': {'gate': False}},
            },
            'deltas': [
                {'id': 'DELTA-001', 'scene_id': 'SC-001', 'status': 'APPROVED', 'changes': [
                    {'path': ['location'], 'operation': 'SET', 'before_exists': True,
                     'before': token + '_INITIAL', 'value': token + '_AFTER_FIRST'},
                    {'path': ['flags', 'gate'], 'operation': 'SET', 'before_exists': True,
                     'before': False, 'value': True},
                    {'path': ['flags', 'stage_1'], 'operation': 'SET',
                     'before_exists': False, 'value': True},
                ]},
                {'id': 'DELTA-002', 'scene_id': 'SC-002', 'status': 'APPROVED', 'changes': [
                    {'path': ['location'], 'operation': 'SET', 'before_exists': True,
                     'before': token + '_AFTER_FIRST', 'value': token + '_AFTER_SECOND'},
                    {'path': ['flags', 'stage_2'], 'operation': 'SET',
                     'before_exists': False, 'value': True},
                ]},
                {'id': 'DELTA-003', 'scene_id': 'SC-003', 'status': 'APPROVED', 'changes': [
                    {'path': ['location'], 'operation': 'SET', 'before_exists': True,
                     'before': 'CONFLICTING_FUTURE_PRECONDITION', 'value': token + '_FUTURE'},
                ]},
            ],
        }
        self.write(root / 'data/state_history.json', history)
        return history

    @staticmethod
    def packed_state(text):
        section = text.split(STATE_HEADING + '\n\n', 1)[1].split('\n\n## OPEN ISSUES', 1)[0]
        return json.loads(section.split('\n\n', 1)[1])

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stdout + result.stderr)

    def assert_failed_output(self, result, output, diagnostic):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        combined = result.stdout + result.stderr
        self.assertIn(diagnostic, combined)
        self.assertIn('ERROR:', combined)
        self.assertNotIn('Traceback', combined)
        self.assertFalse(output.exists(), combined)

    def test_pack_brief_and_replay_cli_share_strict_scene_start_state(self):
        self.assertEqual(novelctl.validate(self.alpha)[0], [])
        self.assertEqual(story_engine.validate(self.alpha)[0], [])
        for target, location, applied in (
            ('SC-002', 'ALPHA_HISTORY_AFTER_FIRST', ['DELTA-001']),
            ('SC-003', 'ALPHA_HISTORY_AFTER_SECOND', ['DELTA-001', 'DELTA-002']),
        ):
            with self.subTest(target=target):
                pack = story_engine.pack(self.alpha, target)
                state = self.packed_state(pack)
                self.assertEqual(state['availability'], 'KNOWN')
                self.assertEqual(state['state']['location'], location)
                self.assertIs(state['state']['flags']['gate'], True)
                self.assertEqual(state['applied_delta_ids'], applied)
                self.assertEqual(state['approval_basis'], state_replay.APPROVAL_BASIS)
                self.assertEqual(self.packed_state(novelctl.build_brief(self.alpha, target)), state)
                self.assertNotIn('ALPHA_HISTORY_FUTURE', pack)
                self.assertNotIn('CONFLICTING_FUTURE_PRECONDITION', pack)
                replay_out = self.workspace / (target + '.json')
                result = self.run_cli('storyctl.py', '--workspace', self.workspace, '--story',
                                      'alpha', 'replay', target, '--out', replay_out)
                self.assert_success(result)
                self.assertEqual(self.read(replay_out), state)
                pack_out = self.workspace / (target + '.md')
                result = self.run_cli('storyctl.py', '--workspace', self.workspace, '--story',
                                      'alpha', 'pack', target, '--out', pack_out)
                self.assert_success(result)
                self.assertEqual(self.packed_state(pack_out.read_text(encoding='utf-8')), state)

    def test_unapproved_or_missing_prior_segment_yields_unknown_without_partial_state(self):
        original_scenes = self.read(self.alpha / 'data/scenes.json')
        # This case exercises UNKNOWN context, without a prerequisite that
        # would independently require known approved pre-scene state.
        original_scenes['scenes'][2]['requires_flags'] = []
        for mode in ('proposed_delta', 'unapproved_source', 'missing_segment'):
            with self.subTest(mode=mode):
                history = copy.deepcopy(self.history)
                scenes = copy.deepcopy(original_scenes)
                snapshot = self.read(self.alpha / 'data/story_state.json')
                snapshot['approved_through_scene'] = 'SC-002'
                if mode == 'proposed_delta':
                    history['deltas'][1]['status'] = 'PROPOSED'
                elif mode == 'unapproved_source':
                    scenes['scenes'][1]['status'] = 'PLANNED'
                    snapshot['approved_through_scene'] = 'SC-001'
                else:
                    del history['deltas'][1]
                self.write(self.alpha / 'data/state_history.json', history)
                self.write(self.alpha / 'data/scenes.json', scenes)
                self.write(self.alpha / 'data/story_state.json', snapshot)
                pack = story_engine.pack(self.alpha, 'SC-003')
                state = self.packed_state(pack)
                self.assertEqual(state['availability'], 'UNKNOWN')
                self.assertNotIn('state', state)
                self.assertNotIn('applied_delta_ids', state)
                self.assertIsNone(state['as_of_scene'])
                self.assertNotIn('ALPHA_HISTORY', pack)
                replay_out = self.workspace / (mode + '.json')
                result = self.run_cli('storyctl.py', '--workspace', self.alpha, 'replay',
                                      'SC-003', '--out', replay_out)
                self.assert_success(result)
                self.assertEqual(self.read(replay_out), state)

    def causal_fixture(self, target='SC-001', snapshot_gate=True, baseline_gate=False):
        """Isolate one gate prerequisite from generic stage-plan dependencies."""
        scenes = self.read(self.alpha / 'data/scenes.json')
        events = self.read(self.alpha / 'data/events.json')
        for scene in scenes['scenes']:
            scene['requires_flags'] = ['gate'] if scene['id'] == target else []
            scene['effects_flags'] = {}
        for event in events['events']:
            event['effects_flags'] = {}
        self.write(self.alpha / 'data/scenes.json', scenes)
        self.write(self.alpha / 'data/events.json', events)
        snapshot = self.read(self.alpha / 'data/story_state.json')
        snapshot.update(active_episode='EP-001', flags={'gate': snapshot_gate})
        self.write(self.alpha / 'data/story_state.json', snapshot)
        history = copy.deepcopy(self.history)
        history['baseline']['state']['flags']['gate'] = baseline_gate
        history['deltas'][0]['changes'][1]['before'] = baseline_gate
        self.write(self.alpha / 'data/state_history.json', history)
        return history, scenes, events

    def assert_gate_unestablished(self, scene_id):
        errors, _ = novelctl.validate(self.alpha)
        self.assertTrue(any(scene_id + ": needs flag 'gate'" in error for error in errors), errors)
        return errors

    def causal_state(self, target):
        # Inspect eligible history itself even when its prerequisite correctly
        # makes the full registry invalid; state_before_target fails closed.
        return state_replay.replay_before(self.alpha, target, novelctl.load(self.alpha))

    def test_active_latest_snapshot_cannot_satisfy_first_scene_before_baseline_gate(self):
        self.causal_fixture(snapshot_gate=True, baseline_gate=False)
        self.assertIs(self.causal_state('SC-001')['state']['flags']['gate'], False)
        self.assert_gate_unestablished('SC-001')
        self.assertTrue(any("SC-001: needs flag 'gate'" in error
                            for error in story_engine.validate(self.alpha)[0]))
        checked = self.run_cli('storyctl.py', '--workspace', self.alpha, 'check')
        self.assertNotEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertIn("SC-001: needs flag 'gate'", checked.stdout + checked.stderr)
        output = self.workspace / 'causal-invalid/must-not-exist.md'
        packed = self.run_cli('storyctl.py', '--workspace', self.alpha,
                              'pack', 'SC-001', '--out', output)
        self.assert_failed_output(packed, output, "SC-001: needs flag 'gate'")
        self.assertFalse(output.parent.exists())

    def test_approved_baseline_can_satisfy_first_scene_despite_false_latest_snapshot(self):
        self.causal_fixture(snapshot_gate=False, baseline_gate=True)
        self.assertEqual(novelctl.validate(self.alpha)[0], [])
        self.assertEqual(story_engine.validate(self.alpha)[0], [])
        state = self.packed_state(story_engine.pack(self.alpha, 'SC-001'))
        self.assertIs(state['state']['flags']['gate'], True)

    def test_prior_eligible_delta_satisfies_later_scene_despite_false_snapshot(self):
        self.causal_fixture('SC-002', snapshot_gate=False)
        self.assertEqual(novelctl.validate(self.alpha)[0], [])
        state = novelctl.state_before_target(self.alpha, 'SC-002')
        self.assertIs(state['state']['flags']['gate'], True)
        self.assertEqual(state['applied_delta_ids'], ['DELTA-001'])
        self.assertEqual(story_engine.validate(self.alpha)[0], [])

    def test_same_scene_or_future_approved_delta_cannot_establish_earlier_prerequisite(self):
        history, _, _ = self.causal_fixture(snapshot_gate=False)
        self.assert_gate_unestablished('SC-001')
        gate_change = history['deltas'][0]['changes'].pop(1)
        history['deltas'][1]['changes'].append(gate_change)
        self.write(self.alpha / 'data/state_history.json', history)
        self.assert_gate_unestablished('SC-001')

    def test_unapproved_source_or_proposed_delta_cannot_satisfy_later_prerequisite(self):
        original_history, original_scenes, _ = self.causal_fixture('SC-002', snapshot_gate=True)
        for mode in ('proposed_delta', 'planned_source', 'draft_source'):
            with self.subTest(mode=mode):
                history, scenes = copy.deepcopy(original_history), copy.deepcopy(original_scenes)
                if mode == 'proposed_delta':
                    history['deltas'][0]['status'] = 'PROPOSED'
                else:
                    scenes['scenes'][0]['status'] = 'PLANNED' if mode == 'planned_source' else 'DRAFT'
                self.write(self.alpha / 'data/state_history.json', history)
                self.write(self.alpha / 'data/scenes.json', scenes)
                self.assertEqual(self.causal_state('SC-002')['availability'], 'UNKNOWN')
                errors = self.assert_gate_unestablished('SC-002')
                self.assertTrue(any('state history' in error.lower() or 'unknown' in error.lower()
                                    for error in errors), errors)

    def test_planned_effect_cannot_replace_explicit_no_change_approved_delta(self):
        history, scenes, events = self.causal_fixture('SC-002', snapshot_gate=True)
        history['deltas'][0]['changes'].pop(1)
        scenes['scenes'][0]['effects_flags'] = {'gate': True}
        events['events'][0]['effects_flags'] = {'gate': True}
        self.write(self.alpha / 'data/state_history.json', history)
        self.write(self.alpha / 'data/scenes.json', scenes)
        self.write(self.alpha / 'data/events.json', events)
        self.assertIs(self.causal_state('SC-002')['state']['flags']['gate'], False)
        self.assert_gate_unestablished('SC-002')

    def test_unknown_history_or_absent_flags_never_fall_back_to_latest_true_snapshot(self):
        original_history, _, _ = self.causal_fixture(snapshot_gate=True)
        for mode in ('absent_baseline', 'proposed_baseline', 'missing_flags', 'missing_gate',
                     'numeric_gate', 'text_gate', 'null_gate'):
            with self.subTest(mode=mode):
                history = copy.deepcopy(original_history)
                if mode == 'absent_baseline':
                    history['baseline'] = None
                elif mode == 'proposed_baseline':
                    history['baseline']['status'] = 'PROPOSED'
                elif mode == 'missing_flags':
                    del history['baseline']['state']['flags']
                elif mode == 'missing_gate':
                    del history['baseline']['state']['flags']['gate']
                else:
                    history['baseline']['state']['flags']['gate'] = {
                        'numeric_gate': 1, 'text_gate': 'true', 'null_gate': None}[mode]
                self.write(self.alpha / 'data/state_history.json', history)
                self.assert_gate_unestablished('SC-001')

    def test_no_history_retains_legacy_snapshot_and_planned_effect_semantics(self):
        _, scenes, events = self.causal_fixture(snapshot_gate=True)
        (self.alpha / 'data/state_history.json').unlink()
        self.assertEqual(novelctl.validate(self.alpha)[0], [])
        snapshot = self.read(self.alpha / 'data/story_state.json')
        snapshot['flags']['gate'] = False
        self.write(self.alpha / 'data/story_state.json', snapshot)
        self.assert_gate_unestablished('SC-001')
        scenes['scenes'][0]['requires_flags'] = []
        scenes['scenes'][0]['effects_flags'] = {'gate': True}
        scenes['scenes'][1]['requires_flags'] = ['gate']
        events['events'][0]['effects_flags'] = {'gate': True}
        self.write(self.alpha / 'data/scenes.json', scenes)
        self.write(self.alpha / 'data/events.json', events)
        self.assertEqual(novelctl.validate(self.alpha)[0], [])

    def test_conflicting_before_values_fail_without_output_artifacts(self):
        self.history['deltas'][1]['changes'][0]['before'] = 'CONFLICTING_PRIOR_VALUE'
        self.write(self.alpha / 'data/state_history.json', self.history)
        for script, root_flag, command in (
            ('storyctl.py', '--workspace', 'pack'),
            ('storyctl.py', '--workspace', 'replay'),
            ('story_engine.py', '--root', 'pack'),
            ('novelctl.py', '--root', 'brief'),
        ):
            with self.subTest(script=script, command=command):
                output = self.workspace / (script + '-' + command) / 'must-not-exist.md'
                result = self.run_cli(script, root_flag, self.alpha, command,
                                      'SC-003', '--out', output)
                self.assert_failed_output(result, output, 'inconsistent before condition')
                self.assertFalse(output.parent.exists())

    def test_malformed_history_and_registry_block_check_and_pack_cleanly(self):
        paths = {'history': self.alpha / 'data/state_history.json',
                 'scenes': self.alpha / 'data/scenes.json'}
        originals = {name: path.read_text(encoding='utf-8') for name, path in paths.items()}
        cases = [
            ('history', '{ malformed JSON', 'state_history.json'),
            ('history', {**self.history, 'schema_version': 2}, 'schema_version'),
            ('history', {**self.history, 'deltas': 'not a list'}, 'deltas'),
            ('scenes', {'schema_version': 1, 'scenes': [{'id': 'SC-001'}]}, 'scenes.json'),
        ]
        for number, (kind, malformed, diagnostic) in enumerate(cases):
            with self.subTest(kind=kind, case=number):
                for name, original in originals.items():
                    paths[name].write_text(original, encoding='utf-8')
                if isinstance(malformed, str):
                    paths[kind].write_text(malformed, encoding='utf-8')
                else:
                    self.write(paths[kind], malformed)
                result = self.run_cli('storyctl.py', '--workspace', self.alpha, 'check')
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('FAIL', result.stdout)
                self.assertIn(diagnostic, result.stdout + result.stderr)
                self.assertNotIn('Traceback', result.stdout + result.stderr)
                output = self.workspace / f'invalid-{number}.md'
                result = self.run_cli('storyctl.py', '--workspace', self.alpha,
                                      'pack', 'SC-003', '--out', output)
                self.assert_failed_output(result, output, diagnostic)

    def test_replay_cli_rejects_invalid_registry_chronology_without_output(self):
        scenes = self.read(self.alpha / 'data/scenes.json')
        episodes = self.read(self.alpha / 'data/episodes.json')
        for mode in ('duplicate_scene_order', 'episode_scene_mismatch'):
            with self.subTest(mode=mode):
                current_scenes, current_episodes = copy.deepcopy(scenes), copy.deepcopy(episodes)
                if mode == 'duplicate_scene_order':
                    current_scenes['scenes'][1]['order'] = 1
                else:
                    current_episodes['episodes'][0]['scene_ids'] = ['SC-001', 'SC-003']
                self.write(self.alpha / 'data/scenes.json', current_scenes)
                self.write(self.alpha / 'data/episodes.json', current_episodes)
                output = self.workspace / (mode + '.json')
                result = self.run_cli('storyctl.py', '--workspace', self.alpha, 'replay',
                                      'SC-003', '--out', output)
                self.assert_failed_output(result, output, 'Cannot replay invalid registry')

    def test_two_stories_and_same_slug_branch_copy_keep_replayed_state_isolated(self):
        self.add_local_history(self.beta, 'BETA_HISTORY')
        branch = self.workspace / 'branches/alpha'
        shutil.copytree(self.alpha, branch)
        branch_history = self.read(branch / 'data/state_history.json')
        branch_history['baseline']['state']['fixture_owner'] = 'BRANCH_HISTORY'
        branch_history['deltas'][0]['changes'][0]['value'] = 'BRANCH_HISTORY_AFTER_FIRST'
        branch_history['deltas'][1]['changes'][0]['before'] = 'BRANCH_HISTORY_AFTER_FIRST'
        self.write(branch / 'data/state_history.json', branch_history)
        for root, own, foreign in (
            (self.alpha, 'ALPHA_HISTORY', ('BETA_HISTORY', 'BRANCH_HISTORY')),
            (self.beta, 'BETA_HISTORY', ('ALPHA_HISTORY', 'BRANCH_HISTORY')),
            (branch, 'BRANCH_HISTORY', ('ALPHA_HISTORY', 'BETA_HISTORY')),
        ):
            with self.subTest(root=root):
                self.assertEqual(story_engine.validate(root)[0], [])
                state = self.packed_state(story_engine.pack(root, 'SC-002'))
                self.assertEqual(state['state']['fixture_owner'], own)
                self.assertEqual(state['state']['location'], own + '_AFTER_FIRST')
                for sentinel in foreign:
                    self.assertNotIn(sentinel, json.dumps(state))
                output = self.workspace / (own + '.json')
                result = self.run_cli('storyctl.py', '--workspace', root, 'replay',
                                      'SC-002', '--out', output)
                self.assert_success(result)
                self.assertEqual(self.read(output), state)
        self.assertEqual(self.read(self.alpha / 'story.json')['slug'],
                         self.read(branch / 'story.json')['slug'])

    def test_absent_history_preserves_legacy_snapshot_and_earlier_unknown_paths(self):
        (self.alpha / 'data/state_history.json').unlink()
        snapshot = self.read(self.alpha / 'data/story_state.json')
        pack = story_engine.pack(self.alpha, 'SC-003')
        self.assertEqual(self.packed_state(pack), snapshot)
        self.assertNotIn('ALPHA_HISTORY', pack)
        self.assertNotIn('approval_basis', self.packed_state(pack))
        for target in ('SC-003', 'SC-002'):
            with self.subTest(target=target):
                output = self.workspace / ('legacy-' + target + '.json')
                result = self.run_cli('storyctl.py', '--workspace', self.alpha, 'replay',
                                      target, '--out', output)
                self.assert_success(result)
                state = self.read(output)
                if target == 'SC-003':
                    self.assertEqual(state, snapshot)
                else:
                    self.assertEqual(state['availability'], 'UNKNOWN')
                    self.assertNotIn('fixture_metadata', state)
                    self.assertNotIn('state', state)
        output = self.workspace / 'legacy-engine-pack.md'
        result = self.run_cli('story_engine.py', '--root', self.alpha, 'pack',
                              'SC-003', '--out', output)
        self.assert_success(result)
        self.assertEqual(self.packed_state(output.read_text(encoding='utf-8')), snapshot)


if __name__ == '__main__':
    unittest.main()
