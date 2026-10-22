"""Read-only local diagnostics with synthetic metadata, never online approval."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_e2_integration as replay_fixtures
import test_story_roots as story_fixtures
from scripts import doctor


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name)
        self.alpha = story_fixtures.StoryRootTests.fixture(self, 'alpha', 'ALPHA_ONLY')
        self.beta = story_fixtures.StoryRootTests.fixture(self, 'beta', 'BETA_ONLY')
        self.write(self.workspace / 'studio.json', {'schema_version': 1, 'default_story': 'alpha'})

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def add_history(self, root, token='LOCAL_METADATA_ONLY'):
        return replay_fixtures.E2IntegrationTests.add_local_history(self, root, token)

    @staticmethod
    def snapshot(root):
        return {str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob('*') if path.is_file()}

    @staticmethod
    def no_git(command, **kwargs):
        return subprocess.CompletedProcess(command, 128, stdout='', stderr='not a Git repository')

    def diagnose(self, root=None, target=None, **kwargs):
        with patch('scripts.doctor.subprocess.run', side_effect=self.no_git):
            return doctor.diagnose(root or self.alpha, target, **kwargs)

    def assert_online_unchecked(self, result):
        self.assertEqual(result['github']['authentication'], 'NOT_CHECKED')
        self.assertEqual(result['github']['settings'], 'UNKNOWN')
        self.assertEqual(result['github']['security'], 'UNKNOWN')
        self.assertEqual(result['github']['check_status'], 'NOT_CHECKED')
        self.assertEqual(result['github']['approval_provenance'], 'UNKNOWN')
        self.assertEqual(result['github']['codeowners_enforcement'], 'UNKNOWN')

    def test_valid_local_metadata_reports_only_local_validation(self):
        result = self.diagnose()
        json.dumps(result)
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['kind'], 'LOCAL_DOCTOR_REPORT')
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['local_validation_status'], 'PASS')
        self.assertEqual(result['story_slug'], 'alpha')
        self.assertEqual(result['selected_root'], str(self.alpha.resolve()))
        self.assertEqual(result['schema']['status'], 'PASS')
        self.assertEqual(result['schema']['dependencies'], 'AVAILABLE')
        self.assertEqual(result['state']['history'], 'LEGACY')
        self.assertEqual(result['state']['availability'], 'NOT_CHECKED')
        self.assert_online_unchecked(result)

    def test_no_git_is_unknown_without_a_validation_error(self):
        result = self.diagnose()
        self.assertEqual(result['git']['status'], 'UNKNOWN')
        self.assertEqual(result['git']['head'], 'UNKNOWN')
        self.assertEqual(result['git']['selected_root_dirty'], 'UNKNOWN')
        self.assertEqual(result['errors'], [])

    def test_git_head_and_selected_root_dirty_use_only_scoped_read_commands(self):
        head = '1' * 40
        filename = 'PRIVATE_DRAFT_FILENAME_SHOULD_NOT_BE_EMITTED.md'

        def git_read(command, **kwargs):
            expected = ['git', '--no-optional-locks', '--no-lazy-fetch', '-C', str(self.alpha.resolve())]
            self.assertEqual(command[:5], expected)
            if command[5:] == ['rev-parse', '--verify', 'HEAD']:
                return subprocess.CompletedProcess(command, 0, stdout=head + '\n', stderr='')
            self.assertEqual(command[5:], ['status', '--porcelain', '--untracked-files=normal', '--ignore-submodules=all', '--', '.'])
            return subprocess.CompletedProcess(command, 0, stdout='?? ' + filename + '\n', stderr='')

        with patch('scripts.doctor.subprocess.run', side_effect=git_read) as runner:
            result = doctor.diagnose(self.alpha)
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(result['git']['status'], 'KNOWN')
        self.assertEqual(result['git']['head'], head)
        self.assertIs(result['git']['selected_root_dirty'], True)
        self.assertIn('submodule', result['git']['dirty_scope'])
        self.assertNotIn(filename, json.dumps(result))
        self.assert_online_unchecked(result)

    def test_git_environment_cannot_redirect_diagnostics_to_another_repository(self):
        inherited = {
            'GIT_DIR': 'SYNTHETIC_FOREIGN_GIT_DIRECTORY',
            'GIT_WORK_TREE': 'SYNTHETIC_FOREIGN_WORK_TREE',
            'GIT_CONFIG_GLOBAL': 'SYNTHETIC_FOREIGN_CONFIG_PATH',
            'GIT_CONFIG_COUNT': '99',
            'GIT_CONFIG_KEY_42': 'SYNTHETIC_INHERITED_CONFIG_KEY',
            'GIT_CONFIG_VALUE_42': 'SYNTHETIC_INHERITED_CONFIG_VALUE',
        }

        def git_read(command, **kwargs):
            environment = kwargs['env']
            for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_CONFIG_GLOBAL',
                        'GIT_CONFIG_KEY_42', 'GIT_CONFIG_VALUE_42'):
                self.assertNotIn(key, environment)
            self.assertNotEqual(environment.get('GIT_CONFIG_COUNT'), '99')
            self.assertEqual(environment['GIT_OPTIONAL_LOCKS'], '0')
            self.assertEqual(environment['GIT_TERMINAL_PROMPT'], '0')
            self.assertEqual(environment['GIT_NO_LAZY_FETCH'], '1')
            if 'rev-parse' in command:
                return subprocess.CompletedProcess(command, 0, stdout='2' * 40 + '\n', stderr='')
            return subprocess.CompletedProcess(command, 0, stdout='', stderr='')

        with patch.dict('os.environ', inherited), \
                patch('scripts.doctor.subprocess.run', side_effect=git_read) as runner:
            result = doctor.diagnose(self.alpha)
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(result['git']['head'], '2' * 40)
        self.assertIs(result['git']['selected_root_dirty'], False)

    def test_invalid_story_configuration_and_selector_are_structured_errors(self):
        (self.alpha / 'story.json').write_text('{ broken JSON', encoding='utf-8')
        for kwargs in ({}, {'story': '../beta'}, {'story': 'missing'}):
            with self.subTest(selector=kwargs):
                result = self.diagnose(self.workspace, **kwargs)
                self.assertTrue(result['errors'])
                self.assertNotEqual(result['local_validation_status'], 'PASS')
                self.assert_online_unchecked(result)

    def test_missing_story_root_is_a_structured_error(self):
        result = self.diagnose(self.workspace / 'missing')
        self.assertTrue(result['errors'])
        self.assertNotEqual(result['local_validation_status'], 'PASS')
        self.assertEqual(result['story_slug'], 'UNKNOWN')

    def test_malformed_registry_and_missing_file_fail_without_traceback(self):
        path = self.alpha / 'data/scenes.json'
        for malformed in ('{ broken JSON', '{"schema_version": 1, "scenes": null}'):
            with self.subTest(malformed=malformed):
                path.write_text(malformed, encoding='utf-8')
                result = self.diagnose(target='SC-002')
                self.assertTrue(result['errors'])
                self.assertEqual(result['local_validation_status'], 'FAIL')
                self.assertEqual(result['state']['availability'], 'ERROR')
        path.unlink()
        result = self.diagnose()
        self.assertTrue(result['errors'])
        self.assertEqual(result['local_validation_status'], 'FAIL')

    def test_missing_dependency_is_actionable_and_does_not_claim_validation(self):
        message = 'JSON Schema dependency unavailable; run python -m pip install -r requirements.txt'
        with patch('scripts.doctor.registry_schema._dependencies', side_effect=ValueError(message)):
            result = self.diagnose(target='SC-001')
        self.assertEqual(result['schema']['status'], 'ERROR')
        self.assertEqual(result['schema']['dependencies'], 'ERROR')
        self.assertNotEqual(result['local_validation_status'], 'PASS')
        self.assertIn('pip install -r requirements.txt', json.dumps(result))
        self.assertTrue(result['errors'])

    def test_malformed_history_is_present_and_reported_as_error(self):
        (self.alpha / 'data/state_history.json').write_text('{"schema_version": 2}', encoding='utf-8')
        result = self.diagnose(target='SC-002')
        self.assertEqual(result['state']['history'], 'PRESENT')
        self.assertEqual(result['state']['availability'], 'ERROR')
        self.assertTrue(any('state_history' in error for error in result['errors']))
        self.assertEqual(result['local_validation_status'], 'FAIL')

    def test_legacy_initial_baseline_is_known_but_not_authenticated(self):
        result = self.diagnose(target='SC-002')
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['state']['history'], 'LEGACY')
        self.assertEqual(result['state']['availability'], 'KNOWN')
        self.assertEqual(result['state']['approval_basis'], 'LOCAL_RECORDS_NOT_GITHUB_AUTHENTICATED')
        self.assert_online_unchecked(result)

    def test_missing_approved_history_segment_stays_unknown_without_partial_state(self):
        history = self.add_history(self.alpha)
        history['deltas'][1]['status'] = 'PROPOSED'
        self.write(self.alpha / 'data/state_history.json', history)
        # UNKNOWN context is permissible only without a causal prerequisite
        # that needs the unavailable preceding segment's approved state.
        scenes = self.read(self.alpha / 'data/scenes.json')
        scenes['scenes'][2]['requires_flags'] = []
        self.write(self.alpha / 'data/scenes.json', scenes)
        result = self.diagnose(target='SC-003')
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['local_validation_status'], 'PASS')
        self.assertEqual(result['state']['availability'], 'UNKNOWN')
        self.assertNotIn('state', result['state'])
        self.assertNotIn('applied_delta_ids', result['state'])
        self.assert_online_unchecked(result)

    def test_missing_history_required_by_a_prerequisite_reports_error_without_false_pass(self):
        history = self.add_history(self.alpha)
        history['deltas'][1]['status'] = 'PROPOSED'
        self.write(self.alpha / 'data/state_history.json', history)
        scenes = self.read(self.alpha / 'data/scenes.json')
        self.assertIn('stage_2', scenes['scenes'][2]['requires_flags'])
        before = self.snapshot(self.workspace)
        result = self.diagnose(target='SC-003')
        self.assertEqual(result['local_validation_status'], 'FAIL')
        self.assertEqual(result['state']['history'], 'PRESENT')
        self.assertEqual(result['state']['availability'], 'ERROR')
        self.assertTrue(any("SC-003: needs flag 'stage_2'" in error
                            for error in result['errors']), result['errors'])
        self.assertTrue(any('UNKNOWN' in error for error in result['errors']), result['errors'])
        self.assertNotIn('state', result['state'])
        self.assertNotIn('applied_delta_ids', result['state'])
        self.assertEqual(self.snapshot(self.workspace), before)
        self.assert_online_unchecked(result)

    def test_contradictory_history_and_unknown_target_report_errors(self):
        history = self.add_history(self.alpha)
        history['deltas'][0]['changes'][0]['before'] = 'CONTRADICTORY_SYNTHETIC_METADATA'
        self.write(self.alpha / 'data/state_history.json', history)
        for target in ('SC-002', 'SC-MISSING'):
            with self.subTest(target=target):
                result = self.diagnose(target=target)
                self.assertEqual(result['state']['availability'], 'ERROR')
                self.assertTrue(result['errors'])

    def test_known_history_does_not_emit_state_payload_or_source_content(self):
        token = 'SYNTHETIC_STATE_CONTENT_SHOULD_NOT_BE_EMITTED'
        self.add_history(self.alpha, token)
        result = self.diagnose(target='SC-003')
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['state']['availability'], 'KNOWN')
        self.assertNotIn(token, json.dumps(result))
        self.assertNotIn('state', result['state'])
        self.assert_online_unchecked(result)

    def test_two_stories_are_selected_independently_without_fallback(self):
        (self.alpha / 'data/scenes.json').write_text('[]', encoding='utf-8')
        alpha = self.diagnose(self.workspace, story='alpha')
        beta = self.diagnose(self.workspace, story='beta')
        self.assertEqual(alpha['story_slug'], 'alpha')
        self.assertEqual(alpha['local_validation_status'], 'FAIL')
        self.assertEqual(beta['story_slug'], 'beta')
        self.assertEqual(beta['selected_root'], str(self.beta.resolve()))
        self.assertEqual(beta['local_validation_status'], 'PASS')
        self.assertEqual(beta['errors'], [])
        self.assertNotIn('ALPHA_ONLY', json.dumps(beta))

    def test_repeated_diagnostics_are_identical_and_do_not_write_or_use_network(self):
        before = self.snapshot(self.workspace)
        with patch('pathlib.Path.write_text', side_effect=AssertionError('doctor attempted a write')), \
                patch('pathlib.Path.write_bytes', side_effect=AssertionError('doctor attempted a write')), \
                patch('pathlib.Path.mkdir', side_effect=AssertionError('doctor attempted mkdir')), \
                patch('pathlib.Path.rename', side_effect=AssertionError('doctor attempted rename')), \
                patch('pathlib.Path.unlink', side_effect=AssertionError('doctor attempted unlink')), \
                patch('urllib.request.urlopen') as opener, \
                patch('socket.create_connection') as connection:
            first = self.diagnose(target='SC-002')
            second = self.diagnose(target='SC-002')
        self.assertEqual(first, second)
        self.assertEqual(before, self.snapshot(self.workspace))
        opener.assert_not_called()
        connection.assert_not_called()


if __name__ == '__main__':
    unittest.main()
