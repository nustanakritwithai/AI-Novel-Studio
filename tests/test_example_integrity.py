"""Verify the non-destructive relocation against baseline Git byte hashes."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ExampleIntegrityTests(unittest.TestCase):
    def test_all_relocated_example_files_preserve_original_git_bytes(self):
        manifest = json.loads((ROOT / 'tests/last_island_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['source_commit'], 'e2f82d2971526bd77ac82999f37f24fe5b7a8816')
        self.assertEqual(len(manifest['files']), 54)
        for item in manifest['files']:
            with self.subTest(source=item['source']):
                target = ROOT / item['path']
                self.assertTrue(target.resolve().is_relative_to(ROOT / 'stories/last-island'))
                self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), item['sha256'])


if __name__ == '__main__':
    unittest.main()
