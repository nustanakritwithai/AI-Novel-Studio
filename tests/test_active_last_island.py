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
        self.assertEqual([e["id"] for e in db["episodes"]["episodes"]], ["EP-001", "EP-002", "EP-003"])
        self.assertEqual([len([s for s in db["scenes"]["scenes"] if s["episode_id"]==e]) for e in ["EP-001", "EP-002", "EP-003"]],[8,10,8])
        self.assertEqual(len(db["events"]["events"]),26)
        self.assertTrue(all(s["status"]=="DRAFT" for s in db["scenes"]["scenes"]))
        for s in db["scenes"]["scenes"]:
            self.assertTrue((ROOT/s["draft_path"]).is_file(),s["id"])
        import json
        self.assertEqual(json.loads((ROOT/"ledger/index.json").read_text(encoding="utf-8"))["episodes"],[])
    def test_episode_three_manuscript_and_continuity_are_draft_only(self):
        import json
        db = novelctl.load(ROOT)
        episode = next(e for e in db["episodes"]["episodes"] if e["id"]=="EP-003")
        self.assertEqual(episode["status"], "DRAFT")
        self.assertIsNone(episode["approved_final_draft"])
        self.assertEqual(episode["scene_ids"], [f"SC-{n:03d}" for n in range(19,27)])
        manuscript = (ROOT/"drafts"/"EP-003"/"CH-03-FULL-DRAFT.md").read_text(encoding="utf-8")
        self.assertIn("หกนัดบนถนน", manuscript)
        self.assertIn("วันต่อมา", manuscript)
        self.assertIn("**ปัง!**", manuscript)
        self.assertIn("**จบบทที่ 3", manuscript)
        for n in range(19,27):
            self.assertTrue((ROOT/"scenes"/f"SC-{n:03d}.md").exists())
            self.assertTrue((ROOT/"drafts"/"EP-003"/f"SC-{n:03d}.md").exists())
        event = next(e for e in db["events"]["events"] if e["scene_id"]=="SC-024")
        self.assertTrue(event["effects_flags"]["ep003_killed_by_pistol"])
        post = next(s for s in db["scenes"]["scenes"] if s["id"]=="SC-026")
        self.assertFalse(post["effects_flags"]["ep003_hunting_started"])
        self.assertFalse(post["effects_flags"]["ep003_furnace_built"])
        self.assertFalse(post["effects_flags"]["ep003_oil_obtained"])
        self.assertFalse(any(e["item_id"] in {"ITEM-014","ITEM-018","ITEM-019","ITEM-020","ITEM-021","ITEM-022"} and e["operation"] in {"GAIN","CRAFT","LOOT","FIND"} for e in db["inventory_ledger"]["entries"] if e["scene_id"].startswith("SC-02")))
        self.assertEqual(json.loads((ROOT/"author_memory"/"index.json").read_text(encoding="utf-8"))["episodes"][-1]["episode_id"], "EP-002")

    def test_episode_three_pack_is_available_without_false_approval(self):
        content=story_engine.pack(ROOT, "EP-003", keep=0)
        self.assertIn("EP-003", content)
        self.assertIn("หกนัดบนถนน", content)
        self.assertIn("FACT-029", content)
        self.assertIn("DRAFT", content)

    def test_historical_example_not_default_modified(self):
        self.assertTrue((ROOT.parent/"last-island"/"data"/"canon.json").is_file())
        self.assertEqual((ROOT/"story.json").exists(),True)

if __name__=="__main__":
    unittest.main()
