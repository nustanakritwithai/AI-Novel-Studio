"""E3/E4 CLI contracts with local Git and synthetic metadata only."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_story_roots as story_roots
from scripts import story_engine


ENGINE_ROOT = Path(__file__).resolve().parents[1]


class StoryctlContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.alpha = story_roots.StoryRootTests.fixture(self, 'alpha', 'ALPHA_ONLY')
        self.beta = story_roots.StoryRootTests.fixture(self, 'beta', 'BETA_ONLY')
        self.write(self.workspace / 'studio.json', {'schema_version': 1, 'default_story': 'alpha'})
        (self.workspace / '.gitignore').write_bytes((ENGINE_ROOT / '.gitignore').read_bytes())
        for root, token in ((self.alpha, 'ALPHA_ONLY'), (self.beta, 'BETA_ONLY')):
            scenes = self.read(root / 'data/scenes.json')
            scenes['scenes'][0]['status'] = 'DRAFT'
            self.write(root / 'data/scenes.json', scenes)
            path = root / 'drafts/EP-001/SC-001.md'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((token + '_DRAFT_ORIGINAL\nSynthetic metadata only; no narrative or approval.\n').encode())
        self.git('init', '-q')
        self.git('add', '--all')
        self.git('-c', 'user.name=Synthetic fixture', '-c', 'user.email=fixture@example.invalid',
                 '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'Synthetic metadata baseline')
        self.base_commit = self.git('rev-parse', 'HEAD').stdout.strip()
        self.draft = self.alpha / 'drafts/EP-001/SC-001.md'
        self.draft.write_bytes(b'ALPHA_ONLY_DRAFT_REVISED\nSynthetic metadata only; no narrative or approval.\n')

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def git(self, *args, check=True):
        return subprocess.run(
            ['git', '-C', str(self.workspace), *args], capture_output=True,
            text=True, encoding='utf-8', errors='replace', check=check, timeout=20,
            env=dict(os.environ, GIT_TERMINAL_PROMPT='0'),
        )

    def cli(self, *args, story='alpha', workspace=None):
        selection = ['--workspace', str(workspace or self.workspace)]
        if story is not None:
            selection += ['--story', story]
        return subprocess.run(
            [sys.executable, str(ENGINE_ROOT / 'scripts/storyctl.py'), *selection, *map(str, args)],
            cwd=self.workspace, env=dict(os.environ, PYTHONIOENCODING='utf-8'),
            capture_output=True, text=True, encoding='utf-8', timeout=30,
        )

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stdout + result.stderr)

    def assert_failure(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stdout + result.stderr)

    def source_snapshot(self):
        return {p.relative_to(self.workspace).as_posix(): p.read_bytes()
                for p in self.workspace.rglob('*') if p.is_file()
                and '.git' not in p.relative_to(self.workspace).parts
                and '.local' not in p.relative_to(self.workspace).parts}

    def test_brief_review_stdout_pins_exact_local_sources_without_approval(self):
        result = self.cli('brief-review', 'SC-001', '--base', 'HEAD')
        self.assert_success(result)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'UNREVIEWED')
        self.assertEqual(report['target'], 'SC-001')
        self.assertEqual(report['approval_basis'], 'LOCAL_BUNDLE_NOT_GITHUB_AUTHENTICATED')
        self.assertEqual(report['git']['head_commit'], self.base_commit)
        self.assertEqual(report['git']['base_commit'], self.base_commit)
        self.assertEqual(report['draft']['content'], self.draft.read_bytes().decode('utf-8'))
        self.assertEqual(report['draft']['sha256'], hashlib.sha256(self.draft.read_bytes()).hexdigest())
        self.assertEqual(report['draft']['byte_length'], len(self.draft.read_bytes()))
        self.assertIn('ALPHA_ONLY_DRAFT_ORIGINAL', report['base_draft']['content'])
        self.assertIn('ALPHA_ONLY_DRAFT_ORIGINAL', report['diff']['content'])
        self.assertIn('ALPHA_ONLY_DRAFT_REVISED', report['diff']['content'])
        self.assertEqual(report['context']['content'], story_engine.pack(self.alpha, 'SC-001'))
        self.assertIn('GitHub main and human approval have not been authenticated', report['context']['content'])
        self.assertNotIn('SOURCE OF TRUTH: GitHub main approved content', report['context']['content'])
        self.assertNotIn('BETA_ONLY', result.stdout)
        self.assertNotIn('LAST ISLAND', result.stdout.upper())

    def test_private_artifacts_are_ignored_and_sources_stay_identical(self):
        before = self.source_snapshot()
        before_status = self.git('status', '--porcelain', '--untracked-files=all').stdout
        review_out = self.workspace / '.local/reviews/SC-001.json'
        doctor_out = self.workspace / '.local/doctor.json'
        self.assert_success(self.cli('brief-review', 'SC-001', '--out', review_out))
        self.assert_success(self.cli('doctor', '--target', 'SC-001', '--out', doctor_out))
        self.assertEqual(self.read(review_out)['status'], 'UNREVIEWED')
        self.assertEqual(self.read(doctor_out)['local_validation_status'], 'PASS')
        self.assertEqual(self.git('check-ignore', '--quiet', '.local/reviews/SC-001.json').returncode, 0)
        self.assertEqual(self.git('check-ignore', '--quiet', '.local/doctor.json').returncode, 0)
        self.assertEqual(self.source_snapshot(), before)
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all').stdout, before_status)

    def test_repeated_read_only_commands_are_deterministic(self):
        before = self.source_snapshot()
        for args in (('brief-review', 'SC-001'), ('doctor', '--target', 'SC-001')):
            with self.subTest(command=args[0]):
                first, second = self.cli(*args), self.cli(*args)
                self.assert_success(first)
                self.assert_success(second)
                self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(self.source_snapshot(), before)

    def test_private_output_replaces_hardlinks_without_changing_story_sources(self):
        source = self.alpha / 'data/characters.json'
        original = source.read_bytes()
        out = self.workspace / '.local/report.json'
        out.parent.mkdir()
        os.link(source, out)
        self.assertTrue(os.path.samefile(source, out))
        before = self.source_snapshot()
        self.assert_success(self.cli('doctor', '--target', 'SC-001', '--out', out))
        self.assertEqual(source.read_bytes(), original)
        self.assertFalse(os.path.samefile(source, out))
        first = out.read_bytes()
        self.assertEqual(self.read(out)['local_validation_status'], 'PASS')
        self.assert_success(self.cli('doctor', '--target', 'SC-001', '--out', out))
        self.assertEqual(out.read_bytes(), first)
        self.assertEqual(self.source_snapshot(), before)

    def test_doctor_reports_only_local_facts_and_explicit_online_unknowns(self):
        result = self.cli('doctor', '--target', 'SC-001')
        self.assert_success(result)
        report = json.loads(result.stdout)
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['local_validation_status'], 'PASS')
        self.assertEqual(report['story_slug'], 'alpha')
        self.assertEqual(Path(report['selected_root']), self.alpha)
        self.assertEqual(report['schema']['status'], 'PASS')
        self.assertEqual(report['git']['head'], self.base_commit)
        self.assertIs(report['git']['selected_root_dirty'], True)
        self.assertEqual(report['state']['approval_basis'], 'LOCAL_RECORDS_NOT_GITHUB_AUTHENTICATED')
        self.assertEqual(report['github']['approval_provenance'], 'UNKNOWN')
        self.assertEqual(report['github']['codeowners_enforcement'], 'UNKNOWN')
        for field in ('authentication', 'check_status'):
            self.assertEqual(report['github'][field], 'NOT_CHECKED')
        for field in ('settings', 'security'):
            self.assertEqual(report['github'][field], 'UNKNOWN')
        self.assertNotIn('ALPHA_ONLY_DRAFT_REVISED', result.stdout)
        self.assertNotIn('BETA_ONLY', result.stdout)

    def test_doctor_without_git_keeps_that_fact_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'isolated'
            shutil.copytree(self.alpha, root)
            result = self.cli('doctor', '--target', 'SC-001', workspace=root, story=None)
        self.assert_success(result)
        report = json.loads(result.stdout)
        self.assertEqual(report['local_validation_status'], 'PASS')
        self.assertEqual(report['git']['status'], 'UNKNOWN')
        self.assertEqual(report['git']['head'], 'UNKNOWN')
        self.assertEqual(report['github']['approval_provenance'], 'UNKNOWN')

    def test_propose_is_an_exact_alias_and_does_not_change_approval(self):
        before = self.source_snapshot()
        old = self.cli('proposal', 'EP-001')
        new = self.cli('propose', 'EP-001')
        self.assert_success(old)
        self.assert_success(new)
        self.assertEqual(old.stdout, new.stdout)
        self.assertEqual(new.stdout, story_engine.proposal(self.alpha, 'EP-001') + '\n')
        self.assertIn('NOT CANON', new.stdout)
        self.assertEqual(self.read(self.alpha / 'ledger/index.json')['episodes'], [])
        self.assertEqual(self.source_snapshot(), before)

    def test_deferred_rollup_has_no_success_stub(self):
        before = self.source_snapshot()
        result = self.cli('rollup', 'EP-001')
        self.assert_failure(result)
        self.assertIn('invalid choice', result.stderr)
        self.assertEqual(self.source_snapshot(), before)

    def test_invalid_review_target_or_git_base_fails_before_artifact_creation(self):
        cases = [
            ('brief-review', 'SC-MISSING'),
            ('brief-review', 'EP-001'),
            ('brief-review', 'SC-001', '--base', 'REF-DOES-NOT-EXIST'),
            ('brief-review', 'SC-001', '--base', 'HEAD:studio.json'),
        ]
        for number, args in enumerate(cases):
            with self.subTest(args=args):
                out = self.workspace / f'.local/failure-{number}/report.json'
                result = self.cli(*args, '--out', out)
                self.assert_failure(result)
                self.assertIn('ERROR:', result.stderr)
                self.assertFalse(out.exists())
                self.assertFalse(out.parent.exists())

    def test_missing_or_escaping_review_draft_is_rejected(self):
        self.draft.unlink()
        out = self.workspace / '.local/missing-source/report.json'
        result = self.cli('brief-review', 'SC-001', '--out', out)
        self.assert_failure(result)
        self.assertFalse(out.parent.exists())
        scenes = self.read(self.alpha / 'data/scenes.json')
        scenes['scenes'][0]['draft_path'] = '../beta/drafts/EP-001/SC-001.md'
        self.write(self.alpha / 'data/scenes.json', scenes)
        result = self.cli('brief-review', 'SC-001', '--out', out)
        self.assert_failure(result)
        self.assertFalse(out.parent.exists())
        self.assertNotIn('BETA_ONLY_DRAFT_ORIGINAL', result.stdout + result.stderr)

    def test_new_private_outputs_cannot_escape_or_overwrite_sources(self):
        before = self.source_snapshot()
        candidates = (
            self.workspace / 'exports/report.json',
            self.workspace / '.local/../escaped/report.json',
            self.alpha / 'data/canon.json',
        )
        for args in (('brief-review', 'SC-001'), ('doctor', '--target', 'SC-001')):
            for out in candidates:
                with self.subTest(command=args[0], out=str(out)):
                    result = self.cli(*args, '--out', out)
                    self.assert_failure(result)
                    self.assertIn('.local', result.stdout + result.stderr)
        self.assertFalse((self.workspace / 'exports').exists())
        self.assertFalse((self.workspace / 'escaped').exists())
        self.assertEqual(self.source_snapshot(), before)

    def test_invalid_doctor_target_produces_structured_errors(self):
        result = self.cli('doctor', '--target', 'SC-MISSING')
        self.assert_failure(result)
        report = json.loads(result.stdout)
        self.assertEqual(report['local_validation_status'], 'FAIL')
        self.assertEqual(report['state']['availability'], 'ERROR')
        self.assertTrue(report['errors'])
        self.assertEqual(report['github']['approval_provenance'], 'UNKNOWN')

    def test_malformed_registry_fails_without_a_traceback_or_false_pass(self):
        (self.alpha / 'data/scenes.json').write_text('{ malformed JSON', encoding='utf-8')
        review = self.cli('brief-review', 'SC-001')
        self.assert_failure(review)
        self.assertIn('ERROR:', review.stderr)
        doctor = self.cli('doctor', '--target', 'SC-001')
        self.assert_failure(doctor)
        report = json.loads(doctor.stdout)
        self.assertEqual(report['local_validation_status'], 'FAIL')
        self.assertTrue(report['errors'])
        self.assertEqual(report['state']['availability'], 'ERROR')

    def test_explicit_story_selection_never_uses_another_story(self):
        review = self.cli('brief-review', 'SC-001', story='beta')
        self.assert_success(review)
        self.assertIn('BETA_ONLY_DRAFT_ORIGINAL', review.stdout)
        self.assertNotIn('ALPHA_ONLY', review.stdout)
        doctor = self.cli('doctor', '--target', 'SC-001', story='beta')
        self.assert_success(doctor)
        self.assertEqual(json.loads(doctor.stdout)['story_slug'], 'beta')
        for args in (('brief-review', 'SC-001'), ('propose', 'EP-001'),
                     ('doctor', '--target', 'SC-001')):
            with self.subTest(command=args[0]):
                result = self.cli(*args, story='missing')
                self.assert_failure(result)
                self.assertNotIn('ALPHA_ONLY', result.stdout + result.stderr)
                self.assertNotIn('BETA_ONLY', result.stdout + result.stderr)
        (self.beta / 'data/scenes.json').write_text('{ invalid selected story', encoding='utf-8')
        self.assert_failure(self.cli('brief-review', 'SC-001', story='beta'))
        self.assert_success(self.cli('brief-review', 'SC-001', story='alpha'))


if __name__ == '__main__':
    unittest.main()
