"""EP-004 author-directed plot / unapproved prose must remain isolated from approved engine state."""
import hashlib
import json
import unittest
from pathlib import Path
from scripts import novelctl, story_engine

ROOT = Path(__file__).resolve().parents[1] / "stories" / "last-island-active"


def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class Ep004DraftContinuityTests(unittest.TestCase):
    def test_ep004_prose_and_references_exist(self):
        episodes = read_json("data/episodes.json")["episodes"]
        ep = next(e for e in episodes if e["id"] == "EP-004")
        self.assertEqual(ep["status"], "DRAFT")
        self.assertIsNone(ep["approved_final_draft"])
        self.assertEqual(ep["scene_ids"], [f"SC-{n:03d}" for n in range(27, 39)])
        content = (ROOT / ep["working_draft_path"]).read_text(encoding="utf-8")
        self.assertIn("วันยาวนานของพรานมือใหม่", content)
        self.assertIn("**จบบทที่ 4", content)
        for n in range(27, 39):
            source = (ROOT / f"drafts/EP-004/SC-{n:03d}.md").read_text(encoding="utf-8").strip()
            self.assertIn(source, content)
            self.assertTrue((ROOT / f"scenes/SC-{n:03d}.md").exists())
        scenes = [x for x in read_json("data/scenes.json")["scenes"] if x["episode_id"] == "EP-004"]
        events = [x for x in read_json("data/events.json")["events"] if x["episode_id"] == "EP-004"]
        self.assertEqual(len(scenes), 12)
        self.assertEqual(len(events), 12)
        self.assertTrue(all(x["status"] == "DRAFT" for x in scenes + events))

    def test_source_bound_proposed_state_does_not_forge_approval(self):
        state = read_json("data/draft_continuity_ep004.json")
        wildlife = read_json("data/wildlife_ep004.json")
        self.assertEqual(state["status"], "DRAFT_PROPOSED_NOT_CANON")
        self.assertFalse(state["approval"]["prose_author_accepted"])
        self.assertFalse(state["approval"]["may_apply_to_approved_ledger"])
        self.assertFalse(state["approval"]["github_reviewer_approved"])
        raw = (ROOT / state["source"]["path"]).read_bytes()
        actual = hashlib.sha1(f"blob {len(raw)}".encode("ascii") + b"\x00" + raw).hexdigest()
        self.assertEqual(actual, state["source"]["git_blob_sha"])
        self.assertEqual(actual, wildlife["source"]["git_blob_sha"])
        self.assertEqual(state["source"]["predecessor"]["episode_id"], "EP-003")
        self.assertEqual([s["scene_id"] for s in state["progress"]],
                         [f"SC-{n:03d}" for n in range(27,39)])
        approved = read_json("data/story_state.json")
        ledger = read_json("ledger/index.json")
        self.assertIsNone(approved["approved_through_scene"])
        self.assertEqual(ledger["episodes"], [])
        self.assertEqual([x["episode_id"] for x in read_json("author_memory/index.json")["episodes"]],
                         ["EP-001","EP-002"])

    def test_hunting_horse_raiders_and_furnace_are_noncontradictory(self):
        state = read_json("data/draft_continuity_ep004.json")["end_after_sc038"]
        hero = state["protagonist"]
        base = state["base"]
        production = state["production"]
        self.assertEqual(hero["location_id"], "LOC-009")
        self.assertEqual(base["footprint"], "2x2")
        self.assertTrue(base["upper_firing_platform"])
        self.assertFalse(base["new_full_second_floor"])
        self.assertTrue(base["entrance_repaired_scene"] == "SC-037")
        self.assertTrue(base["has_furnace"])
        self.assertEqual(base["possible_items_taken_by_raiders"], "UNKNOWN")
        self.assertTrue(state["horse"]["tamed"])
        self.assertFalse(state["horse"]["stable_constructed"])
        self.assertEqual(state["horse"]["character_id"], "CHAR-008")
        self.assertEqual(state["raiders"]["ids"], ["CHAR-004", "CHAR-005"])
        self.assertFalse(state["raiders"]["hero_attacked_them"])
        self.assertEqual(hero["pvp_opponents_defeated_this_episode"], 0)
        self.assertTrue(production["oil_from_fat_created"])
        self.assertTrue(production["furnace_built"])
        self.assertTrue(production["iron_ore_entered_processing"])
        self.assertFalse(production["finished_iron_ready"])
        self.assertFalse(production["finished_gunpowder_ready"])
        self.assertFalse(production["new_ammunition_ready"])
        flags = next(x for x in read_json("data/scenes.json")["scenes"]
                     if x["id"]=="SC-038")["effects_flags"]
        self.assertTrue(flags["ep004_furnace_built"])
        self.assertFalse(flags["ep004_finished_iron_ready"])
        self.assertFalse(flags["ep004_finished_gunpowder_ready"])
        self.assertFalse(flags["ep004_crafted_bullets_ready"])

    def test_wildlife_and_consumed_resources_are_tracked(self):
        species = read_json("data/wildlife_ep004.json")["species"]
        names = {x["name"] for x in species}
        self.assertEqual(names, {"ไก่","กระต่าย","กวาง","ม้า","หมาป่า","หมี"})
        for beast in species:
            self.assertEqual(beast["actual_game_verification"], "UNVERIFIED")
        for beast in species:
            if beast["name"] in {"หมาป่า", "หมี"}:
                self.assertEqual(beast["count_killed"], 0)
        entries = read_json("data/inventory_ledger.json")["entries"]
        ep4 = [e for e in entries if 27 <= int(e["scene_id"].split("-")[1]) <= 38]
        self.assertTrue(ep4)
        self.assertTrue(all(x["status"] == "PLANNED" for x in ep4))
        self.assertTrue(any(x["item_id"] == "ITEM-018" and x["operation"] == "SPEND" for x in ep4))
        self.assertTrue(any(x["item_id"] == "ITEM-014" and x["operation"] == "CRAFT" for x in ep4))
        self.assertTrue(any(x["item_id"] == "ITEM-016" and x["operation"] == "CRAFT" for x in ep4))
        self.assertFalse(any(x["item_id"] in {"ITEM-021", "ITEM-030", "ITEM-022"}
                             and x["operation"] in {"CRAFT","GAIN","FIND","LOOT"} for x in ep4))
        self.assertTrue(all(x["quantity"] is None or x["quantity"] >= 1 for x in ep4))

    def test_pack_and_dashboard_can_continue_ep004(self):
        errors, _ = story_engine.validate(ROOT)
        self.assertEqual(errors, [])
        pack = story_engine.pack(ROOT, "EP-004", keep=0)
        self.assertIn("EP-004", pack)
        self.assertIn("FACT-040", pack)
        self.assertIn("DRAFT", pack)
        html = (ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("data.episodes.episodes.length", html)
        self.assertNotIn("Story Spine · ตอนที่ 1", html)
        for rel in ["drafts/READING_ORDER_CH-01_04.md",
                    "plot/episodes/EP-004.md",
                    "research/EP004_GAMEPLAY_GAPS.md",
                    "data/draft_continuity_ep004.json",
                    "data/wildlife_ep004.json"]:
            self.assertTrue((ROOT/rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
