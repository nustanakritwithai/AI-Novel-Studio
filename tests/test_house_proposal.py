"""Focused seeded-invalid tests for the proposal-only workshop pilot QA."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
QA_PATH = ROOT / "stories/last-island-active/design/proposals/house-atlas-v1/tools/qa_pilot.py"
DATA_PATH = ROOT / "stories/last-island-active/design/proposals/house-atlas-v1/pilot_workshop_versions.json"
SPEC = importlib.util.spec_from_file_location("qa_pilot", QA_PATH)
qa_pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qa_pilot)


class HouseProposalTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    def version(self, version_id):
        return next(v for v in self.data["house"]["versions"] if v["version_id"] == version_id)

    def test_proposal_passes_without_claiming_physical_feasibility(self):
        self.assertEqual([], qa_pilot.validate_pilot(self.data))
        for version in self.data["house"]["versions"]:
            self.assertEqual("UNKNOWN", version["physical_feasibility"])

    def test_door_room_refs_must_match_rooms_owning_edge_tiles(self):
        door = next(d for d in self.version("V03")["doors"] if d["door_id"] == "DOOR-ANNEX-N")
        door["from_room_id"] = "ROOM-WORKSHOP"
        self.assertTrue(any("rooms do not own its adjacent edge tiles" in e for e in qa_pilot.validate_pilot(self.data)))

    def test_disconnected_tiles_cannot_form_one_room(self):
        room = next(r for r in self.version("V03")["rooms"] if r["room_id"] == "ROOM-ENTRY")
        room["tile_refs"] = ["TILE-G-SE", "TILE-G-NW"]
        self.assertTrue(any("room ROOM-ENTRY tiles are disconnected" in e for e in qa_pilot.validate_pilot(self.data)))

    def test_stair_landing_room_must_touch_its_opening_edge(self):
        floor = next(f for f in self.version("V02")["floors"] if f["floor_index"] == 1)
        void = next(x for x in floor["voids"] if x["void_id"] == "VOID-STAIR-F1")
        void["polygon_xy"] = [[4, 0], [4, 1], [5, 1]]
        self.assertTrue(any("landing room is not edge-adjacent" in e for e in qa_pilot.validate_pilot(self.data)))

    def test_stair_requires_both_openings_and_landings(self):
        stair = self.version("V02")["stairs"][0]
        stair["to"]["opening_ref"] = "MISSING"
        self.assertTrue(any("opening is missing or mismatched" in e for e in qa_pilot.validate_pilot(self.data)))

    def test_floor_void_cannot_overlap_occupied_tile(self):
        floor = next(f for f in self.version("V03")["floors"] if f["floor_index"] == 0)
        void = next(x for x in floor["voids"] if x["void_id"] == "VOID-STAIR-F0")
        void["polygon_xy"] = [[0, -1], [1, -1], [1, 0], [0, 0]]
        self.assertTrue(any("overlaps TILE-G-SE" in e for e in qa_pilot.validate_pilot(self.data)))

    def test_positive_tile_overlap_is_rejected(self):
        v = self.version("V01")
        tile = next(t for t in v["tiles"] if t["tile_id"] == "TILE-G-SE")
        tile["polygon_xy"] = copy.deepcopy(next(t for t in v["tiles"] if t["tile_id"] == "TILE-G-SW")["polygon_xy"])
        self.assertTrue(any("overlap" in e for e in qa_pilot.validate_pilot(self.data)))

    def test_missing_full_edge_declaration_is_rejected(self):
        v = self.version("V03")
        v["edge_connections"] = [e for e in v["edge_connections"] if e["edge_id"] != "EDGE-TILE-G-NW--TILE-G-SW"]
        self.assertTrue(any("declared full-edge connections" in e for e in qa_pilot.validate_pilot(self.data)))

    def test_pillar_target_must_match_declared_centroid_metric(self):
        self.version("V03")["pillars"][0]["centering_target_xy"] = [1, 0]
        self.assertTrue(any("ground footprint area centroid" in e for e in qa_pilot.validate_pilot(self.data)))


if __name__ == "__main__":
    unittest.main()
