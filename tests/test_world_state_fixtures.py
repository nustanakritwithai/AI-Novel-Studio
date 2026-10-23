"""Check the published metadata-only two-story examples, including source bytes."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import world_state_model


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = b'S1 synthetic evidence\n'


class WorldStateFixtureTests(unittest.TestCase):
    def test_line_terminators_never_pass_stable_id_or_digest_grammar(self):
        model = json.loads((ROOT / 'tests/fixtures/world_state/synthetic_valid.json').read_text(encoding='utf-8'))['cases'][0]['model']
        for suffix in ('\n', '\r', '\r\n', '\u2028', '\u2029'):
            for field in ('id', 'clock_id', 'sha256', 'story_slug'):
                with self.subTest(field=field, suffix=repr(suffix)):
                    changed = copy.deepcopy(model)
                    target = (changed if field == 'story_slug' else changed['baseline'] if field == 'id'
                              else changed['baseline']['source'] if field == 'sha256'
                              else changed['baseline']['anchor']['world_time'])
                    target[field] += suffix
                    self.assertTrue(list(world_state_model.validator().iter_errors(changed)))

    def test_two_independent_examples_round_trip_without_deriving_state(self):
        cases = json.loads((ROOT / 'tests/fixtures/world_state/synthetic_valid.json').read_text(encoding='utf-8'))['cases']
        self.assertEqual([case['slug'] for case in cases], ['alpha', 'beta'])
        original = copy.deepcopy(cases)
        with tempfile.TemporaryDirectory() as directory:
            for case in cases:
                with self.subTest(story=case['slug']):
                    root = Path(directory) / case['slug']
                    (root / 'data').mkdir(parents=True)
                    (root / 'evidence').mkdir()
                    (root / 'story.json').write_text(json.dumps({
                        'schema_version': 1, 'slug': case['slug'], 'title': 'Synthetic metadata',
                        'extensions': {'gameplay': False}, 'rules': [],
                        'world_state': {'schema_version': 1, 'enabled': True},
                    }), encoding='utf-8')
                    (root / world_state_model.MODEL_PATH).write_text(json.dumps(case['model'], ensure_ascii=False), encoding='utf-8')
                    (root / 'evidence/baseline.txt').write_bytes(EVIDENCE)
                    db = {kind: {'schema_version': 1, kind: rows} for kind, rows in case['catalogs'].items()}
                    loaded = world_state_model.load(root, db)
                    self.assertEqual(loaded, case['model'])
                    self.assertEqual(loaded['baseline']['source']['sha256'], hashlib.sha256(EVIDENCE).hexdigest())
                    self.assertLess(loaded['observations'][0]['anchor']['world_time']['tick'],
                                    loaded['baseline']['anchor']['world_time']['tick'])
                    wrong_story = 'beta' if case['slug'] == 'alpha' else 'alpha'
                    self.assertTrue(world_state_model.validation_errors(loaded, db, wrong_story))
                    (root / 'evidence/baseline.txt').write_bytes(EVIDENCE + b'changed')
                    with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                        world_state_model.load(root, db)
        self.assertEqual(cases, original)


if __name__ == '__main__':
    unittest.main()
