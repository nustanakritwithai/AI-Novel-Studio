"""EP-006 full manuscript: structural, source-bound and continuity checks only, not literary approval."""
import hashlib
import json
import unittest
from pathlib import Path

from scripts import novelctl, story_engine

ROOT = Path(__file__).resolve().parents[1] / "stories" / "last-island-active"

def data(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))

def entry(identifier, name):
    return next(x for x in data("data/" + name + ".json")[name] if x["id"] == identifier)

class EpisodeSixDraftTests(unittest.TestCase):
    def test_manuscript_and_each_scene_are_complete_and_ordered(self):
        ep = entry("EP-006", "episodes")
        self.assertEqual(ep["status"], "DRAFT")
        self.assertIsNone(ep["approved_final_draft"])
        self.assertEqual(ep["scene_ids"], [f"SC-{n:03d}" for n in range(48, 59)])
        full = (ROOT / ep["working_draft_path"]).read_text(encoding="utf-8")
        self.assertIn("บทที่ 6 — ราคาของน้ำมัน", full)
        self.assertIn("**จบบทที่ 6 — ราคาของน้ำมัน**", full)
        prior = -1
        for n in range(48, 59):
            scene_id = f"SC-{n:03d}"
            snippet = (ROOT / f"drafts/EP-006/{scene_id}.md").read_text(encoding="utf-8").strip()
            self.assertTrue((ROOT / f"scenes/{scene_id}.md").is_file())
            offset = full.find(snippet)
            self.assertGreater(offset, prior, scene_id)
            prior = offset
        scene_rows = [x for x in data("data/scenes.json")["scenes"] if x["episode_id"] == "EP-006"]
        event_rows = [x for x in data("data/events.json")["events"] if x["episode_id"] == "EP-006"]
        self.assertEqual(len(scene_rows), 11)
        self.assertEqual(len(event_rows), 11)
        self.assertTrue(all(x["status"] == "DRAFT" for x in scene_rows + event_rows))

    def test_proposed_snapshot_is_bound_to_exact_source_not_approved(self):
        snap = data("data/draft_continuity_ep006.json")
        self.assertEqual(snap["status"], "DRAFT_PROPOSED_NOT_CANON")
        manuscript = (ROOT / snap["source"]["path"]).read_bytes()
        digest = hashlib.sha1(f"blob {len(manuscript)}".encode("ascii") + b"\x00" + manuscript).hexdigest()
        self.assertEqual(snap["source"]["git_blob_sha"], digest)
        self.assertEqual(snap["editorial"]["plot_directive_id"], "DEC-010")
        self.assertFalse(snap["editorial"]["prose_approved_in_chat"])
        self.assertFalse(snap["editorial"]["github_review_approved"])
        self.assertFalse(snap["editorial"]["apply_to_approved_ledger"])
        self.assertIsNone(data("data/story_state.json")["approved_through_scene"])
        self.assertEqual(data("ledger/index.json")["episodes"], [])
        self.assertEqual([x["episode_id"] for x in data("author_memory/index.json")["episodes"]],
                         ["EP-001", "EP-002"])

    def test_cowboy_mount_then_first_horse_dies_permanently_for_this_chapter(self):
        scenes = data("data/scenes.json")["scenes"]
        start = next(x for x in scenes if x["id"] == "SC-048")
        death = next(x for x in scenes if x["id"] == "SC-055")
        last = next(x for x in scenes if x["id"] == "SC-058")
        horse = entry("CHAR-008", "characters")
        end = data("data/draft_continuity_ep006.json")["end_after_sc058"]
        self.assertIn("CHAR-008", start["character_ids"])
        self.assertIn("CHAR-008", death["character_ids"])
        self.assertTrue(death["effects_flags"]["ep006_horse_killed"])
        self.assertFalse(last["effects_flags"]["ep006_horse_still_alive"])
        self.assertEqual(horse["status"], "DEAD_IN_EP006_DRAFT")
        self.assertEqual(end["horse"]["status"], "DEAD_IN_SC055")
        self.assertFalse(end["horse"]["replacement_mount"])
        self.assertEqual(end["hero"]["location_id"], "LOC-009")
        self.assertFalse(end["hero"]["motorcycle_owned"])
        self.assertFalse(end["hero"]["light_machine_gun_owned"])

    def test_green_card_crude_refining_and_uncertain_output(self):
        end = data("data/draft_continuity_ep006.json")["end_after_sc058"]
        refinery = end["refinery"]
        self.assertEqual(refinery["green_card_acquired"], 1)
        self.assertFalse(refinery["green_card_used"])
        self.assertEqual(refinery["crude_barrels_inserted"], 1)
        self.assertTrue(refinery["crude_processing_started"])
        self.assertFalse(refinery["refined_output_collected_by_hero"])
        self.assertEqual(refinery["other_group_collected_output"], "UNKNOWN")
        self.assertEqual(refinery["refinery_owner_or_controller"], "UNKNOWN")
        self.assertTrue(end["hero"]["green_card_owned"])
        self.assertTrue(end["hero"]["ready_oil_from_refinery_scavenging_owned"])
        self.assertEqual(end["hero"]["ready_oil_quantity"], "UNKNOWN")
        self.assertEqual(end["base"]["furnace_output_status_in_ep006"], "NOT_OBSERVED")
        entries = [e for e in data("data/inventory_ledger.json")["entries"]
                   if e["scene_id"] in {f"SC-{i:03d}" for i in range(48, 59)}]
        cards = [e for e in entries if e["item_id"] == "ITEM-034"]
        barrels = [e for e in entries if e["item_id"] == "ITEM-035"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["quantity"], 1)
        self.assertEqual([(e["operation"],e["quantity"]) for e in barrels], [("FIND",1),("SPEND",1)])
        self.assertFalse(any(e["item_id"] in {"ITEM-037","ITEM-038","ITEM-021","ITEM-030"}
                             and e["operation"] in {"GAIN","LOOT","FIND","CRAFT"} for e in entries))
        self.assertFalse(any(e["item_id"] == "ITEM-014" and e["scene_id"] > "SC-054"
                             and e["operation"] in {"GAIN","LOOT","FIND","CRAFT"} for e in entries))

    def test_three_new_armed_players_and_no_pvp_with_them(self):
        end = data("data/draft_continuity_ep006.json")["end_after_sc058"]
        group = end["new_opponents"]
        self.assertEqual(group["ids"], ["CHAR-010","CHAR-011","CHAR-012"])
        self.assertEqual(group["number_of_players"], 3)
        self.assertEqual(group["motorcycles"], 3)
        self.assertTrue(group["armed_with_light_machine_guns"])
        self.assertFalse(group["hero_fought_them"])
        self.assertFalse(group["hero_killed_any"])
        self.assertEqual(group["controls_refinery"], "UNVERIFIED_PROTAGONIST_INFERENCE")
        self.assertEqual(group["which_player_killed_horse"], "UNKNOWN")
        self.assertEqual(end["road"]["ambusher_id"], "CHAR-009")
        self.assertTrue(end["road"]["ambusher_defeated"])
        self.assertEqual(end["road"]["ambusher_identity_related_to_ep001"], "UNKNOWN")

    def test_migration_registry_and_dashboard_readback(self):
        errors, _warnings = story_engine.validate(ROOT)
        self.assertEqual(errors, [])
        db = novelctl.load(ROOT)
        self.assertEqual(len(db["episodes"]["episodes"]), 6)
        self.assertEqual(len(db["scenes"]["scenes"]), 58)
        self.assertEqual(len(db["events"]["events"]), 58)
        self.assertEqual(len(db["inventory_ledger"]["entries"]), 71)
        pack = story_engine.pack(ROOT, "EP-006", keep=0)
        self.assertIn("EP-006", pack)
        self.assertIn("FACT-065", pack)
        self.assertIn("DRAFT", pack)
        dashboard = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("draft_continuity_ep006.json", dashboard)
        self.assertIn("pack EP-006", dashboard)
        for relative in [
            "drafts/READING_ORDER_CH-01_06.md",
            "plot/episodes/EP-006.md",
            "research/EP006_GAMEPLAY_GAPS.md",
            "drafts/EP-006/README.md",
        ]:
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
