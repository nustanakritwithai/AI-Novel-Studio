"""S1 world-model opt-in compatibility with v1 story roots and replay."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from . import test_story_roots as story_roots
except ImportError:
    try:
        from tests import test_story_roots as story_roots
    except ImportError:
        import test_story_roots as story_roots
from scripts import novelctl, registry_schema, story_config, story_engine, storyctl, world_state_model


ENGINE_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_BYTES = b"S1 synthetic evidence\n"


class WorldStateCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.alpha = story_roots.StoryRootTests.fixture(self, 'alpha', 'ALPHA_ONLY')
        self.beta = story_roots.StoryRootTests.fixture(self, 'beta', 'BETA_ONLY')
        self.write(self.workspace / 'studio.json', {
            'schema_version': 1, 'default_story': 'alpha',
        })

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def set_world_state(self, root, enabled=True):
        config = self.read(root / 'story.json')
        config['world_state'] = {'schema_version': 1, 'enabled': enabled}
        self.write(root / 'story.json', config)

    def evidence(self, root, relative='evidence/baseline.txt', content=EVIDENCE_BYTES):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def record(self, record_id='BASELINE-001', *, scene_id='SC-001', source_path='evidence/baseline.txt',
               local_status='PROPOSED', positions=None, holdings=None, narration_suborder=0,
               boundary='BEFORE', world_time=None):
        return {
            'id': record_id,
            'anchor': {
                'scene_id': scene_id,
                'narration_suborder': narration_suborder,
                'boundary': boundary,
                'world_time': world_time or {'status': 'UNKNOWN'},
            },
            'source': {
                'path': source_path,
                'sha256': hashlib.sha256(EVIDENCE_BYTES).hexdigest(),
            },
            'local_status': local_status,
            'positions': [] if positions is None else positions,
            'holdings': [] if holdings is None else holdings,
        }

    def model(self, slug, **changes):
        result = {
            'schema_version': 1,
            'story_slug': slug,
            'baseline': self.record(),
            'observations': [],
            'item_policies': [],
        }
        result.update(changes)
        return result

    def write_model(self, root, value):
        self.write(root / world_state_model.MODEL_PATH, value)

    def cli(self, story, *args):
        return subprocess.run(
            [sys.executable, str(ENGINE_ROOT / 'scripts/storyctl.py'),
             '--workspace', str(self.workspace), '--story', story, *map(str, args)],
            cwd=self.workspace, env=dict(os.environ, PYTHONIOENCODING='utf-8'),
            capture_output=True, text=True, encoding='utf-8', timeout=30,
        )

    def test_absent_or_disabled_switch_ignores_missing_and_malformed_stray_model(self):
        # Old story.json files have no switch; new disabled stories opt out explicitly.
        self.set_world_state(self.beta, enabled=False)
        for root in (self.alpha, self.beta):
            with self.subTest(story=root.name):
                model_path = root / world_state_model.MODEL_PATH
                model_path.parent.mkdir(parents=True, exist_ok=True)
                model_path.write_text('{ malformed JSON', encoding='utf-8')
                self.assertIsNone(world_state_model.load(root))
                self.assertEqual(novelctl.validate(root), ([], []))
                result = self.cli(root.name, 'check')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('PASS |', result.stdout)

    def test_empty_new_story_check_stays_compatible_and_enabled_empty_model_is_valid(self):
        root = storyctl.new_story(self.workspace, 'empty', 'Empty compatibility fixture')
        self.assertNotIn('world_state', story_config.load_config(root))
        result = self.cli('empty', 'check')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        self.set_world_state(root, enabled=True)
        missing = self.cli('empty', 'check')
        self.assertNotEqual(missing.returncode, 0, missing.stdout + missing.stderr)
        self.assertIn('data/world_model.json', missing.stdout + missing.stderr)

        self.write_model(root, {
            'schema_version': 1, 'story_slug': 'empty', 'baseline': None,
            'observations': [], 'item_policies': [],
        })
        valid = self.cli('empty', 'check')
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        self.assertIn('PASS |', valid.stdout)

    def test_world_state_config_switch_is_versioned_and_closed(self):
        original = self.read(self.alpha / 'story.json')
        invalid = (
            {'schema_version': 2, 'enabled': True},
            {'schema_version': True, 'enabled': False},
            {'schema_version': 1, 'enabled': 'true'},
            {'schema_version': 1, 'enabled': False, 'path': 'data/other.json'},
            None,
        )
        for value in invalid:
            with self.subTest(world_state=value):
                self.write(self.alpha / 'story.json', {**original, 'world_state': value})
                with self.assertRaisesRegex(ValueError, 'world_state'):
                    story_config.load_config(self.alpha)
        self.write(self.alpha / 'story.json', original)

    def test_enabled_model_rejects_unsupported_model_version_through_storyctl_check(self):
        self.set_world_state(self.alpha)
        self.evidence(self.alpha)
        bad = self.model('alpha')
        bad['schema_version'] = 2
        self.write_model(self.alpha, bad)
        result = self.cli('alpha', 'check')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('data/world_model.json', result.stdout + result.stderr)

    def test_fresh_stories_with_repeated_ids_load_only_their_own_models(self):
        self.set_world_state(self.alpha)
        self.set_world_state(self.beta)
        for root in (self.alpha, self.beta):
            self.evidence(root)
            self.write_model(root, self.model(root.name))

        self.assertEqual(novelctl.get(novelctl.load(self.alpha), 'characters', 'CHAR-001')['name'], 'ALPHA_ONLY_CHAR')
        self.assertEqual(novelctl.get(novelctl.load(self.beta), 'characters', 'CHAR-001')['name'], 'BETA_ONLY_CHAR')
        self.assertEqual(world_state_model.load(self.alpha)['story_slug'], 'alpha')
        self.assertEqual(world_state_model.load(self.beta)['story_slug'], 'beta')
        self.assertEqual(self.cli('alpha', 'check').returncode, 0)
        self.assertEqual(self.cli('beta', 'check').returncode, 0)

    def test_cross_story_only_reference_fails_against_selected_story_catalog(self):
        beta_chars = self.read(self.beta / 'data/characters.json')
        beta_chars['characters'].append({
            'id': 'CHAR-BETA-ONLY', 'name': 'Beta-only character', 'role': 'Synthetic metadata',
            'known_traits': [], 'unknowns': [], 'knowledge': [],
        })
        self.write(self.beta / 'data/characters.json', beta_chars)
        self.assertEqual(novelctl.get(novelctl.load(self.beta), 'characters', 'CHAR-BETA-ONLY')['id'],
                         'CHAR-BETA-ONLY')

        self.set_world_state(self.alpha)
        self.evidence(self.alpha)
        bad = self.model('alpha', baseline=self.record(
            positions=[{'character_id': 'CHAR-BETA-ONLY', 'location': {'status': 'UNKNOWN'}}]))
        self.write_model(self.alpha, bad)
        result = self.cli('alpha', 'check')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('CHAR-BETA-ONLY', result.stdout + result.stderr)
        self.assertIn('selected-story characters reference', result.stdout + result.stderr)

    def test_wrong_slug_fails_for_explicit_selection_without_falling_back(self):
        self.set_world_state(self.alpha)
        self.set_world_state(self.beta)
        self.evidence(self.alpha)
        self.evidence(self.beta)
        self.write_model(self.alpha, self.model('alpha'))
        self.write_model(self.beta, self.model('alpha'))

        alpha = self.cli('alpha', 'check')
        beta = self.cli('beta', 'check')
        self.assertEqual(alpha.returncode, 0, alpha.stdout + alpha.stderr)
        self.assertNotEqual(beta.returncode, 0, beta.stdout + beta.stderr)
        self.assertIn('story_slug does not match selected story beta', beta.stdout + beta.stderr)

    def test_v1_accepts_existing_non_english_ids_without_rewriting_or_migration(self):
        root = storyctl.new_story(self.workspace, 'legacy-ids', 'Legacy ID compatibility fixture')
        replacements = {
            'characters': {'characters': [{
                'id': '角色甲', 'name': '艾莉丝', 'role': 'Synthetic metadata',
                'known_traits': [], 'unknowns': [], 'knowledge': [],
            }]},
            'locations': {'locations': [{'id': '地点一', 'name': '旧港'}]},
            'items': {'items': [{'id': '物品一', 'name': '铜钥匙'}]},
        }
        for kind, payload in replacements.items():
            value = {'schema_version': 1, **payload}
            registry_schema.ensure_valid(kind, value)
            self.write(root / 'data' / f'{kind}.json', value)
        before = {kind: (root / 'data' / f'{kind}.json').read_bytes() for kind in replacements}

        self.assertIsNone(world_state_model.load(root))
        self.assertEqual(story_engine.validate(root), ([], []))
        self.assertEqual({kind: (root / 'data' / f'{kind}.json').read_bytes() for kind in replacements}, before)

    def test_unknown_values_and_editorial_metadata_survive_enabled_load(self):
        self.set_world_state(self.alpha)
        self.evidence(self.alpha)
        value = self.model(
            'alpha',
            baseline=self.record(
                positions=[{'character_id': 'CHAR-001', 'location': {'status': 'UNKNOWN'}}],
                holdings=[{'item_id': 'ITEM-001', 'holder': {'kind': 'UNKNOWN'}, 'quantity': None}],
            ),
            item_policies=[{'item_id': 'ITEM-001', 'tracking': 'STACK', 'important': True}],
            metadata={'editorial': {'custom_field': ['keep', None, 0]}},
        )
        self.write_model(self.alpha, value)

        self.assertEqual(world_state_model.load(self.alpha), value)

    def test_flashback_world_time_and_event_boundary_fields_do_not_change_v1_replay(self):
        before_pack = story_engine.pack(self.alpha, 'SC-002')
        before_replay = novelctl.state_before_target(self.alpha, 'SC-002')
        self.set_world_state(self.alpha)
        self.evidence(self.alpha)
        value = self.model(
            'alpha',
            baseline=self.record(
                'WORLD-LATE', scene_id='SC-002', narration_suborder=3, boundary='AFTER',
                world_time={'status': 'KNOWN', 'clock_id': 'main-clock', 'tick': 4, 'suborder': 0}),
            observations=[self.record(
                'WORLD-EARLY', scene_id='SC-001', narration_suborder=1, boundary='BEFORE',
                world_time={'status': 'KNOWN', 'clock_id': 'main-clock', 'tick': 400, 'suborder': 2})],
        )
        self.write_model(self.alpha, value)

        self.assertEqual(world_state_model.load(self.alpha), value)
        self.assertEqual(story_engine.pack(self.alpha, 'SC-002'), before_pack)
        self.assertEqual(novelctl.state_before_target(self.alpha, 'SC-002'), before_replay)
        self.assertIn('GitHub main and human approval have not been authenticated', before_pack)

    def test_approved_local_label_remains_unverified_and_is_not_used_by_pack_or_replay(self):
        before_pack = story_engine.pack(self.alpha, 'SC-002')
        before_replay = novelctl.state_before_target(self.alpha, 'SC-002')
        self.set_world_state(self.alpha)
        self.evidence(self.alpha)
        value = self.model('alpha', baseline=self.record(local_status='APPROVED'))
        self.write_model(self.alpha, value)

        loaded = world_state_model.load(self.alpha)
        self.assertEqual(loaded, value)
        self.assertEqual(loaded['baseline']['local_status'], 'APPROVED')
        self.assertEqual(world_state_model.HUMAN_APPROVAL, 'UNVERIFIED')
        self.assertEqual(story_engine.pack(self.alpha, 'SC-002'), before_pack)
        self.assertEqual(novelctl.state_before_target(self.alpha, 'SC-002'), before_replay)

    def test_changed_source_bytes_make_an_existing_declaration_stale(self):
        self.set_world_state(self.alpha)
        self.evidence(self.alpha)
        self.write_model(self.alpha, self.model('alpha'))
        self.evidence(self.alpha, content=b"changed after declaration\n")

        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch.*stale'):
            world_state_model.load(self.alpha)

    def test_source_path_cannot_escape_selected_story_or_expose_sibling_bytes(self):
        self.set_world_state(self.alpha)
        secret = b"BETA_PRIVATE_SYNTHETIC_SOURCE\n"
        self.evidence(self.beta, 'evidence/private.txt', secret)
        value = self.model('alpha', baseline=self.record(
            source_path='../beta/evidence/private.txt'))
        value['baseline']['source']['sha256'] = hashlib.sha256(secret).hexdigest()
        self.write_model(self.alpha, value)

        with self.assertRaisesRegex(ValueError, 'escapes selected story') as error:
            world_state_model.load(self.alpha)
        self.assertNotIn(secret.decode(), str(error.exception))
        result = self.cli('alpha', 'check')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('escapes selected story', result.stdout + result.stderr)
        self.assertNotIn(secret.decode(), result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
