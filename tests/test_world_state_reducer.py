"""Adversarial contract tests for the pure S2 world-state preview reducer.

The fixtures here are synthetic declarations. Evidence callbacks explicitly
stand in for a successful local byte check; they do not establish human
approval or authorize applying a proposal.
"""
from __future__ import annotations

import copy
import hashlib
import unittest

from scripts import world_state_reducer


STORY = "alpha"
CLOCK = "CLOCK-MAIN"


def catalog_db(suffix: str = "") -> dict:
    """Selected-story catalog fixture; repeated IDs across stories are valid."""
    return {
        "characters": {"schema_version": 1, "characters": [
            {"id": "CHAR-A" + suffix, "name": "A", "aliases": []},
            {"id": "CHAR-B" + suffix, "name": "B", "aliases": []},
        ]},
        "locations": {"schema_version": 1, "locations": [
            {"id": "LOC-WORLD" + suffix, "name": "World"},
            {"id": "LOC-SITE" + suffix, "name": "Site"},
            {"id": "LOC-ROOM" + suffix, "name": "Room"},
        ]},
        "items": {"schema_version": 1, "items": [
            {"id": "ITEM-KEY" + suffix, "name": "Key"},
            {"id": "ITEM-STOCK" + suffix, "name": "Stock"},
        ]},
        "scenes": {"schema_version": 1, "scenes": [
            {"id": "SC-001" + suffix},
            {"id": "SC-002" + suffix},
            {"id": "SC-003" + suffix},
        ]},
    }


def source(path: str) -> dict:
    """A syntactically valid source declaration for explicit callback tests."""
    return {"path": path, "sha256": hashlib.sha256(path.encode("utf-8")).hexdigest()}


def cursor(tick: int, boundary: str = "AFTER", *, suborder: int = 0,
           clock_id: str = CLOCK) -> dict:
    return {"clock_id": clock_id, "tick": tick, "suborder": suborder,
            "boundary": boundary}


def model(*, slug: str = STORY, baseline_status: str = "APPROVED",
          baseline_world_time: dict | None = None) -> dict:
    if baseline_world_time is None:
        baseline_world_time = {"status": "KNOWN", "clock_id": CLOCK,
                               "tick": 0, "suborder": 0}
    return {
        "schema_version": 1,
        "story_slug": slug,
        "baseline": {
            "id": "BASE-001",
            "anchor": {"scene_id": "SC-001", "narration_suborder": 0,
                       "boundary": "BEFORE", "world_time": copy.deepcopy(baseline_world_time)},
            "source": source("evidence/baseline.txt"),
            "local_status": baseline_status,
            "positions": [
                {"character_id": "CHAR-A", "location": {"status": "KNOWN", "location_id": "LOC-ROOM"}},
                {"character_id": "CHAR-B", "location": {"status": "UNKNOWN"}},
            ],
            "holdings": [
                {"item_id": "ITEM-KEY", "holder": {"kind": "CHARACTER", "character_id": "CHAR-A"},
                 "quantity": 1},
                {"item_id": "ITEM-STOCK", "holder": {"kind": "LOCATION", "location_id": "LOC-ROOM"},
                 "quantity": 10},
                {"item_id": "ITEM-STOCK", "holder": {"kind": "CHARACTER", "character_id": "CHAR-A"},
                 "quantity": 0},
            ],
        },
        "observations": [],
        "item_policies": [
            {"item_id": "ITEM-KEY", "tracking": "UNIQUE", "important": True},
            {"item_id": "ITEM-STOCK", "tracking": "STACK", "important": True},
        ],
    }


def move(character_id: str = "CHAR-A", origin: str = "LOC-ROOM",
         destination: str = "LOC-SITE") -> dict:
    return {"operation": "MOVE_CHARACTER", "character_id": character_id,
            "from_location_id": origin, "to_location_id": destination}


def holder(kind: str, value: str) -> dict:
    return {"kind": kind, "character_id" if kind == "CHARACTER" else "location_id": value}


