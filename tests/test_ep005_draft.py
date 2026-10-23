"""EP-005: chat-accepted literary working source without forged reviewer provenance."""
import hashlib
import json
import unittest
from pathlib import Path
from scripts import novelctl, story_engine

ROOT = Path(__file__).resolve().parents[1] / "stories" / "last-island-active"


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class Ep005ContinuityTests(unittest.TestCase):
    def test_manuscript_is_exactly_nine_written_scenes_in_order(self):
        ep = next(e for e in read("data/episodes.json")["episodes"] if e["id"] == "EP-005")
        self.assertEqual(ep["status"], "DRAFT")
        self.assertEqual(ep["scene_ids"], [f"SC-{n:03d}" for n in range(39, 48)])
        full = (ROOT / ep["working_draft_path"]).read_text(encoding="utf-8")
        self.assertIn("ค้อนที่หน้าประตู", full)
        self.assertIn("**จบบทที่ 5 — ค้อนที่หน้าประตู**", full)
        last_offset = -1
        for n in range(39, 48):
            name = f"SC-{n:03d}"
            scene_text = (ROOT / f"drafts/EP-005/{name}.md").read_text(encoding="utf-8").strip()
            self.assertTrue((ROOT / f"scenes/{name}.md").exists())
            offset = full.find(scene_text)
            self.assertGreater(offset, last_offset)
            last_offset = offset

    def test_accepted_chat_source_is_pinned_but_not_approved_ledger(self):
        ep = next(e for e in read("data/episodes.json")["episodes"] if e["id"] == "EP-005")
        decision = next(x for x in read("data/decisions.json")["decisions"] if x["id"] == "DEC-009")
        snap = read("data/draft_continuity_ep005.json")
        source = (ROOT / snap["source"]["path"]).read_bytes()
        digest = hashlib.sha1(f"blob {len(source)}".encode("ascii") + b"\x00" + source).hexdigest()
        self.assertEqual(digest, snap["source"]["git_blob_sha"])
        self.assertEqual(digest, decision["source_blob_sha"])
        self.assertEqual(digest, ep["author_decision"]["source_blob_sha"])
        self.assertEqual(decision["authority"], "USER")
        self.assertEqual(decision["status"], "AUTHOR_ACCEPTED_IN_CHAT_FOR_INGEST")
        self.assertTrue(snap["editorial"]["author_accepted_for_ingest"])
        self.assertFalse(snap["editorial"]["github_review_approval_verified"])
        self.assertTrue(snap["editorial"]["official_story_state_not_updated"])
        self.assertIsNone(read("data/story_state.json")["approved_through_scene"])
        self.assertEqual(read("ledger/index.json")["episodes"], [])
        self.assertEqual([x["episode_id"] for x in read("author_memory/index.json")["episodes"]],["EP-001","EP-002"])

    def test_siege_has_two_defeats_then_return_without_more(self):
        data=read("data/draft_continuity_ep005.json")["end_state"]
        self.assertEqual(data["rivals"], ["CHAR-004", "CHAR-005"])
        self.assertEqual(data["first_encounter_rivals_defeated"], 2)
        self.assertEqual(data["second_arrival_rivals_retreated"], 2)
        self.assertEqual(data["additional_defeats_after_return"], 0)
        scenes=read("data/scenes.json")["scenes"]
        s40=next(x for x in scenes if x["id"]=="SC-040")
        s43=next(x for x in scenes if x["id"]=="SC-043")
        s45=next(x for x in scenes if x["id"]=="SC-045")
        s46=next(x for x in scenes if x["id"]=="SC-046")
        self.assertTrue(s40["effects_flags"]["ep005_first_raider_defeated"])
        self.assertTrue(s43["effects_flags"]["ep005_second_raider_defeated"])
        self.assertTrue(s45["effects_flags"]["ep005_warning_round_fired"])
        self.assertTrue(s46["effects_flags"]["ep005_raiders_retreated"])
        self.assertFalse(s46["effects_flags"]["ep005_additional_kills"])
        self.assertEqual(s40["character_ids"], ["CHAR-001","CHAR-004","CHAR-005"])

    def test_pistol_count_ammo_moment_and_leather_consistency(self):
        entries = [e for e in read("data/inventory_ledger.json")["entries"] if e["scene_id"] in {f"SC-{n:03d}" for n in range(39,48)}]
        guns = [e for e in entries if e["item_id"] == "ITEM-017" and e["operation"] == "LOOT"]
        self.assertEqual(sorted(e["quantity"] for e in guns), [1,1])
        rounds = [e for e in entries if e["item_id"] == "ITEM-022"]
        self.assertEqual(len([e for e in rounds if e["operation"] == "LOOT" and e["quantity"] == 100]),1)
        self.assertEqual(len([e for e in rounds if e["scene_id"] == "SC-045" and e["operation"] == "SPEND" and e["quantity"] == 1]),1)
        self.assertTrue(any(e["item_id"] == "ITEM-032" and e["operation"] == "LOOT" for e in entries))
        self.assertTrue(all(e["status"]=="PLANNED" for e in entries))
        snap = read("data/draft_continuity_ep005.json")["end_state"]
        self.assertEqual(snap["protagonist_has_pistols"],2)
        self.assertEqual(snap["observed_ammunition_loot_rounds"],100)
        self.assertEqual(snap["warning_rounds_after_loot"],1)
        self.assertEqual(snap["remaining_ammunition"],"UNKNOWN")

    def test_final_position_furnace_and_defense_not_auto_built(self):
        end=read("data/draft_continuity_ep005.json")["end_state"]
        self.assertTrue(end["protagonist_alive"])
        self.assertEqual(end["location_id"],"LOC-009")
        self.assertEqual(end["house_footprint"],"2x2")
        self.assertTrue(end["upper_firing_platform"])
        self.assertFalse(end["defensive_extensions_built"])
        self.assertTrue(end["furnace_present"])
        self.assertEqual(end["furnace_processing_status"],"RUNNING_NOT_HARVESTED")
        self.assertEqual(end["horse_status"],"NOT_OBSERVED_IN_EP005")
        s47=next(s for s in read("data/scenes.json")["scenes"] if s["id"]=="SC-047")
        self.assertTrue(s47["effects_flags"]["ep005_base_defense_motivation"])
        self.assertFalse(s47["effects_flags"]["ep005_new_fortification_built"])
        ep5=[e for e in read("data/inventory_ledger.json")["entries"] if e["scene_id"] in {f"SC-{n:03d}" for n in range(39,48)}]
        self.assertFalse(any(x["item_id"] in {"ITEM-021","ITEM-030"} and x["operation"] in {"GAIN","LOOT","CRAFT"} for x in ep5))

    def test_pack_dashboard_and_reading_order_ready(self):
        errors,_ = story_engine.validate(ROOT)
        self.assertEqual(errors,[])
        pack=story_engine.pack(ROOT,"EP-005",keep=0)
        self.assertIn("EP-005",pack)
        self.assertIn("FACT-050",pack)
        self.assertIn("DRAFT",pack)
        ui=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("draft_continuity_ep005.json",ui)
        self.assertIn("pack EP-005",ui)
        self.assertIn("data.episodes.episodes.length",ui)
        for path in ["drafts/READING_ORDER_CH-01_05.md","plot/episodes/EP-005.md",
                     "research/EP005_GAMEPLAY_GAPS.md","drafts/EP-005/README.md"]:
            self.assertTrue((ROOT/path).exists(),path)


if __name__=="__main__":
    unittest.main()
