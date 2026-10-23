"""Core contracts for private per-scene delta proposal assembly."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import test_story_roots as story_roots
from scripts import scene_delta_proposal


class SceneDeltaProposalCoreTests(unittest.TestCase):
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
        self.raw = b"SYNTHETIC FIRST LINE\r\nSYNTHETIC SECOND LINE\r\nSYNTHETIC THIRD LINE\n"
        self.draft.write_bytes(self.raw)

    def tearDown(self):
        self.temp.cleanup()

    def claims(self, raw=None):
        raw = self.raw if raw is None else raw
        return {
            "schema_version": 1,
            "scene_id": "SC-001",
            "draft_path": self.path,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "observations": [
                {
                    "id": "OBS-MOVE",
                    "category": "MOVE",
                    "claim": "The synthetic character changes location.",
                    "locator": {"start_line": 2, "end_line": 2,
                                "quote": "SYNTHETIC SECOND LINE"},
                    "subject": {"kind": "CHARACTER", "id": "CHAR-001"},
                    "candidate": {"character_id": "CHAR-001", "from_location_id": "UNKNOWN",
                                  "to_location_id": "LOC-001"},
                },
                {
                    "id": "OBS-REPAIR",
                    "category": "REPAIR",
                    "claim": "A synthetic fixture records a repair observation.",
                    "locator": {"start_line": 3, "end_line": 3,
                                "quote": "SYNTHETIC THIRD LINE"},
                    "subject": {"kind": "LOCATION", "id": "LOC-001"},
                    "candidate": {"target_kind": "LOCATION", "target_id": "LOC-001",
                                  "aspect": "roof"},
                },
            ],
        }

    def build(self, claims=None, **kwargs):
        return scene_delta_proposal.build(self.root, "SC-001", self.claims() if claims is None else claims,
                                          **kwargs)

    def add_catalog_entry(self, registry_name, entry):
        path = self.root / "data" / f"{registry_name}.json"
        value = self.read(path)
        rows_key = registry_name
        if registry_name == "characters":
            row = copy.deepcopy(value[rows_key][0])
            row.update(entry)
        else:
            row = dict(entry)
        value[rows_key].append(row)
        self.write(path, value)

    @staticmethod
    def reseal(report):
        identity = report["proposal_identity"]
        report["revision_sha256"] = scene_delta_proposal._revision_sha(report)
        report["revision_id"] = scene_delta_proposal._revision_id(
            identity, report["revision_sha256"], report["previous_revision_id"])
        report["revision_chain_sha256"] = scene_delta_proposal._chain_sha(
            identity, scene_delta_proposal._record(report))
        return report

    def test_exact_crlf_quote_uses_selected_bytes_and_unknown_time(self):
        proposal = self.build()
        self.assertEqual(proposal["source"]["selected_sha256"], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(proposal["source"]["selected_byte_length"], len(self.raw))
        self.assertEqual(proposal["source"]["raw_status"], "MATCH")
        self.assertEqual(proposal["observations"][0]["evidence"]["quote"], "SYNTHETIC SECOND LINE")
        self.assertEqual(proposal["observations"][0]["evidence"]["start_line"], 2)
        self.assertEqual(proposal["observations"][0]["evidence"]["semantic_assessment"], "NOT_EVALUATED")
        self.assertEqual(proposal["observations"][0]["candidate"]["world_time"], {"status": "UNKNOWN"})
        self.assertEqual(proposal["observations"][1]["candidate"]["world_time"], {"status": "UNKNOWN"})
        self.assertEqual(proposal["status"], "PROPOSED")
        self.assertFalse(proposal["canon_change_authorized"])
        self.assertFalse(proposal["ledger_apply_authorized"])
        self.assertEqual(proposal["world_state_application"], "NOT_RUN")

    def test_complete_world_time_is_preserved_without_order_inference(self):
        packet = self.claims()
        packet["observations"][0]["candidate"]["world_time"] = {
            "status": "KNOWN", "clock_id": "CLOCK-MAIN", "tick": 7,
            "suborder": 1, "boundary": "AFTER",
        }
        proposal = self.build(packet)
        self.assertEqual(proposal["observations"][0]["candidate"]["world_time"],
                         packet["observations"][0]["candidate"]["world_time"])
        packet["observations"][0]["candidate"]["world_time"].pop("boundary")
        with self.assertRaises(ValueError):
            self.build(packet)

        packet["observations"][0]["candidate"]["world_time"] = {
            "status": "KNOWN", "clock_id": "CLOCK-MAIN", "tick": True,
            "suborder": 1, "boundary": "AFTER",
        }
        with self.assertRaises(ValueError):
            self.build(packet)

    def test_multiline_crlf_locator_preserves_exact_line_endings(self):
        packet = self.claims()
        packet["observations"][0]["locator"] = {
            "start_line": 1, "end_line": 2,
            "quote": "SYNTHETIC FIRST LINE\r\nSYNTHETIC SECOND LINE",
        }
        proposal = self.build(packet)
        evidence = proposal["observations"][0]["evidence"]
        self.assertEqual(evidence["quote"], packet["observations"][0]["locator"]["quote"])
        self.assertEqual((evidence["start_line"], evidence["end_line"]), (1, 2))

    def test_construction_damage_and_repair_remain_observations(self):
        packet = self.claims()
        for index, category, quote in (
            (1, "CONSTRUCTION", "SYNTHETIC FIRST LINE"),
            (2, "DAMAGE", "SYNTHETIC SECOND LINE"),
        ):
            packet["observations"].append({
                "id": f"OBS-PHYSICAL-{category}", "category": category,
                "claim": f"Synthetic {category.lower()} observation.",
                "locator": {"start_line": index, "end_line": index, "quote": quote},
                "subject": {"kind": "LOCATION", "id": "LOC-001"},
                "candidate": {"target_kind": "LOCATION", "target_id": "LOC-001",
                              "aspect": category.lower()},
            })
        proposal = self.build(packet)
        categories = {row["category"] for row in proposal["observations"]}
        self.assertEqual(categories, {"MOVE", "CONSTRUCTION", "DAMAGE", "REPAIR"})
        self.assertEqual(proposal["proposal_scope"], "OBSERVATIONS_ONLY")
        self.assertEqual(proposal["world_state_application"], "NOT_RUN")
        self.assertNotIn("state", proposal)

    def test_known_subject_and_candidate_mismatches_fail_closed(self):
        self.add_catalog_entry("characters", {"id": "CHAR-002", "name": "SECOND_CHAR"})
        self.add_catalog_entry("items", {"id": "ITEM-002", "name": "SECOND_ITEM"})

        packet = self.claims()
        packet["observations"][0]["candidate"]["character_id"] = "CHAR-002"
        with self.assertRaisesRegex(ValueError, "must match when known"):
            self.build(packet)

        packet = self.claims()
        packet["observations"][0]["subject"] = {"kind": "LOCATION", "id": "LOC-001"}
        with self.assertRaises(ValueError):
            self.build(packet)

        packet = self.claims()
        transfer = {
            "id": "OBS-TRANSFER", "category": "TRANSFER",
            "claim": "A synthetic transfer observation.",
            "locator": {"start_line": 2, "end_line": 2, "quote": "SYNTHETIC SECOND LINE"},
            "subject": {"kind": "ITEM", "id": "ITEM-001"},
            "candidate": {"item_id": "ITEM-002"},
        }
        packet["observations"] = [transfer]
        with self.assertRaisesRegex(ValueError, "must match when known"):
            self.build(packet)

        packet = self.claims()
        packet["observations"][1]["category"] = "DAMAGE"
        packet["observations"][1]["candidate"]["target_kind"] = "ITEM"
        packet["observations"][1]["candidate"]["target_id"] = "ITEM-001"
        with self.assertRaisesRegex(ValueError, "physical subject and candidate target"):
            self.build(packet)

    def test_unknown_subject_or_candidate_is_not_filled_from_the_other(self):
        packet = self.claims()
        packet["observations"][0]["candidate"]["character_id"] = "UNKNOWN"
        packet["observations"][1]["subject"] = {"kind": "UNKNOWN", "id": "UNKNOWN"}
        proposal = self.build(packet)
        self.assertEqual(proposal["observations"][0]["candidate"]["character_id"], "UNKNOWN")
        self.assertEqual(proposal["observations"][1]["subject"], {"kind": "UNKNOWN", "id": "UNKNOWN"})
        self.assertEqual(proposal["observations"][1]["candidate"]["target_id"], "LOC-001")

    def test_revision_identity_is_stable_and_revision_chain_is_bounded_flat_history(self):
        first = self.build()
        self.assertEqual(self.build(), first)
        self.assertEqual(self.build(previous=first), first)

        updated_raw = self.raw + b"SYNTHETIC EDIT\n"
        self.draft.write_bytes(updated_raw)
        second = self.build(self.claims(updated_raw), previous=first)
        self.assertEqual(second["proposal_identity"], first["proposal_identity"])
        self.assertNotEqual(second["revision_id"], first["revision_id"])
        self.assertEqual(second["previous_revision_id"], first["revision_id"])
        self.assertEqual(len(second["revision_history"]), 1)
        self.assertEqual(second["revision_history"][0]["revision_id"], first["revision_id"])

        tampered = copy.deepcopy(second)
        tampered["revision_history"][0]["revision_chain_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.build(self.claims(updated_raw), previous=tampered)

    def test_resealed_previous_reports_with_inconsistent_source_evidence_are_rejected(self):
        first = self.build()
        corruptions = (
            ("source", lambda row: row["source"].update(path="drafts/EP-001/OTHER.md")),
            ("evidence path", lambda row: row["observations"][0]["evidence"].update(
                path="drafts/EP-001/OTHER.md")),
            ("evidence hash", lambda row: row["observations"][0]["evidence"].update(
                draft_sha256="0" * 64)),
            ("duplicate IDs", lambda row: row["observations"][1].update(
                id=row["observations"][0]["id"])),
            ("subject mismatch", lambda row: row["observations"][0]["candidate"].update(
                character_id="CHAR-002")),
        )
        for label, corrupt in corruptions:
            with self.subTest(label=label):
                prior = copy.deepcopy(first)
                corrupt(prior)
                self.reseal(prior)
                with self.assertRaises(ValueError):
                    self.build(previous=prior)

    def test_duplicate_quote_on_same_declared_lines_is_ambiguous(self):
        raw = b"SYNTHETIC TOKEN TOKEN\n"
        self.draft.write_bytes(raw)
        packet = self.claims(raw)
        packet["observations"] = [packet["observations"][0]]
        packet["observations"][0]["locator"] = {
            "start_line": 1, "end_line": 1, "quote": "TOKEN",
        }
        with self.assertRaisesRegex(ValueError, "absent or ambiguous"):
            self.build(packet)

    def test_source_changed_after_first_fingerprint_fails_at_final_evidence_check(self):
        original = scene_delta_proposal._source_record

        def mutate_after_capture(reader, draft_path):
            captured = original(reader, draft_path)
            self.draft.write_bytes(self.raw + b"SYNTHETIC RACE\n")
            return captured

        with mock.patch.object(scene_delta_proposal, "_source_record", side_effect=mutate_after_capture):
            with self.assertRaises(ValueError):
                self.build()

    def test_metadata_changed_during_build_fails_closed(self):
        original = scene_delta_proposal.scene_prepare._metadata_snapshot
        calls = 0

        def mutate_before_final_snapshot(root):
            nonlocal calls
            calls += 1
            if calls == 2:
                path = root / "data/characters.json"
                value = self.read(path)
                value["characters"][0]["name"] = "CHANGED_DURING_BUILD"
                self.write(path, value)
            return original(root)

        with mock.patch.object(scene_delta_proposal.scene_prepare, "_metadata_snapshot",
                               side_effect=mutate_before_final_snapshot):
            with self.assertRaisesRegex(ValueError, "metadata changed"):
                self.build()


if __name__ == "__main__":
    unittest.main()