def transfer(item_id: str = "ITEM-STOCK", origin: dict | None = None,
             destination: dict | None = None, quantity: int = 4) -> dict:
    return {"operation": "TRANSFER_ITEM", "item_id": item_id,
            "from_holder": copy.deepcopy(origin or holder("LOCATION", "LOC-ROOM")),
            "to_holder": copy.deepcopy(destination or holder("CHARACTER", "CHAR-A")),
            "quantity": quantity}


def event(event_id: str, tick: int, operations: list[dict], *,
          status: str = "APPROVED", narration: int | None = None,
          scene: str = "SC-001", narrative_boundary: str = "AFTER",
          world_suborder: int = 0, clock_id: str = CLOCK,
          world_time_status: str = "KNOWN") -> dict:
    if world_time_status == "KNOWN":
        world_time = {"status": "KNOWN", "clock_id": clock_id,
                      "tick": tick, "suborder": world_suborder}
    else:
        world_time = {"status": "UNKNOWN"}
    return {
        "id": event_id,
        "anchor": {"scene_id": scene,
                   "narration_suborder": tick if narration is None else narration,
                   "boundary": narrative_boundary, "world_time": world_time},
        "local_status": status,
        "source": source(f"evidence/{event_id}.txt"),
        "operations": copy.deepcopy(operations),
    }


def history(world_model: dict, events: list[dict] | None = None, *,
            baseline_boundary: str = "BEFORE", coverage_status: str = "APPROVED",
            coverage_clock: str = CLOCK, coverage_tick: int = 10,
            coverage_boundary: str = "AFTER", story_slug: str | None = None) -> dict:
    return {
        "schema_version": 1,
        "story_slug": world_model["story_slug"] if story_slug is None else story_slug,
        "model_sha256": world_state_reducer.digest(world_model),
        "baseline_id": "BASE-001",
        "baseline_boundary": baseline_boundary,
        "coverage": {"through": cursor(coverage_tick, coverage_boundary, clock_id=coverage_clock),
                     "local_status": coverage_status,
                     "source": source("evidence/coverage.txt")},
        "deltas": copy.deepcopy(events or []),
    }


def checked_evidence(source_declaration: dict) -> None:
    """Explicit synthetic evidence callback; the reducer still reports UNVERIFIED."""
    if not isinstance(source_declaration, dict):
        raise ValueError("source declaration required")


