"""Deterministic CLI acceptance for the synthetic scene workflow fixture."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts import scene_workflow_acceptance as fixture


class SceneWorkflowAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def read(self, path):
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def snapshot(root):
        return {path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob('*') if path.is_file()}

    def test_fixture_facts_bind_to_frozen_source_and_existing_story_is_untouched(self):
        story = fixture.populate(self.root)
        source = story / 'bible/SC001_FIXTURE_FACTS.md'
        source_bytes = source.read_bytes()
        facts = self.read(story / 'data/canon.json')['facts']
        self.assertEqual(len(facts), 4)
        for fact in facts:
            evidence = fact['source_evidence']
            self.assertEqual(evidence['path'], 'bible/SC001_FIXTURE_FACTS.md')
            self.assertEqual(evidence['sha256'], hashlib.sha256(source_bytes).hexdigest())
            lines = source_bytes.decode('utf-8').splitlines()
            quote = lines[evidence['start_line'] - 1]
            self.assertEqual(evidence['start_line'], evidence['end_line'])
            self.assertEqual(evidence['quote'], quote)
            self.assertIn('SYNTHETIC_FIXTURE_ONLY', fact['origin'])
            self.assertIn('no record in this workspace is human editorial approval', fact['notes'])

        scenes = self.read(story / 'data/scenes.json')['scenes']
        self.assertEqual([row['fixture_world_time']['tick'] for row in scenes], [10, 5, 20])
        self.assertEqual([row['fixture_world_time']['label'] for row in scenes],
                         ['present', 'flashback', 'future'])
        self.assertEqual(scenes[0]['draft_path'], fixture.SC001_DRAFT)
        self.assertEqual(scenes[2]['goal'], fixture.FUTURE_PLAN_MARKER)
        before = self.snapshot(story)
        with self.assertRaises(ValueError):
            fixture.populate(self.root)
        self.assertEqual(before, self.snapshot(story))

    def test_runner_uses_cli_and_keeps_approval_and_source_boundaries(self):
        out = self.root / '.local' / 'scene-workflow-run'
        report = fixture.run(out)
        self.assertEqual(report, self.read(out / 'report.json'))
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['empty_story_check'], 'PASS')
        self.assertIs(report['source_preserved'], True)
        self.assertEqual(report['semantic_evaluation'], 'NOT_RUN')
        self.assertEqual(report['human_editorial_approval'], 'BLOCKED')
        self.assertEqual(report['owner_approval'], 'BLOCKED')
        self.assertIs(report['canon_change_authorized'], False)
        self.assertIs(report['ledger_apply_authorized'], False)
        self.assertTrue(report['checks']['future_scene_plan_excluded_from_SC001'])
        self.assertEqual(report['checks']['SC002_cursor_mapping'], 'UNKNOWN_NO_AUTOMATIC_MAPPING')
        self.assertEqual(report['checks']['SC002_pov_knowledge'], 'UNKNOWN')
        self.assertEqual(report['checks']['SC002_world_preview'], 'UNKNOWN')
        self.assertEqual(report['checks']['SC001_construction_candidate'],
                         'PROPOSED_UNKNOWN_WORLD_TIME')
        self.assertEqual(report['checks']['scene_replay']['SC-001'], 'UNKNOWN')
        self.assertEqual(report['checks']['scene_replay']['SC-002'], 'UNKNOWN')

        labels = {command['label'] for command in report['commands']}
        self.assertTrue({'empty-new', 'empty-check', 'fixture-check', 'pack-SC-001',
            'prepare-SC-001', 'prepare-SC-002', 'prepare-SC-003', 'replay-SC-001',
            'replay-SC-002', 'replay-SC-003', 'brief-review-SC-001',
            'propose-deltas-SC-001', 'rollup-EP-001-EP-002', 'doctor',
            'review-packet-SC-001', 'final-check'} <= labels)
        self.assertTrue(all(command['returncode'] == 0 for command in report['commands']))
        for command in report['commands']:
            self.assertNotIn('--verify-remote', command['argv'])
            self.assertNotIn('push', command['argv'])
            self.assertNotIn('fetch', command['argv'])
        isolated = out / 'workspace'
        for metadata in report['outputs'].values():
            path = out / metadata['path']
            self.assertTrue(path.resolve().is_relative_to(isolated / '.local'))
            raw = path.read_bytes()
            self.assertEqual(metadata['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(metadata['byte_length'], len(raw))

        sc001 = self.read(out / report['outputs']['prepare-SC-001']['path'])
        sc002 = self.read(out / report['outputs']['prepare-SC-002']['path'])
        self.assertIsNone(sc001['world_cursor'])
        self.assertEqual(sc002['world_cursor']['tick'], 5)
        self.assertNotIn(fixture.FUTURE_PLAN_MARKER, json.dumps(sc001))
        self.assertNotIn('SYNTHETIC RECAP ASSERTION EP-001',
                         sc002['author_planning_context']['content'])

    def test_runner_refuses_to_reuse_an_output_directory(self):
        out = self.root / 'prior-run'
        out.mkdir()
        marker = out / 'keep.txt'
        marker.write_text('prior content', encoding='utf-8')
        with self.assertRaises(ValueError):
            fixture.run(out)
        self.assertEqual(marker.read_text(encoding='utf-8'), 'prior content')


if __name__ == '__main__':
    unittest.main()
