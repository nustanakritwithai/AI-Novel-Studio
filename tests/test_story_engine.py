"""v0.2 Story Engine regression tests, no credentials/network required."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from scripts import story_engine

ROOT = Path(__file__).resolve().parent.parent


class StoryEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ("data", "ledger", "bible", "scenes", "drafts"):
            shutil.copytree(ROOT / name, self.root / name)

    def tearDown(self):
        self.temp.cleanup()

    def read_index(self):
        return story_engine.load_index(self.root)

    def write_index(self, index):
        (self.root / "ledger/index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")

    def test_empty_approved_history_is_valid(self):
        self.assertEqual(story_engine.validate(self.root)[0], [])

    def test_pack_includes_style_and_locked_user_facts(self):
        pack = story_engine.pack(self.root, "SC-001")
        self.assertIn("REQUIRED WRITING STYLE", pack)
        self.assertIn("No earlier approved episodes", pack)
        self.assertIn("WORLD-CHAMPIONSHIP", pack.upper())

    def test_unknown_scene_rejected(self):
        with self.assertRaises(ValueError):
            story_engine.pack(self.root, "SC-999")

    def test_proposal_is_not_approval(self):
        result = story_engine.proposal(self.root, "EP-001")
        self.assertIn("NOT CANON", result)
        self.assertEqual(self.read_index()["episodes"], [])

    def test_unapproved_episode_cannot_enter_ledger(self):
        idx = self.read_index()
        idx["episodes"].append({"id": "EP-001", "scene_ids": [],
                                "summary_path": "ledger/episodes/EP-001.md"})
        self.write_index(idx)
        errs, _ = story_engine.validate(self.root)
        self.assertTrue(any("unapproved episode" in s for s in errs))

    def test_path_escape_fails(self):
        with self.assertRaises(ValueError):
            story_engine.within(self.root, "../outside.md", "ledger/episodes")

    def test_unknown_episode_in_proposal_fails(self):
        with self.assertRaises(ValueError):
            story_engine.proposal(self.root, "EP-999")

    def test_recent_pack_does_not_use_proposal_draft_as_approved(self):
        (self.root / "ledger/episodes/EP-001.md").write_text("SECRET FUTURE ENDING", encoding="utf-8")
        text = story_engine.pack(self.root, "SC-001")
        self.assertNotIn("SECRET FUTURE ENDING", text)

    def test_valid_approved_episode_summary_and_provenance(self):
        eps_path = self.root / "data/episodes.json"
        episodes = json.loads(eps_path.read_text(encoding="utf-8"))
        episodes["episodes"][0]["status"] = "APPROVED"
        eps_path.write_text(json.dumps(episodes, ensure_ascii=False), encoding="utf-8")
        scene_path = self.root / "data/scenes.json"
        scenes = json.loads(scene_path.read_text(encoding="utf-8"))
        for scene in scenes["scenes"]:
            scene["status"] = "APPROVED"
            path = self.root / scene["draft_path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("ร่างฉบับอนุมัติ " * 100, encoding="utf-8")
        scene_path.write_text(json.dumps(scenes, ensure_ascii=False), encoding="utf-8")
        state_path = self.root / "data/story_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["phase"] = "APPROVED_PROSE"
        state["approved_through_scene"] = "SC-008"
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        summary_path = self.root / "ledger/episodes/EP-001.md"
        summary_path.write_text("เหตุการณ์ที่อนุมัติแล้ว " * 50, encoding="utf-8")
        idx = self.read_index()
        idx["episodes"].append({
            "id": "EP-001", "scene_ids": episodes["episodes"][0]["scene_ids"],
            "summary_path": "ledger/episodes/EP-001.md",
            "approval": {"pr_number": 12, "approved_by": "editor",
                         "merge_commit": "a" * 40, "approved_at": "2026-10-22T13:00:00+07:00"}
        })
        self.write_index(idx)
        self.assertEqual(story_engine.validate(self.root)[0], [])
        self.assertNotIn("เหตุการณ์ที่อนุมัติแล้ว", story_engine.render_approved_history(self.root, "SC-008"))

    def test_approval_missing_provenance_rejected(self):
        eps_file = self.root / "data/episodes.json"
        eps = json.loads(eps_file.read_text(encoding="utf-8"))
        eps["episodes"][0]["status"] = "APPROVED"
        eps_file.write_text(json.dumps(eps, ensure_ascii=False), encoding="utf-8")
        scfile = self.root / "data/scenes.json"
        sc = json.loads(scfile.read_text(encoding="utf-8"))
        for s in sc["scenes"]: s["status"] = "APPROVED"
        scfile.write_text(json.dumps(sc, ensure_ascii=False), encoding="utf-8")
        idx = self.read_index()
        idx["episodes"].append({"id": "EP-001", "scene_ids": eps["episodes"][0]["scene_ids"],
                                "summary_path": "ledger/episodes/EP-001.md", "approval": {}})
        self.write_index(idx)
        (self.root / "ledger/episodes/EP-001.md").write_text("ฉากผ่านแล้ว"*100, encoding="utf-8")
        errs, _ = story_engine.validate(self.root)
        self.assertTrue(any("approval" in s for s in errs))


if __name__ == "__main__":
    unittest.main()
