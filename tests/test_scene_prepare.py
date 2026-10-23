"""Scene-start preparation contracts with synthetic metadata only."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import test_story_roots as story_roots
import test_house_cards as house_fixtures
from scripts import scene_prepare, story_engine

ENGINE = Path(__file__).resolve().parents[1]


class ScenePreparationTests(unittest.TestCase):
    read = staticmethod(story_roots.StoryRootTests.read)
    write = staticmethod(story_roots.StoryRootTests.write)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.alpha = story_roots.StoryRootTests.fixture(self, 'alpha', 'ALPHA_ONLY')
        self.beta = story_roots.StoryRootTests.fixture(self, 'beta', 'BETA_ONLY')
        self.write(self.workspace / 'studio.json', {'schema_version': 1, 'default_story': 'alpha'})
        (self.workspace / '.gitignore').write_bytes((ENGINE / '.gitignore').read_bytes())
        scenes = self.read(self.alpha / 'data/scenes.json')
        scenes['scenes'][1]['goal'] = 'FORBIDDEN_NEXT_SCENE_PLAN'
        scenes['scenes'][2]['outcome'] = 'FORBIDDEN_LATER_OUTCOME'
        self.write(self.alpha / 'data/scenes.json', scenes)
        episodes = self.read(self.alpha / 'data/episodes.json')
        episodes['episodes'][0]['questions'] = ['FORBIDDEN_UNTIMED_EPISODE_SPOILER']
        self.write(self.alpha / 'data/episodes.json', episodes)
        inventory = self.read(self.alpha / 'data/inventory_ledger.json')
        inventory['entries'][0]['notes'] = 'FORBIDDEN_TARGET_INVENTORY_GAIN'
        self.write(self.alpha / 'data/inventory_ledger.json', inventory)

    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self):
        return {p.relative_to(self.workspace).as_posix(): p.read_bytes()
                for p in self.workspace.rglob('*') if p.is_file()
                and '.git' not in p.parts and '.local' not in p.parts}

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ENGINE / 'scripts/storyctl.py'),
            '--workspace', str(self.workspace), '--story', 'alpha', 'prepare-scene', *map(str, args)],
            capture_output=True, text=True, encoding='utf-8', timeout=60,
            env=dict(os.environ, PYTHONIOENCODING='utf-8'))

    def house_fixture(self):
        fixture = house_fixtures.HouseCardTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        events = []
        for index, row in enumerate(self.read(fixture.root / 'data/scenes.json')['scenes'], 1):
            (fixture.root / 'scenes' / (row['id'] + '.md')).write_bytes(b'Synthetic scene card metadata.\n')
            events.append({'id': f'EV-{index:03}', 'scene_id': row['id'], 'episode_id': row['episode_id'],
                'order': row['order'], 'location_id': row['location_id'], 'actors': row['character_ids'],
                'effects_flags': {}, 'status': 'PLANNED'})
        self.write(fixture.root / 'data/events.json', {'schema_version': 1, 'events': events})
        return fixture

    def test_scene_only_context_excludes_next_plan_without_changing_legacy_pack(self):
        self.assertIn('FORBIDDEN_NEXT_SCENE_PLAN', story_engine.pack(self.alpha, 'SC-001'))
        report = scene_prepare.build(self.alpha, 'SC-001')
        text = json.dumps(report)
        self.assertNotIn('FORBIDDEN_NEXT_SCENE_PLAN', text)
        self.assertNotIn('FORBIDDEN_LATER_OUTCOME', text)
        self.assertNotIn('ALPHA_ONLY_LATE_KNOWLEDGE', text)
        self.assertNotIn('FORBIDDEN_UNTIMED_EPISODE_SPOILER', text)
        self.assertNotIn('FORBIDDEN_TARGET_INVENTORY_GAIN', text)
        self.assertNotIn('BETA_ONLY', text)
        self.assertEqual(report['scene_cursor'], {'scene_id': 'SC-001', 'boundary': 'BEFORE'})
        self.assertIsNone(report['world_cursor'])
        self.assertEqual(report['source_evidence']['mode'], 'working-tree')
        self.assertEqual(report['pov_knowledge']['availability'], 'UNKNOWN')
        self.assertEqual(report['house_reference']['availability'], 'NOT_REQUESTED')
        self.assertIn('ALPHA_ONLY_STYLE', report['author_planning_context']['content'])
        self.assertFalse(report['canon_change_authorized'])
        self.assertFalse(report['ledger_apply_authorized'])
        self.assertEqual(report['human_editorial_approval'], 'UNVERIFIED')

    def test_repeated_preparation_preserves_every_source_and_story_isolation(self):
        before = self.snapshot()
        self.assertEqual(scene_prepare.build(self.alpha, 'SC-001'), scene_prepare.build(self.alpha, 'SC-001'))
        beta = json.dumps(scene_prepare.build(self.beta, 'SC-001'))
        self.assertIn('BETA_ONLY', beta)
        self.assertNotIn('ALPHA_ONLY', beta)
        self.assertEqual(self.snapshot(), before)

    def test_unknown_scene_episode_or_foreign_pov_is_rejected(self):
        for target in ('SC-999', 'EP-001'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                scene_prepare.build(self.alpha, target)
        with self.assertRaises(ValueError):
            scene_prepare.build(self.alpha, 'SC-001', pov='CHAR-999')

    def test_committed_preparation_exposes_raw_crlf_and_edited_source_differences(self):
        style = self.alpha / 'bible/STYLE_GUIDE.md'
        style.write_bytes(b'ALPHA_ONLY_STYLE\n')
        def git(*args):
            return subprocess.run(['git', '-C', str(self.workspace), '-c', 'core.autocrlf=false',
                '-c', 'user.name=Synthetic fixture', '-c', 'user.email=fixture@example.invalid',
                '-c', 'commit.gpgsign=false', *args], check=True, capture_output=True,
                text=True, encoding='utf-8', timeout=30)
        git('init', '-q')
        git('add', '--all')
        git('commit', '-q', '-m', 'Synthetic exact-source baseline')
        expected = git('rev-parse', 'HEAD').stdout.strip()
        for raw in (b'ALPHA_ONLY_STYLE\r\n', b'ALPHA_ONLY_STYLE\nUNAPPROVED_STYLE_EDIT\n'):
            style.write_bytes(raw)
            report = scene_prepare.build(self.alpha, 'SC-001', source_mode='committed')
            self.assertEqual(report['source_evidence']['commit'], expected)
            self.assertEqual(report['source_evidence']['mode'], 'committed')
            source = report['source_evidence']['sources']['bible/STYLE_GUIDE.md']
            self.assertEqual(source['raw_status'], 'DIFFERENT')
            self.assertNotEqual(source['raw_sha256'], source['selected_sha256'])
            self.assertNotIn('UNAPPROVED_STYLE_EDIT', report['author_planning_context']['content'])

    def test_explicit_world_cursor_is_separate_and_disabled_world_is_unknown(self):
        cursor = {'clock_id': 'CLOCK-EXPLICIT', 'tick': 0, 'suborder': 0, 'boundary': 'BEFORE'}
        report = scene_prepare.build(self.alpha, 'SC-001', world_cursor=cursor)
        self.assertEqual(report['world_cursor'], cursor)
        self.assertEqual(report['world_preview']['result']['availability'], 'UNKNOWN')
        self.assertEqual(report['world_preview']['audience'], 'AUTHOR_ONLY_NOT_POV_KNOWLEDGE')
        self.assertEqual(report['cursor_mapping'], 'UNKNOWN_NO_AUTOMATIC_MAPPING')
        for key in cursor:
            partial = copy.deepcopy(cursor)
            del partial[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                scene_prepare.build(self.alpha, 'SC-001', world_cursor=partial)

    def test_metadata_change_during_build_refuses_a_mixed_snapshot(self):
        cursor = {'clock_id': 'CLOCK-EXPLICIT', 'tick': 0, 'suborder': 0, 'boundary': 'BEFORE'}
        def change_metadata(*args, **kwargs):
            value = self.read(self.alpha / 'data/characters.json')
            value['characters'][0]['name'] = 'CHANGED_DURING_BUILD'
            self.write(self.alpha / 'data/characters.json', value)
            return {'availability': 'UNKNOWN'}
        with mock.patch.object(scene_prepare.world_history, 'preview', side_effect=change_metadata):
            with self.assertRaisesRegex(ValueError, 'metadata changed'):
                scene_prepare.build(self.alpha, 'SC-001', world_cursor=cursor)

    def test_cli_private_output_and_partial_cursor_fail_closed(self):
        before = self.snapshot()
        out = self.workspace / '.local/preparation/scene.json'
        result = self.cli('SC-001', '--out', out)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.read(out)['kind'], 'SCENE_PREPARATION')
        for args in (('SC-001', '--world-tick', '0'),
                     ('SC-001', '--world-clock', 'CLOCK-EXPLICIT'),
                     ('SC-001', '--out', self.workspace / 'public.json')):
            bad = self.cli(*args)
            self.assertNotEqual(bad.returncode, 0, bad.stdout + bad.stderr)
            self.assertNotIn('Traceback', bad.stderr)
        self.assertFalse((self.workspace / 'public.json').exists())
        self.assertEqual(self.snapshot(), before)

    def test_pov_inventory_and_threads_require_prior_local_approved_evidence(self):
        scenes = self.read(self.alpha / 'data/scenes.json')
        scenes['scenes'][0]['status'] = 'APPROVED'
        self.write(self.alpha / 'data/scenes.json', scenes)
        source = self.alpha / scenes['scenes'][0]['draft_path']
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b'Synthetic approved-source marker, not human approval.\n')
        chars = self.read(self.alpha / 'data/characters.json')
        chars['characters'][0]['knowledge'].append({'after_scene': 'SC-001', 'knows': 'EARLIER_LOCAL_FACT'})
        self.write(self.alpha / 'data/characters.json', chars)
        inventory = self.read(self.alpha / 'data/inventory_ledger.json')
        inventory['entries'][0]['status'] = 'APPROVED'
        self.write(self.alpha / 'data/inventory_ledger.json', inventory)
        threads = self.read(self.alpha / 'data/threads.json')
        later = copy.deepcopy(threads['threads'][0])
        later.update(id='THREAD-002', title='FORBIDDEN_FUTURE_THREAD', setup_scene_id='SC-003', payoff_scene_id=None)
        threads['threads'].append(later)
        self.write(self.alpha / 'data/threads.json', threads)
        report = scene_prepare.build(self.alpha, 'SC-002')
        self.assertEqual([k['knows'] for k in report['pov_knowledge']['entries']], ['EARLIER_LOCAL_FACT'])
        self.assertNotIn('ALPHA_ONLY_LATE_KNOWLEDGE', json.dumps(report))
        entries = report['scene_references']['inventory']['earlier_local_approved_events']
        self.assertEqual(len(entries), 1)
        self.assertIsNone(entries[0]['quantity'])
        self.assertEqual(report['scene_references']['inventory']['current_balance'], 'UNKNOWN')
        self.assertNotIn('FORBIDDEN_FUTURE_THREAD', json.dumps(report))
        self.assertEqual(report['scene_references']['open_threads']['historical_open_state'], 'UNKNOWN')

    def test_house_view_keeps_unfinished_stairs_and_future_repairs_unknown(self):
        fixture = self.house_fixture()
        report = scene_prepare.build(fixture.root, 'SC-018', house_id='LOC-009')
        card = report['house_reference']
        self.assertEqual(card['boundary'], 'BEFORE')
        self.assertEqual(card['facts']['material']['value'], 'STONE')
        self.assertIn('stairs', card['unknown_fields'])
        self.assertNotIn('repair', card['facts'])
        self.assertEqual(card['world_time'], 'UNKNOWN')
        self.assertNotIn('Synthetic later episode', report['author_planning_context']['content'])

    def test_invalid_house_source_refuses_the_entire_preparation(self):
        fixture = self.house_fixture()
        fixture._write_source(b'Stale synthetic reference.\n')
        with self.assertRaisesRegex(ValueError, 'pinned|hash|source'):
            scene_prepare.build(fixture.root, 'SC-018', house_id='LOC-009')
