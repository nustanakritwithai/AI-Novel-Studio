"""E1 story isolation and compatibility using metadata-only synthetic fixtures."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import novelctl, story_config, story_engine, storyctl

ENGINE_ROOT = Path(__file__).resolve().parents[1]


class StoryRootTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.alpha = self.fixture('alpha', 'ALPHA_ONLY')
        self.beta = self.fixture('beta', 'BETA_ONLY')
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
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def fixture(self, slug, token):
        """Three ordered scene records, never prose or approved history."""
        root = storyctl.new_story(self.workspace, slug, token + '_TITLE')
        config = self.read(root / 'story.json')
        config['rules'] = [token + '_RULE']
        self.write(root / 'story.json', config)
        (root / 'bible/STYLE_GUIDE.md').write_text(token + '_STYLE\n', encoding='utf-8')
        values = {
            'canon': {'project': token + '_TITLE', 'facts': [{
                'id': 'FACT-001', 'status': 'LOCKED', 'scope': 'GLOBAL',
                'origin': 'USER_DIRECTIVE', 'statement': token + '_FACT',
            }]},
            'characters': {'characters': [{
                'id': 'CHAR-001', 'name': token + '_CHAR', 'role': 'Synthetic metadata role',
                'status': 'IN_STORY', 'aliases': [], 'goals': [], 'known_traits': [],
                'unknowns': [], 'first_scene': 'SC-001',
                'knowledge': [{'after_scene': 'SC-002', 'knows': token + '_LATE_KNOWLEDGE'}],
            }]},
            'locations': {'locations': [{'id': 'LOC-001', 'name': token + '_LOCATION'}]},
            'items': {'items': [{'id': 'ITEM-001', 'name': token + '_ITEM'}]},
            'episodes': {'episodes': [{
                'id': 'EP-001', 'title': token + '_EPISODE', 'status': 'OUTLINE',
                'scene_ids': ['SC-001', 'SC-002', 'SC-003'], 'questions': [],
                'approved_final_draft': None,
            }]},
            'scenes': {'scenes': []},
            'events': {'events': []},
            'inventory_ledger': {'entries': [{
                'id': 'INV-001', 'scene_id': 'SC-001', 'owner_id': 'CHAR-001',
                'item_id': 'ITEM-001', 'quantity': None, 'operation': 'GAIN',
                'status': 'PLANNED', 'notes': token + '_INVENTORY_METADATA',
            }]},
            'threads': {'threads': [{
                'id': 'THREAD-001', 'title': token + '_THREAD', 'status': 'OPEN',
                'setup_scene_id': 'SC-001', 'payoff_scene_id': 'SC-003',
                'owner_character_id': 'CHAR-001', 'canon_refs': ['FACT-001'],
            }]},
            'relationships': {'relationships': []},
            'decisions': {'decisions': []},
            'story_state': {
                'active_episode': 'EP-001', 'phase': 'OUTLINE_NOT_CANON_PROSE',
                'approved_through_scene': None, 'flags': {},
                'fixture_metadata': token + '_STATE', 'pending_review': [],
            },
        }
        for number in range(1, 4):
            sid = f'SC-{number:03}'
            effects = {f'stage_{number}': True}
            values['scenes']['scenes'].append({
                'id': sid, 'episode_id': 'EP-001', 'order': number,
                'title': token + f'_SCENE_{number}', 'status': 'PLANNED',
                'pov': 'CHAR-001', 'location_id': 'LOC-001',
                'character_ids': ['CHAR-001'], 'item_ids': ['ITEM-001'],
                'canon_refs': ['FACT-001'], 'goal': 'Synthetic goal metadata',
                'conflict': 'Synthetic conflict metadata', 'outcome': 'Synthetic outcome metadata',
                'beats': ['Synthetic beat metadata'],
                'requires_flags': [f'stage_{number - 1}'] if number > 1 else [],
                'effects_flags': effects, 'draft_path': f'drafts/EP-001/{sid}.md',
            })
            values['events']['events'].append({
                'id': f'EV-{number:03}', 'scene_id': sid, 'episode_id': 'EP-001',
                'order': number, 'location_id': 'LOC-001', 'actors': ['CHAR-001'],
                'effects_flags': copy.deepcopy(effects), 'status': 'PLANNED',
            })
            (root / 'scenes' / f'{sid}.md').write_text(
                f'# {sid}\nSynthetic scene metadata fixture; no narrative prose or approval.\n',
                encoding='utf-8')
        for kind, value in values.items():
            self.write(root / 'data' / f'{kind}.json', {'schema_version': 1, **value})
        return root

    def run_cli(self, script, *args):
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        return subprocess.run(
            [sys.executable, str(ENGINE_ROOT / 'scripts' / script), *map(str, args)],
            cwd=self.workspace, env=env, capture_output=True, text=True, encoding='utf-8',
            timeout=30,
        )

    def test_two_generic_stories_check_and_pack_without_leakage(self):
        for root, own, other in ((self.alpha, 'ALPHA_ONLY', 'BETA_ONLY'),
                                 (self.beta, 'BETA_ONLY', 'ALPHA_ONLY')):
            with self.subTest(story=root.name):
                self.assertEqual(novelctl.validate(root), ([], []))
                self.assertEqual(story_engine.validate(root), ([], []))
                pack = story_engine.pack(root, 'SC-002')
                for suffix in ('_FACT', '_RULE', '_STYLE', '_CHAR', '_STATE'):
                    self.assertIn(own + suffix, pack)
                self.assertNotIn(other, pack)
                for forbidden in ('LAST ISLAND', 'WORLD-CHAMPIONSHIP', '2×2',
                                  'single scrap crate', 'private-game opening'):
                    self.assertNotIn(forbidden, pack.upper() if forbidden.isupper() else pack)
                self.assertFalse((root / 'data/mechanics.json').exists())
                self.assertFalse((root / 'data/sources.json').exists())
                self.assertEqual(novelctl.get(novelctl.load(root), 'scenes', 'SC-001')['id'], 'SC-001')

    def test_workspace_default_and_explicit_story_selection(self):
        self.assertEqual(story_config.resolve_root(self.workspace), self.alpha)
        self.assertEqual(story_config.resolve_root(self.workspace, 'beta'), self.beta)
        self.assertEqual(story_config.resolve_root(self.beta), self.beta)
        default_pack = story_engine.pack(self.workspace, 'SC-002')
        self.assertIn('ALPHA_ONLY_FACT', default_pack)
        self.assertNotIn('BETA_ONLY', default_pack)
        self.assertNotIn('ALPHA_ONLY', novelctl.status(self.beta))
        self.assertIn('BETA_ONLY', novelctl.status(self.beta))

    def test_knowledge_boundaries_hold_for_each_story(self):
        for root, token in ((self.alpha, 'ALPHA_ONLY'), (self.beta, 'BETA_ONLY')):
            with self.subTest(story=root.name):
                self.assertNotIn(token + '_LATE_KNOWLEDGE', story_engine.pack(root, 'SC-002'))
                self.assertIn(token + '_LATE_KNOWLEDGE', story_engine.pack(root, 'SC-003'))
                self.assertNotIn(token + '_LATE_KNOWLEDGE', story_engine.pack(root, 'EP-001'))

    def test_new_scaffold_is_empty_metadata_and_has_no_approval(self):
        root = storyctl.new_story(self.workspace, 'empty', 'Empty metadata fixture')
        self.assertEqual(story_engine.validate(root), ([], []))
        self.assertFalse(story_config.load_config(root)['extensions']['gameplay'])
        for kind in novelctl.CORE_DATA:
            data = self.read(root / 'data' / f'{kind}.json')
            self.assertEqual(data['schema_version'], 1)
            if kind == 'story_state':
                self.assertIsNone(data['approved_through_scene'])
            else:
                key = 'facts' if kind == 'canon' else 'entries' if kind == 'inventory_ledger' else kind
                self.assertEqual(data[key], [])
        self.assertEqual(story_engine.load_index(root)['episodes'], [])
        self.assertEqual([p for p in (root / 'drafts').rglob('*') if p.is_file() and p.name != '.gitkeep'], [])

    def test_scaffold_never_overwrites_an_existing_story(self):
        before = {str(p.relative_to(self.alpha)): p.read_bytes()
                  for p in self.alpha.rglob('*') if p.is_file()}
        with self.assertRaises((ValueError, FileExistsError)):
            storyctl.new_story(self.workspace, 'alpha', 'Replacement must not be written')
        after = {str(p.relative_to(self.alpha)): p.read_bytes()
                 for p in self.alpha.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_invalid_story_slugs_cannot_escape_or_fall_back(self):
        for slug in ('', '.', '..', '../beta', 'alpha/../beta', '..\\beta', '/tmp', 'UPPER'):
            with self.subTest(slug=slug):
                with self.assertRaises(ValueError):
                    story_config.resolve_root(self.workspace, slug)
                with self.assertRaises(ValueError):
                    storyctl.new_story(self.workspace, slug, 'Invalid fixture')
        with self.assertRaises(ValueError):
            story_config.resolve_root(self.workspace, 'missing')

    def test_config_schema_and_field_types_are_checked(self):
        original = self.read(self.beta / 'story.json')
        mutations = [
            {'schema_version': 2}, {'schema_version': True}, {'title': ''},
            {'extensions': {'gameplay': 'false'}}, {'rules': 'not a list'},
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.write(self.beta / 'story.json', {**original, **mutation})
                with self.assertRaises(ValueError):
                    story_config.load_config(self.beta)
        self.write(self.beta / 'story.json', original)

    def test_invalid_selected_config_does_not_fall_back_to_default(self):
        (self.beta / 'story.json').write_text('{ broken JSON', encoding='utf-8')
        with self.assertRaises((ValueError, OSError)):
            story_engine.pack(self.beta, 'SC-002')
        self.assertIn('ALPHA_ONLY_FACT', story_engine.pack(self.workspace, 'SC-002'))

    def test_registry_schema_version_is_validated(self):
        path = self.alpha / 'data/scenes.json'
        value = self.read(path)
        value['schema_version'] = 2
        self.write(path, value)
        errors, _ = novelctl.validate(self.alpha)
        self.assertTrue(any('schema_version' in error for error in errors), errors)
        with self.assertRaises(ValueError):
            story_engine.pack(self.alpha, 'SC-002')
        ledger = story_engine.load_index(self.beta)
        ledger['schema_version'] = True
        self.write(self.beta / 'ledger/index.json', ledger)
        self.assertTrue(any('schema_version' in error for error in story_engine.validate(self.beta)[0]))

    def test_disabled_gameplay_does_not_silently_accept_references(self):
        path = self.alpha / 'data/scenes.json'
        value = self.read(path)
        value['scenes'][0].update(mechanic_refs=['MECH-MISSING'], source_refs=['SRC-MISSING'])
        self.write(path, value)
        errors, _ = novelctl.validate(self.alpha)
        self.assertTrue(any('MECH-MISSING' in error for error in errors), errors)
        self.assertTrue(any('SRC-MISSING' in error for error in errors), errors)
        with self.assertRaises(ValueError):
            story_engine.pack(self.alpha, 'SC-002')
        with self.assertRaisesRegex(ValueError, 'gameplay extension'):
            novelctl.build_brief(self.alpha, 'SC-001')

    def test_enabled_gameplay_requires_and_checks_evidence(self):
        config = self.read(self.alpha / 'story.json')
        config['extensions']['gameplay'] = True
        self.write(self.alpha / 'story.json', config)
        self.assertTrue(novelctl.validate(self.alpha)[0])
        self.write(self.alpha / 'data/sources.json', {'schema_version': 1, 'sources': [{
            'id': 'SRC-001', 'access_level': 'TRANSCRIPT_ONLY', 'title': 'Synthetic source metadata',
        }]})
        self.write(self.alpha / 'data/mechanics.json', {'schema_version': 1, 'mechanics': [{
            'id': 'MECH-001', 'title': 'Synthetic mechanic metadata',
            'game_verification': 'VISUALLY_VERIFIED', 'source_ids': ['SRC-001'],
            'story_requirement': 'PROPOSED', 'notes': 'Synthetic evidence metadata only',
        }]})
        items = self.read(self.alpha / 'data/items.json')
        items['items'][0]['gameplay_mechanic_id'] = 'MECH-001'
        self.write(self.alpha / 'data/items.json', items)
        errors, _ = novelctl.validate(self.alpha)
        self.assertTrue(any('cannot claim visual verification' in error for error in errors), errors)
        with self.assertRaises(ValueError):
            story_engine.pack(self.alpha, 'SC-002')
        mechanics = self.read(self.alpha / 'data/mechanics.json')
        mechanics['mechanics'][0]['game_verification'] = 'TRANSCRIPT_SUPPORTED'
        self.write(self.alpha / 'data/mechanics.json', mechanics)
        self.assertEqual(novelctl.validate(self.alpha), ([], []))

    def test_canon_and_knowledge_reference_violations_still_fail(self):
        canon = self.read(self.alpha / 'data/canon.json')
        canon['facts'][0]['origin'] = 'ASSISTANT_PROPOSAL'
        self.write(self.alpha / 'data/canon.json', canon)
        errors, _ = novelctl.validate(self.alpha)
        self.assertTrue(any('assistant proposal' in error for error in errors), errors)
        with self.assertRaises(ValueError):
            story_engine.pack(self.alpha, 'SC-002')
        chars = self.read(self.beta / 'data/characters.json')
        chars['characters'][0]['knowledge'][0]['after_scene'] = 'SC-MISSING'
        self.write(self.beta / 'data/characters.json', chars)
        self.assertTrue(any('SC-MISSING' in error for error in novelctl.validate(self.beta)[0]))

    def test_unapproved_history_cannot_enter_either_story_pack(self):
        index = story_engine.load_index(self.alpha)
        index['episodes'].append({
            'id': 'EP-001', 'scene_ids': ['SC-001', 'SC-002', 'SC-003'],
            'summary_path': 'ledger/episodes/EP-001.md', 'approval': {},
        })
        self.write(self.alpha / 'ledger/index.json', index)
        (self.alpha / 'ledger/episodes/EP-001.md').write_text(
            'UNAPPROVED_METADATA_SENTINEL\n' * 5, encoding='utf-8')
        errors, _ = story_engine.validate(self.alpha)
        self.assertTrue(any('unapproved episode' in error for error in errors), errors)
        self.assertTrue(any('approval' in error for error in errors), errors)
        with self.assertRaises(ValueError):
            story_engine.pack(self.alpha, 'SC-002')
        self.assertNotIn('UNAPPROVED_METADATA_SENTINEL', story_engine.pack(self.beta, 'SC-002'))

    def test_story_local_evidence_paths_cannot_read_a_sibling(self):
        with self.assertRaises(ValueError):
            story_engine.within(self.alpha, '../beta/drafts/EP-001/SC-001.md', 'drafts')

    def test_resource_symlinks_cannot_read_a_sibling(self):
        link = self.alpha / 'sibling'
        try:
            link.symlink_to(self.beta, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f'Symlink creation unavailable: {exc}')
        with self.assertRaises(ValueError):
            story_config.story_path(self.alpha, 'sibling/data/canon.json')
        with self.assertRaises(ValueError):
            story_engine.within(self.alpha, 'sibling/bible/STYLE_GUIDE.md', 'sibling')

    def test_new_and_legacy_cli_routes_use_selected_story(self):
        commands = [
            ('storyctl.py', '--workspace', self.workspace, '--story', 'beta', 'check'),
            ('novelctl.py', '--root', self.beta, 'check'),
            ('story_engine.py', '--root', self.beta, 'check'),
        ]
        for script, *args in commands:
            with self.subTest(script=script):
                result = self.run_cli(script, *args)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('PASS', result.stdout)
        for script, root_flag, command in (
            ('storyctl.py', '--workspace', 'pack'),
            ('novelctl.py', '--root', 'brief'),
            ('story_engine.py', '--root', 'pack'),
        ):
            with self.subTest(script=script, command=command):
                out = self.workspace / (script + '.md')
                result = self.run_cli(script, root_flag, self.workspace, '--story', 'beta',
                                      command, 'SC-002', '--out', out)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                text = out.read_text(encoding='utf-8')
                self.assertIn('BETA_ONLY_FACT', text)
                self.assertNotIn('ALPHA_ONLY', text)

    def test_old_default_cli_invocations_remain_supported(self):
        for script in ('novelctl.py', 'story_engine.py'):
            with self.subTest(script=script):
                result = self.run_cli(script, 'check')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('PASS', result.stdout)

    def test_new_cli_creates_only_requested_empty_story(self):
        result = self.run_cli('storyctl.py', '--workspace', self.workspace,
                              'new', 'gamma', '--title', 'Gamma metadata fixture')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        root = self.workspace / 'stories/gamma'
        self.assertEqual(story_engine.validate(root), ([], []))
        self.assertEqual(self.read(root / 'data/canon.json')['facts'], [])
        result = self.run_cli('storyctl.py', '--workspace', self.workspace,
                              'new', 'gamma', '--title', 'Must not overwrite')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.read(root / 'story.json')['title'], 'Gamma metadata fixture')


if __name__ == '__main__':
    unittest.main()
