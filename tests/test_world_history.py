"""Real-file checks for the opt-in S2 proposed history loader.

All stories and evidence in this module are generated under a temporary root.
The fixtures contain synthetic metadata only; local APPROVED labels are never
treated as authenticated editorial approval.
"""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

try:  # Works both for package-style and ``unittest discover -s tests`` runs.
    from . import test_story_roots as story_root_fixtures
except ImportError:
    import test_story_roots as story_root_fixtures

from scripts import novelctl, storyctl, world_history, world_state_reducer


EVIDENCE = b"S2 synthetic evidence\n"
CLOCK = "CLOCK-MAIN"


def cursor(tick: int, boundary: str = "AFTER", suborder: int = 0) -> dict:
    return {"clock_id": CLOCK, "tick": tick, "suborder": suborder,
            "boundary": boundary}


def anchor(tick: int, scene: str = "SC-003", boundary: str = "AFTER",
           suborder: int = 0) -> dict:
    return {"scene_id": scene, "narration_suborder": 0, "boundary": boundary,
            "world_time": {"status": "KNOWN", "clock_id": CLOCK,
                           "tick": tick, "suborder": suborder}}


class WorldHistoryLoaderTests(unittest.TestCase):
    def setUp(self):
        # Reuse the established S1-shaped synthetic v1 story fixture through
        # composition.  Do not inherit its test cases or depend on test order.
        self.story_roots = story_root_fixtures.StoryRootTests()
        self.story_roots.setUp()
        self.addCleanup(self.story_roots.tearDown)
        self.workspace = self.story_roots.workspace
        self.alpha = self.story_roots.alpha
        self.beta = self.story_roots.beta

    @staticmethod
    def read(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write(path: Path, value: object):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    @staticmethod
    def source(path: str, content: bytes = EVIDENCE) -> dict:
        return {"path": path, "sha256": hashlib.sha256(content).hexdigest()}

    def put_evidence(self, root: Path, path: str, content: bytes = EVIDENCE) -> dict:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return self.source(path, content)

    def prepare(self, root: Path | None = None, *, slug: str = "alpha",
                start_location: str = "LOC-001", events: list[dict] | None = None,
                include_history: bool = True) -> tuple[dict, dict]:
        root = self.alpha if root is None else root
        config = self.read(root / "story.json")
        config["world_state"] = {"schema_version": 1, "enabled": True}
        self.write(root / "story.json", config)

        locations = self.read(root / "data/locations.json")
        if not any(row.get("id") == "LOC-002" for row in locations["locations"]):
            locations["locations"].append({"id": "LOC-002", "name": "Synthetic destination"})
        self.write(root / "data/locations.json", locations)
        items = self.read(root / "data/items.json")
        if not any(row.get("id") == "ITEM-002" for row in items["items"]):
            items["items"].append({"id": "ITEM-002", "name": "Synthetic unique item"})
        self.write(root / "data/items.json", items)

        baseline_source = self.put_evidence(root, "evidence/baseline.txt")
        coverage_source = self.put_evidence(root, "evidence/coverage.txt")
        model = {
            "schema_version": 1,
            "story_slug": slug,
            "baseline": {
                "id": "BASE-001",
                "anchor": anchor(0, scene="SC-001", boundary="BEFORE"),
                "source": baseline_source,
                "local_status": "APPROVED",
                "positions": [{"character_id": "CHAR-001",
                               "location": {"status": "KNOWN", "location_id": start_location}}],
                "holdings": [
                    {"item_id": "ITEM-001",
                     "holder": {"kind": "CHARACTER", "character_id": "CHAR-001"},
                     "quantity": 4},
                    {"item_id": "ITEM-001",
                     "holder": {"kind": "LOCATION", "location_id": "LOC-001"},
                     "quantity": 0},
                    {"item_id": "ITEM-002",
                     "holder": {"kind": "CHARACTER", "character_id": "CHAR-001"},
                     "quantity": 1},
                ],
            },
            "observations": [],
            "item_policies": [
                {"item_id": "ITEM-001", "tracking": "STACK", "important": True},
                {"item_id": "ITEM-002", "tracking": "UNIQUE", "important": True},
            ],
            "hierarchy": [
                {"location_id": "LOC-001", "parent": {"kind": "ROOT"}, "level": "WORLD"},
                {"location_id": "LOC-002",
                 "parent": {"kind": "LOCATION", "location_id": "LOC-001"},
                 "level": "SITE"},
            ],
            "metadata": {"fixture": "synthetic loader test"},
        }
        self.write(root / "data/world_model.json", model)

        prepared_events = []
        for spec in (events or []):
            event = copy.deepcopy(spec)
            if "source" not in event:
                event_id = event["id"]
                event["source"] = self.put_evidence(root, f"evidence/{event_id}.txt")
            prepared_events.append(event)
        history = {
            "schema_version": 1,
            "story_slug": slug,
            "model_sha256": world_state_reducer.digest(model),
            "baseline_id": "BASE-001",
            "baseline_boundary": "BEFORE",
            "coverage": {"through": cursor(10), "local_status": "APPROVED",
                         "source": coverage_source},
            "deltas": prepared_events,
        }
        if include_history:
            self.write(root / world_history.HISTORY_PATH, history)
        return model, history

    @staticmethod
    def move_event(event_id: str = "EVENT-001", *, tick: int = 1,
                   status: str = "APPROVED", source: dict | None = None) -> dict:
        event = {
            "id": event_id,
            "anchor": anchor(tick),
            "local_status": status,
            "operations": [{"operation": "MOVE_CHARACTER", "character_id": "CHAR-001",
                            "from_location_id": "LOC-001", "to_location_id": "LOC-002"}],
        }
        if source is not None:
            event["source"] = copy.deepcopy(source)
        return event

    @staticmethod
    def stack_event(event_id: str = "EVENT-002", *, tick: int = 2,
                    amount: int = 2, source: dict | None = None) -> dict:
        event = {
            "id": event_id,
            "anchor": anchor(tick),
            "local_status": "APPROVED",
            "operations": [{
                "operation": "TRANSFER_ITEM", "item_id": "ITEM-001",
                "from_holder": {"kind": "CHARACTER", "character_id": "CHAR-001"},
                "to_holder": {"kind": "LOCATION", "location_id": "LOC-001"},
                "quantity": amount,
            }],
        }
        if source is not None:
            event["source"] = copy.deepcopy(source)
        return event

    def update_history(self, root: Path, model: dict, history: dict):
        history["model_sha256"] = world_state_reducer.digest(model)
        self.write(root / world_history.HISTORY_PATH, history)

    def assert_proposed_report(self, report: dict):
        self.assertEqual(report["proposal_status"], "PROPOSED")
        self.assertEqual(report["human_editorial_approval"], "UNVERIFIED")
        self.assertEqual(report["approval_basis"], "LOCAL_DECLARATIONS_NOT_AUTHENTICATED")
        self.assertIs(report["canon_change_authorized"], False)
        self.assertIs(report["ledger_apply_authorized"], False)

    @staticmethod
    def snapshot(root: Path) -> dict[str, bytes]:
        return {path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*") if path.is_file()}

    def test_real_evidence_loads_and_produces_only_an_unverified_proposal(self):
        self.prepare(events=[self.move_event(), self.stack_event()])
        loaded = world_history.load(self.alpha)
        self.assertIsNotNone(loaded)
        report = world_history.preview(self.alpha, cursor(5))
        self.assertEqual(report["availability"], "AVAILABLE", report)
        self.assertEqual(report["applied_event_ids"], ["EVENT-001", "EVENT-002"])
        self.assertEqual(report["state"]["positions"], [{
            "character_id": "CHAR-001",
            "location": {"status": "KNOWN", "location_id": "LOC-002"},
        }])
        holdings = report["state"]["holdings"]
        self.assertEqual(holdings[0]["quantity"], 2)
        self.assertEqual(holdings[1]["quantity"], 2)
        self.assert_proposed_report(report)
        self.assertEqual(novelctl.validate(self.alpha), ([], []))

    def test_disabled_history_is_ignored_by_loader_and_v1_check(self):
        before = novelctl.validate(self.alpha)
        (self.alpha / world_history.HISTORY_PATH).write_text("{broken", encoding="utf-8")
        self.assertIsNone(world_history.load(self.alpha))
        self.assertEqual(world_history.validate(self.alpha), [])
        self.assertEqual(novelctl.validate(self.alpha), before)
        self.assertEqual(world_history.preview(self.alpha, cursor(1))["availability"], "UNKNOWN")

    def test_enabled_s1_with_absent_optional_history_keeps_legacy_unknown_path(self):
        self.prepare(include_history=False)
        self.assertIsNone(world_history.load(self.alpha))
        self.assertEqual(world_history.validate(self.alpha), [])
        report = world_history.preview(self.alpha, cursor(1))
        self.assertEqual(report["availability"], "UNKNOWN")
        self.assertIsNone(report["state"])
        self.assertEqual(novelctl.validate(self.alpha), ([], []))

    def test_explicit_malformed_cursor_is_invalid_when_history_is_disabled_or_absent(self):
        malformed = {"clock_id": "CLOCK-MAIN", "tick": True, "suborder": 0,
                     "boundary": "AFTER"}
        self.assertEqual(world_history.preview(self.alpha, malformed)["availability"], "INVALID")
        self.prepare(include_history=False)
        report = world_history.preview(self.alpha, malformed)
        self.assertEqual(report["availability"], "INVALID", report)

    def test_history_parser_rejects_duplicate_keys_nonfinite_and_invalid_utf8(self):
        self.prepare()
        path = self.alpha / world_history.HISTORY_PATH
        for raw in (b'{"schema_version":1,"schema_version":1}',
                    b'{"value":NaN}', b"\xff"):
            with self.subTest(raw=raw[:20]):
                path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    world_history.load(self.alpha)

    def test_model_parser_rejects_duplicate_keys_nonfinite_and_invalid_utf8(self):
        self.prepare()
        path = self.alpha / "data/world_model.json"
        for raw in (b'{"schema_version":1,"schema_version":1}',
                    b'{"value":Infinity}', b"\xfe"):
            with self.subTest(raw=raw[:20]):
                path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    world_history.load(self.alpha)

    def test_history_and_model_inputs_obey_the_eight_mib_bound(self):
        self.prepare()
        path = self.alpha / world_history.HISTORY_PATH
        path.write_bytes(b" " * (world_history.MAX_INPUT_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "byte input limit"):
            world_history.load(self.alpha)
        self.prepare(include_history=True)
        model_path = self.alpha / "data/world_model.json"
        model_path.write_bytes(b" " * (world_history.MAX_INPUT_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "byte input limit"):
            world_history.load(self.alpha)

    def test_dangling_history_symlink_is_invalid_when_history_is_enabled(self):
        self.prepare(include_history=False)
        link = self.alpha / world_history.HISTORY_PATH
        try:
            link.symlink_to(self.alpha / "evidence/missing-history-target.json")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        with self.assertRaises(ValueError):
            world_history.load(self.alpha)
        report = world_history.preview(self.alpha, cursor(1))
        self.assertEqual(report["availability"], "INVALID", report)

    def test_digest_mismatch_is_a_bad_present_history(self):
        _, history = self.prepare()
        history["model_sha256"] = "0" * 64
        self.write(self.alpha / world_history.HISTORY_PATH, history)
        with self.assertRaisesRegex(ValueError, "model_sha256"):
            world_history.load(self.alpha)

    def test_story_slug_mismatch_is_rejected_before_preview(self):
        model, history = self.prepare()
        history["story_slug"] = "beta"
        self.update_history(self.alpha, model, history)
        with self.assertRaisesRegex(ValueError, "story_slug"):
            world_history.load(self.alpha)
        self.assertEqual(world_history.preview(self.alpha, cursor(1))["availability"], "INVALID")

    def test_approved_missing_blank_stale_and_oversize_evidence_fail_real_preview(self):
        self.prepare()
        baseline_path = self.alpha / "evidence/baseline.txt"
        original = baseline_path.read_bytes()
        mutations = [
            ("missing", None),
            ("blank", b" \n\t"),
            ("stale", b"different bytes\n"),
            ("oversize", b"x" * (world_history.MAX_EVIDENCE_BYTES + 1)),
        ]
        for label, content in mutations:
            with self.subTest(label=label):
                if content is None:
                    baseline_path.unlink()
                else:
                    baseline_path.write_bytes(content)
                report = world_history.preview(self.alpha, cursor(1))
                self.assertEqual(report["availability"], "UNKNOWN", report)
                self.assertIsNone(report["state"])
                self.assertEqual(report["applied_event_ids"], [])
                self.assertTrue(world_history.validate(self.alpha))
                baseline_path.write_bytes(original)

    def test_evidence_cannot_be_the_model_or_history_file(self):
        model, history = self.prepare()
        for source_path in ("data/world_model.json", world_history.HISTORY_PATH):
            with self.subTest(source_path=source_path):
                model["baseline"]["source"] = self.source(source_path)
                self.write(self.alpha / "data/world_model.json", model)
                self.update_history(self.alpha, model, history)
                report = world_history.preview(self.alpha, cursor(1))
                self.assertEqual(report["availability"], "UNKNOWN", report)
                self.assertIsNone(report["state"])
                self.assertTrue(world_history.validate(self.alpha))
                # Start the next subcase from a freshly hashed model/history.
                model, history = self.prepare()

    def test_evidence_path_escape_is_checked_by_the_real_story_resolver(self):
        model, history = self.prepare()
        model["baseline"]["source"] = self.source("../outside-evidence.txt")
        self.write(self.alpha / "data/world_model.json", model)
        self.update_history(self.alpha, model, history)
        report = world_history.preview(self.alpha, cursor(1))
        self.assertEqual(report["availability"], "UNKNOWN", report)
        self.assertIn("source", report["reason"].lower())

    def test_evidence_symlink_outside_story_is_rejected_when_supported(self):
        self.prepare()
        outside = self.workspace / "outside-evidence.txt"
        outside.write_bytes(EVIDENCE)
        link = self.alpha / "evidence/outside-link.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        model = self.read(self.alpha / "data/world_model.json")
        history = self.read(self.alpha / world_history.HISTORY_PATH)
        model["baseline"]["source"] = self.source("evidence/outside-link.txt")
        self.write(self.alpha / "data/world_model.json", model)
        self.update_history(self.alpha, model, history)
        report = world_history.preview(self.alpha, cursor(1))
        self.assertEqual(report["availability"], "UNKNOWN", report)

    def test_prebaseline_and_future_event_evidence_is_never_opened(self):
        pre = self.move_event("EVENT-PRE", tick=-1,
                              source=self.source("../missing-prebaseline.txt"))
        future = self.stack_event("EVENT-FUTURE", tick=11,
                                  source=self.source("../missing-future.txt"))
        self.prepare(events=[future, pre])
        report = world_history.preview(self.alpha, cursor(5))
        self.assertEqual(report["availability"], "AVAILABLE", report)
        self.assertEqual(report["applied_event_ids"], [])
        self.assertEqual(report["state"]["positions"][0]["location"]["location_id"], "LOC-001")
        self.assertEqual(report["state"]["holdings"][0]["quantity"], 4)

    def test_included_proposed_delta_is_an_explicit_gap_even_with_valid_bytes(self):
        proposed = self.move_event(status="PROPOSED")
        self.prepare(events=[proposed])
        report = world_history.preview(self.alpha, cursor(5))
        self.assertEqual(report["availability"], "UNKNOWN", report)
        self.assertIsNone(report["state"])
        self.assertEqual(report["applied_event_ids"], [])
        self.assert_proposed_report(report)

    def test_validate_checks_approved_evidence_but_does_not_require_proposed_sources(self):
        proposed = self.move_event(status="PROPOSED",
                                   source=self.source("../not-read-proposed.txt"))
        self.prepare(events=[proposed])
        self.assertEqual(world_history.validate(self.alpha), [])
        report = world_history.preview(self.alpha, cursor(5))
        self.assertEqual(report["availability"], "UNKNOWN")

    def test_preview_calls_leave_every_source_and_input_byte_unchanged(self):
        self.prepare(events=[self.move_event(), self.stack_event()])
        before = self.snapshot(self.alpha)
        for _ in range(2):
            report = world_history.preview(self.alpha, cursor(5))
            self.assertEqual(report["availability"], "AVAILABLE")
        self.assertEqual(self.snapshot(self.alpha), before)

    def test_late_failed_transfer_discards_an_earlier_successful_event(self):
        self.prepare(events=[self.move_event(), self.stack_event("EVENT-002", tick=2, amount=99)])
        report = world_history.preview(self.alpha, cursor(5))
        self.assertEqual(report["availability"], "UNKNOWN", report)
        self.assertIsNone(report["state"])
        self.assertEqual(report["applied_event_ids"], [])

    def test_same_record_ids_are_isolated_to_the_selected_story_root(self):
        self.prepare(self.alpha, slug="alpha", start_location="LOC-001")
        self.prepare(self.beta, slug="beta", start_location="LOC-002")
        alpha = world_history.preview(self.alpha, cursor(1))
        beta = world_history.preview(self.beta, cursor(1))
        self.assertEqual(alpha["availability"], "AVAILABLE", alpha)
        self.assertEqual(beta["availability"], "AVAILABLE", beta)
        self.assertEqual(alpha["story_slug"], "alpha")
        self.assertEqual(beta["story_slug"], "beta")
        self.assertEqual(alpha["baseline_id"], beta["baseline_id"])
        self.assertEqual(alpha["state"]["positions"][0]["location"]["location_id"], "LOC-001")
        self.assertEqual(beta["state"]["positions"][0]["location"]["location_id"], "LOC-002")

    def test_story_validation_composes_history_errors_after_existing_v1_checks(self):
        self.prepare()
        (self.alpha / "evidence/coverage.txt").write_bytes(b"stale coverage evidence\n")
        errors, warnings = novelctl.validate(self.alpha)
        self.assertFalse(warnings)
        self.assertTrue(any("coverage" in error.lower() for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
