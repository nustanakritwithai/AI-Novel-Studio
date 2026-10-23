"""EP-006 narrative/continuity regression; structural checks are not editorial approval."""
import hashlib
import json
import unittest
from pathlib import Path
from scripts import story_engine

ROOT = Path(__file__).resolve().parents[1] / "stories" / "last-island-active"

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

class Ep006DraftTests(unittest.TestCase):
    def test_all_eleven_scenes_and_prose_order(self):
        ep=next(x for x in load("data/episodes.json")["episodes"] if x["id"]=="EP-006")
        self.assertEqual(ep["status"],"DRAFT")
        self.assertIsNone(ep["approved_final_draft"])
        self.assertEqual(ep["scene_ids"],[f"SC-{n:03d}" for n in range(48,59)])
        whole=(ROOT/ep["working_draft_path"]).read_text(encoding="utf-8")
        self.assertIn("ราคาของน้ำมัน",whole)
        self.assertIn("**จบบทที่ 6 — ราคาของน้ำมัน**",whole)
        last=-1
        for n in range(48,59):
            p=f"SC-{n:03d}"
            chunk=(ROOT/f"drafts/EP-006/{p}.md").read_text(encoding="utf-8").strip()
            self.assertTrue((ROOT/f"scenes/{p}.md").exists())
            at=whole.find(chunk)
            self.assertGreater(at,last)
            last=at
        self.assertEqual(len([e for e in load("data/events.json")["events"] if e["episode_id"]=="EP-006"]),11)

    def test_pinned_source_and_unapproved_ledger_separation(self):
        snap=load("data/draft_continuity_ep006.json")
        raw=(ROOT/snap["source"]["path"]).read_bytes()
        digest=hashlib.sha1(f"blob {len(raw)}".encode("ascii")+b"\x00"+raw).hexdigest()
        self.assertEqual(digest,snap["source"]["git_blob_sha"])
        self.assertEqual(snap["status"],"DRAFT_PROPOSED_NOT_CANON")
        self.assertFalse(snap["editorial"]["prose_approved_in_chat"])
        self.assertFalse(snap["editorial"]["github_review_approved"])
        self.assertFalse(snap["editorial"]["apply_to_approved_ledger"])
        self.assertEqual(load("ledger/index.json")["episodes"],[])
        self.assertIsNone(load("data/story_state.json")["approved_through_scene"])
        self.assertEqual([x["episode_id"] for x in load("author_memory/index.json")["episodes"]],["EP-001","EP-002"])

    def test_first_horse_dead_and_hero_does_not_gain_bike_or_lmg(self):
        snap=load("data/draft_continuity_ep006.json")["end_after_sc058"]
        self.assertEqual(snap["horse"]["id"],"CHAR-008")
        self.assertEqual(snap["horse"]["status"],"DEAD_IN_SC055")
        self.assertFalse(snap["horse"]["replacement_mount"])
        horse=next(x for x in load("data/characters.json")["characters"] if x["id"]=="CHAR-008")
        self.assertEqual(horse["status"],"DEAD_IN_EP006_DRAFT")
        self.assertFalse(snap["hero"]["motorcycle_owned"])
        self.assertFalse(snap["hero"]["light_machine_gun_owned"])
        self.assertEqual(snap["hero"]["pistols_from_ep005"],2)
        self.assertEqual(snap["hero"]["pistol_ammo_remaining"],"UNKNOWN")
        self.assertEqual(snap["new_opponents"]["number_of_players"],3)
        self.assertEqual(snap["new_opponents"]["motorcycles"],3)
        self.assertEqual(snap["new_opponents"]["which_player_killed_horse"],"UNKNOWN")
        self.assertFalse(snap["new_opponents"]["hero_fought_them"])
        self.assertFalse(snap["new_opponents"]["hero_killed_any"])

    def test_refinery_card_ready_oil_and_uncollected_crude_output(self):
        snap=load("data/draft_continuity_ep006.json")["end_after_sc058"]
        site=snap["refinery"]
        self.assertEqual(site["green_card_acquired"],1)
        self.assertFalse(site["green_card_used"])
        self.assertEqual(site["crude_barrels_inserted"],1)
        self.assertTrue(site["crude_processing_started"])
        self.assertFalse(site["refined_output_collected_by_hero"])
        self.assertEqual(site["refined_output_status_after_escape"],"UNKNOWN")
        self.assertEqual(site["other_group_collected_output"],"UNKNOWN")
        self.assertEqual(site["refinery_owner_or_controller"],"UNKNOWN")
        self.assertTrue(snap["hero"]["green_card_owned"])
        self.assertTrue(snap["hero"]["ready_oil_from_refinery_scavenging_owned"])
        self.assertEqual(snap["hero"]["location_id"],"LOC-009")
        self.assertEqual(snap["base"]["footprint"],"2x2")
        ledger=[x for x in load("data/inventory_ledger.json")["entries"]
                if x["scene_id"] in {f"SC-{n:03d}" for n in range(48,59)}]
        self.assertEqual(len([x for x in ledger if x["item_id"]=="ITEM-034" and x["operation"]=="LOOT" and x["quantity"]==1]),1)
        self.assertEqual(len([x for x in ledger if x["item_id"]=="ITEM-035" and x["operation"]=="SPEND" and x["quantity"]==1]),1)
        self.assertFalse(any(x["item_id"] in {"ITEM-037","ITEM-038"} and
                             x["operation"] in {"GAIN","LOOT","FIND","CRAFT"} for x in ledger))

    def test_bat_enemy_not_equated_with_old_opponents(self):
        chars=load("data/characters.json")["characters"]
        ids={x["id"] for x in chars}
        self.assertTrue({"CHAR-009","CHAR-010","CHAR-011","CHAR-012","CHAR-013"} <= ids)
        site=load("data/draft_continuity_ep006.json")["end_after_sc058"]
        self.assertEqual(site["road"]["ambusher_identity_related_to_ep001"],"UNKNOWN")
        self.assertEqual(site["new_opponents"]["controls_refinery"],"UNVERIFIED_PROTAGONIST_INFERENCE")
        self.assertEqual(len(site["new_opponents"]["ids"]),3)
        self.assertEqual(site["hero"]["pistol_ammo_remaining"],"UNKNOWN")

    def test_context_pack_and_dashboard_handoff(self):
        errors,_=story_engine.validate(ROOT)
        self.assertEqual(errors,[])
        pack=story_engine.pack(ROOT,"EP-006",keep=0)
        self.assertIn("EP-006",pack)
        self.assertIn("FACT-065",pack)
        self.assertIn("DRAFT",pack)
        ui=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("draft_continuity_ep006.json",ui)
        self.assertIn("pack EP-006",ui)
        self.assertIn("draft_continuity_ep005.json",ui)
        for rel in ["drafts/READING_ORDER_CH-01_06.md","plot/episodes/EP-006.md",
                    "research/EP006_GAMEPLAY_GAPS.md","data/draft_continuity_ep006.json"]:
            self.assertTrue((ROOT/rel).exists(),rel)

if __name__=="__main__":
    unittest.main()
