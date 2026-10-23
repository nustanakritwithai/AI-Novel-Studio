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

    def test_ep003_source_bound_proposed_world_state_is_not_canon(self):
        import hashlib, json
        draft = json.loads((ROOT/"data"/"draft_continuity_ep003.json").read_text(encoding="utf-8"))
        manuscript = (ROOT/draft["source"]["path"]).read_bytes()
        sha = hashlib.sha1(f"blob {len(manuscript)}".encode("ascii")+b"\\x00"+manuscript).hexdigest()
        self.assertEqual(draft["source"]["git_blob_sha"], sha)
        self.assertEqual(draft["status"], "DRAFT_PROPOSED_NOT_CANON")
        self.assertIs(draft["approval"]["prose_author_accepted"], False)
        self.assertIs(draft["approval"]["may_apply_to_approved_ledger"], False)
        self.assertEqual(draft["after_sc026"]["base"]["footprint"], "2x2")
        self.assertTrue(draft["after_sc026"]["base"]["upper_firing_platform"])
        self.assertFalse(draft["after_sc026"]["base"]["new_extensions_ep003"])
        self.assertEqual(draft["clock"]["sequence"][1]["realm"], "REAL")
        self.assertEqual(draft["clock"]["sequence"][2]["realm"], "REAL_TO_VR")
        self.assertEqual(draft["after_sc026"]["avatar"]["location_id"], "LOC-009")
        self.assertFalse(draft["after_sc026"]["resources_and_production"]["furnace_built"])
        self.assertFalse(draft["after_sc026"]["resources_and_production"]["oil_acquired_during_ep003"])
        self.assertEqual(draft["after_sc026"]["resources_and_production"]["animals_hunted"], 0)
        self.assertTrue(draft["after_sc026"]["inventory"]["supplies_in_storage_remain"])
        self.assertFalse(draft["after_sc026"]["inventory"]["returned_to_retrieve_road_loot"])

    def test_ep003_six_shots_and_draft_item_integrity(self):
        import json
        db=novelctl.load(ROOT)
        entries=db["inventory_ledger"]["entries"]
        pistol=[x for x in entries if x["id"]=="INV-029"]
        self.assertEqual(len(pistol), 1)
        self.assertEqual(pistol[0]["owner_id"],"CHAR-006")
        self.assertEqual(pistol[0]["item_id"],"ITEM-022")
        self.assertEqual(pistol[0]["operation"],"SPEND")
        self.assertEqual(pistol[0]["quantity"],6)
        draft=json.loads((ROOT/"data"/"draft_continuity_ep003.json").read_text(encoding="utf-8"))
        self.assertEqual(draft["shots"]["rounds_fired"],6)
        self.assertEqual(len(draft["shots"]["sequence"]),6)
        self.assertEqual([x["shot"] for x in draft["shots"]["sequence"]],list(range(1,7)))
        manuscript=(ROOT/"drafts"/"EP-003"/"SC-024.md").read_text(encoding="utf-8")
        self.assertEqual(manuscript.count("**ปัง!**"),6)
        scene=next(s for s in db["scenes"]["scenes"] if s["id"]=="SC-024")
        self.assertTrue(scene["effects_flags"]["ep003_six_pistol_shots_fired"])
        self.assertEqual(scene["rounds_used_in_encounter"],6)
        self.assertNotIn("CHAR-001",[x["owner_id"] for x in pistol])
        self.assertEqual(json.loads((ROOT/"ledger/index.json").read_text(encoding="utf-8"))["episodes"],[])
        self.assertIsNone(db["story_state"]["approved_through_scene"])

    def test_ep003_dashboard_and_ep004_handoff_are_not_stale(self):
        ui=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertNotIn("Story Spine · ตอนที่ 1",ui)
        self.assertIn("data.episodes.episodes.length",ui)
        self.assertIn("s.episode_id",ui)
        self.assertIn("EP-003-CONTINUITY-AUDIT.md",ui)
        self.assertIn("EP-003",ui)
        for path in ["bible/BASE_TIMELINE.md",
                     "research/EP003_GAMEPLAY_GAPS.md",
                     "drafts/READING_ORDER_CH-01_03.md",
                     "drafts/EP-003/EP-003-CONTINUITY-AUDIT.md",
                     "plot/episodes/EP-004-HANDOFF-PROPOSED.md"]:
            self.assertTrue((ROOT/path).is_file(),path)

    def test_historical_example_not_default_modified(self):
        self.assertTrue((ROOT.parent/"last-island"/"data"/"canon.json").is_file())
        self.assertEqual((ROOT/"story.json").exists(),True)

if __name__=="__main__":
    unittest.main()
