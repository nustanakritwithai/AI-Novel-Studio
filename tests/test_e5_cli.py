"""E5 CLI boundaries using supplied synthetic evidence; never real network."""
import contextlib
import copy
import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_provenance as provenance_fixtures
import test_rollup as rollup_fixtures
from scripts import storyctl


ENGINE_ROOT = Path(__file__).resolve().parents[1]


class E5CliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name).resolve()
        self.root = rollup_fixtures.RollupTests.fixture(self, 'alpha')
        self.beta = rollup_fixtures.RollupTests.fixture(self, 'beta')
        self.write(self.workspace / 'studio.json', {'schema_version': 1, 'default_story': 'alpha'})
        (self.workspace / '.gitignore').write_bytes((ENGINE_ROOT / '.gitignore').read_bytes())
        self.cache = self.workspace / '.local/offline-evidence.json'
        self.cache.parent.mkdir()
        self.evidence = provenance_fixtures.make_evidence()
        self.write(self.cache, self.evidence)

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    @staticmethod
    def digest(value):
        return hashlib.sha256(value).hexdigest()

    def snapshot(self):
        return {path.relative_to(self.workspace).as_posix(): path.read_bytes()
                for path in self.workspace.rglob('*') if path.is_file()
                and '.local' not in path.relative_to(self.workspace).parts}

    def verify_args(self, repository_flag='--repository', **changes):
        values = {
            'repository': provenance_fixtures.REPOSITORY,
            'pr_number': provenance_fixtures.PR_NUMBER,
            'head_commit': provenance_fixtures.HEAD_COMMIT,
            'merge_commit': provenance_fixtures.MERGE_COMMIT,
            'source_path': provenance_fixtures.SOURCE_PATH,
            'source_sha256': self.digest(provenance_fixtures.SOURCE_BYTES),
            'evidence': self.cache,
        }
        values.update(changes)
        args = ['verify-provenance', repository_flag, values['repository'],
                '--pr', str(values['pr_number']), '--head', values['head_commit'],
                '--merge', values['merge_commit']]
        if values['source_path'] is not None:
            args += ['--source', values['source_path']]
        if values['source_sha256'] is not None:
            args += ['--sha256', values['source_sha256']]
        if values['evidence'] is not None:
            args += ['--evidence', str(values['evidence'])]
        return args

    def cli(self, *args, story=None):
        """Exercise the actual parser/handler with every transport denied."""
        selected = ['--workspace', str(self.workspace)]
        if story is not None:
            selected += ['--story', story]
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr), \
                patch('scripts.provenance.subprocess.run', side_effect=AssertionError('CLI attempted a subprocess')) as process, \
                patch('scripts.provenance.subprocess.Popen', side_effect=AssertionError('CLI attempted a process')) as popen, \
                patch('scripts.provenance._gh_get', side_effect=AssertionError('CLI attempted GitHub')) as github, \
                patch('urllib.request.urlopen', side_effect=AssertionError('CLI attempted HTTP')) as http, \
                patch('socket.create_connection', side_effect=AssertionError('CLI attempted a socket')) as connection:
            try:
                code = storyctl.main(selected + list(map(str, args)))
            except SystemExit as exc:
                code = exc.code
        process.assert_not_called()
        popen.assert_not_called()
        github.assert_not_called()
        http.assert_not_called()
        connection.assert_not_called()
        result = subprocess.CompletedProcess(args, code, stdout.getvalue(), stderr.getvalue())
        self.assertNotIn('Traceback', result.stdout + result.stderr)
        return result

    def test_valid_offline_verification_is_explicitly_unverified_exit_two(self):
        before = self.snapshot()
        for flag in ('--repository', '--repo'):
            with self.subTest(repository_flag=flag):
                result = self.cli(*self.verify_args(repository_flag=flag))
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report['status'], 'OFFLINE_UNVERIFIED')
                self.assertEqual(report['errors'], [])
                self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')
                self.assertEqual(report['transport']['mode'], 'OFFLINE_SUPPLIED_EVIDENCE')
                self.assertIs(report['transport']['network_attempted'], False)
                self.assertEqual(report['offline_input']['authenticity'], 'UNVERIFIED_OFFLINE_INPUT')
                self.assertEqual(report['offline_input']['sha256'], self.digest(self.cache.read_bytes()))
        self.assertEqual(self.snapshot(), before)

    def test_offline_self_claims_cannot_turn_into_observed_live_success(self):
        self.evidence.update(status='OBSERVED_MERGED_METADATA', authenticated=True,
                             human_editorial_approval='VERIFIED',
                             transport={'mode': 'LIVE_GITHUB_API', 'network_attempted': True})
        self.write(self.cache, self.evidence)
        result = self.cli(*self.verify_args())
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertNotEqual(report['status'], 'OBSERVED_MERGED_METADATA')
        self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')
        self.assertIs(report['transport']['network_attempted'], False)

    def test_mocked_backend_status_controls_exit_code_without_any_transport(self):
        # This only tests handler routing. No GitHub observation is claimed.
        for status, errors, expected in (
                ('OBSERVED_MERGED_METADATA', [], 0), ('OFFLINE_UNVERIFIED', [], 2),
                ('OBSERVED_MERGED_METADATA', ['Synthetic backend failure'], 1)):
            with self.subTest(status=status, errors=errors):
                mocked_report = {'status': status, 'errors': errors,
                                 'human_editorial_approval': 'UNVERIFIED'}
                with patch('scripts.storyctl.provenance.verify', return_value=mocked_report) as verifier:
                    result = self.cli(*self.verify_args(evidence=None))
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                verifier.assert_called_once()
                self.assertIsNone(verifier.call_args.kwargs['offline_evidence'])
                self.assertEqual(json.loads(result.stdout)['human_editorial_approval'], 'UNVERIFIED')

    def test_verify_rejects_misleading_story_selector(self):
        out = self.workspace / '.local/failure/selector.json'
        result = self.cli(*self.verify_args(), '--out', out, story='alpha')
        self.assertEqual(result.returncode, 1)
        self.assertIn('--story', result.stderr)
        self.assertFalse(out.exists())
        self.assertFalse(out.parent.exists())

    def test_invalid_requested_identity_or_digest_cannot_pass(self):
        mutations = [
            {'repository': 'another-owner/another-studio'},
            {'pr_number': provenance_fixtures.PR_NUMBER + 1},
            {'head_commit': 'f' * 40}, {'merge_commit': 'e' * 40},
            {'source_sha256': '0' * 64}, {'source_path': '../other/source.md'},
            {'source_sha256': None}, {'pr_number': 0},
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                result = self.cli(*self.verify_args(**mutation))
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                if result.stdout.strip():
                    report = json.loads(result.stdout)
                    self.assertTrue(report['errors'])
                    self.assertNotEqual(report['status'], 'OBSERVED_MERGED_METADATA')

    def test_bad_or_missing_offline_evidence_fails_before_artifacts(self):
        out = self.workspace / '.local/failed-input/report.json'
        invalid = [b'{ malformed JSON', b'[]', b'{"x":1,"x":2}',
                   b'{"x":NaN}', b'\xff\xfe', b' ' * (8 * 1024 * 1024 + 1)]
        for number, content in enumerate(invalid):
            with self.subTest(case=number):
                self.cache.write_bytes(content)
                result = self.cli(*self.verify_args(), '--out', out)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertFalse(out.exists())
                self.assertFalse(out.parent.exists())
        result = self.cli(*self.verify_args(evidence=self.workspace / 'missing-evidence.json'), '--out', out)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(out.parent.exists())

        # Decoder depth limits vary by Python/dependency runtime. A valid deep
        # object may reach structural verification, which may emit a failure
        # report; either path must fail cleanly and stay unverified.
        deep = b'{"x":' + b'[' * 10000 + b'0' + b']' * 10000 + b'}'
        self.cache.write_bytes(deep)
        deep_out = self.workspace / '.local/deep-input/report.json'
        result = self.cli(*self.verify_args(), '--out', deep_out)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        if deep_out.exists():
            report = self.read(deep_out)
            self.assertTrue(report['errors'])
            self.assertNotEqual(report['status'], 'OBSERVED_MERGED_METADATA')
            self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')

        # Force the exact parser failure to verify the catch independently of
        # runtime depth policy. No module report or directory may be created.
        with patch('scripts.storyctl.json.loads', side_effect=RecursionError('Synthetic parser depth failure')):
            result = self.cli(*self.verify_args(), '--out', out)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('UTF-8 JSON object', result.stderr)
        self.assertFalse(out.parent.exists())

    def test_verification_output_cannot_replace_its_input_cache(self):
        before = self.cache.read_bytes()
        result = self.cli(*self.verify_args(), '--out', self.cache)
        self.assertEqual(result.returncode, 1)
        self.assertIn('evidence', result.stderr.lower())
        self.assertEqual(self.cache.read_bytes(), before)

    def test_offline_rollup_is_a_selected_story_proposal_with_exact_sources(self):
        before = self.snapshot()
        for slug in ('alpha', 'beta'):
            with self.subTest(story=slug):
                result = self.cli('rollup', 'EP-001', 'EP-002', story=slug)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report['kind'], 'ROLLUP_PROPOSAL')
                self.assertEqual(report['status'], 'PROPOSED')
                self.assertEqual(report['approval_basis'], 'UNVERIFIED_LOCAL_DECLARATIONS')
                self.assertEqual(report['source_verification'], 'OFFLINE_UNVERIFIED')
                self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')
                self.assertEqual(report['story']['slug'], slug)
                self.assertEqual(report['episode_ids'], ['EP-001', 'EP-002'])
                root = self.root if slug == 'alpha' else self.beta
                expected = '\n\n'.join((root / f'ledger/episodes/EP-{number:03}.md').read_bytes().decode('utf-8')
                                       for number in (1, 2))
                self.assertEqual(report['assembly']['content'], expected)
                self.assertNotIn('recap metadata ' + ('beta' if slug == 'alpha' else 'alpha'), result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_offline_rollup_rejects_unknown_unordered_or_missing_story(self):
        selections = [('EP-MISSING',), ('EP-002', 'EP-001'), ('EP-001', 'EP-003')]
        for number, episodes in enumerate(selections):
            with self.subTest(episodes=episodes):
                out = self.workspace / f'.local/bad-selection-{number}/rollup.json'
                result = self.cli('rollup', *episodes, '--out', out, story='alpha')
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertFalse(out.parent.exists())
        result = self.cli('rollup', 'EP-001', story='missing')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('recap metadata alpha', result.stdout + result.stderr)
        self.assertNotIn('recap metadata beta', result.stdout + result.stderr)

    def test_rollup_source_failures_block_artifacts_and_cross_story_fallback(self):
        recap = self.root / 'ledger/episodes/EP-001.md'
        original_recap = recap.read_bytes()
        episodes_path = self.root / 'data/episodes.json'
        original_episodes = self.read(episodes_path)
        index_path = self.root / 'ledger/index.json'
        original_index = rollup_fixtures.RollupTests.add_provenance(self, self.root)
        scenes_path = self.root / 'data/scenes.json'
        original_scenes = self.read(scenes_path)
        for number, mode in enumerate(('missing', 'unapproved', 'hash', 'path', 'reference')):
            with self.subTest(mode=mode):
                recap.write_bytes(original_recap)
                self.write(episodes_path, original_episodes)
                self.write(index_path, original_index)
                self.write(scenes_path, original_scenes)
                if mode == 'missing':
                    recap.unlink()
                elif mode == 'unapproved':
                    episodes = copy.deepcopy(original_episodes)
                    episodes['episodes'][0]['status'] = 'OUTLINE'
                    self.write(episodes_path, episodes)
                elif mode == 'hash':
                    index = copy.deepcopy(original_index)
                    index['episodes'][0]['provenance']['source_sha256'] = '0' * 64
                    self.write(index_path, index)
                elif mode == 'path':
                    index = copy.deepcopy(original_index)
                    index['episodes'][0]['summary_path'] = '../beta/ledger/episodes/EP-001.md'
                    self.write(index_path, index)
                else:
                    scenes = copy.deepcopy(original_scenes)
                    scenes['scenes'][0]['location_id'] = 'LOC-MISSING'
                    self.write(scenes_path, scenes)
                out = self.workspace / f'.local/bad-source-{number}/rollup.json'
                result = self.cli('rollup', 'EP-001', '--out', out, story='alpha')
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertFalse(out.parent.exists())
                self.assertNotIn('recap metadata beta', result.stdout + result.stderr)

    def test_remote_rollup_cannot_accept_offline_verifier_status(self):
        rollup_fixtures.RollupTests.add_provenance(self, self.root)
        out = self.workspace / '.local/remote-not-observed/rollup.json'
        with patch('scripts.rollup.review_bundle._git', return_value=(str(self.workspace) + '\n').encode()), \
                patch('scripts.rollup.provenance.verify', return_value={
                    'status': 'OFFLINE_UNVERIFIED', 'errors': [], 'human_editorial_approval': 'UNVERIFIED',
                }) as verifier:
            result = self.cli('rollup', 'EP-001', '--repo', rollup_fixtures.REPOSITORY,
                              '--verify-remote', '--out', out, story='alpha')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        verifier.assert_called_once()
        self.assertFalse(out.parent.exists())

    def test_new_outputs_stay_private_and_cannot_overwrite_story_sources(self):
        before = self.snapshot()
        for command, story in ((self.verify_args(), None), (['rollup', 'EP-001'], 'alpha')):
            for out in (self.workspace / 'exports/result.json', self.root / 'data/canon.json'):
                with self.subTest(command=command[0], out=str(out)):
                    result = self.cli(*command, '--out', out, story=story)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn('.local', result.stderr)
        self.assertFalse((self.workspace / 'exports').exists())
        self.assertEqual(self.snapshot(), before)

    def test_private_hardlink_outputs_and_repetition_preserve_source_bytes(self):
        source = self.root / 'data/characters.json'
        original = source.read_bytes()
        before = self.snapshot()
        for number, (command, story, expected_code) in enumerate((
                (self.verify_args(), None, 2), (['rollup', 'EP-001', 'EP-002'], 'alpha', 0))):
            with self.subTest(command=command[0]):
                out = self.workspace / f'.local/report-{number}.json'
                os.link(source, out)
                self.assertTrue(os.path.samefile(source, out))
                first = self.cli(*command, '--out', out, story=story)
                self.assertEqual(first.returncode, expected_code, first.stdout + first.stderr)
                self.assertEqual(source.read_bytes(), original)
                self.assertFalse(os.path.samefile(source, out))
                first_bytes = out.read_bytes()
                second = self.cli(*command, '--out', out, story=story)
                self.assertEqual(second.returncode, expected_code, second.stdout + second.stderr)
                self.assertEqual(out.read_bytes(), first_bytes)
                self.assertEqual(self.snapshot(), before)
        self.assertIn('.local/', (self.workspace / '.gitignore').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
