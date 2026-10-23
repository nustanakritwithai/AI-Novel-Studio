"""Integrity and binding checks for the recorded scene workflow evaluation."""
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "evaluation" / "scene_workflow_v1"
SEALED_KEY_SHA256 = "3e93a9854d86f436703d3196a45e4d98ed03330d84ba19f139afca217b0347d3"
EXPECTED_FAULT_MAP = {
    "K-CANON": "Q7-001",
    "K-KNOWLEDGE": "Q7-002",
    "K-INVENTORY": "Q7-003",
    "K-CONSTRUCTION": "Q7-004",
    "K-APPROVAL": "Q7-006",
}
EXPECTED_FAULT_LINES = {
    "K-CANON": 1,
    "K-KNOWLEDGE": 2,
    "K-INVENTORY": 3,
    "K-CONSTRUCTION": 4,
    "K-APPROVAL": 5,
}


def read_json(path):
    return json.loads(path.read_bytes().decode("utf-8"))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def resolve_json_pointer(document, pointer):
    value = document
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise AssertionError(f"Expected an absolute JSON pointer, got {pointer!r}")
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


class SceneWorkflowEvidenceTests(unittest.TestCase):
    def test_sealed_key_and_every_fixed_json_artifact_match_manifest(self):
        manifest = read_json(ARTIFACTS / "manifest.json")
        self.assertEqual(manifest["sealed_key_sha256"], SEALED_KEY_SHA256)
        self.assertIs(manifest["key_precedes_review_dispatch"], True)
        self.assertEqual(sha256((ARTIFACTS / "sealed-key.json").read_bytes()), SEALED_KEY_SHA256)
        key = read_json(ARTIFACTS / "sealed-key.json")
        self.assertEqual(key["scope"], "SYNTHETIC_METADATA_ONLY")
        self.assertEqual(key["human_editorial_approval"], "BLOCKED_NOT_TESTED")
        self.assertEqual(len(key["critical_faults"]), 5)
        self.assertEqual({fault["id"] for fault in key["critical_faults"]}, set(EXPECTED_FAULT_MAP))

        entries = manifest["fixed_json_artifacts"]
        indexed_paths = {entry["path"] for entry in entries}
        disk_paths = {
            path.relative_to(ARTIFACTS).as_posix()
            for path in ARTIFACTS.rglob("*.json")
            if path.name != "manifest.json"
        }
        self.assertEqual(indexed_paths, disk_paths)
        self.assertEqual(len(entries), len(indexed_paths))
        for entry in entries:
            with self.subTest(path=entry["path"]):
                path = (ARTIFACTS / entry["path"]).resolve()
                self.assertTrue(path.is_relative_to(ARTIFACTS.resolve()))
                content = path.read_bytes()
                self.assertEqual(len(content), entry["byte_length"])
                self.assertEqual(sha256(content), entry["sha256"])

    def test_reports_bind_to_current_packets_and_all_locators_resolve(self):
        case_packets = read_json(ARTIFACTS / "case-packets.json")
        for case in ("Q7", "M2", "R9"):
            with self.subTest(case=case):
                packet_path = ARTIFACTS / f"packet-{case}.json"
                report_path = ARTIFACTS / "raw" / f"review-{case}.json"
                validation_path = ARTIFACTS / f"validation-{case}.json"
                packet = read_json(packet_path)
                report = read_json(report_path)
                validation = read_json(validation_path)
                binding = case_packets.get(case, {
                    "packet_id": packet["packet_id"],
                    "draft_sha256": packet["raw_draft"]["sha256"],
                })

                self.assertEqual(packet["packet_id"], binding["packet_id"])
                self.assertEqual(report["packet_id"], packet["packet_id"])
                self.assertEqual(report["draft_sha256"], binding["draft_sha256"])
                draft = packet["raw_draft"]["content"]
                self.assertEqual(packet["raw_draft"]["sha256"], binding["draft_sha256"])
                self.assertEqual(sha256(draft.encode("utf-8")), binding["draft_sha256"])
                self.assertEqual(validation["packet_id"], packet["packet_id"])
                self.assertEqual(validation["draft_sha256"], binding["draft_sha256"])
                self.assertEqual(validation["report"], report)
                self.assertEqual(validation["kind"], "GROUNDED_REVIEW_VALIDATION")
                self.assertEqual(validation["status"], "BOUND_ADVISORY_NOT_APPROVAL")
                self.assertEqual(report["kind"], "GROUNDED_REVIEW_REPORT")
                self.assertEqual(report["schema_version"], 1)
                self.assertEqual(report["semantic_assessment"], "MODEL_DEPENDENT_NOT_AUTHENTICATED")
                self.assertEqual(validation["finding_count"], len(report["findings"]))

                for finding in report["findings"]:
                    with self.subTest(case=case, finding=finding["id"]):
                        draft_locator = finding["draft_locator"]
                        lines = draft.splitlines()
                        selected = lines[draft_locator["start_line"] - 1:draft_locator["end_line"]]
                        self.assertEqual("\n".join(selected), draft_locator["quote"])
                        context = resolve_json_pointer(
                            packet["scene_preparation"]["content"],
                            finding["context_locator"]["pointer"],
                        )
                        self.assertIn(finding["context_locator"]["quote"], context)
                        self.assertTrue(finding["explanation"])

    def test_recorded_seeded_hits_and_clean_rereview_counts_are_bounded(self):
        manifest = read_json(ARTIFACTS / "manifest.json")
        adjudication = manifest["adjudication"]
        mappings = {item["fault_id"]: item for item in adjudication["critical_fault_mapping"]}
        self.assertEqual({fault_id: item["finding_id"] for fault_id, item in mappings.items()},
                         EXPECTED_FAULT_MAP)
        q7 = read_json(ARTIFACTS / "raw" / "review-Q7.json")
        q7_findings = {finding["id"]: finding for finding in q7["findings"]}
        self.assertEqual(set(q7_findings), {"Q7-001", "Q7-002", "Q7-003", "Q7-004", "Q7-005", "Q7-006"})
        self.assertEqual(len(mappings), len(EXPECTED_FAULT_MAP))
        for fault_id, finding_id in EXPECTED_FAULT_MAP.items():
            with self.subTest(fault=fault_id):
                finding = q7_findings[finding_id]
                mapping = mappings[fault_id]
                self.assertEqual(mapping["result"], "CAUGHT")
                self.assertEqual(mapping["draft_line"], EXPECTED_FAULT_LINES[fault_id])
                self.assertTrue(mapping["basis"])
                self.assertEqual(finding["classification"], "CONTRADICTION")
                self.assertEqual(finding["severity"], "CRITICAL")
                self.assertEqual(finding["draft_locator"]["start_line"], mapping["draft_line"])
                self.assertEqual(finding["draft_locator"]["end_line"], mapping["draft_line"])
        self.assertEqual(adjudication["critical_hits"], 5)
        self.assertEqual(adjudication["critical_misses"], 0)
        self.assertEqual(q7_findings["Q7-005"]["classification"], "UNKNOWN")
        self.assertEqual(q7_findings["Q7-005"]["severity"], "WARNING")
        self.assertEqual(adjudication["additional_unknown_findings"][0]["finding_id"], "Q7-005")

        m2 = read_json(ARTIFACTS / "raw" / "review-M2.json")
        r9 = read_json(ARTIFACTS / "raw" / "review-R9.json")
        self.assertEqual(m2["findings"], [])
        self.assertEqual(r9["findings"], [])
        self.assertEqual(read_json(ARTIFACTS / "validation-M2.json")["finding_count"], 0)
        self.assertEqual(read_json(ARTIFACTS / "validation-R9.json")["finding_count"], 0)
        self.assertEqual(adjudication["clean_control_findings"], 0)
        self.assertEqual(adjudication["clean_control_contradictions"], 0)
        self.assertEqual(adjudication["rereview_findings"], 0)
        self.assertEqual(adjudication["bounded_result"],
                         "PASS_FOR_THIS_RECORDED_SYNTHETIC_CASE_AND_CONTROL_ONLY")

    def test_owner_checkpoint_and_proposal_remain_blocked_and_unapplied(self):
        flow = read_json(ARTIFACTS / "flows" / "06-owner-blocked.json")
        verification = read_json(ARTIFACTS / "flow-verification.json")
        gate = read_json(ARTIFACTS / "proposal-gate.json")
        proposal = read_json(ARTIFACTS / "final-proposal.json")
        manifest = read_json(ARTIFACTS / "manifest.json")

        self.assertEqual(flow["records"][-1]["stage"], "OWNER_CHECKPOINT")
        self.assertEqual(flow["owner_gate"], "BLOCKED_AUTHENTICATED_SIGNOFF_NOT_ESTABLISHED")
        self.assertEqual(flow["status"], "PROPOSED")
        self.assertEqual(verification["status"], "CONSISTENT_LOCAL_CHAIN_NOT_APPROVAL")
        self.assertEqual(verification["last_stage"], "OWNER_CHECKPOINT")
        self.assertEqual(verification["human_editorial_approval"], "UNVERIFIED")
        self.assertEqual(verification["historical_source_verification"], "NOT_RUN")
        self.assertIs(verification["canon_change_authorized"], False)
        self.assertIs(verification["ledger_apply_authorized"], False)
        self.assertEqual(gate["status"], "BLOCKED")
        self.assertEqual(gate["standalone_proposal_status"], "PROPOSED")
        self.assertIs(gate["apply"], False)
        self.assertEqual(proposal["status"], "PROPOSED")
        self.assertEqual(proposal["human_editorial_approval"], "UNVERIFIED")
        self.assertIs(proposal["canon_change_authorized"], False)
        self.assertIs(proposal["ledger_apply_authorized"], False)
        self.assertEqual(proposal["observations"][0]["candidate"]["world_time"]["status"], "UNKNOWN")
        self.assertEqual(manifest["pipeline"]["human_approval_run"], False)
        self.assertEqual(manifest["pipeline"]["post_merge_changed_workflow_live_proof"], False)


if __name__ == "__main__":
    unittest.main()
