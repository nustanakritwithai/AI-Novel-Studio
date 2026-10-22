"""Integrity of recorded E6 evidence, not a new semantic review or approval."""
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'evaluation/e6'
SEALED_KEY = 'd71842f3fe3a3a2679f8eb45df65561d97ce45fe2b9d781802f4f3b94593322f'
RAW_HASHES = {
    'A94': '05e49bda1680907bc9b2facbbc743d8192b85e674a9461f2cbc931ddf0d05e94',
    'B17': 'c94e1839ce8e085ea2a4c224875b93edbfc6a02dc12dac74ac4b850320d7c0c3',
}


def read(path):
    return json.loads(path.read_bytes().decode('utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EvaluationArtifactTests(unittest.TestCase):
    def test_answer_key_remains_the_pre_dispatch_sealed_input(self):
        key = read(ARTIFACTS / 'answer_key.json')
        manifest = read(ARTIFACTS / 'manifest.json')
        self.assertEqual(digest(ARTIFACTS / 'answer_key.json'), SEALED_KEY)
        self.assertEqual(manifest['sealed_key_sha256'], SEALED_KEY)
        self.assertIs(manifest['key_precedes_review_dispatch'], True)
        self.assertIs(key['prepared_before_review'], True)
        faults = key['candidates']['A94']['faults']
        self.assertEqual(len(faults), 5)
        self.assertEqual({fault['id'] for fault in faults}, {'F1', 'F2', 'F3', 'F4', 'F5'})
        self.assertEqual({fault['claim_id'] for fault in faults},
                         {'C-01', 'C-02', 'C-03', 'C-04', 'C-05'})
        self.assertTrue(all(fault['critical'] is True for fault in faults))
        self.assertEqual({fault['category'] for fault in faults},
                         {'CANON', 'KNOWLEDGE', 'INVENTORY', 'APPROVAL'})
        self.assertEqual(key['candidates']['B17']['role'], 'CLEAN_CONTROL')
        self.assertEqual(key['candidates']['B17']['expected_contradictions'], [])

    def test_packets_match_manifest_and_share_the_same_selected_story_context(self):
        manifest = read(ARTIFACTS / 'manifest.json')
        self.assertEqual({entry['candidate_id'] for entry in manifest['packets']}, {'A94', 'B17'})
        packs = []
        for entry in manifest['packets']:
            with self.subTest(candidate=entry['candidate_id']):
                path = ROOT / entry['path']
                self.assertTrue(path.resolve().is_relative_to((ARTIFACTS / 'packets').resolve()))
                self.assertEqual(digest(path), entry['sha256'])
                packet = read(path)
                self.assertEqual(packet['candidate_id'], entry['candidate_id'])
                self.assertEqual(packet['target'], 'SC-002')
                self.assertEqual(hashlib.sha256(packet['context_pack'].encode('utf-8')).hexdigest(),
                                 manifest['pack_sha256'])
                self.assertEqual(set(packet), {'candidate_id', 'target', 'scope', 'context_pack', 'draft'})
                self.assertNotIn('SEEDED_FAULTS', path.read_text(encoding='utf-8'))
                self.assertNotIn('CLEAN_CONTROL', path.read_text(encoding='utf-8'))
                packs.append(packet['context_pack'])
        self.assertEqual(packs[0], packs[1])

    def test_raw_reports_remain_unchanged_and_bind_to_the_reviewed_packets(self):
        manifest = read(ARTIFACTS / 'manifest.json')
        packets = {entry['candidate_id']: entry for entry in manifest['packets']}
        for candidate, expected in RAW_HASHES.items():
            with self.subTest(candidate=candidate):
                path = ARTIFACTS / 'raw' / (candidate + '.json')
                report = read(path)
                packet = read(ROOT / packets[candidate]['path'])
                self.assertEqual(digest(path), expected)
                self.assertEqual(report['candidate_id'], candidate)
                self.assertEqual(report['input_sha256'], packets[candidate]['sha256'])
                self.assertTrue(report['scope_limitations'])
                evidence_text = '\n'.join(packet[name] for name in ('scope', 'context_pack', 'draft'))
                for finding in report['findings']:
                    self.assertTrue(finding['id'])
                    self.assertTrue(finding['claim_ids'])
                    self.assertTrue(finding['description'])
                    self.assertTrue(finding['evidence'])
                    for evidence in finding['evidence']:
                        if isinstance(evidence, dict) and 'quote' in evidence:
                            self.assertIn(evidence['quote'], evidence_text)

    def test_clean_control_reports_no_findings_and_does_not_establish_human_approval(self):
        report = read(ARTIFACTS / 'raw/B17.json')
        self.assertEqual(report['findings'], [])
        self.assertTrue(report['uncertainties'])
        self.assertEqual(report['approval_status']['human_editorial_approval'],
                         'UNKNOWN_NOT_AUTHENTICATED')
        self.assertEqual(report['approval_status']['canon_change_authorization'], 'NOT_ESTABLISHED')
        seeded = read(ARTIFACTS / 'raw/A94.json')
        self.assertIs(seeded['approval_status']['canon_promotion_authorized'], False)
        self.assertIs(seeded['approval_status']['human_approval_required'], True)

    def test_recorded_reviewer_protocol_binds_raw_hashes_to_only_the_named_packets(self):
        adjudication = read(ARTIFACTS / 'adjudication.json')
        self.assertEqual(adjudication['sealed_key_sha256'], SEALED_KEY)
        self.assertEqual(len(adjudication['reviewers']), 2)
        seen = set()
        for reviewer in adjudication['reviewers']:
            with self.subTest(task=reviewer['task']):
                self.assertEqual(reviewer['fork_turns'], 'none')
                packet_path = ARTIFACTS / reviewer['allowed_input']
                raw_path = ARTIFACTS / reviewer['raw_report']
                self.assertTrue(packet_path.resolve().is_relative_to((ARTIFACTS / 'packets').resolve()))
                self.assertTrue(raw_path.resolve().is_relative_to((ARTIFACTS / 'raw').resolve()))
                packet, report = read(packet_path), read(raw_path)
                candidate = packet['candidate_id']
                self.assertNotIn(candidate, seen)
                seen.add(candidate)
                self.assertEqual(report['candidate_id'], candidate)
                self.assertEqual(report['input_sha256'], digest(packet_path))
                self.assertEqual(reviewer['raw_sha256'], digest(raw_path))
                self.assertEqual(reviewer['raw_sha256'], RAW_HASHES[candidate])
        self.assertEqual(seen, {'A94', 'B17'})

    def test_recorded_adjudication_references_actual_findings_without_upgrading_approval(self):
        # This checks provenance and internal consistency of the recorded manual
        # comparison. It does not judge the language or rerun semantic review.
        adjudication = read(ARTIFACTS / 'adjudication.json')
        faults = {fault['id']: fault for fault in read(ARTIFACTS / 'answer_key.json')['candidates']['A94']['faults']}
        report = read(ARTIFACTS / 'raw/A94.json')
        findings = {finding['id']: finding for finding in report['findings']}
        matches = adjudication['matches']
        self.assertEqual(len(matches), len(faults))
        self.assertEqual({match['fault_id'] for match in matches}, set(faults))
        self.assertEqual({match['finding_id'] for match in matches}, set(findings))
        for match in matches:
            with self.subTest(fault=match['fault_id']):
                self.assertEqual(match['claim_id'], faults[match['fault_id']]['claim_id'])
                self.assertIn(match['claim_id'], findings[match['finding_id']]['claim_ids'])
                self.assertEqual(match['result'], 'CAUGHT')
                self.assertTrue(match['reason'])
        self.assertEqual(adjudication['misses'], [])
        self.assertEqual(adjudication['extra_seeded_candidate_findings'], [])
        control = adjudication['clean_control']
        self.assertEqual(control['candidate_id'], 'B17')
        self.assertEqual(control['reported_findings'], len(read(ARTIFACTS / 'raw/B17.json')['findings']))
        self.assertEqual(control['false_positives'], [])
        self.assertTrue(control['uncertainty'])
        self.assertEqual(adjudication['bounded_semantic_gate'], 'PASS_FOR_RECORDED_SYNTHETIC_ASSERTIONS_ONLY')
        self.assertEqual(adjudication['human_editorial_signoff'], 'BLOCKED_NOT_SUPPLIED')
        self.assertTrue(adjudication['limitations'])
