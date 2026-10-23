"""Grounded review packet bindings and locator checks; synthetic markers only."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import test_story_roots as story_roots
from scripts import grounded_review, registry_schema, scene_prepare


class GroundedReviewCoreTests(unittest.TestCase):
    read = staticmethod(story_roots.StoryRootTests.read)
    write = staticmethod(story_roots.StoryRootTests.write)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.root = story_roots.StoryRootTests.fixture(self, "alpha", "ALPHA_ONLY")
        self.write(self.workspace / "studio.json", {"schema_version": 1, "default_story": "alpha"})
        self.path = "drafts/EP-001/SC-001.md"
        self.draft = self.root / self.path
        self.draft.parent.mkdir(parents=True, exist_ok=True)
        self.raw = b"SYNTHETIC HEADER\r\nSYNTHETIC_DRAFT_MARKER appears here\n"
        self.draft.write_bytes(self.raw)

    def tearDown(self):
        self.temp.cleanup()

    def build(self, **kwargs):
        return grounded_review.build_packet(self.root, "SC-001", **kwargs)

    @staticmethod
    def report(packet, findings=None):
        if findings is None:
            findings = [{
                "id": "FINDING-001",
                "classification": "UNKNOWN",
                "explanation": "Synthetic locator fixture; no semantic truth claim.",
                "severity": "WARNING",
                "draft_locator": {"start_line": 2, "end_line": 2,
                                  "quote": "SYNTHETIC_DRAFT_MARKER"},
                "context_locator": {"pointer": "/author_planning_context/content",
                                    "quote": "ALPHA_ONLY_STYLE"},
            }]
        return {
            "schema_version": 1,
            "kind": "GROUNDED_REVIEW_REPORT",
            "packet_id": packet["packet_id"],
            "draft_sha256": packet["raw_draft"]["sha256"],
            "findings": findings,
            "coverage": "The selected synthetic draft and scene-only context were inspected.",
            "limitations": ["Semantic assessment depends on an external reviewer."],
            "semantic_assessment": "MODEL_DEPENDENT_NOT_AUTHENTICATED",
        }

    def test_packet_freezes_exact_raw_crlf_draft_and_scene_only_context(self):
        packet = self.build()
        self.assertEqual(grounded_review.validate_packet(packet)["status"], "PACKET_BINDINGS_VALID")
        self.assertEqual(packet["raw_draft"]["content"].encode("utf-8"), self.raw)
        self.assertEqual(packet["raw_draft"]["sha256"], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(packet["raw_draft"]["byte_length"], len(self.raw))
        self.assertEqual(packet["context_source_mode"], "working-tree")
        self.assertEqual(packet["scene_preparation"]["content"]["kind"], "SCENE_PREPARATION")
        self.assertEqual(packet["scene_preparation"]["content"]["scene_cursor"],
                         {"scene_id": "SC-001", "boundary": "BEFORE"})
        self.assertEqual(packet["status"], "PROPOSED")
        self.assertEqual(packet["human_editorial_approval"], "UNVERIFIED")
        self.assertFalse(packet["canon_change_authorized"])
        self.assertFalse(packet["ledger_apply_authorized"])
        body = {key: value for key, value in packet.items() if key != "packet_id"}
        canonical = json.dumps(body, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False).encode("utf-8")
        self.assertEqual(packet["packet_id"], hashlib.sha256(canonical).hexdigest())

    def test_bound_report_validates_exact_lf_lines_and_context_pointer(self):
        packet = self.build()
        result = grounded_review.validate_report(packet, self.report(packet))
        self.assertEqual(result["status"], "BOUND_ADVISORY_NOT_APPROVAL")
        self.assertEqual(result["finding_count"], 1)
        self.assertEqual(result["semantic_assessment"], "MODEL_DEPENDENT_NOT_AUTHENTICATED")
        self.assertEqual(result["human_editorial_approval"], "UNVERIFIED")
        self.assertFalse(result["canon_change_authorized"])
        self.assertFalse(result["ledger_apply_authorized"])

    def test_empty_findings_remain_advisory_and_not_a_pass(self):
        packet = self.build()
        result = grounded_review.validate_report(packet, self.report(packet, []))
        self.assertEqual(result["status"], "BOUND_ADVISORY_NOT_APPROVAL")
        self.assertEqual(result["finding_count"], 0)

    def test_packet_and_report_bindings_and_closed_schema_fail_closed(self):
        packet = self.build()
        tampered_packet = copy.deepcopy(packet)
        tampered_packet["raw_draft"]["content"] += "changed"
        with self.assertRaisesRegex(ValueError, "digest"):
            grounded_review.validate_report(tampered_packet, self.report(packet))

        wrong_hash = self.report(packet)
        wrong_hash["draft_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "draft_sha256"):
            grounded_review.validate_report(packet, wrong_hash)

        extra = self.report(packet)
        extra["unrecognized"] = True
        with self.assertRaisesRegex(ValueError, "schema"):
            grounded_review.validate_report(packet, extra)

    def test_bad_draft_or_context_locator_is_rejected(self):
        packet = self.build()
        bad_draft = self.report(packet)
        bad_draft["findings"][0]["draft_locator"]["start_line"] = 1
        with self.assertRaisesRegex(ValueError, "draft locator"):
            grounded_review.validate_report(packet, bad_draft)

        bad_context = self.report(packet)
        bad_context["findings"][0]["context_locator"]["pointer"] = "/no/such/value"
        with self.assertRaisesRegex(ValueError, "JSON Pointer"):
            grounded_review.validate_report(packet, bad_context)

    def test_duplicate_scene_source_is_refused(self):
        scenes_path = self.root / "data/scenes.json"
        scenes = self.read(scenes_path)
        scenes["scenes"][1]["draft_path"] = self.path
        self.write(scenes_path, scenes)
        with self.assertRaisesRegex(ValueError, "shared scene draft"):
            self.build()

    def test_episode_author_decision_source_alias_is_refused(self):
        episodes_path = self.root / "data/episodes.json"
        episodes = self.read(episodes_path)
        episodes["episodes"][0]["author_decision"] = {"source_path": self.path}
        self.write(episodes_path, episodes)
        self.assertEqual(registry_schema.validate("episodes", episodes), [])
        with self.assertRaisesRegex(ValueError, "aliases an episode manuscript source"):
            self.build()

    def test_distinct_episode_author_decision_source_is_allowed(self):
        episodes_path = self.root / "data/episodes.json"
        episodes = self.read(episodes_path)
        source_path = "drafts/EP-001/FULL-DRAFT.md"
        episodes["episodes"][0]["author_decision"] = {"source_path": source_path}
        self.write(episodes_path, episodes)
        source = self.root / source_path
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("SYNTHETIC WHOLE-EPISODE SOURCE FIXTURE\n", encoding="utf-8")
        self.assertEqual(registry_schema.validate("episodes", episodes), [])
        packet = self.build()
        self.assertEqual(packet["target"]["draft_path"], self.path)

    def test_unsafe_episode_author_decision_source_refuses_packet(self):
        episodes_path = self.root / "data/episodes.json"
        episodes = self.read(episodes_path)
        episodes["episodes"][0]["author_decision"] = {"source_path": "../outside.md"}
        self.write(episodes_path, episodes)
        self.assertEqual(registry_schema.validate("episodes", episodes), [])
        with self.assertRaisesRegex(ValueError, "unsafe source path"):
            self.build()

    def test_metadata_race_during_preparation_refuses_packet(self):
        original = scene_prepare.build

        def change_metadata_after(*args, **kwargs):
            result = original(*args, **kwargs)
            path = self.root / "data/characters.json"
            value = self.read(path)
            value["characters"][0]["name"] = "CHANGED_DURING_GROUNDED_REVIEW"
            self.write(path, value)
            return result

        with mock.patch.object(grounded_review.scene_prepare, "build", side_effect=change_metadata_after):
            with self.assertRaisesRegex(ValueError, "metadata changed"):
                self.build()


if __name__ == "__main__":
    unittest.main()
