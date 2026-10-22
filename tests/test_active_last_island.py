"""Acceptance checks for the active Last Island story dataset (not editorial approval)."""
import unittest
from pathlib import Path
from scripts import novelctl, story_engine

ROOT=Path(__file__).resolve().parents[1]/"stories"/"last-island-active"

class ActiveLastIslandAcceptance(unittest.TestCase):
    def test_active_story_registries_validate(self):
        errors,warnings=story_engine.validate(ROOT)
        self.assertEqual(errors, [], f"Active story invalid: {errors}")
    def test_episode_two_context_pack_is_available(self):
        content=story_engine.pack(ROOT, "EP-002", keep=0)
        self.assertIn("EP-002", content)
        self.assertIn("ธนูแรกและกำแพงหิน", content)
        self.assertIn("FACT-022", content)
        self.assertIn("DRAFT", content)
    def test_drafts_do_not_promote_approved_history(self):
        db=novelctl.load(ROOT)
        self.assertIsNone(db["story_state"]["approved_through_scene"])
        self.assertEqual([e["id"] for e in db["episodes"]["episodes"]], ["EP-001", "EP-002"])
        self.assertEqual([len([s for s in db["scenes"]["scenes"] if s["episode_id"]==e]) for e in ["EP-001", "EP-002"]],[8,10])
        self.assertEqual(len(db["events"]["events"]),18)
        self.assertTrue(all(s["status"]=="DRAFT" for s in db["scenes"]["scenes"]))
        for s in db["scenes"]["scenes"]:
            self.assertTrue((ROOT/s["draft_path"]).is_file(),s["id"])
        import json
        self.assertEqual(json.loads((ROOT/"ledger/index.json").read_text(encoding="utf-8"))["episodes"],[])
    def test_historical_example_not_default_modified(self):
        self.assertTrue((ROOT.parent/"last-island"/"data"/"canon.json").is_file())
        self.assertEqual((ROOT/"story.json").exists(),True)

if __name__=="__main__":
    unittest.main()
