"""Structural acceptance workflow tests; no semantic review or real approval."""
import contextlib
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import acceptance, novelctl, story_engine, storyctl


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name).resolve()

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def snapshot(root):
        return {path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob('*') if path.is_file()}

    def fixture(self, slug='synthetic-three'):
        storyctl.new_story(self.workspace, slug)
        return acceptance.populate_fixture(self.workspace, slug)

    def test_genuinely_empty_new_story_passes_actual_cli_check(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(storyctl.main(['--workspace', str(self.workspace), 'new', 'empty']), 0)
            root = self.workspace / 'stories/empty'
            before = self.snapshot(root)
            self.assertEqual(storyctl.main(['--workspace', str(self.workspace), '--story', 'empty', 'check']), 0)
        self.assertIn('PASS | 0 errors; 0 warnings', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')
        self.assertEqual(self.snapshot(root), before)
        db = novelctl.load(root)
        for kind in novelctl.CORE_DATA:
            if kind != 'story_state':
                self.assertEqual(novelctl.rows(db, kind), [])
        self.assertFalse((root / 'data/state_history.json').exists())

    def test_three_scene_fixture_replays_inventory_and_excludes_future_knowledge(self):
        with patch('urllib.request.urlopen') as http, patch('socket.create_connection') as connection:
            root = self.fixture()
            before = self.snapshot(root)
            self.assertEqual(novelctl.validate(root), ([], []))
            self.assertEqual(story_engine.validate(root), ([], []))
            for target, quantity, deltas in (
                    ('SC-001', 1, []), ('SC-002', 0, ['DELTA-001']),
                    ('SC-003', 0, ['DELTA-001', 'DELTA-002'])):
                with self.subTest(target=target):
                    result = novelctl.state_before_target(root, target)
                    self.assertEqual(result['availability'], 'KNOWN')
                    self.assertEqual(result['state']['inventory']['CHAR-001']['ITEM-TOKEN'], quantity)
                    self.assertIs(result['state']['knowledge']['CHAR-001']['token_code_known'], False)
                    self.assertEqual(result['applied_delta_ids'], deltas)
                    self.assertEqual(result['approval_basis'], 'LOCAL_RECORDS_NOT_GITHUB_AUTHENTICATED')
            pack = story_engine.pack(root, 'SC-002')
            # Bind the live fixture to the context actually given to the blind
            # reviewers. Only its machine-specific absolute root is normalized.
            manifest = self.read(Path(__file__).resolve().parents[1] / 'evaluation/e6/manifest.json')
            normalized_pack = pack.replace(str(root), '<SYNTHETIC_STORY_ROOT>')
            self.assertEqual(hashlib.sha256(normalized_pack.encode('utf-8')).hexdigest(),
                             manifest['pack_sha256'])
            self.assertNotIn(acceptance.FUTURE_KNOWLEDGE, pack)
            self.assertIn('no remote override', pack)
            self.assertIn('fixed red color', pack)
            self.assertIn('"ITEM-TOKEN": 0', pack)
            self.assertFalse((root / 'data/mechanics.json').exists())
            self.assertFalse((root / 'data/sources.json').exists())
            self.assertEqual(self.snapshot(root), before)
        http.assert_not_called()
        connection.assert_not_called()

    def test_proposed_prior_delta_leaves_state_unknown_without_invented_counts(self):
        root = self.fixture()
        path = root / 'data/state_history.json'
        history = self.read(path)
        history['deltas'][0]['status'] = 'PROPOSED'
        path.write_text(json.dumps(history), encoding='utf-8')
        before = self.snapshot(root)
        result = novelctl.state_before_target(root, 'SC-002')
        self.assertEqual(result['availability'], 'UNKNOWN')
        self.assertNotIn('state', result)
        self.assertNotIn('applied_delta_ids', result)
        self.assertEqual(self.snapshot(root), before)

    def test_fixture_refuses_to_overwrite_existing_story_metadata_or_evidence(self):
        populated = self.fixture()
        before = self.snapshot(populated)
        with self.assertRaises(ValueError):
            acceptance.populate_fixture(self.workspace)
        self.assertEqual(self.snapshot(populated), before)
        for number, mode in enumerate(('threads', 'nested_evidence', 'state', 'style', 'rules', 'baseline')):
            with self.subTest(mode=mode):
                slug = f'existing-{number}'
                root = storyctl.new_story(self.workspace, slug)
                if mode == 'threads':
                    path = root / 'data/threads.json'
                    path.write_text(json.dumps({'schema_version': 1, 'threads': [{'id': 'EXISTING'}]}), encoding='utf-8')
                elif mode == 'state':
                    path = root / 'data/story_state.json'
                    data = self.read(path)
                    data['phase'] = 'EXISTING_METADATA'
                    path.write_text(json.dumps(data), encoding='utf-8')
                elif mode == 'nested_evidence':
                    path = root / 'drafts/nested/source.md'
                    path.parent.mkdir()
                    path.write_bytes(b'Synthetic existing evidence; must remain untouched.\n')
                elif mode == 'style':
                    (root / 'bible/STYLE_GUIDE.md').write_bytes(b'Existing synthetic style decision.\n')
                elif mode == 'baseline':
                    (root / 'bible/INITIAL_STATE.md').write_bytes(b'Existing synthetic baseline evidence.\n')
                else:
                    path = root / 'story.json'
                    config = self.read(path)
                    config['rules'] = ['Existing synthetic rule decision']
                    path.write_text(json.dumps(config), encoding='utf-8')
                before = self.snapshot(root)
                with self.assertRaises(ValueError):
                    acceptance.populate_fixture(self.workspace, slug)
                self.assertEqual(self.snapshot(root), before)

    def test_real_runner_exercises_commands_and_preserves_sources_without_approval(self):
        out = self.workspace / '.local/structural-run'
        with patch('urllib.request.urlopen') as http, patch('socket.create_connection') as connection:
            report = acceptance.run_acceptance(self.workspace, out)
        self.assertEqual(report, self.read(out / 'report.json'))
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['empty_story_check'], 'PASS')
        self.assertEqual(report['semantic_evaluation'], 'NOT_RUN')
        self.assertEqual(report['human_editorial_approval'], 'BLOCKED')
        self.assertIs(report['source_preserved'], True)
        self.assertEqual(report['local_anchor']['kind'], 'SYNTHETIC_LOCAL_GIT_ONLY')
        self.assertEqual(report['local_anchor']['human_editorial_approval'], 'UNVERIFIED')
        self.assertRegex(report['local_anchor']['commit'], r'^[0-9a-f]{40}$')
        labels = [command['label'] for command in report['commands']]
        expected = {'empty-new', 'empty-check', 'fixture-new', 'fixture-check',
                    'local-git-init', 'local-git-add', 'local-git-anchor', 'local-git-head',
                    'pack', 'brief-review', 'propose', 'replay-SC-001', 'replay-SC-002',
                    'replay-SC-003', 'rollup', 'doctor', 'final-check'}
        self.assertEqual(set(labels), expected)
        self.assertEqual(len(labels), len(expected))
        self.assertTrue(all(command['returncode'] == 0 for command in report['commands']))
        for command in report['commands']:
            self.assertNotIn('--verify-remote', command['argv'])
            self.assertNotIn('gh', command['argv'])
            self.assertNotIn('push', command['argv'])
            self.assertNotIn('fetch', command['argv'])
        self.assertEqual(set(report['outputs']), {'pack', 'brief-review', 'propose',
            'replay-SC-001', 'replay-SC-002', 'replay-SC-003', 'rollup', 'doctor'})
        isolated = out / 'workspace'
        for metadata in report['outputs'].values():
            path = out / metadata['path']
            self.assertTrue(path.resolve().is_relative_to(isolated / '.local'))
            content = path.read_bytes()
            self.assertEqual(metadata['sha256'], hashlib.sha256(content).hexdigest())
            self.assertEqual(metadata['byte_length'], len(content))
        actual_manifest = {}
        for relative, content in self.snapshot(isolated / 'stories').items():
            actual_manifest['stories/' + relative] = {
                'sha256': hashlib.sha256(content).hexdigest(), 'byte_length': len(content)}
        self.assertEqual(report['source_manifest'], actual_manifest)
        bundle = self.read(out / report['outputs']['brief-review']['path'])
        self.assertEqual(bundle['status'], 'UNREVIEWED')
        self.assertEqual(bundle['git']['head_commit'], report['local_anchor']['commit'])
        self.assertTrue(bundle['diff']['content'])
        rollup = self.read(out / report['outputs']['rollup']['path'])
        self.assertEqual(rollup['status'], 'PROPOSED')
        self.assertEqual(rollup['source_verification'], 'OFFLINE_UNVERIFIED')
        self.assertEqual(rollup['human_editorial_approval'], 'UNVERIFIED')
        http.assert_not_called()
        connection.assert_not_called()

    def test_runner_rejects_existing_outside_and_linked_destinations_before_commands(self):
        local = self.workspace / '.local'
        existing = local / 'existing'
        existing.mkdir(parents=True)
        sentinel = existing / 'keep.txt'
        sentinel.write_bytes(b'Existing synthetic artifact; preserve bytes.\n')
        original = self.snapshot(self.workspace)
        with patch('scripts.acceptance.subprocess.run') as process:
            for out in (self.workspace / 'outside', local, existing):
                with self.subTest(path=out):
                    with self.assertRaises(ValueError):
                        acceptance.run_acceptance(self.workspace, out)
                    self.assertEqual(self.snapshot(self.workspace), original)
            target = self.workspace / 'linked-target'
            target.mkdir()
            link = local / 'linked'
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(ValueError):
                acceptance.run_acceptance(self.workspace, link / 'must-not-exist')
            self.assertEqual(list(target.iterdir()), [])
            self.assertEqual(sentinel.read_bytes(), b'Existing synthetic artifact; preserve bytes.\n')
        process.assert_not_called()

    def test_failed_command_retains_failure_report_and_cannot_look_successful(self):
        out = self.workspace / '.local/failed-run'
        failure = subprocess.CompletedProcess(['synthetic-command'], 1, '', 'Synthetic command failure')
        with patch('scripts.acceptance.subprocess.run', return_value=failure) as process:
            with self.assertRaisesRegex(ValueError, 'retained report'):
                acceptance.run_acceptance(self.workspace, out)
        process.assert_called_once()
        report = self.read(out / 'report.json')
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['semantic_evaluation'], 'NOT_RUN')
        self.assertEqual(report['human_editorial_approval'], 'BLOCKED')
        self.assertEqual(report['commands'][0]['label'], 'empty-new')
        self.assertEqual(report['commands'][0]['returncode'], 1)
        self.assertNotIn('source_preserved', report)
        self.assertNotIn('empty_story_check', report)
        self.assertEqual(report['outputs'], {})


if __name__ == '__main__':
    unittest.main()
