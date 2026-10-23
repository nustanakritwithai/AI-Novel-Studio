"""EP007: accepted-for-ingest working manuscript, source-pinned build progress and missing spring."""
import hashlib
import json
import unittest
from collections import deque
from pathlib import Path

from scripts import novelctl, story_engine

ROOT = Path(__file__).resolve().parents[1] / "stories" / "last-island-active"


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class EpSevenContinuity(unittest.TestCase):
    def test_full_manuscript_contains_ten_scene_sources_in_order(self):
        ep = next(e for e in read("data/episodes.json")["episodes"] if e["id"] == "EP-007")
        self.assertEqual(ep["status"], "DRAFT")
        self.assertIsNone(ep["approved_final_draft"])
        self.assertEqual(ep["scene_ids"], [f"SC-{n:03d}" for n in range(59,69)])
        manuscript = (ROOT / ep["working_draft_path"]).read_text(encoding="utf-8")
        self.assertIn("บทที่ 7 — กำแพงชั้นใหม่", manuscript)
        self.assertIn("**จบบทที่ 7 — กำแพงชั้นใหม่**", manuscript)
        last_index = -1
        for n in range(59,69):
            name = f"SC-{n:03d}"
            text = (ROOT / f"drafts/EP-007/{name}.md").read_text(encoding="utf-8").strip()
            self.assertTrue((ROOT / f"scenes/{name}.md").is_file())
            i = manuscript.find(text)
            self.assertGreater(i,last_index,name)
            last_index = i
        ss = [s for s in read("data/scenes.json")["scenes"] if s["episode_id"] == "EP-007"]
        es = [e for e in read("data/events.json")["events"] if e["episode_id"] == "EP-007"]
        self.assertEqual(len(ss),10)
        self.assertEqual(len(es),10)
        self.assertTrue(all(x["status"] == "DRAFT" for x in ss+es))

    def test_source_hash_approved_in_chat_not_github_canon(self):
        snap = read("data/draft_continuity_ep007.json")
        ep = next(e for e in read("data/episodes.json")["episodes"] if e["id"] == "EP-007")
        d = next(x for x in read("data/decisions.json")["decisions"] if x["id"] == "DEC-013")
        blob = (ROOT / snap["source"]["path"]).read_bytes()
        digest = hashlib.sha1(f"blob {len(blob)}".encode("ascii") + b"\x00" + blob).hexdigest()
        self.assertEqual(snap["source"]["git_blob_sha"],digest)
        self.assertEqual(ep["author_decision"]["source_blob_sha"],digest)
        self.assertEqual(d["source_blob_sha"],digest)
        self.assertEqual(d["authority"],"USER")
        self.assertEqual(d["status"],"AUTHOR_ACCEPTED_IN_CHAT_FOR_INGEST")
        self.assertTrue(snap["editorial"]["chat_author_acceptance_for_ingest"])
        self.assertFalse(snap["editorial"]["formal_github_reviewer_approve_verified"])
        self.assertFalse(snap["editorial"]["may_apply_to_approved_ledger"])
        self.assertIsNone(read("data/story_state.json")["approved_through_scene"])
        self.assertEqual(read("ledger/index.json")["episodes"], [])
        self.assertEqual([x["episode_id"] for x in read("author_memory/index.json")["episodes"]],
                         ["EP-001","EP-002"])

    def test_lmg_learned_one_spring_held_one_missing_no_new_weapon(self):
        snap = read("data/draft_continuity_ep007.json")
        end = snap["end_after_sc068"]
        gun = end["gun_progress"]
        self.assertTrue(gun["learning_system_upgraded"])
        self.assertTrue(gun["lmg_recipe_learned"])
        self.assertEqual(gun["springs_required"],2)
        self.assertEqual(gun["springs_found_in_preexisting_storage"],1)
        self.assertEqual(gun["springs_newly_looted_during_ep007"],0)
        self.assertEqual(gun["springs_consumed_during_ep007"],0)
        self.assertEqual(gun["springs_still_held"],1)
        self.assertEqual(gun["springs_missing"],1)
        self.assertFalse(gun["ready_to_craft"])
        self.assertFalse(end["hero"]["gun_lmg_owned"])
        sc60 = next(s for s in read("data/scenes.json")["scenes"] if s["id"]=="SC-060")
        self.assertTrue(sc60["effects_flags"]["ep007_lmg_recipe_learned"])
        self.assertFalse(sc60["effects_flags"]["ep007_lmg_crafted"])
        new_entries = [e for e in read("data/inventory_ledger.json")["entries"]
                       if e["scene_id"] in {f"SC-{i:03d}" for i in range(59,69)}]
        self.assertFalse(any(e["item_id"] in {"ITEM-038","ITEM-039"}
                             and e["operation"] in {"GAIN","FIND","LOOT","CRAFT","SPEND"} for e in new_entries))

    def test_construction_is_partial_before_sc066_and_complete_corridor_after(self):
        snap = read("data/draft_continuity_ep007.json")
        progress = {x["scene_id"]: x for x in snap["progress"]}
        self.assertEqual(progress["SC-062"]["ring_tiles_built"],0)
        self.assertFalse(progress["SC-064"]["corridor_loop_complete"])
        self.assertFalse(progress["SC-065"]["corridor_loop_complete"])
        self.assertEqual(progress["SC-066"]["ring_tiles_built"],12)
        self.assertTrue(progress["SC-066"]["corridor_loop_complete"])
        self.assertTrue(progress["SC-066"]["test_walk_360"])
        self.assertEqual(progress["SC-067"]["outer_wall"],"PARTIAL_SEGMENTS_NOT_CLOSED")
        self.assertEqual(progress["SC-068"]["outer_wall"],"PARTIAL_SEGMENTS_NOT_CLOSED")
        end = snap["end_after_sc068"]["base_current"]
        self.assertEqual(end["original_core_footprint"],[2,2])
        self.assertFalse(end["blueprint_entire_two_story_building_completed"])
        self.assertEqual(end["ground_floor_ring"]["built_cells"],12)
        self.assertEqual(end["ground_floor_ring"]["unbuilt_cells"],0)
        self.assertTrue(end["ground_floor_ring"]["continuous_orthogonal_walkable_loop"])
        self.assertTrue(end["ground_floor_ring"]["all_four_sides_connected"])
        self.assertFalse(end["ground_floor_ring"]["internal_partitions"])
        self.assertEqual(end["outer_wall"]["built_state"],"PARTIAL")
        self.assertFalse(end["outer_wall"]["completely_closed"])
        self.assertFalse(end["outer_upper_firing_platform"]["built"])
        self.assertTrue(end["inner_original_firing_platform"]["built"])
        self.assertEqual(end["inner_original_firing_platform"]["used_in_last_scene"],"SC-068")
        self.assertEqual(end["new_main_support_pillar"]["installed"],"NOT_DEMONSTRATED")
        self.assertFalse(end["original_fixtures"]["moved_this_episode"])

    def test_built_ring_is_connected_and_blueprint_is_historical_target(self):
        target=read("data/base_expansion_4x4_target.json")
        snap=read("data/draft_continuity_ep007.json")
        self.assertEqual(target["existing_state_at_scene"],"SC-058")
        self.assertEqual(target["operational_status"],"PLANNED_NOT_BUILT")
        self.assertEqual(target["blueprint_id"],"BASE-TARGET-4X4-001")
        lines=snap["end_after_sc068"]["base_current"]["ground_floor_ring"]["plan"]
        self.assertEqual(lines,["PPPP","PCCP","PCCP","PPPP"])
        queue=deque([(0,0)])
        seen={(0,0)}
        while queue:
            r,c=queue.popleft()
            for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                nr,nc=r+dr,c+dc
                if 0<=nr<4 and 0<=nc<4 and lines[nr][nc]=="P" and (nr,nc) not in seen:
                    seen.add((nr,nc))
                    queue.append((nr,nc))
        self.assertEqual(len(seen),12)
        # BASE_TIMELINE.md is pinned by independent house-card evidence; no edits allowed.
        original=(ROOT/"bible/BASE_TIMELINE.md").read_bytes()
        sha=hashlib.sha1(f"blob {len(original)}".encode("ascii")+b"\x00"+original).hexdigest()
        self.assertEqual(sha, "6ad780ff895556e0352fc53bf80dfae58078e9b7")
        self.assertTrue((ROOT/"bible/BASE_CONSTRUCTION_EP007_DRAFT.md").is_file())

    def test_house_card_pinned_original_registry_blobs_still_resolve(self):
        refs = read("data/house_references.json")
        old_paths = {
            "SRC-CHARACTERS": ("data/house_evidence/characters_pre_ep007.json",
                               "9d321f7898e59db31b819e69fa1cd87e4f7b755e"),
            "SRC-SCENES": ("data/house_evidence/scenes_pre_ep007.json",
                           "63fcb7e21d69824f4235e8f042608a4b6e6cc486"),
        }
        for source_id, (path, expected_sha) in old_paths.items():
            source = next(x for x in refs["sources"] if x["id"] == source_id)
            self.assertEqual(source["path"], path)
            self.assertEqual(source["git_blob_sha"], expected_sha)
            self.assertEqual(source["status"], "LOCAL_REFERENCE")
            binary = (ROOT / path).read_bytes()
            actual_sha = hashlib.sha1(f"blob {len(binary)}".encode("ascii") + b"\\x00" + binary).hexdigest()
            self.assertEqual(actual_sha, expected_sha)
        self.assertTrue((ROOT/"bible/HOUSE_CARD_EVIDENCE_FREEZE_EP007.md").exists())

    def test_inventory_represents_segments_not_twenty_four_extra_tiles(self):
        all_entries=read("data/inventory_ledger.json")["entries"]
        ep7=[e for e in all_entries if e["scene_id"] in {f"SC-{i:03d}" for i in range(59,69)}]
        self.assertEqual(len(ep7),4)
        self.assertEqual([e["item_id"] for e in ep7], ["ITEM-040","ITEM-040","ITEM-040","ITEM-041"])
        self.assertEqual([e["scene_id"] for e in ep7], ["SC-064","SC-065","SC-066","SC-067"])
        self.assertTrue(all(e["quantity"] is None for e in ep7))
        self.assertTrue(all(e["status"]=="PLANNED" for e in ep7))
        self.assertEqual(len(all_entries),75)

    def test_context_pack_dashboard_and_full_registries_validate(self):
        errors,_=story_engine.validate(ROOT)
        self.assertEqual(errors,[])
        db=novelctl.load(ROOT)
        self.assertEqual(len(db["episodes"]["episodes"]),7)
        self.assertEqual(len(db["scenes"]["scenes"]),68)
        self.assertEqual(len(db["events"]["events"]),68)
        self.assertEqual(len(db["inventory_ledger"]["entries"]),75)
        pack=story_engine.pack(ROOT,"EP-007",keep=0)
        self.assertIn("EP-007",pack)
        self.assertIn("FACT-081",pack)
        self.assertIn("DRAFT",pack)
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("draft_continuity_ep007.json",html)
        self.assertIn("pack EP-007",html)
        self.assertIn("data.episodes.episodes.length",html)
        for path in ("drafts/READING_ORDER_CH-01_07.md","plot/episodes/EP-007.md",
                     "research/EP007_GAMEPLAY_GAPS.md","drafts/EP-007/README.md"):
            self.assertTrue((ROOT/path).is_file(),path)


if __name__ == "__main__":
    unittest.main()
