"""Bounded synthetic acceptance checks for S3 world diagnostics.

The fixtures use local metadata and synthetic evidence only.  APPROVED labels
remain declarations and never count as authenticated editorial approval.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

try:  # Keep imported TestCase classes namespaced during unittest discovery.
    from . import test_world_history as s2_fixtures
except ImportError:
    import test_world_history as s2_fixtures

from scripts import world_consistency, world_history, world_state_reducer


ENGINE_ROOT = Path(__file__).resolve().parents[1]
CLOCK = "CLOCK-MAIN"
AFTER_5 = {"clock_id": CLOCK, "tick": 5, "suborder": 0, "boundary": "AFTER"}


class WorldConsistencyTests(unittest.TestCase):
    def setUp(self):
        # Compose the established S2 synthetic fixture without adding its
        # unittest case class to this module's discovery namespace.
        self.s2 = s2_fixtures.WorldHistoryLoaderTests()
        self.s2.setUp()
        self.addCleanup(self.s2.doCleanups)
        self.workspace = self.s2.workspace
        self.alpha = self.s2.alpha
        self.beta = self.s2.beta

    @staticmethod
    def rules(*rule_ids: str, slug: str = "alpha", enabled: bool = True) -> dict:
        return {"schema_version": 1, "story_slug": slug,
                "enabled": enabled, "rules": list(rule_ids)}

    @staticmethod
    def unique_event(event_id: str = "EVENT-UNIQUE", *, tick: int = 1,
                     source_holder: dict | None = None,
                     destination_holder: dict | None = None,
                     quantity: int = 1) -> dict:
        return {
            "id": event_id,
            "anchor": s2_fixtures.anchor(tick, scene="SC-003"),
            "local_status": "APPROVED",
            "operations": [{
                "operation": "TRANSFER_ITEM", "item_id": "ITEM-002",
                "from_holder": (source_holder or
                                {"kind": "CHARACTER", "character_id": "CHAR-001"}),
                "to_holder": (destination_holder or
                              {"kind": "LOCATION", "location_id": "LOC-001"}),
                "quantity": quantity,
            }],
        }

    def db(self, root: Path | None = None) -> dict:
        selected = self.alpha if root is None else root
        return {kind: self.s2.read(selected / f"data/{kind}.json")
                for kind in ("characters", "locations", "items", "scenes")}

    @staticmethod
    def event(history: dict, event_id: str) -> dict:
        return next(row for row in history["deltas"] if row["id"] == event_id)

    def diagnose(self, model: dict, history: dict, *, root: Path | None = None,
                 rules: dict | None = None, cutoff: dict | None = None,
                 evidence_check=None) -> dict:
        selected = self.alpha if root is None else root
        if evidence_check is None:
            evidence_check = world_history._evidence_checker(selected)
        return world_consistency.diagnose(
            model, history, self.db(selected), AFTER_5 if cutoff is None else cutoff,
            self.rules("MOVE_ORIGIN", "UNIQUE_CUSTODY", "STACK_BALANCE")
            if rules is None else rules,
            evidence_check=evidence_check,
        )

    def write_rules(self, root: Path, value: dict) -> Path:
        path = root / world_consistency.RULES_PATH
        self.s2.write(path, value)
        return path

    def cli(self, *args: object, story: str = "alpha") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ENGINE_ROOT / "scripts/storyctl.py"),
             "--workspace", str(self.workspace), "--story", story,
             *map(str, args)],
            cwd=self.workspace,
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )

    def test_move_origin_classifies_known_mismatch_and_valid_control(self):
        bad_event = self.s2.move_event("MOVE-BAD")
        bad_event["operations"][0]["from_location_id"] = "LOC-002"
        bad_model, bad_history = self.s2.prepare(events=[bad_event])

        bad = self.diagnose(bad_model, bad_history,
                            rules=self.rules("MOVE_ORIGIN"))

        self.assertEqual(bad["status"], "CONTRADICTION")
        self.assertEqual(bad["preview_availability"], "UNKNOWN")
        self.assertEqual(bad["summary"], {"pass": 0, "contradiction": 1, "unknown": 0})
        self.assertEqual(bad["enabled_rules"], ["MOVE_ORIGIN"])
        diagnostic = bad["diagnostics"][0]
        self.assertEqual(diagnostic["rule_id"], "MOVE_ORIGIN")
        self.assertEqual(diagnostic["result"], "CONTRADICTION")
        self.assertEqual(diagnostic["event_id"], "MOVE-BAD")
        self.assertEqual(diagnostic["scene_id"], "SC-003")
        self.assertEqual(diagnostic["operation_index"], 0)
        self.assertEqual(diagnostic["world_time"], bad_event["anchor"]["world_time"])
        self.assertEqual(diagnostic["entity_id"], "CHAR-001")
        self.assertEqual(diagnostic["before"],
                         {"status": "KNOWN", "location_id": "LOC-001"})
        self.assertEqual(diagnostic["expected"],
                         {"from_location_id": "LOC-002", "to_location_id": "LOC-002"})
        self.assertIsNone(diagnostic["after"])
        self.assertEqual(diagnostic["source"], self.event(bad_history, "MOVE-BAD")["source"])
        self.assertEqual(diagnostic["baseline_source"], bad_model["baseline"]["source"])
        self.assertEqual(diagnostic["coverage_source"], bad_history["coverage"]["source"])
        self.assertTrue(diagnostic["reason"])

        valid_event = self.s2.move_event("MOVE-VALID")
        valid_model, valid_history = self.s2.prepare(events=[valid_event])
        valid = self.diagnose(valid_model, valid_history,
                              rules=self.rules("MOVE_ORIGIN"))
        self.assertEqual(valid["status"], "PASS")
        self.assertEqual(valid["preview_availability"], "AVAILABLE")
        self.assertTrue(valid["complete"])
        self.assertEqual(valid["diagnostics"][0]["result"], "PASS")
        self.assertEqual(valid["diagnostics"][0]["after"],
                         {"status": "KNOWN", "location_id": "LOC-002"})

    def test_unique_custody_uses_the_actual_sole_holder_for_contradiction(self):
        wrong = self.unique_event(
            "UNIQUE-WRONG",
            source_holder={"kind": "LOCATION", "location_id": "LOC-001"},
            destination_holder={"kind": "LOCATION", "location_id": "LOC-002"},
        )
        model, history = self.s2.prepare(events=[wrong])

        report = self.diagnose(model, history,
                               rules=self.rules("UNIQUE_CUSTODY"))

        self.assertEqual(report["status"], "CONTRADICTION")
        self.assertEqual(report["preview_availability"], "UNKNOWN")
        diagnostic = report["diagnostics"][0]
        self.assertEqual((diagnostic["rule_id"], diagnostic["result"],
                          diagnostic["event_id"], diagnostic["entity_id"]),
                         ("UNIQUE_CUSTODY", "CONTRADICTION", "UNIQUE-WRONG", "ITEM-002"))
        self.assertEqual(diagnostic["before"], {"holders": [{
            "holder": {"kind": "CHARACTER", "character_id": "CHAR-001"},
            "quantity": 1,
        }]})
        self.assertEqual(diagnostic["expected"], {
            "from_holder": {"kind": "LOCATION", "location_id": "LOC-001"},
            "to_holder": {"kind": "LOCATION", "location_id": "LOC-002"},
            "quantity": 1, "required_quantity": 1,
        })
        self.assertIsNone(diagnostic["after"])

        valid_event = self.unique_event("UNIQUE-VALID")
        valid_model, valid_history = self.s2.prepare(events=[valid_event])
        valid = self.diagnose(valid_model, valid_history,
                              rules=self.rules("UNIQUE_CUSTODY"))
        self.assertEqual(valid["status"], "PASS")
        self.assertEqual(valid["diagnostics"][0]["after"], {
            "holder": {"kind": "LOCATION", "location_id": "LOC-001"},
            "quantity": 1,
        })

    def test_unique_unknown_holder_or_quantity_remains_unknown(self):
        for case in ("unknown-holder", "null-quantity"):
            with self.subTest(case=case):
                event = self.unique_event(f"UNIQUE-{case.upper()}")
                model, history = self.s2.prepare(events=[event])
                holding = next(row for row in model["baseline"]["holdings"]
                               if row["item_id"] == "ITEM-002")
                if case == "unknown-holder":
                    holding["holder"] = {"kind": "UNKNOWN"}
                else:
                    holding["quantity"] = None
                self.s2.update_history(self.alpha, model, history)

                report = self.diagnose(model, history,
                                       rules=self.rules("UNIQUE_CUSTODY"))

                self.assertEqual(report["status"], "UNKNOWN")
                self.assertEqual(report["preview_availability"], "UNKNOWN")
                diagnostic = report["diagnostics"][0]
                self.assertEqual(diagnostic["rule_id"], "UNIQUE_CUSTODY")
                self.assertEqual(diagnostic["result"], "UNKNOWN")
                self.assertEqual(diagnostic["event_id"], event["id"])
                self.assertIsNone(diagnostic["after"])

    def test_stack_shortfall_is_contradiction_even_when_destination_is_absent(self):
        short = self.s2.stack_event("STACK-SHORT", tick=1, amount=5)
        short["operations"][0]["to_holder"] = {
            "kind": "LOCATION", "location_id": "LOC-002"}
        model, history = self.s2.prepare(events=[short])

        report = self.diagnose(model, history,
                               rules=self.rules("STACK_BALANCE"))

        self.assertEqual(report["status"], "CONTRADICTION")
        self.assertEqual(report["preview_availability"], "UNKNOWN")
        diagnostic = report["diagnostics"][0]
        self.assertEqual((diagnostic["rule_id"], diagnostic["result"],
                          diagnostic["event_id"], diagnostic["entity_id"]),
                         ("STACK_BALANCE", "CONTRADICTION", "STACK-SHORT", "ITEM-001"))
        self.assertEqual(diagnostic["before"], {
            "source": {"holder": {"kind": "CHARACTER", "character_id": "CHAR-001"},
                       "quantity": 4},
            "destination": None,
        })
        self.assertEqual(diagnostic["expected"], {
            "from_holder": {"kind": "CHARACTER", "character_id": "CHAR-001"},
            "to_holder": {"kind": "LOCATION", "location_id": "LOC-002"},
            "quantity": 5,
        })
        self.assertIsNone(diagnostic["after"])

        valid = self.s2.stack_event("STACK-VALID", tick=1, amount=2)
        valid_model, valid_history = self.s2.prepare(events=[valid])
        control = self.diagnose(valid_model, valid_history,
                                rules=self.rules("STACK_BALANCE"))
        self.assertEqual(control["status"], "PASS")
        self.assertEqual(control["diagnostics"][0]["before"], {
            "source": {"holder": {"kind": "CHARACTER", "character_id": "CHAR-001"},
                       "quantity": 4},
            "destination": {"holder": {"kind": "LOCATION", "location_id": "LOC-001"},
                            "quantity": 0},
        })
        self.assertEqual(control["diagnostics"][0]["after"], {
            "source_quantity": 2, "destination_quantity": 2,
        })

    def test_missing_or_unknown_required_facts_remain_unknown(self):
        cases = ("missing-position", "unknown-position", "missing-source",
                 "null-source-quantity", "missing-destination")
        for case in cases:
            with self.subTest(case=case):
                if case.endswith("position"):
                    event = self.s2.move_event("MOVE-UNKNOWN")
                    model, history = self.s2.prepare(events=[event])
                    positions = model["baseline"]["positions"]
                    if case == "missing-position":
                        model["baseline"]["positions"] = []
                    else:
                        positions[0]["location"] = {"status": "UNKNOWN"}
                    self.s2.update_history(self.alpha, model, history)
                    report = self.diagnose(model, history,
                                           rules=self.rules("MOVE_ORIGIN"))
                    diagnostic = report["diagnostics"][0]
                    self.assertEqual(diagnostic["result"], "UNKNOWN")
                    self.assertIsNone(diagnostic["after"])
                else:
                    event = self.s2.stack_event("STACK-UNKNOWN", tick=1, amount=2)
                    event["operations"][0]["to_holder"] = {
                        "kind": "LOCATION", "location_id": "LOC-002"}
                    model, history = self.s2.prepare(events=[event])
                    holdings = model["baseline"]["holdings"]
                    source_index = next(i for i, row in enumerate(holdings)
                                        if row["item_id"] == "ITEM-001"
                                        and row["holder"]["kind"] == "CHARACTER")
                    if case == "missing-source":
                        del holdings[source_index]
                    elif case == "null-source-quantity":
                        holdings[source_index]["quantity"] = None
                    self.s2.update_history(self.alpha, model, history)
                    report = self.diagnose(model, history,
                                           rules=self.rules("STACK_BALANCE"))
                    diagnostic = report["diagnostics"][0]
                    self.assertEqual(diagnostic["result"], "UNKNOWN")
                    self.assertIsNone(diagnostic["after"])
                    if case == "missing-destination":
                        self.assertIsNone(diagnostic["before"]["destination"])
                self.assertEqual(report["status"], "UNKNOWN")
                self.assertEqual(report["preview_availability"], "UNKNOWN")
                self.assertEqual(report["summary"]["contradiction"], 0)

    def test_evidence_and_approval_gaps_suppress_all_operation_diagnostics(self):
        move = self.s2.move_event("EARLY-MOVE", tick=1)
        stack = self.s2.stack_event("LATE-STACK", tick=2, amount=1)
        model, history = self.s2.prepare(events=[move, stack])
        prepared_stack = self.event(history, "LATE-STACK")
        (self.alpha / prepared_stack["source"]["path"]).unlink()

        missing_evidence = self.diagnose(model, history)

        self.assertEqual(missing_evidence["status"], "UNKNOWN")
        self.assertEqual(missing_evidence["preview_availability"], "UNKNOWN")
        self.assertEqual(missing_evidence["diagnostics"], [])
        self.assertIsNone(missing_evidence["state"])

        stale_event = self.s2.move_event("STALE-EVIDENCE", tick=1)
        stale_model, stale_history = self.s2.prepare(events=[stale_event])
        prepared_stale = self.event(stale_history, "STALE-EVIDENCE")
        (self.alpha / prepared_stale["source"]["path"]).write_bytes(b"stale evidence\n")
        stale_evidence = self.diagnose(stale_model, stale_history)
        self.assertEqual(stale_evidence["status"], "UNKNOWN")
        self.assertEqual(stale_evidence["preview_availability"], "UNKNOWN")
        self.assertEqual(stale_evidence["diagnostics"], [])

        proposed = self.s2.move_event("PROPOSED-EVENT", status="PROPOSED")
        proposed_model, proposed_history = self.s2.prepare(events=[proposed])
        approval_gap = self.diagnose(proposed_model, proposed_history)
        self.assertEqual(approval_gap["status"], "UNKNOWN")
        self.assertEqual(approval_gap["preview_availability"], "UNKNOWN")
        self.assertEqual(approval_gap["diagnostics"], [])
        self.assertEqual(approval_gap["summary"],
                         {"pass": 0, "contradiction": 0, "unknown": 0})

    def test_failed_reduction_is_atomic_and_diagnostics_are_immutable_and_repeatable(self):
        passing = self.s2.move_event("FIRST-MOVE", tick=1)
        failing = self.s2.stack_event("SECOND-STACK", tick=2, amount=99)
        model, history = self.s2.prepare(events=[failing, passing])
        rules = self.rules("MOVE_ORIGIN", "STACK_BALANCE")
        db = self.db()
        cutoff = copy.deepcopy(AFTER_5)
        original = copy.deepcopy((model, history, db, cutoff, rules))

        first = world_consistency.diagnose(
            model, history, db, cutoff, rules,
            evidence_check=world_history._evidence_checker(self.alpha))
        second = world_consistency.diagnose(
            model, history, db, cutoff, rules,
            evidence_check=world_history._evidence_checker(self.alpha))

        self.assertEqual(first, second)
        self.assertEqual((model, history, db, cutoff, rules), original)
        self.assertEqual(first["status"], "CONTRADICTION")
        self.assertEqual(first["preview_availability"], "UNKNOWN")
        self.assertFalse(first["complete"])
        self.assertIsNone(first["state"])
        self.assertEqual([item["event_id"] for item in first["diagnostics"]],
                         ["FIRST-MOVE", "SECOND-STACK"])
        self.assertEqual([item["result"] for item in first["diagnostics"]],
                         ["PASS", "CONTRADICTION"])
        self.assertEqual(first["diagnostics"][0]["after"],
                         {"status": "KNOWN", "location_id": "LOC-002"})
        self.assertIsNone(first["diagnostics"][1]["after"])
        self.assertTrue(all("state" not in item for item in first["diagnostics"]))
        self.assertEqual(first["summary"], {"pass": 1, "contradiction": 1, "unknown": 0})
        self.assertEqual(first["diagnostics"][0]["event_id"], "FIRST-MOVE")
        self.assertEqual(first["diagnostics"][0]["scene_id"], "SC-003")
        self.assertEqual(first["diagnostics"][0]["operation_index"], 0)
        self.assertEqual(first["diagnostics"][0]["world_time"],
                         passing["anchor"]["world_time"])
        prepared_failure = self.event(history, "SECOND-STACK")
        self.assertEqual(first["diagnostics"][1]["source"], prepared_failure["source"])
        self.assertEqual(first["diagnostics"][1]["baseline_source"],
                         model["baseline"]["source"])
        self.assertEqual(first["diagnostics"][1]["coverage_source"],
                         history["coverage"]["source"])

        same_event = self.s2.move_event("TWO-OP-EVENT", tick=1)
        late_failure = self.s2.stack_event("IGNORED-ID", tick=1, amount=99)
        same_event["operations"].append(copy.deepcopy(late_failure["operations"][0]))
        same_model, same_history = self.s2.prepare(events=[same_event])
        same_db = self.db()
        checker = world_history._evidence_checker(self.alpha)
        legacy_preview = world_state_reducer.preview(
            same_model, same_history, same_db, AFTER_5, evidence_check=checker)
        inspected = world_state_reducer.inspect_preview(
            same_model, same_history, same_db, AFTER_5,
            evidence_check=world_history._evidence_checker(self.alpha))
        same_report = self.diagnose(same_model, same_history,
                                    rules=self.rules("MOVE_ORIGIN", "STACK_BALANCE"))

        self.assertEqual(inspected["preview"], legacy_preview)
        self.assertEqual(legacy_preview["availability"], "UNKNOWN")
        self.assertIsNone(legacy_preview["state"])
        self.assertEqual(legacy_preview["applied_event_ids"], [])
        self.assertEqual([d["event_id"] for d in same_report["diagnostics"]],
                         ["TWO-OP-EVENT", "TWO-OP-EVENT"])
        self.assertEqual([d["operation_index"] for d in same_report["diagnostics"]], [0, 1])
        self.assertEqual([d["result"] for d in same_report["diagnostics"]],
                         ["PASS", "CONTRADICTION"])
        self.assertEqual(same_report["status"], "CONTRADICTION")
        self.assertIsNone(same_report["state"])
        self.assertFalse(same_report["complete"])

    def test_world_clock_controls_boundary_order_flashbacks_and_collisions(self):
        move = self.s2.move_event("CLOCK-MOVE", tick=1)
        stack = self.s2.stack_event("CLOCK-STACK", tick=2, amount=1)
        stack["anchor"]["scene_id"] = "SC-001"  # A narrated flashback.
        model, history = self.s2.prepare(events=[stack, move])  # Reverse world order.
        both = self.rules("MOVE_ORIGIN", "STACK_BALANCE")

        before = self.diagnose(model, history, rules=both,
                               cutoff={"clock_id": CLOCK, "tick": 1,
                                       "suborder": 0, "boundary": "BEFORE"})
        after = self.diagnose(model, history, rules=both,
                              cutoff={"clock_id": CLOCK, "tick": 1,
                                      "suborder": 0, "boundary": "AFTER"})
        all_events = self.diagnose(model, history, rules=both)

        self.assertEqual(before["status"], "NO_CHECKS")
        self.assertEqual(before["diagnostics"], [])
        self.assertEqual(after["status"], "PASS")
        self.assertEqual([d["event_id"] for d in after["diagnostics"]], ["CLOCK-MOVE"])
        self.assertEqual(all_events["status"], "PASS")
        self.assertEqual([d["event_id"] for d in all_events["diagnostics"]],
                         ["CLOCK-MOVE", "CLOCK-STACK"])
        self.assertEqual([d["scene_id"] for d in all_events["diagnostics"]],
                         ["SC-003", "SC-001"])

        collision_a = self.s2.move_event("COLLISION-A", tick=1)
        collision_b = self.s2.stack_event("COLLISION-B", tick=1, amount=1)
        collision_model, collision_history = self.s2.prepare(
            events=[collision_a, collision_b])
        collision = self.diagnose(collision_model, collision_history, rules=both)
        self.assertEqual(collision["status"], "INVALID")
        self.assertEqual(collision["preview_availability"], "INVALID")
        self.assertEqual(collision["diagnostics"], [])
        self.assertIsNone(collision["state"])

    def test_future_event_evidence_is_never_checked(self):
        selected = self.s2.move_event("SELECTED", tick=1)
        future = self.s2.stack_event("FUTURE", tick=11, amount=1,
                                     source=self.s2.source("../missing-future-evidence.txt"))
        model, history = self.s2.prepare(events=[future, selected])
        checked: list[dict] = []

        def evidence_check(source: dict) -> None:
            checked.append(copy.deepcopy(source))

        report = self.diagnose(model, history, evidence_check=evidence_check)

        self.assertEqual(report["status"], "PASS")
        self.assertEqual([d["event_id"] for d in report["diagnostics"]], ["SELECTED"])
        self.assertNotIn(future["source"], checked)
        self.assertEqual(checked, [model["baseline"]["source"],
                                   history["coverage"]["source"],
                                   self.event(history, "SELECTED")["source"]])

    def test_rules_config_is_strict_and_disabled_config_does_not_read_world_files(self):
        model, history = self.s2.prepare(events=[])
        (self.alpha / "data/world_model.json").write_text("{malformed", encoding="utf-8")
        (self.alpha / "data/world_history.json").write_text("{malformed", encoding="utf-8")

        missing = world_consistency.build(self.alpha, AFTER_5)
        self.assertEqual(missing["status"], "DISABLED")
        self.assertIsNone(missing["model_sha256"])
        self.assertIsNone(missing["history_sha256"])

        disabled = self.rules("MOVE_ORIGIN", enabled=False)
        self.write_rules(self.alpha, disabled)
        disabled_report = world_consistency.build(self.alpha, AFTER_5)
        self.assertEqual(disabled_report["status"], "DISABLED")
        self.assertIsNone(disabled_report["model_sha256"])
        self.assertIsNone(disabled_report["history_sha256"])

        bad_documents = []
        boolean_version = self.rules("MOVE_ORIGIN")
        boolean_version["schema_version"] = True
        bad_documents.append(boolean_version)
        bad_documents.append({**self.rules("MOVE_ORIGIN"), "enabled": "true"})
        bad_documents.append({**self.rules("MOVE_ORIGIN"), "rules": ["MOVE_ORIGIN", "MOVE_ORIGIN"]})
        bad_documents.append({**self.rules("MOVE_ORIGIN"), "extra": "closed object"})
        bad_documents.append(self.rules("FUTURE_RULE"))
        for invalid_rules in bad_documents:
            with self.subTest(invalid_rules=invalid_rules):
                self.write_rules(self.alpha, invalid_rules)
                invalid = world_consistency.build(self.alpha, AFTER_5)
                self.assertEqual(invalid["status"], "INVALID", invalid)
                self.assertEqual(invalid["diagnostics"], [])

        mismatched_disabled = self.rules("MOVE_ORIGIN", slug="beta", enabled=False)
        self.write_rules(self.alpha, mismatched_disabled)
        mismatch = world_consistency.build(self.alpha, AFTER_5)
        self.assertEqual(mismatch["status"], "INVALID")
        self.assertIn("story_slug", mismatch.get("reason", ""))

    def test_story_roots_are_isolated_and_rules_file_must_stay_inside_story(self):
        alpha_model, alpha_history = self.s2.prepare(
            self.alpha, slug="alpha", start_location="LOC-001",
            events=[self.s2.move_event("ALPHA-MOVE")])
        beta_model, beta_history = self.s2.prepare(
            self.beta, slug="beta", start_location="LOC-002",
            events=[self.s2.move_event("BETA-MOVE")])
        self.write_rules(self.alpha, self.rules("MOVE_ORIGIN", slug="alpha"))
        self.write_rules(self.beta, self.rules("MOVE_ORIGIN", slug="beta"))

        alpha = world_consistency.build(self.alpha, AFTER_5)
        beta = world_consistency.build(self.beta, AFTER_5)

        self.assertEqual(alpha["status"], "PASS")
        self.assertEqual(beta["status"], "CONTRADICTION")
        self.assertEqual(alpha["story_slug"], "alpha")
        self.assertEqual(beta["story_slug"], "beta")
        self.assertEqual(alpha["diagnostics"][0]["event_id"], "ALPHA-MOVE")
        self.assertEqual(beta["diagnostics"][0]["event_id"], "BETA-MOVE")
        self.assertEqual(alpha["diagnostics"][0]["before"]["location_id"], "LOC-001")
        self.assertEqual(beta["diagnostics"][0]["before"]["location_id"], "LOC-002")
        self.assertEqual(alpha["model_sha256"], world_state_reducer.digest(alpha_model))
        self.assertEqual(beta["model_sha256"], world_state_reducer.digest(beta_model))
        self.assertEqual(alpha["history_sha256"], world_state_reducer.digest(alpha_history))
        self.assertEqual(beta["history_sha256"], world_state_reducer.digest(beta_history))

        outside = self.workspace / "outside-world-rules.json"
        self.s2.write(outside, self.rules("MOVE_ORIGIN"))
        linked_rules = self.alpha / world_consistency.RULES_PATH
        linked_rules.unlink()
        try:
            linked_rules.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        rejected = world_consistency.build(self.alpha, AFTER_5)
        self.assertEqual(rejected["status"], "INVALID")
        self.assertEqual(rejected["diagnostics"], [])

    def test_world_rules_cannot_be_reused_as_approved_operation_evidence(self):
        event = self.s2.move_event("RULES-AS-SOURCE")
        model, history = self.s2.prepare(events=[event])
        rules_path = self.write_rules(self.alpha, self.rules("MOVE_ORIGIN"))
        rules_bytes = rules_path.read_bytes()
        model["baseline"]["source"] = {
            "path": world_consistency.RULES_PATH,
            "sha256": hashlib.sha256(rules_bytes).hexdigest(),
        }
        self.s2.write(self.alpha / "data/world_model.json", model)
        self.s2.update_history(self.alpha, model, history)

        report = world_consistency.build(self.alpha, AFTER_5)

        self.assertEqual(report["status"], "UNKNOWN")
        self.assertEqual(report["preview_availability"], "UNKNOWN")
        self.assertEqual(report["diagnostics"], [])
        self.assertIsNone(report["state"])

    def test_lintstate_cli_status_exit_codes_and_private_output(self):
        event = self.s2.move_event("CLI-MOVE")
        model, history = self.s2.prepare(events=[event])
        self.write_rules(self.alpha, self.rules("MOVE_ORIGIN"))
        out = self.workspace / ".local" / "reports" / "world.json"
        result = self.cli("lintstate", "--clock", CLOCK, "--tick", "5",
                          "--boundary", "AFTER", "--out", out)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Wrote private local artifact", result.stdout)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["status"], "PASS")

        outside = self.workspace / "world-report.json"
        rejected_output = self.cli("lintstate", "--clock", CLOCK, "--tick", "5",
                                   "--out", outside)
        self.assertEqual(rejected_output.returncode, 1)
        self.assertFalse(outside.exists())

        no_checks_model, no_checks_history = self.s2.prepare(events=[])
        no_checks = self.cli("lintstate", "--clock", CLOCK, "--tick", "5")
        self.assertEqual(no_checks.returncode, 2, no_checks.stderr)
        self.assertEqual(json.loads(no_checks.stdout)["status"], "NO_CHECKS")

        proposed = self.s2.move_event("CLI-PROPOSED", status="PROPOSED")
        proposed_model, proposed_history = self.s2.prepare(events=[proposed])
        unknown = self.cli("lintstate", "--clock", CLOCK, "--tick", "5")
        self.assertEqual(unknown.returncode, 2, unknown.stderr)
        self.assertEqual(json.loads(unknown.stdout)["status"], "UNKNOWN")

        disabled = self.rules("MOVE_ORIGIN", enabled=False)
        self.write_rules(self.alpha, disabled)
        disabled_run = self.cli("lintstate", "--clock", CLOCK, "--tick", "5")
        self.assertEqual(disabled_run.returncode, 2, disabled_run.stderr)
        self.assertEqual(json.loads(disabled_run.stdout)["status"], "DISABLED")

        self.write_rules(self.alpha, self.rules("FUTURE_RULE"))
        invalid_run = self.cli("lintstate", "--clock", CLOCK, "--tick", "5")
        self.assertEqual(invalid_run.returncode, 1, invalid_run.stderr)
        self.assertEqual(json.loads(invalid_run.stdout)["status"], "INVALID")

        bad_event = self.s2.move_event("CLI-CONTRADICTION")
        bad_event["operations"][0]["from_location_id"] = "LOC-002"
        bad_model, bad_history = self.s2.prepare(events=[bad_event])
        self.write_rules(self.alpha, self.rules("MOVE_ORIGIN"))
        contradiction = self.cli("lintstate", "--clock", CLOCK, "--tick", "5")
        self.assertEqual(contradiction.returncode, 1, contradiction.stderr)
        contradiction_report = json.loads(contradiction.stdout)
        self.assertEqual(contradiction_report["status"], "CONTRADICTION")
        self.assertEqual(contradiction_report["diagnostics"][0]["event_id"],
                         "CLI-CONTRADICTION")
        self.assertEqual(contradiction_report["diagnostics"][0]["source"],
                         self.event(bad_history, "CLI-CONTRADICTION")["source"])

    def test_unselected_failures_and_stale_or_unapproved_evidence_never_claim_pass(self):
        def assert_advisory(report: dict) -> None:
            self.assertEqual(report["proposal_status"], "PROPOSED")
            self.assertEqual(report["human_editorial_approval"], "UNVERIFIED")
            self.assertEqual(report["approval_basis"],
                             "LOCAL_DECLARATIONS_NOT_AUTHENTICATED")
            self.assertIs(report["canon_change_authorized"], False)
            self.assertIs(report["ledger_apply_authorized"], False)
            self.assertIs(report["usable_world_state"], False)
            self.assertIsNone(report["state"])

        move = self.s2.move_event("SELECTED-PASS", tick=1)
        failing = self.s2.stack_event("UNSELECTED-FAIL", tick=2, amount=99)
        model, history = self.s2.prepare(events=[failing, move])
        self.write_rules(self.alpha, self.rules("MOVE_ORIGIN"))

        unselected_failure = world_consistency.build(self.alpha, AFTER_5)

        self.assertEqual(unselected_failure["status"], "UNKNOWN")
        self.assertEqual(unselected_failure["preview_availability"], "UNKNOWN")
        self.assertEqual(unselected_failure["diagnostics"][0]["event_id"],
                         "SELECTED-PASS")
        self.assertEqual(unselected_failure["diagnostics"][0]["result"], "PASS")
        self.assertEqual(unselected_failure["summary"],
                         {"pass": 1, "contradiction": 0, "unknown": 0})
        self.assertFalse(unselected_failure["complete"])
        assert_advisory(unselected_failure)

        stale = self.s2.move_event("STALE-BYTES")
        stale_model, stale_history = self.s2.prepare(events=[stale])
        stale_source = self.event(stale_history, "STALE-BYTES")["source"]
        (self.alpha / stale_source["path"]).write_bytes(b"different source bytes\n")
        stale_report = world_consistency.build(self.alpha, AFTER_5)
        self.assertEqual(stale_report["status"], "UNKNOWN")
        self.assertEqual(stale_report["preview_availability"], "UNKNOWN")
        self.assertEqual(stale_report["diagnostics"], [])
        assert_advisory(stale_report)

        stale_digest_event = self.s2.move_event("STALE-MODEL-DIGEST")
        digest_model, digest_history = self.s2.prepare(events=[stale_digest_event])
        digest_history["model_sha256"] = "0" * 64
        self.s2.write(self.alpha / world_history.HISTORY_PATH, digest_history)
        stale_digest = world_consistency.build(self.alpha, AFTER_5)
        self.assertEqual(stale_digest["status"], "INVALID")
        self.assertEqual(stale_digest["diagnostics"], [])
        assert_advisory(stale_digest)

        for gap in ("baseline-proposed", "coverage-proposed"):
            with self.subTest(gap=gap):
                event = self.s2.move_event(f"GAP-{gap}")
                gap_model, gap_history = self.s2.prepare(events=[event])
                if gap == "baseline-proposed":
                    gap_model["baseline"]["local_status"] = "PROPOSED"
                    self.s2.write(self.alpha / world_history.MODEL_PATH, gap_model)
                else:
                    gap_history["coverage"]["local_status"] = "PROPOSED"
                self.s2.update_history(self.alpha, gap_model, gap_history)
                gap_report = world_consistency.build(self.alpha, AFTER_5)
                self.assertEqual(gap_report["status"], "UNKNOWN")
                self.assertEqual(gap_report["preview_availability"], "UNKNOWN")
                self.assertEqual(gap_report["diagnostics"], [])
                assert_advisory(gap_report)

    def test_rules_file_parser_cursor_order_and_empty_opt_in_boundaries(self):
        self.s2.prepare(events=[])
        self.write_rules(self.alpha, self.rules("MOVE_ORIGIN"))
        rules_path = self.alpha / world_consistency.RULES_PATH
        malformed_files = (
            b'{"schema_version":1,"schema_version":1,"story_slug":"alpha","enabled":true,"rules":["MOVE_ORIGIN"]}',
            b'{"schema_version":1,"story_slug":"alpha","enabled":true,"rules":[NaN]}',
        )
        for raw in malformed_files:
            with self.subTest(raw=raw):
                rules_path.write_bytes(raw)
                report = world_consistency.build(self.alpha, AFTER_5)
                self.assertEqual(report["status"], "INVALID", report)
                self.assertEqual(report["diagnostics"], [])

        self.write_rules(self.alpha, {**self.rules("MOVE_ORIGIN"), "schema_version": 2})
        version_two = world_consistency.build(self.alpha, AFTER_5)
        self.assertEqual(version_two["status"], "INVALID")
        self.assertEqual(version_two["diagnostics"], [])

        rules_path.unlink()
        try:
            rules_path.symlink_to(self.alpha / "evidence/missing-world-rules.json")
        except (OSError, NotImplementedError):
            dangling_link_supported = False
        else:
            dangling_link_supported = True
        if dangling_link_supported:
            dangling = world_consistency.build(self.alpha, AFTER_5)
            self.assertEqual(dangling["status"], "INVALID")
            self.assertEqual(dangling["diagnostics"], [])
            rules_path.unlink()

        disabled = self.rules("MOVE_ORIGIN", enabled=False)
        self.write_rules(self.alpha, disabled)
        invalid_cursor = world_consistency.build(
            self.alpha, {"clock_id": CLOCK, "tick": True,
                         "suborder": 0, "boundary": "AFTER"})
        self.assertEqual(invalid_cursor["status"], "INVALID")

        self.s2.write(self.alpha / world_consistency.RULES_PATH,
                      self.rules(slug="alpha", enabled=True))
        (self.alpha / "data/world_model.json").write_text("{malformed", encoding="utf-8")
        (self.alpha / world_history.HISTORY_PATH).write_text("{malformed", encoding="utf-8")
        empty_rules = world_consistency.build(self.alpha, AFTER_5)
        self.assertEqual(empty_rules["status"], "DISABLED")
        self.assertIsNone(empty_rules["model_sha256"])
        self.assertIsNone(empty_rules["history_sha256"])
        self.assertEqual(empty_rules["diagnostics"], [])

    def test_missing_history_disabled_s1_unique_request_and_null_stack_destination(self):
        self.s2.prepare(events=[self.s2.move_event("HISTORY-MISSING")])
        self.write_rules(self.alpha, self.rules("MOVE_ORIGIN"))
        (self.alpha / world_history.HISTORY_PATH).unlink()
        missing_history = world_consistency.build(self.alpha, AFTER_5)
        self.assertEqual(missing_history["status"], "UNKNOWN")
        self.assertEqual(missing_history["preview_availability"], "UNKNOWN")
        self.assertEqual(missing_history["diagnostics"], [])
        self.assertIsNone(missing_history["state"])

        self.s2.prepare(events=[self.s2.move_event("S1-DISABLED")])
        story_config = self.s2.read(self.alpha / "story.json")
        story_config["world_state"]["enabled"] = False
        self.s2.write(self.alpha / "story.json", story_config)
        disabled_s1 = world_consistency.build(self.alpha, AFTER_5)
        self.assertEqual(disabled_s1["status"], "UNKNOWN")
        self.assertEqual(disabled_s1["preview_availability"], "UNKNOWN")
        self.assertEqual(disabled_s1["diagnostics"], [])
        self.assertIsNone(disabled_s1["state"])

        unique = self.unique_event("UNIQUE-QTY-TWO", quantity=2)
        self.s2.prepare(events=[unique])
        self.write_rules(self.alpha, self.rules("UNIQUE_CUSTODY"))
        wrong_unique_quantity = world_consistency.build(self.alpha, AFTER_5)
        self.assertEqual(wrong_unique_quantity["status"], "CONTRADICTION")
        self.assertEqual(wrong_unique_quantity["preview_availability"], "UNKNOWN")
        self.assertEqual(wrong_unique_quantity["diagnostics"][0]["rule_id"],
                         "UNIQUE_CUSTODY")
        self.assertEqual(wrong_unique_quantity["diagnostics"][0]["result"],
                         "CONTRADICTION")
        self.assertEqual(wrong_unique_quantity["diagnostics"][0]["event_id"],
                         "UNIQUE-QTY-TWO")
        self.assertEqual(wrong_unique_quantity["diagnostics"][0]["expected"]["quantity"], 2)
        self.assertIsNone(wrong_unique_quantity["diagnostics"][0]["after"])

        stack = self.s2.stack_event("STACK-NULL-DEST", tick=1, amount=2)
        model, _history = self.s2.prepare(events=[stack])
        destination = next(row for row in model["baseline"]["holdings"]
                           if row["item_id"] == "ITEM-001"
                           and row["holder"] == {"kind": "LOCATION", "location_id": "LOC-001"})
        destination["quantity"] = None
        history = self.s2.read(self.alpha / world_history.HISTORY_PATH)
        self.s2.write(self.alpha / "data/world_model.json", model)
        self.s2.update_history(self.alpha, model, history)
        self.write_rules(self.alpha, self.rules("STACK_BALANCE"))
        unknown_destination = world_consistency.build(self.alpha, AFTER_5)
        self.assertEqual(unknown_destination["status"], "UNKNOWN")
        self.assertEqual(unknown_destination["preview_availability"], "UNKNOWN")
        diagnostic = unknown_destination["diagnostics"][0]
        self.assertEqual(diagnostic["rule_id"], "STACK_BALANCE")
        self.assertEqual(diagnostic["result"], "UNKNOWN")
        self.assertEqual(diagnostic["event_id"], "STACK-NULL-DEST")
        self.assertEqual(diagnostic["before"]["destination"], {
            "holder": {"kind": "LOCATION", "location_id": "LOC-001"},
            "quantity": None,
        })
        self.assertIsNone(diagnostic["after"])


if __name__ == "__main__":
    unittest.main()
