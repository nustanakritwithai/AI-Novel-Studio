"""Acceptance tests for source-backed S1 + chat-accepted episode memory.

These tests intentionally do NOT relabel user chat consent as an authenticated
GitHub APPROVE review, and do not call a language model.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import author_memory, novelctl, story_config, story_engine, world_state_model

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "stories" / "last-island-active"
HISTORICAL = ROOT / "stories" / "last-island"


class ActiveStoryLatestEngineTests(unittest.TestCase):
    def test_default_story_selects_live_data_and_old_example_is_explicit(self):
        config = json.loads((ROOT / "studio.json").read_text(encoding="utf-8"))
        self.assertEqual(config["default_story"], "last-island-active")
        self.assertEqual(story_config.resolve_root(ROOT), ACTIVE)
        self.assertEqual(story_config.resolve_root(ROOT, "last-island"), HISTORICAL)
        self.assertEqual(story_engine.validate(ACTIVE)[0], [])

    def test_s1_validates_all_bound_sources_without_invented_world_time(self):
        model = world_state_model.load(ACTIVE)
        self.assertIsNotNone(model)
        observations = model["observations"]
        self.assertEqual(len(observations), 18)
        self.assertEqual(len({r["anchor"]["scene_id"] for r in observations}), 18)
        self.assertTrue(all(r["local_status"] == "PROPOSED" for r in observations))
        self.assertTrue(all(r["anchor"]["world_time"] == {"status": "UNKNOWN"} for r in observations))
        self.assertTrue(any(r["holdings"] for r in observations))
        self.assertTrue(any(h["quantity"] is None for r in observations for h in r["holdings"]))
        self.assertEqual(observations[-1]["positions"][0]["location"]["location_id"], "LOC-001")

    def test_v1_approved_only_ledger_kept_separate(self):
        ledger = json.loads((ACTIVE / "ledger/index.json").read_text(encoding="utf-8"))
        state = json.loads((ACTIVE / "data/story_state.json").read_text(encoding="utf-8"))
        receipt = json.loads((ACTIVE / "editorial/AUTHOR_APPROVAL_2026-10-23.json").read_text(encoding="utf-8"))
        self.assertEqual(ledger["episodes"], [])
        self.assertEqual(ledger["chapters"], [])
        self.assertEqual(ledger["books"], [])
        self.assertIsNone(state["approved_through_scene"])
        self.assertEqual(receipt["github_review"]["state"], "NOT_OBSERVED")
        self.assertEqual(receipt["decision_id"], "DEC-004")

    def test_context_only_includes_prior_author_accepted_episodes(self):
        pack1 = story_engine.pack(ACTIVE, "EP-001")
        self.assertNotIn("AUTHOR-ACCEPTED EPISODE MEMORY", pack1)
        early = story_engine.pack(ACTIVE, "SC-005")
        self.assertNotIn("AUTHOR-ACCEPTED EPISODE MEMORY", early)
        pack2 = story_engine.pack(ACTIVE, "EP-002")
        self.assertIn("AUTHOR-ACCEPTED EPISODE MEMORY", pack2)
        self.assertIn("EP-001 — AUTHOR ACCEPTED IN CHAT", pack2)
        self.assertIn("บ้านหลังแรก", pack2)
        self.assertIn("GitHub APPROVE reviewer provenance is NOT OBSERVED", pack2)
        self.assertNotIn("EP-002 — AUTHOR ACCEPTED IN CHAT", pack2)
        pack2_no_history = story_engine.pack(ACTIVE, "EP-002", keep=0)
        self.assertNotIn("AUTHOR-ACCEPTED EPISODE MEMORY", pack2_no_history)

    def test_historical_story_has_no_author_memory_or_s1(self):
        self.assertIsNone(author_memory.load(HISTORICAL))
        self.assertIsNone(world_state_model.load(HISTORICAL))
        self.assertNotIn("AUTHOR-ACCEPTED EPISODE MEMORY",
                         story_engine.pack(HISTORICAL, "SC-001"))

    def test_source_integrity_fails_closed_on_scene_edits(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "last-island-active"
            shutil.copytree(ACTIVE, root)
            target = root / "drafts/EP-002/SC-018.md"
            target.write_text(target.read_text(encoding="utf-8") + "\nTampered", encoding="utf-8")
            errors, _ = story_engine.validate(root)
            self.assertTrue(any("SHA256 mismatch" in e for e in errors), errors)
            with self.assertRaisesRegex(ValueError, "world_model.json"):
                world_state_model.load(root)

    def test_accepted_manuscript_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "last-island-active"
            shutil.copytree(ACTIVE, root)
            p = root / "drafts/EP-001/CH-01-FULL-DRAFT.md"
            p.write_text(p.read_text(encoding="utf-8") + "\nAlteration", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "bytes changed"):
                author_memory.load(root)
            errors, _ = story_engine.validate(root)
            self.assertTrue(any("manuscript bytes changed" in e for e in errors), errors)

    def test_missing_author_memory_does_not_generate_approval(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "last-island-active"
            shutil.copytree(ACTIVE, root)
            (root / "editorial/author_accepted_index.json").unlink()
            self.assertIsNone(author_memory.load(root))
            pack = story_engine.pack(root, "EP-002")
            self.assertNotIn("AUTHOR-ACCEPTED EPISODE MEMORY", pack)


    def test_visual_reference_image_is_pinned_and_proposal_only(self):
        import hashlib
        thumbnail = ACTIVE / "assets/CHAR-001_PORTRAIT_THUMB.webp"
        data = thumbnail.read_bytes()
        self.assertGreater(len(data), 1000)
        self.assertEqual(hashlib.sha256(data).hexdigest(), "80f13a614e0891a5346d5f146a7b8a8b7e51228a50cb0cab75524f980bbbcc97")
        design = json.loads((ACTIVE / "bible/CHAR-001_VISUAL_LOCK_PROPOSED.json").read_text(encoding="utf-8"))
        self.assertEqual(design["design_approval"], "PROPOSED")
        self.assertEqual(design["nationality"]["value"], "Thai")
        self.assertIsNone(design["permanent_identity"]["exact_age"])
        self.assertFalse(design["images"]["full_reference_committed"])


if __name__ == "__main__":
    unittest.main()
