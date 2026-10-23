"""Adversarial safety tests for source-bound scene delta proposals.

All inputs are short synthetic metadata fixtures. The proposal remains an
unverified suggestion; these tests never edit an existing story.
"""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import test_story_roots as story_roots
from scripts import scene_delta_proposal


SOURCE = b"SYNTHETIC_SOURCE_LINE_1\nSYNTHETIC_SOURCE_LINE_2\nSYNTHETIC_SOURCE_LINE_3\n"


class SceneDeltaAdversarialTests(unittest.TestCase):
    # StoryRootTests.fixture uses these two helpers on its receiver.
    read = staticmethod(story_roots.StoryRootTests.read)
    write = staticmethod(story_roots.StoryRootTests.write)
    read_json = staticmethod(story_roots.StoryRootTests.read)
    write_json = staticmethod(story_roots.StoryRootTests.write)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.alpha = story_roots.StoryRootTests.fixture(self, "alpha", "ALPHA_ONLY")
        self.beta = story_roots.StoryRootTests.fixture(self, "beta", "BETA_ONLY")
        self.write_json(self.workspace / "studio.json", {
            "schema_version": 1, "default_story": "alpha",
        })
        self.draft_path = "drafts/EP-001/SC-001.md"
        self.draft = self.alpha / self.draft_path
        self.draft.parent.mkdir(parents=True, exist_ok=True)
        self.draft.write_bytes(SOURCE)
        self.beta_draft = self.beta / self.draft_path
        self.beta_draft.parent.mkdir(parents=True, exist_ok=True)
        self.beta_draft.write_bytes(b"BETA_ONLY_FOREIGN_SOURCE\n")

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def digest(raw):
        return hashlib.sha256(raw).hexdigest()

    def claims(self, *, raw=SOURCE, path=None, quote="SYNTHETIC_SOURCE_LINE_2",
               start_line=2, end_line=2):
        """A closed v1 claim packet that cites only the selected draft."""
        return {
            "schema_version": 1,
            "scene_id": "SC-001",
            "draft_path": path or self.draft_path,
            "source_sha256": self.digest(raw),
            "observations": [
                {
                    "id": "OBS-001", "category": "MOVE",
                    # Deliberately unsupported by the quoted fixture text.
                    "claim": "Aster crossed the eastern sea and arrived safely.",
                    "locator": {
                        "start_line": start_line, "end_line": end_line,
                        "quote": quote,
                    },
                    "subject": {"kind": "CHARACTER", "id": "CHAR-001"},
                    "candidate": {
                        "character_id": "CHAR-001",
                        "from_location_id": "UNKNOWN",
                        "to_location_id": "LOC-001",
                    },
                },
                {
                    "id": "OBS-002", "category": "TRANSFER",
                    "claim": "An item may have changed hands; amount is unstated.",
                    "locator": {
                        "start_line": 3, "end_line": 3,
                        "quote": "SYNTHETIC_SOURCE_LINE_3",
                    },
                    "subject": {"kind": "ITEM", "id": "ITEM-001"},
                    "candidate": {
                        "item_id": "ITEM-001", "quantity": "UNKNOWN",
                        "from_holder": {"kind": "UNKNOWN", "id": "UNKNOWN"},
                        "to_holder": {"kind": "CHARACTER", "id": "CHAR-001"},
                    },
                },
            ],
        }

    def build(self, claims=None, *, root=None, previous=None):
        return scene_delta_proposal.build(
            self.alpha if root is None else root,
            "SC-001",
            self.claims() if claims is None else claims,
            previous=previous,
        )

    def test_exact_quote_coordinates_and_source_digest_are_required(self):
        stale = self.claims()
        stale["source_sha256"] = "0" * 64
        wrong_lines = self.claims(start_line=1, end_line=1)
        wrong_quote = self.claims(quote="SYNTHETIC_SOURCE_LINE_1")
        for label, packet in (("stale hash", stale), ("wrong line", wrong_lines),
                              ("wrong quote", wrong_quote)):
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.build(packet)

    def test_forged_semantics_stay_unassessed_and_cannot_apply_state(self):
        before_state = (self.alpha / "data/story_state.json").read_bytes()
        before_ledger = (self.alpha / "data/inventory_ledger.json").read_bytes()
        proposal = self.build()

        self.assertEqual(proposal["status"], "PROPOSED")
        self.assertEqual(proposal["human_editorial_approval"], "UNVERIFIED")
        self.assertFalse(proposal["canon_change_authorized"])
        self.assertFalse(proposal["ledger_apply_authorized"])
        first = proposal["observations"][0]
        self.assertEqual(first["claim"], "Aster crossed the eastern sea and arrived safely.")
        self.assertEqual(first["evidence"]["semantic_assessment"], "NOT_EVALUATED")
        self.assertEqual(first["evidence"]["locator_status"], "EXACT_QUOTE_AT_LINES")
        self.assertNotIn("state", proposal)
        self.assertNotIn("applied_delta_ids", proposal)
        self.assertEqual((self.alpha / "data/story_state.json").read_bytes(), before_state)
        self.assertEqual((self.alpha / "data/inventory_ledger.json").read_bytes(), before_ledger)

    def test_source_reader_reads_only_the_selected_draft_and_omits_future_chapter(self):
        future = self.alpha / "drafts/EP-001/SC-002.md"
        future.parent.mkdir(parents=True, exist_ok=True)
        future.write_text("FUTURE_CHAPTER_SECRET_SYNTHETIC\n", encoding="utf-8")
        calls = []
        original_read = scene_delta_proposal.SourceReader.read

        def recording_read(reader, relative, *args, **kwargs):
            calls.append(relative)
            return original_read(reader, relative, *args, **kwargs)

        with mock.patch.object(scene_delta_proposal.SourceReader, "read", new=recording_read):
            proposal = self.build()

        self.assertEqual(calls, [self.draft_path])
        self.assertEqual(proposal["source"]["path"], self.draft_path)
        self.assertNotIn("FUTURE_CHAPTER_SECRET_SYNTHETIC", json.dumps(proposal))

    def test_a_draft_shared_with_a_future_scene_is_rejected(self):
        scenes = self.read_json(self.alpha / "data/scenes.json")
        scenes["scenes"][1]["draft_path"] = self.draft_path
        self.write_json(self.alpha / "data/scenes.json", scenes)

        with self.assertRaises(ValueError):
            self.build()

    def test_claim_path_escape_and_registered_path_escape_are_rejected(self):
        escape = "../../beta/drafts/EP-001/SC-001.md"
        packet = self.claims(raw=self.beta_draft.read_bytes(), path=escape)
        with self.assertRaises(ValueError):
            self.build(packet)

        scenes = self.read_json(self.alpha / "data/scenes.json")
        scenes["scenes"][0]["draft_path"] = escape
        self.write_json(self.alpha / "data/scenes.json", scenes)
        with self.assertRaises(ValueError):
            self.build(packet)

    def test_symlinked_selected_draft_is_rejected(self):
        self.draft.unlink()
        try:
            self.draft.symlink_to(self.beta_draft)
        except OSError as exc:
            self.skipTest(f"Platform cannot create symlinks: {exc}")

        with self.assertRaises(ValueError):
            self.build(self.claims(raw=self.beta_draft.read_bytes()))

    def test_foreign_story_claim_packet_cannot_cross_selected_story_boundary(self):
        foreign = self.claims(raw=self.beta_draft.read_bytes())
        with self.assertRaises(ValueError):
            self.build(foreign, root=self.alpha)

        own = self.build(root=self.alpha)
        self.assertEqual(own["story_slug"], "alpha")
        self.assertEqual(own["target"]["scene_id"], "SC-001")
        self.assertEqual(own["source"]["selected_sha256"], self.digest(SOURCE))
        self.assertNotIn("BETA_ONLY", json.dumps(own))

    def test_unknown_quantity_remains_unknown(self):
        proposal = self.build()
        transfer = next(row for row in proposal["observations"] if row["category"] == "TRANSFER")
        self.assertEqual(transfer["candidate"]["quantity"], "UNKNOWN")

    def test_identical_inputs_produce_identical_proposals(self):
        self.assertEqual(self.build(), self.build())

    def test_tampered_previous_revision_is_rejected(self):
        previous = self.build()
        previous = copy.deepcopy(previous)
        previous["revision_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.build(previous=previous)

    def test_source_mutation_after_exact_read_fails_closed(self):
        original_read = scene_delta_proposal.SourceReader.read
        changed = False

        def mutate_after_read(reader, relative, *args, **kwargs):
            nonlocal changed
            result = original_read(reader, relative, *args, **kwargs)
            if relative == self.draft_path and not changed:
                changed = True
                self.draft.write_bytes(SOURCE + b"RACE_EDIT\n")
            return result

        with mock.patch.object(scene_delta_proposal.SourceReader, "read", new=mutate_after_read):
            with self.assertRaises(ValueError):
                self.build()
        self.assertTrue(changed)


if __name__ == "__main__":
    unittest.main()
