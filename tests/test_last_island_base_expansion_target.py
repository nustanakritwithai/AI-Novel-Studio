"""User-locked base expansion blueprint is a plan, not a built scene or Canon replay."""
import json
import unittest
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stories" / "last-island-active"


class GroundRingBlueprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.target = json.loads((ROOT / "data/base_expansion_4x4_target.json").read_text(encoding="utf-8"))

    def test_4x4_core_and_exact_twelve_corridor_tiles(self):
        plan = self.target["ground_floor"]
        grid = plan["plan"]
        self.assertEqual(plan["footprint"], [4, 4])
        self.assertEqual(len(grid), 4)
        self.assertTrue(all(len(row) == 4 for row in grid))
        self.assertEqual(sum(v == "P" for row in grid for v in row), 12)
        self.assertEqual(sum(v == "C" for row in grid for v in row), 4)
        self.assertEqual(grid[1][1:3], ["C", "C"])
        self.assertEqual(grid[2][1:3], ["C", "C"])
        for x in range(4):
            self.assertEqual(grid[0][x], "P")
            self.assertEqual(grid[3][x], "P")
        for y in range(4):
            self.assertEqual(grid[y][0], "P")
            self.assertEqual(grid[y][3], "P")

    def test_walkway_all_four_sides_connected_by_orthogonal_steps(self):
        ground = self.target["ground_floor"]
        grid = ground["plan"]
        seen = {(0,0)}
        queue = deque([(0,0)])
        while queue:
            y,x = queue.popleft()
            for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                ny,nx = y+dy,x+dx
                if (0 <= ny < 4 and 0 <= nx < 4 and grid[ny][nx] == "P"
                        and (ny,nx) not in seen):
                    seen.add((ny,nx))
                    queue.append((ny,nx))
        self.assertEqual(len(seen), 12)
        self.assertEqual(ground["corridor_width_floor_units"], 1)
        self.assertTrue(ground["corridor_can_circulate_all_four_sides"])
        self.assertTrue(ground["corridor_no_internal_partition_walls"])
        self.assertEqual(ground["corridor_layout"], "OPEN_SINGLE_CONTINUOUS_LOOP")

    def test_exactly_two_side_walls_single_pillar_and_open_upper_parapet(self):
        target = self.target
        self.assertEqual(target["defensive_walls"]["side_wall_lines"], 2)
        self.assertEqual(target["main_support_column"]["target_count"], 1)
        self.assertTrue(target["upper_floor"]["outer_perimeter_firing_area"])
        self.assertTrue(target["upper_floor"]["perimeter_parapet"])
        self.assertFalse(target["upper_floor"]["parapet_is_third_defense_wall"])
        self.assertFalse(target["upper_floor"]["third_habitable_story"])
        self.assertEqual(target["upper_floor"]["stairs_position"], "TBD")
        self.assertEqual(target["ground_floor"]["internal_roof_status"], "TBD_NOT_INFERRED")

    def test_author_future_plan_not_inserted_as_built_history(self):
        target = self.target
        self.assertEqual(target["operational_status"], "PLANNED_NOT_BUILT")
        self.assertEqual(target["existing_state_at_scene"], "SC-058")
        self.assertFalse(target["existing_structure"]["outer_4x4_ring_built"])
        facts = json.loads((ROOT / "data/canon.json").read_text(encoding="utf-8"))["facts"]
        design = next(f for f in facts if f["id"] == "FACT-067")
        self.assertEqual(design["scope"], "FUTURE_BASE_4X4_TARGET_NOT_BUILT")
        decisions = json.loads((ROOT / "data/decisions.json").read_text(encoding="utf-8"))["decisions"]
        decision = next(d for d in decisions if d["id"] == "DEC-011")
        self.assertEqual(decision["authority"], "USER")
        self.assertEqual(decision["canon_refs"], ["FACT-067"])
        self.assertIsNone(json.loads((ROOT / "data/story_state.json").read_text(encoding="utf-8"))["approved_through_scene"])
        self.assertEqual(json.loads((ROOT / "ledger/index.json").read_text(encoding="utf-8"))["episodes"], [])
        scenes = json.loads((ROOT / "data/scenes.json").read_text(encoding="utf-8"))["scenes"]
        self.assertEqual(scenes[57]["id"], "SC-058")
        self.assertEqual(scenes[-1]["id"], "SC-068")
        # The blueprint records history at SC-058; newer ring construction
        # is recorded separately by the EP007 draft continuity snapshot.
        self.assertTrue((ROOT / "bible/BASE_EXPANSION_4X4_TARGET.md").exists())


if __name__ == "__main__":
    unittest.main()
