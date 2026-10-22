"""Local Git review packaging with synthetic metadata, never narrative/approval."""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import test_story_roots as story_roots
from scripts import review_bundle


BASE_DRAFT = b'# Synthetic review metadata only\r\nBASE_VALUE\r\n'
WORKING_DRAFT = b'# Synthetic review metadata only\r\nWORKING_VALUE\r\n'


class ReviewBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name).resolve()
        self.alpha = story_roots.StoryRootTests.fixture(self, 'alpha', 'ALPHA_ONLY')
        self.beta = story_roots.StoryRootTests.fixture(self, 'beta', 'BETA_ONLY')
        self.draft = self.alpha / 'drafts/EP-001/SC-002.md'
        self.draft.parent.mkdir(parents=True, exist_ok=True)
        self.draft.write_bytes(BASE_DRAFT)
        self.git('init', '--quiet', '--initial-branch=main')
        self.git('add', '--', '.')
        self.git('commit', '--quiet', '-m', 'Synthetic metadata fixture baseline')
        self.base = self.git('rev-parse', 'HEAD').decode('ascii').strip()
        (self.workspace / '.fixture-anchor').write_bytes(b'Second synthetic commit anchor\n')
        self.git('add', '--', '.fixture-anchor')
        self.git('commit', '--quiet', '-m', 'Synthetic second anchor')
        self.head = self.git('rev-parse', 'HEAD').decode('ascii').strip()
        self.draft.write_bytes(WORKING_DRAFT)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def git(self, *args, input=None):
        env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_NO_LAZY_FETCH='1')
        for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'):
            env.pop(name, None)
        result = subprocess.run(
            ['git', '-C', str(self.workspace), '-c', 'core.autocrlf=false',
             '-c', 'user.name=Synthetic Fixture', '-c', 'user.email=fixture@example.invalid', *args],
            input=input, capture_output=True, timeout=30, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
        return result.stdout

    def build(self, target='SC-002', base=None):
        return review_bundle.build(self.alpha, target, self.base if base is None else base)

    def commit_draft(self, value):
        self.draft.write_bytes(value)
        self.git('add', '--', self.draft.relative_to(self.workspace).as_posix())
        self.git('commit', '--quiet', '-m', 'Synthetic review source variant')
        return self.git('rev-parse', 'HEAD').decode('ascii').strip()

    def test_actual_commit_anchors_and_exact_draft_base_diff_hashes(self):
        bundle = self.build()
        path = 'stories/alpha/drafts/EP-001/SC-002.md'
        self.assertNotEqual(self.head, self.base)
        self.assertEqual(bundle['git']['head_commit'], self.head)
        self.assertEqual(bundle['git']['base_commit'], self.base)
        self.assertEqual(bundle['status'], 'UNREVIEWED')
        self.assertEqual(bundle['approval_basis'], 'LOCAL_BUNDLE_NOT_GITHUB_AUTHENTICATED')
        self.assertEqual(bundle['draft']['origin'], 'WORKING_TREE')
        self.assertEqual(bundle['context']['origin'], 'WORKING_TREE')
        self.assertEqual(bundle['draft']['path'], path)
        self.assertEqual(bundle['draft']['content'].encode('utf-8'), WORKING_DRAFT)
        self.assertEqual(bundle['base_draft']['content'].encode('utf-8'), BASE_DRAFT)
        self.assertTrue(bundle['base_draft']['exists'])
        self.assertEqual(bundle['base_draft']['blob_id'], self.git(
            'rev-parse', self.base + ':' + path).decode('ascii').strip())
        self.assertEqual(bundle['diff']['content'], (
            '--- base/' + path + '\n+++ working-tree/' + path + '\n'
            '@@ -1,2 +1,2 @@\n # Synthetic review metadata only\r\n'
            '-BASE_VALUE\r\n+WORKING_VALUE\r\n'))
        for field in ('draft', 'base_draft', 'context', 'diff'):
            content = bundle[field]['content'].encode('utf-8')
            self.assertEqual(bundle[field]['sha256'], hashlib.sha256(content).hexdigest())
            self.assertEqual(bundle[field]['byte_length'], len(content))
        self.assertEqual(json.loads(json.dumps(bundle)), bundle)

    def test_untracked_addition_has_explicit_empty_base_and_no_final_newline_marker(self):
        current = self.alpha / 'drafts/EP-001/SC-003.md'
        exact = '# Synthetic fixture metadata\nUTF8_VALUE_ทดสอบ'.encode('utf-8')
        current.write_bytes(exact)
        bundle = self.build('SC-003')
        self.assertFalse(bundle['base_draft']['exists'])
        self.assertIsNone(bundle['base_draft']['blob_id'])
        self.assertEqual(bundle['base_draft']['content'], '')
        self.assertEqual(bundle['base_draft']['byte_length'], 0)
        self.assertEqual(bundle['base_draft']['sha256'], hashlib.sha256(b'').hexdigest())
        self.assertEqual(bundle['draft']['content'].encode('utf-8'), exact)
        self.assertTrue(bundle['diff']['content'].startswith('--- /dev/null\n'))
        self.assertIn('+UTF8_VALUE_ทดสอบ\n\\ No newline at end of file\n', bundle['diff']['content'])

    def test_working_changes_have_new_content_hash_without_invented_commit(self):
        before = self.build()
        self.draft.write_bytes(WORKING_DRAFT + b'ADDITIONAL_FIXTURE_METADATA\n')
        after = self.build()
        self.assertEqual(before['git'], after['git'])
        self.assertNotEqual(before['draft']['sha256'], after['draft']['sha256'])
        self.assertNotEqual(before['diff']['content'], after['diff']['content'])
        self.assertEqual(before['base_draft'], after['base_draft'])
        self.assertEqual(before['context']['content'], after['context']['content'])

    def test_unchanged_draft_has_empty_diff(self):
        self.draft.write_bytes(BASE_DRAFT)
        self.assertEqual(self.build()['diff']['content'], '')

    def test_context_and_source_hashes_use_selected_story_only(self):
        bundle = self.build()
        self.assertIn('ALPHA_ONLY_FACT', bundle['context']['content'])
        self.assertNotIn('BETA_ONLY', json.dumps(bundle))
        sources = {row['path']: row for row in bundle['context']['sources']}
        for path in ('story.json', 'data/scenes.json', 'data/story_state.json',
                     'bible/STYLE_GUIDE.md', 'ledger/index.json', 'drafts/EP-001/SC-002.md'):
            value = (self.alpha / path).read_bytes()
            self.assertEqual(sources[path]['sha256'], hashlib.sha256(value).hexdigest())
            self.assertEqual(sources[path]['byte_length'], len(value))
        draft = self.beta / 'drafts/EP-001/SC-002.md'
        draft.parent.mkdir(parents=True, exist_ok=True)
        draft.write_bytes(b'# BETA review fixture metadata\n')
        beta = review_bundle.build(self.beta, 'SC-002', self.base)
        self.assertIn('BETA_ONLY_FACT', beta['context']['content'])
        self.assertNotIn('ALPHA_ONLY', json.dumps(beta))
        self.assertEqual(beta['story']['repository_path'], 'stories/beta')

    def test_unknown_episode_and_missing_draft_fail_clearly(self):
        for target in ('SC-MISSING', 'EP-001'):
            with self.subTest(target=target):
                with self.assertRaisesRegex(ValueError, 'known scene target'):
                    self.build(target)
        self.draft.unlink()
        with self.assertRaisesRegex(ValueError, 'Cannot read review source'):
            self.build()

    def test_invalid_or_option_like_refs_are_not_commands(self):
        for base in ('', '--help', '--output=unexpected-file', 'MISSING-REF',
                     self.base + ':stories/alpha/story.json', 'HEAD;echo injected'):
            with self.subTest(base=base):
                with self.assertRaises(ValueError):
                    self.build(base=base)
        self.assertFalse((self.workspace / 'unexpected-file').exists())
        self.assertEqual(self.git('rev-parse', 'HEAD').decode('ascii').strip(), self.head)

    def test_outside_git_fails_without_fabricating_commit_identifiers(self):
        with tempfile.TemporaryDirectory() as temporary:
            outside = Path(temporary) / 'outside'
            shutil.copytree(self.alpha, outside)
            with self.assertRaisesRegex(ValueError, 'Git repository'):
                review_bundle.build(outside, 'SC-002')

    def test_inherited_git_environment_cannot_redirect_repository_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            other = Path(temporary)
            result = subprocess.run(['git', '-C', str(other), 'init', '--quiet'],
                                    capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            redirected = {
                'GIT_DIR': str(other / '.git'), 'GIT_WORK_TREE': str(other),
                'GIT_COMMON_DIR': str(other / '.git'), 'GIT_OBJECT_DIRECTORY': str(other / 'missing'),
                'GIT_INDEX_FILE': str(other / 'missing-index'), 'GIT_CONFIG_COUNT': '1',
                'GIT_CONFIG_KEY_0': 'core.bare', 'GIT_CONFIG_VALUE_0': 'true',
                'GIT_CEILING_DIRECTORIES': str(self.workspace),
            }
            with mock.patch.dict(os.environ, redirected):
                bundle = self.build()
            self.assertEqual(bundle['git']['head_commit'], self.head)
            self.assertEqual(bundle['git']['base_commit'], self.base)

    def test_draft_paths_cannot_escape_story_or_leave_drafts(self):
        scenes = self.read(self.alpha / 'data/scenes.json')
        for relative in ('../beta/drafts/EP-001/SC-002.md',
                         'drafts/../bible/STYLE_GUIDE.md', 'bible/STYLE_GUIDE.md',
                         str(self.beta / 'drafts/EP-001/SC-002.md'), 'drafts/source.txt'):
            with self.subTest(relative=relative):
                scenes['scenes'][1]['draft_path'] = relative
                self.write(self.alpha / 'data/scenes.json', scenes)
                with self.assertRaises(ValueError):
                    self.build()

    def test_working_symlink_source_is_rejected_even_inside_same_story(self):
        destination = self.alpha / 'drafts/EP-001/OTHER.md'
        destination.write_bytes(WORKING_DRAFT)
        self.draft.unlink()
        try:
            self.draft.symlink_to(destination)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f'Symlink creation unavailable: {exc}')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.build()

    def test_git_symlink_base_is_rejected_without_following_its_target(self):
        path = self.draft.relative_to(self.workspace).as_posix()
        blob = self.git('hash-object', '-w', '--stdin', input=b'../../beta/story.json').decode('ascii').strip()
        self.git('update-index', '--add', '--cacheinfo', '120000', blob, path)
        self.git('commit', '--quiet', '-m', 'Synthetic Git symlink fixture')
        base = self.git('rev-parse', 'HEAD').decode('ascii').strip()
        with self.assertRaisesRegex(ValueError, 'Git symlink'):
            self.build(base=base)

    def test_oversized_working_and_base_sources_fail_without_truncation(self):
        oversized = b'X' * (review_bundle.MAX_SOURCE_BYTES + 1)
        self.draft.write_bytes(oversized)
        with self.assertRaisesRegex(ValueError, '1 MiB limit'):
            self.build()
        base = self.commit_draft(oversized)
        self.draft.write_bytes(WORKING_DRAFT)
        with self.assertRaisesRegex(ValueError, 'Base review source exceeds'):
            self.build(base=base)

    def test_invalid_utf8_and_binary_control_bytes_are_rejected(self):
        for value, diagnostic in ((b'\xff', 'UTF-8'), (b'METADATA\x00VALUE', 'nontext'),
                                  (b'METADATA\x01VALUE', 'nontext')):
            with self.subTest(value=value):
                self.draft.write_bytes(value)
                with self.assertRaisesRegex(ValueError, diagnostic):
                    self.build()
        base = self.commit_draft(b'\xff')
        self.draft.write_bytes(WORKING_DRAFT)
        with self.assertRaisesRegex(ValueError, 'Base draft.*UTF-8'):
            self.build(base=base)

    def test_repeated_reads_are_identical_and_do_not_mutate_sources_or_index(self):
        before = {str(path.relative_to(self.workspace)): path.read_bytes()
                  for root in (self.alpha, self.beta) for path in root.rglob('*') if path.is_file()}
        status = self.git('status', '--porcelain=v1')
        first = self.build()
        self.assertEqual(first, self.build())
        after = {str(path.relative_to(self.workspace)): path.read_bytes()
                 for root in (self.alpha, self.beta) for path in root.rglob('*') if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(self.git('status', '--porcelain=v1'), status)

    def test_changes_during_composition_fail_instead_of_attaching_stale_anchors(self):
        original_pack = review_bundle.story_engine.pack
        for mode in ('draft', 'style', 'head'):
            with self.subTest(mode=mode):
                def concurrent_change(root, target):
                    context = original_pack(root, target)
                    if mode == 'draft':
                        self.draft.write_bytes(self.draft.read_bytes() + b'CONCURRENT_METADATA\n')
                    elif mode == 'style':
                        path = self.alpha / 'bible/STYLE_GUIDE.md'
                        path.write_bytes(path.read_bytes() + b'CONCURRENT_STYLE_METADATA\n')
                    else:
                        (self.workspace / '.fixture-anchor').write_bytes(b'Concurrent synthetic anchor\n')
                        self.git('add', '--', '.fixture-anchor')
                        self.git('commit', '--quiet', '-m', 'Concurrent synthetic anchor')
                    return context

                with mock.patch.object(review_bundle.story_engine, 'pack', side_effect=concurrent_change):
                    with self.assertRaisesRegex(ValueError, 'changed while building review bundle'):
                        self.build()

    def test_pre_manifest_registry_reassignment_cannot_mix_draft_and_context(self):
        original_sources = review_bundle._sources
        replacement = self.alpha / 'drafts/EP-001/REASSIGNED.md'
        replacement.write_bytes(b'# Reassigned synthetic metadata fixture\n')

        def reassign_source(root, relative):
            scenes = self.read(self.alpha / 'data/scenes.json')
            scenes['scenes'][1]['draft_path'] = 'drafts/EP-001/REASSIGNED.md'
            self.write(self.alpha / 'data/scenes.json', scenes)
            return original_sources(root, relative)

        with mock.patch.object(review_bundle, '_sources', side_effect=reassign_source):
            with self.assertRaisesRegex(ValueError, 'registry changed while building review bundle'):
                self.build()

    def test_optional_history_created_after_enumeration_cannot_escape_source_manifest(self):
        original_sources = review_bundle._sources

        def create_history(root, relative):
            paths = original_sources(root, relative)
            self.write(root / 'data/state_history.json', {'schema_version': 1, 'baseline': None, 'deltas': []})
            return paths

        with mock.patch.object(review_bundle, '_sources', side_effect=create_history):
            with self.assertRaisesRegex(ValueError, 'registry changed while building review bundle'):
                self.build()


if __name__ == '__main__':
    unittest.main()
