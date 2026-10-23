"""Supervised stage guards, not simulated human editorial approval."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import grounded_review, scene_workflow, scene_delta_proposal
import test_grounded_review_core as fixtures

ENGINE = Path(__file__).resolve().parents[1]


class SceneWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.GroundedReviewCoreTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.root
        self.packet = self.fixture.build()

    def artifact(self, packet=None, **extra):
        packet = packet or self.packet
        return {'packet_id': packet['packet_id'], 'draft_sha256': packet['raw_draft']['sha256'],
                'notes': 'Synthetic handoff note; no person identity or approval is authenticated.', **extra}

    def start(self):
        plan = scene_workflow.advance(self.root, self.packet, 'PLANNER', self.artifact())
        return scene_workflow.advance(self.root, self.packet, 'WRITER', self.artifact(), previous=plan)

    def test_out_of_order_stale_and_rehashed_authority_claims_fail_closed(self):
        with self.assertRaises(ValueError):
            scene_workflow.advance(self.root, self.packet, 'WRITER', self.artifact())
        plan = scene_workflow.advance(self.root, self.packet, 'PLANNER', self.artifact())
        bad = copy.deepcopy(plan)
        bad['human_editorial_approval'] = 'APPROVED'
        bad['chain_sha256'] = scene_workflow.digest(scene_workflow._without(bad, 'chain_sha256'))
        with self.assertRaises(ValueError):
            scene_workflow.verify(bad)
        (self.root / 'bible/STYLE_GUIDE.md').write_bytes(b'CHANGED_CONTEXT\n')
        with self.assertRaisesRegex(ValueError, 'stale'):
            scene_workflow.advance(self.root, self.packet, 'WRITER', self.artifact(), previous=plan)

    def test_contradiction_requires_changed_revision_and_fresh_review(self):
        flow = self.start()
        report = self.fixture.report(self.packet)
        report['findings'][0]['classification'] = 'CONTRADICTION'
        reviewed = scene_workflow.advance(self.root, self.packet, 'REVIEWER', self.artifact(report=report), previous=flow)
        with self.assertRaisesRegex(ValueError, 'contradictions'):
            scene_workflow.advance(self.root, self.packet, 'OWNER_CHECKPOINT', self.artifact(), previous=reviewed)
        with self.assertRaisesRegex(ValueError, 'changed draft'):
            scene_workflow.advance(self.root, self.packet, 'REVISION', self.artifact(), previous=reviewed)
        self.fixture.draft.write_bytes(self.fixture.raw + b'SYNTHETIC REVISION\n')
        revised_packet = self.fixture.build()
        revised = scene_workflow.advance(self.root, revised_packet, 'REVISION', self.artifact(revised_packet), previous=reviewed)
        with self.assertRaises(ValueError):
            scene_workflow.advance(self.root, revised_packet, 'REVIEWER', self.artifact(revised_packet, report=report), previous=revised)
        clear = self.fixture.report(revised_packet, findings=[])
        checked = scene_workflow.advance(self.root, revised_packet, 'REVIEWER', self.artifact(revised_packet, report=clear), previous=revised)
        owner = scene_workflow.advance(self.root, revised_packet, 'OWNER_CHECKPOINT', self.artifact(revised_packet), previous=checked)
        self.assertEqual(owner['human_editorial_approval'], 'UNVERIFIED')
        self.assertTrue(owner['owner_gate'].startswith('BLOCKED'))
        self.assertFalse(owner['canon_change_authorized'])

    def test_standalone_proposal_cannot_cross_unverified_owner_gate(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        flow = self.start()
        clear = self.fixture.report(self.packet, findings=[])
        flow = scene_workflow.advance(self.root, self.packet, 'REVIEWER', self.artifact(report=clear), previous=flow)
        flow = scene_workflow.advance(self.root, self.packet, 'OWNER_CHECKPOINT', self.artifact(), previous=flow)
        claims = {'schema_version': 1, 'scene_id': 'SC-001', 'draft_path': self.fixture.path,
                  'source_sha256': self.packet['raw_draft']['sha256'], 'observations': []}
        proposal = scene_delta_proposal.build(self.root, 'SC-001', claims)
        with self.assertRaisesRegex(ValueError, 'signoff'):
            scene_workflow.advance(self.root, self.packet, 'DELTA_PROPOSAL', self.artifact(proposal=proposal), previous=flow)
        verified = scene_workflow.verify(flow)
        self.assertEqual(verified['last_stage'], 'OWNER_CHECKPOINT')
        self.assertEqual(verified['historical_source_verification'], 'NOT_RUN')
        self.assertFalse(flow['ledger_apply_authorized'])
        self.assertEqual(proposal['status'], 'PROPOSED')
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_cli_packet_report_and_handoff_outputs_are_private_and_exclusive(self):
        local = self.fixture.workspace / '.local'
        local.mkdir()
        packet = local / 'packet.json'
        report = local / 'report.json'
        note = local / 'note.json'
        packet.write_text(json.dumps(self.packet), encoding='utf-8')
        report.write_text(json.dumps(self.fixture.report(self.packet, findings=[])), encoding='utf-8')
        note.write_text(json.dumps(self.artifact()), encoding='utf-8')
        def cli(*args):
            return subprocess.run([sys.executable, str(ENGINE / 'scripts/storyctl.py'),
                '--workspace', str(self.fixture.workspace), '--story', 'alpha', *map(str, args)],
                capture_output=True, text=True, encoding='utf-8', timeout=60,
                env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        checked = cli('review-check', '--packet', packet, '--report', report)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout)['status'], 'BOUND_ADVISORY_NOT_APPROVAL')
        output = local / 'flow.json'
        first = cli('scene-flow', 'PLANNER', '--packet', packet, '--artifact', note, '--out', output)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertNotEqual(cli('scene-flow', 'PLANNER', '--packet', packet, '--artifact', note, '--out', output).returncode, 0)
        verified = cli('scene-flow', 'VERIFY', '--previous', output, '--packet', packet)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        public = self.fixture.workspace / 'public.json'
        self.assertNotEqual(cli('review-packet', 'SC-001', '--out', public).returncode, 0)
        self.assertFalse(public.exists())

    def test_cli_valid_near_limit_draft_packet_roundtrips_with_json_headroom(self):
        self.fixture.draft.write_bytes(b'A' * (1024 * 1024 - 1) + b'\n')
        local = self.fixture.workspace / '.local'
        local.mkdir()
        packet_path, report_path = local / 'large-packet.json', local / 'large-report.json'
        emission = subprocess.run([sys.executable, str(ENGINE / 'scripts/storyctl.py'),
            '--workspace', str(self.fixture.workspace), '--story', 'alpha', 'review-packet',
            'SC-001', '--out', str(packet_path)], capture_output=True, text=True, encoding='utf-8',
            timeout=60, env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        self.assertEqual(emission.returncode, 0, emission.stderr)
        packet = json.loads(packet_path.read_text(encoding='utf-8'))
        self.assertGreater(packet_path.stat().st_size, 1024 * 1024)
        report_path.write_text(json.dumps(self.fixture.report(packet, findings=[])), encoding='utf-8')
        result = subprocess.run([sys.executable, str(ENGINE / 'scripts/storyctl.py'),
            '--workspace', str(self.fixture.workspace), '--story', 'alpha', 'review-check',
            '--packet', str(packet_path), '--report', str(report_path)], capture_output=True,
            text=True, encoding='utf-8', timeout=60, env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'BOUND_ADVISORY_NOT_APPROVAL')


if __name__ == '__main__':
    unittest.main()
