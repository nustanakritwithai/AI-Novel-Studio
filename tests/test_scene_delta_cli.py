"""Actual CLI admission checks using synthetic metadata only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_story_roots as fixtures

ENGINE = Path(__file__).resolve().parents[1]


class SceneDeltaCLITests(unittest.TestCase):
    read = staticmethod(fixtures.StoryRootTests.read)
    write = staticmethod(fixtures.StoryRootTests.write)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.root = fixtures.StoryRootTests.fixture(self, 'alpha', 'ALPHA_ONLY')
        self.write(self.workspace / 'studio.json', {'schema_version': 1, 'default_story': 'alpha'})
        self.raw = b'SYNTHETIC: unfinished frame.\n'
        path = self.root / 'drafts/EP-001/SC-001.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.raw)
        self.claims = self.workspace / '.local/claims.json'
        self.claims.parent.mkdir()
        self.write(self.claims, {'schema_version': 1, 'scene_id': 'SC-001',
            'draft_path': 'drafts/EP-001/SC-001.md', 'source_sha256': hashlib.sha256(self.raw).hexdigest(),
            'observations': [{'id': 'OBS-001', 'category': 'CONSTRUCTION',
                'claim': 'Frame unfinished; usable status UNKNOWN.',
                'locator': {'start_line': 1, 'end_line': 1, 'quote': 'unfinished frame'},
                'subject': {'kind': 'LOCATION', 'id': 'LOC-001'}}]})

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ENGINE / 'scripts/storyctl.py'),
            '--workspace', str(self.workspace), '--story', 'alpha', 'propose-deltas',
            'SC-001', '--claims', str(self.claims), *map(str, args)], capture_output=True,
            text=True, encoding='utf-8', timeout=60,
            env=dict(os.environ, PYTHONIOENCODING='utf-8'))

    def test_private_output_is_immutable_and_existing_source_is_preserved(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()}
        out = self.workspace / '.local/proposal-v1.json'
        result = self.cli('--out', out)
        self.assertEqual(result.returncode, 0, result.stderr)
        first = out.read_bytes()
        self.assertFalse(json.loads(first)['ledger_apply_authorized'])
        repeated = self.cli('--out', out)
        self.assertNotEqual(repeated.returncode, 0)
        self.assertEqual(out.read_bytes(), first)
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): p.read_bytes()
                                for p in self.root.rglob('*') if p.is_file()})
        public = self.workspace / 'public.json'
        self.assertNotEqual(self.cli('--out', public).returncode, 0)
        self.assertFalse(public.exists())

    def test_duplicate_or_oversize_claims_are_rejected_without_output(self):
        out = self.workspace / '.local/rejected.json'
        for raw in (b'{"scene_id":"SC-001","scene_id":"SC-002"}', b' ' * (1024 * 1024 + 1)):
            self.claims.write_bytes(raw)
            result = self.cli('--out', out)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback', result.stderr)
            self.assertFalse(out.exists())

    def test_stdout_is_deterministic_and_explicit_previous_is_not_approval(self):
        first = self.cli()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, self.cli().stdout)
        previous = self.workspace / '.local/previous.json'
        previous.write_text(first.stdout, encoding='utf-8')
        second = self.cli('--previous', previous)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(first.stdout), json.loads(second.stdout))
        self.assertEqual(json.loads(second.stdout)['human_editorial_approval'], 'UNVERIFIED')


if __name__ == '__main__':
    unittest.main()