class WorldStateReducerTests(unittest.TestCase):
    def preview(self, world_model=None, world_history=None, *, db=None,
                cutoff=None, evidence_check=checked_evidence):
        world_model = model() if world_model is None else world_model
        world_history = history(world_model) if world_history is None else world_history
        return world_state_reducer.preview(
            world_model, world_history, catalog_db() if db is None else db,
            cursor(3) if cutoff is None else cutoff, evidence_check=evidence_check)

    def assert_failure_is_atomic(self, report, availability="UNKNOWN"):
        self.assertEqual(report["availability"], availability)
        self.assertIsNone(report["state"])
        self.assertEqual(report["applied_event_ids"], [])

    @staticmethod
    def position(report, character_id="CHAR-A"):
        return next(row for row in report["state"]["positions"]
                    if row["character_id"] == character_id)

    @staticmethod
    def holding(report, item_id, expected_holder):
        return next(row for row in report["state"]["holdings"]
                    if row["item_id"] == item_id and row["holder"] == expected_holder)

    def test_world_clock_orders_flashback_events_independently_of_narration_and_array_order(self):
        world_model = model()
        # The earlier-in-world event is narrated later and appears second in the array.
        later = event("EVT-WORLD-2", 2, [move("CHAR-A", "LOC-SITE", "LOC-WORLD")],
                      narration=1, scene="SC-001")
        flashback = event("EVT-WORLD-1", 1, [move()], narration=9, scene="SC-003")
        result = self.preview(world_model, history(world_model, [later, flashback]))
        self.assertEqual(result["availability"], "AVAILABLE")
        self.assertEqual(result["applied_event_ids"], ["EVT-WORLD-1", "EVT-WORLD-2"])
        self.assertEqual(self.position(result)["location"],
                         {"status": "KNOWN", "location_id": "LOC-WORLD"})

    def test_cutoff_before_and_after_select_the_state_side_at_an_event_point(self):
        world_model = model()
        ev = event("EVT-1", 1, [move()])
        world_history = history(world_model, [ev])
        before = self.preview(world_model, world_history, cutoff=cursor(1, "BEFORE"))
        after = self.preview(world_model, world_history, cutoff=cursor(1, "AFTER"))
        self.assertEqual(before["availability"], "AVAILABLE")
        self.assertEqual(before["applied_event_ids"], [])
        self.assertEqual(self.position(before)["location"],
                         {"status": "KNOWN", "location_id": "LOC-ROOM"})
        self.assertEqual(after["availability"], "AVAILABLE")
        self.assertEqual(after["applied_event_ids"], ["EVT-1"])
        self.assertEqual(self.position(after)["location"],
                         {"status": "KNOWN", "location_id": "LOC-SITE"})

    def test_baseline_before_and_after_control_events_at_the_baseline_point(self):
        world_model = model()
        ev = event("EVT-BASE", 0, [move()])
        before = self.preview(world_model, history(world_model, [ev], baseline_boundary="BEFORE"),
                              cutoff=cursor(1))
        after = self.preview(world_model, history(world_model, [ev], baseline_boundary="AFTER"),
                             cutoff=cursor(1))
        self.assertEqual(before["availability"], "AVAILABLE")
        self.assertEqual(before["applied_event_ids"], ["EVT-BASE"])
        self.assertEqual(self.position(before)["location"]["location_id"], "LOC-SITE")
        self.assertEqual(after["availability"], "AVAILABLE")
        self.assertEqual(after["applied_event_ids"], [])
        self.assertEqual(self.position(after)["location"]["location_id"], "LOC-ROOM")

    def test_coverage_must_use_the_comparable_clock(self):
        world_model = model()
        result = self.preview(world_model, history(world_model, coverage_clock="CLOCK-OTHER"))
        self.assert_failure_is_atomic(result)

    def test_cutoff_beyond_declared_coverage_is_unknown(self):
        world_model = model()
        result = self.preview(world_model, history(world_model, coverage_tick=2), cutoff=cursor(3))
        self.assert_failure_is_atomic(result)

    def test_cutoff_before_baseline_is_unknown(self):
        world_model = model()
        result = self.preview(world_model, history(world_model), cutoff=cursor(-1, "BEFORE"))
        self.assert_failure_is_atomic(result)

    def test_unapproved_coverage_is_an_unknown_completeness_gap(self):
        world_model = model()
        result = self.preview(world_model, history(world_model, coverage_status="PROPOSED"))
        self.assert_failure_is_atomic(result)

    def test_included_proposed_event_is_a_gap_instead_of_a_silently_skipped_delta(self):
        world_model = model()
        ev = event("EVT-PROPOSED", 1, [move()], status="PROPOSED")
        result = self.preview(world_model, history(world_model, [ev]))
        self.assert_failure_is_atomic(result)

    def test_future_bad_source_is_not_read_or_hashed(self):
        world_model = model()
        future = event("EVT-FUTURE", 8, [move()], status="PROPOSED")
        future["source"]["sha256"] = "0" * 64
        seen = []

        def check(source_declaration):
            seen.append(source_declaration["path"])
            if source_declaration["path"] == future["source"]["path"]:
                raise AssertionError("future evidence must not be inspected")

        result = self.preview(world_model, history(world_model, [future]),
                              cutoff=cursor(3), evidence_check=check)
        self.assertEqual(result["availability"], "AVAILABLE")
        self.assertNotIn(future["source"]["path"], seen)
        self.assertEqual(set(seen), {"evidence/baseline.txt", "evidence/coverage.txt"})

    def test_missing_evidence_callback_keeps_local_declarations_unknown(self):
        world_model = model()
        result = self.preview(world_model, history(world_model), evidence_check=None)
        self.assert_failure_is_atomic(result)

    def test_evidence_callback_failure_fails_closed_without_a_partial_state(self):
        world_model = model()

        def stale(source_declaration):
            if source_declaration["path"] == "evidence/coverage.txt":
                raise ValueError("stale synthetic evidence")

        result = self.preview(world_model, history(world_model), evidence_check=stale)
        self.assert_failure_is_atomic(result)

    def test_approved_labels_do_not_authenticate_editorial_approval_or_apply_canon(self):
        world_model = model()
        ev = event("EVT-1", 1, [move()])
        result = self.preview(world_model, history(world_model, [ev]))
        self.assertEqual(result["availability"], "AVAILABLE")
        self.assertEqual(result["proposal_status"], "PROPOSED")
        self.assertEqual(result["human_editorial_approval"], "UNVERIFIED")
        self.assertEqual(result["approval_basis"], "LOCAL_DECLARATIONS_NOT_AUTHENTICATED")
        self.assertIs(result["canon_change_authorized"], False)
        self.assertIs(result["ledger_apply_authorized"], False)

    def test_missing_or_unapproved_baseline_is_unknown(self):
        world_model = model(baseline_status="PROPOSED")
        result = self.preview(world_model, history(world_model))
        self.assert_failure_is_atomic(result)
        world_model = model()
        world_model["baseline"] = None
        result = self.preview(world_model, history(world_model))
        self.assert_failure_is_atomic(result)

    def test_unknown_baseline_world_time_cannot_anchor_a_replay(self):
        world_model = model(baseline_world_time={"status": "UNKNOWN"})
        result = self.preview(world_model, history(world_model))
        self.assert_failure_is_atomic(result)

    def test_any_unplaceable_unknown_time_or_incomparable_event_clock_fails_closed(self):
        for ev in (event("EVT-UNKNOWN-TIME", 1, [move()], world_time_status="UNKNOWN"),
                   event("EVT-OTHER-CLOCK", 1, [move()], clock_id="CLOCK-OTHER")):
            with self.subTest(event_id=ev["id"]):
                world_model = model()
                result = self.preview(world_model, history(world_model, [ev]))
                self.assert_failure_is_atomic(result)

    def test_move_requires_a_known_current_location_matching_from_location(self):
        world_model = model()
        wrong_origin = event("EVT-WRONG-FROM", 1, [move(origin="LOC-SITE")])
        result = self.preview(world_model, history(world_model, [wrong_origin]))
        self.assert_failure_is_atomic(result)

    def test_move_of_missing_or_unknown_character_position_is_unknown_not_created(self):
        world_model = model()
        world_model["baseline"]["positions"] = [p for p in world_model["baseline"]["positions"]
                                                  if p["character_id"] != "CHAR-A"]
        missing = self.preview(world_model, history(world_model, [event("EVT-MISSING", 1, [move()])]))
        unknown_ev = event("EVT-UNKNOWN-POS", 1,
                           [move(character_id="CHAR-B", origin="LOC-ROOM", destination="LOC-SITE")])
        unknown_model = model()
        unknown = self.preview(unknown_model, history(unknown_model, [unknown_ev]))
        self.assert_failure_is_atomic(missing)
        self.assert_failure_is_atomic(unknown)

    def test_unique_item_transfer_moves_the_single_known_quantity_one_row(self):
        world_model = model()
        operation = transfer("ITEM-KEY", holder("CHARACTER", "CHAR-A"),
                             holder("CHARACTER", "CHAR-B"), 1)
        result = self.preview(world_model, history(world_model, [event("EVT-KEY", 1, [operation])]))
        self.assertEqual(result["availability"], "AVAILABLE")
        self.assertNotIn({"item_id": "ITEM-KEY", "holder": holder("CHARACTER", "CHAR-A"), "quantity": 1},
                         result["state"]["holdings"])
        self.assertEqual(self.holding(result, "ITEM-KEY", holder("CHARACTER", "CHAR-B"))["quantity"], 1)

    def test_unique_transfer_requires_quantity_one_and_matching_known_holding(self):
        world_model = model()
        for operation in (
            transfer("ITEM-KEY", holder("CHARACTER", "CHAR-A"), holder("CHARACTER", "CHAR-B"), 2),
            transfer("ITEM-KEY", holder("CHARACTER", "CHAR-B"), holder("CHARACTER", "CHAR-A"), 1),
        ):
            with self.subTest(operation=operation):
                result = self.preview(world_model, history(world_model, [event("EVT-KEY", 1, [operation])]))
                self.assert_failure_is_atomic(result)

    def test_stack_transfer_subtracts_and_adds_to_explicit_rows_including_zero(self):
        world_model = model()
        operation = transfer(quantity=10)
        result = self.preview(world_model, history(world_model, [event("EVT-STOCK", 1, [operation])]))
        self.assertEqual(result["availability"], "AVAILABLE")
        self.assertEqual(self.holding(result, "ITEM-STOCK", holder("LOCATION", "LOC-ROOM"))["quantity"], 0)
        self.assertEqual(self.holding(result, "ITEM-STOCK", holder("CHARACTER", "CHAR-A"))["quantity"], 10)

    def test_stack_transfer_rejects_insufficient_balance_without_creating_or_subtracting(self):
        world_model = model()
        operation = transfer(quantity=11)
        result = self.preview(world_model, history(world_model, [event("EVT-OVERDRAW", 1, [operation])]))
        self.assert_failure_is_atomic(result)

    def test_stack_transfer_requires_explicit_destination_holding_even_when_absent_means_nothing(self):
        world_model = model()
        world_model["baseline"]["holdings"] = [h for h in world_model["baseline"]["holdings"]
                                                if not (h["item_id"] == "ITEM-STOCK"
                                                        and h["holder"] == holder("CHARACTER", "CHAR-A"))]
        result = self.preview(world_model, history(world_model, [event("EVT-NO-DEST", 1, [transfer()])]))
        self.assert_failure_is_atomic(result)

    def test_transfer_with_unknown_source_quantity_is_unknown(self):
        world_model = model()
        row = next(h for h in world_model["baseline"]["holdings"]
                   if h["item_id"] == "ITEM-STOCK" and h["holder"] == holder("LOCATION", "LOC-ROOM"))
        row["quantity"] = None
        result = self.preview(world_model, history(world_model, [event("EVT-UNKNOWN-QTY", 1, [transfer()])]))
        self.assert_failure_is_atomic(result)

    def test_transfer_same_holder_is_invalid(self):
        world_model = model()
        operation = transfer(origin=holder("LOCATION", "LOC-ROOM"),
                             destination=holder("LOCATION", "LOC-ROOM"))
        result = self.preview(world_model, history(world_model, [event("EVT-SAME-HOLDER", 1, [operation])]))
        self.assert_failure_is_atomic(result, "INVALID")

    def test_late_failed_operation_keeps_the_whole_event_atomic(self):
        world_model = model()
        operations = [move(), move(origin="LOC-WORLD", destination="LOC-ROOM")]
        result = self.preview(world_model, history(world_model, [event("EVT-MULTI-OP", 1, operations)]))
        self.assert_failure_is_atomic(result)

    def test_late_failed_event_keeps_the_entire_preview_atomic(self):
        world_model = model()
        events = [event("EVT-1", 1, [move()]),
                  event("EVT-2", 2, [move(origin="LOC-WORLD", destination="LOC-ROOM")])]
        result = self.preview(world_model, history(world_model, events))
        self.assert_failure_is_atomic(result)

    def test_exact_repeated_event_payload_is_deduplicated_and_applied_once(self):
        world_model = model()
        ev = event("EVT-REPEAT", 1, [move()])
        result = self.preview(world_model, history(world_model, [ev, copy.deepcopy(ev)]))
        self.assertEqual(result["availability"], "AVAILABLE")
        self.assertEqual(result["applied_event_ids"], ["EVT-REPEAT"])
        self.assertEqual(result["duplicate_event_ids"], ["EVT-REPEAT"])
        self.assertEqual(self.position(result)["location"]["location_id"], "LOC-SITE")

    def test_conflicting_payloads_with_same_event_id_are_globally_invalid(self):
        world_model = model()
        first = event("EVT-CONFLICT", 1, [move()])
        second = copy.deepcopy(first)
        second["operations"] = [move(destination="LOC-WORLD")]
        result = self.preview(world_model, history(world_model, [first, second]))
        self.assert_failure_is_atomic(result, "INVALID")

    def test_distinct_event_ids_at_same_worldpoint_are_ambiguous_even_if_narrative_boundaries_differ(self):
        world_model = model()
        first = event("EVT-SAME-A", 1, [move()], narrative_boundary="BEFORE")
        second = event("EVT-SAME-B", 1, [move()], narrative_boundary="AFTER", narration=2)
        result = self.preview(world_model, history(world_model, [first, second]))
        self.assert_failure_is_atomic(result, "INVALID")

    def test_same_tick_events_with_explicit_world_suborders_have_a_defined_order(self):
        world_model = model()
        first = event("EVT-SUB-0", 1, [move()], world_suborder=0,
                      narrative_boundary="AFTER", narration=8)
        second = event("EVT-SUB-1", 1, [move("CHAR-A", "LOC-SITE", "LOC-WORLD")],
                       world_suborder=1, narrative_boundary="BEFORE", narration=1)
        result = self.preview(world_model, history(world_model, [second, first]))
        self.assertEqual(result["availability"], "AVAILABLE")
        self.assertEqual(result["applied_event_ids"], ["EVT-SUB-0", "EVT-SUB-1"])
        self.assertEqual(self.position(result)["location"]["location_id"], "LOC-WORLD")

    def test_stale_model_digest_is_invalid_before_any_event_can_apply(self):
        world_model = model()
        world_history = history(world_model, [event("EVT-1", 1, [move()])])
        world_history["model_sha256"] = "0" * 64
        result = self.preview(world_model, world_history)
        self.assert_failure_is_atomic(result, "INVALID")

    def test_cross_story_history_and_operation_references_are_invalid(self):
        world_model = model()
        result = self.preview(world_model, history(world_model, story_slug="beta"))
        self.assert_failure_is_atomic(result, "INVALID")
        ev = event("EVT-CROSS-STORY", 1, [move(character_id="CHAR-A-BETA")])
        result = self.preview(world_model, history(world_model, [ev]))
        self.assert_failure_is_atomic(result, "INVALID")

    def test_schema_rejects_boolean_as_transfer_quantity(self):
        world_model = model()
        operation = transfer(quantity=True)
        result = self.preview(world_model, history(world_model, [event("EVT-BOOL", 1, [operation])]))
        self.assert_failure_is_atomic(result, "INVALID")

    def test_caller_model_history_and_catalog_inputs_are_never_mutated(self):
        world_model = model()
        world_history = history(world_model, [event("EVT-1", 1, [move(), transfer()])])
        db = catalog_db()
        before = copy.deepcopy((world_model, world_history, db))
        result = self.preview(world_model, world_history, db=db)
        self.assertEqual(result["availability"], "AVAILABLE")
        self.assertEqual((world_model, world_history, db), before)

    def test_report_contains_canonical_digests_and_a_copy_of_the_cutoff(self):
        world_model = model()
        world_history = history(world_model)
        cutoff = cursor(3, "AFTER", suborder=2)
        result = self.preview(world_model, world_history, cutoff=cutoff)
        cutoff["tick"] = 100
        self.assertEqual(result["model_sha256"], world_state_reducer.digest(world_model))
        self.assertEqual(result["history_sha256"], world_state_reducer.digest(world_history))
        self.assertEqual(result["cutoff"], cursor(3, "AFTER", suborder=2))
        self.assertEqual(result["baseline_id"], "BASE-001")


if __name__ == "__main__":
    unittest.main()
