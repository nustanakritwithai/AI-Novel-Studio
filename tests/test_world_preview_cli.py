"""Acceptance checks for the read-only ``storyctl world-preview`` command.

All story data is materialized from the synthetic S2 fixture in temporary
story roots. Local APPROVED labels remain fixture declarations, not human
editorial approval.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

try:  # Supports both ``tests.*`` imports and ``unittest discover -s tests``.
    from . import test_story_roots
except ImportError:
    import test_story_roots


ENGINE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures/world_state/synthetic_history.json"
EVIDENCE = b"S2 synthetic evidence\n"
CLOCK = "CLOCK-MAIN"


class WorldPreviewCLITests(unittest.TestCase):
    def setUp(self):
        # Reuse the established S1-shaped isolated story roots without
        # inheriting or re-running that helper's test cases.
        self.story_roots = test_story_roots.StoryRootTests()
        self.story_roots.setUp()
        self.addCleanup(self.story_roots.tearDown)
        self.workspace = self.story_roots.workspace
        self.alpha = self.story_roots.alpha
        self.beta = self.story_roots.beta
        self.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def read(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write(path: Path, value: object):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    def fixture_case(self, slug: str) -> dict:
        return next(case for case in self.fixture["cases"] if case["slug"] == slug)

    def install_case(self, root: Path, case: dict, *, enabled: bool = True) -> None:
        config = self.read(root / "story.json")
        config["world_state"] = {"schema_version": 1, "enabled": enabled}
        self.write(root / "story.json", config)

        for kind, rows in case["catalogs"].items():
            self.write(root / f"data/{kind}.json", {"schema_version": 1, kind: rows})
        self.write(root / "data/world_model.json", case["model"])
        self.write(root / "data/world_history.json", case["history"])

        declarations = [case["model"]["baseline"]["source"],
                        case["history"]["coverage"]["source"]]
        declarations.extend(event["source"] for event in case["history"]["deltas"])
        for declaration in declarations:
            evidence_path = root / declaration["path"]
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_path.write_bytes(EVIDENCE)

    def cli(self, *args, story: str | None = "alpha") -> subprocess.CompletedProcess:
        selection = ["--workspace", str(self.workspace)]
        if story is not None:
            selection.extend(["--story", story])
        return subprocess.run(
            [sys.executable, str(ENGINE_ROOT / "scripts/storyctl.py"),
             *selection, *map(str, args)],
            cwd=self.workspace, env=dict(os.environ, PYTHONIOENCODING="utf-8"),
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )

    def preview(self, *args, story: str | None = "alpha"):
        result = self.cli("world-preview", "--clock", CLOCK, "--tick", "3", *args,
                          story=story)
        return result, json.loads(result.stdout) if result.stdout.lstrip().startswith("{") else None

    def source_snapshot(self) -> dict[str, bytes]:
        return {
            path.relative_to(self.workspace).as_posix(): path.read_bytes()
            for path in self.workspace.rglob("*")
            if path.is_file()
            and ".git" not in path.relative_to(self.workspace).parts
            and ".local" not in path.relative_to(self.workspace).parts
        }

    def test_available_stdout_is_a_proposed_report_with_fixture_state(self):
        case = self.fixture_case("alpha")
        self.install_case(self.alpha, case)

        result, report = self.preview()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["availability"], "AVAILABLE")
        self.assertEqual(report["state"], case["expected_state"])
        # The fixture array is reversed relative to world time, and the first
        # event is narrated in SC-003 before the second in SC-001.
        self.assertEqual(report["applied_event_ids"], ["EV1", "EV2"])
        self.assertEqual(report["proposal_status"], "PROPOSED")
        self.assertEqual(report["human_editorial_approval"], "UNVERIFIED")
        self.assertEqual(report["approval_basis"], "LOCAL_DECLARATIONS_NOT_AUTHENTICATED")
        self.assertIs(report["canon_change_authorized"], False)
        self.assertIs(report["ledger_apply_authorized"], False)
        self.assertNotIn(str(self.workspace), result.stdout)

    def test_exit_two_covers_missing_disabled_and_unapproved_history(self):
        case = self.fixture_case("alpha")
        scenarios = ("missing", "disabled", "unapproved")
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                self.install_case(self.alpha, case)
                history_path = self.alpha / "data/world_history.json"
                if scenario == "missing":
                    history_path.unlink()
                elif scenario == "disabled":
                    config = self.read(self.alpha / "story.json")
                    config["world_state"]["enabled"] = False
                    self.write(self.alpha / "story.json", config)
                else:
                    history = self.read(history_path)
                    history["coverage"]["local_status"] = "PROPOSED"
                    self.write(history_path, history)

                result, report = self.preview()

                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(report["availability"], "UNKNOWN")
                self.assertIsNone(report["state"])
                self.assertEqual(report["applied_event_ids"], [])

    def test_invalid_negative_suborder_maps_to_exit_one(self):
        self.install_case(self.alpha, self.fixture_case("alpha"))

        result = self.cli("world-preview", "--clock", CLOCK, "--tick", "3",
                          "--suborder", "-1")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["availability"], "INVALID")
        self.assertIsNone(report["state"])
        self.assertEqual(report["applied_event_ids"], [])

    def test_invalid_present_history_maps_to_exit_one_without_partial_state(self):
        self.install_case(self.alpha, self.fixture_case("alpha"))
        history_path = self.alpha / "data/world_history.json"
        history = self.read(history_path)
        history["model_sha256"] = "0" * 64
        self.write(history_path, history)

        result = self.cli("world-preview", "--clock", CLOCK, "--tick", "3")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["availability"], "INVALID")
        self.assertIsNone(report["state"])
        self.assertEqual(report["applied_event_ids"], [])

    def test_argparse_syntax_error_keeps_default_exit_two(self):
        result = self.cli("world-preview", "--clock", CLOCK)

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("usage:", result.stderr.lower())
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_before_and_after_cutoffs_select_event_side_even_in_flashback_scene(self):
        self.install_case(self.alpha, self.fixture_case("alpha"))

        before = self.cli("world-preview", "--clock", CLOCK, "--tick", "1",
                          "--boundary", "BEFORE")
        after = self.cli("world-preview", "--clock", CLOCK, "--tick", "1",
                         "--boundary", "AFTER")
        before_report, after_report = json.loads(before.stdout), json.loads(after.stdout)

        self.assertEqual(before.returncode, 0, before.stderr)
        self.assertEqual(after.returncode, 0, after.stderr)
        self.assertEqual(before_report["applied_event_ids"], [])
        self.assertEqual(after_report["applied_event_ids"], ["EV1"])
        self.assertEqual(before_report["state"]["positions"][0]["location"]["location_id"],
                         "LOC-ROOM")
        self.assertEqual(after_report["state"]["positions"][0]["location"]["location_id"],
                         "LOC-SITE")

    def test_private_output_is_limited_to_local_and_rejects_source_targets(self):
        self.install_case(self.alpha, self.fixture_case("alpha"))
        out = self.workspace / ".local/reports/world.json"
        source_path = self.alpha / "data/characters.json"
        original_source = source_path.read_bytes()

        accepted = self.cli("world-preview", "--clock", CLOCK, "--tick", "3",
                            "--out", out)
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        self.assertEqual(self.read(out)["availability"], "AVAILABLE")
        first_bytes = out.read_bytes()

        outside = self.cli("world-preview", "--clock", CLOCK, "--tick", "3",
                           "--out", self.workspace / "report.json")
        direct_source = self.cli("world-preview", "--clock", CLOCK, "--tick", "3",
                                 "--out", source_path)
        self.assertEqual(outside.returncode, 1, outside.stdout + outside.stderr)
        self.assertEqual(direct_source.returncode, 1,
                         direct_source.stdout + direct_source.stderr)
        self.assertEqual(source_path.read_bytes(), original_source)
        self.assertEqual(out.read_bytes(), first_bytes)

        # A .local entry that resolves to a source path is rejected as well.
        linked_out = self.workspace / ".local/source-link.json"
        try:
            linked_out.symlink_to(source_path)
        except (OSError, NotImplementedError):
            return  # File symlinks may be unavailable on Windows workers.
        via_link = self.cli("world-preview", "--clock", CLOCK, "--tick", "3",
                            "--out", linked_out)
        self.assertEqual(via_link.returncode, 1, via_link.stdout + via_link.stderr)
        self.assertEqual(source_path.read_bytes(), original_source)

    def test_repeated_stdout_is_deterministic_read_only_and_never_auto_approves(self):
        self.install_case(self.alpha, self.fixture_case("alpha"))
        before = self.source_snapshot()

        first = self.cli("world-preview", "--clock", CLOCK, "--tick", "3")
        second = self.cli("world-preview", "--clock", CLOCK, "--tick", "3")

        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(first.stdout, second.stdout)
        report = json.loads(first.stdout)
        self.assertEqual(report["human_editorial_approval"], "UNVERIFIED")
        self.assertEqual(report["approval_basis"], "LOCAL_DECLARATIONS_NOT_AUTHENTICATED")
        self.assertIs(report["canon_change_authorized"], False)
        self.assertIs(report["ledger_apply_authorized"], False)
        self.assertEqual(self.source_snapshot(), before)

    def test_explicit_story_selection_keeps_same_ids_and_facts_isolated(self):
        self.install_case(self.alpha, self.fixture_case("alpha"))
        self.install_case(self.beta, self.fixture_case("beta"))

        alpha = self.cli("world-preview", "--clock", CLOCK, "--tick", "0",
                         "--boundary", "BEFORE", story="alpha")
        beta = self.cli("world-preview", "--clock", CLOCK, "--tick", "0",
                        "--boundary", "BEFORE", story="beta")
        alpha_report, beta_report = json.loads(alpha.stdout), json.loads(beta.stdout)

        self.assertEqual(alpha.returncode, 0, alpha.stderr)
        self.assertEqual(beta.returncode, 0, beta.stderr)
        self.assertEqual(alpha_report["story_slug"], "alpha")
        self.assertEqual(beta_report["story_slug"], "beta")
        self.assertEqual(alpha_report["baseline_id"], beta_report["baseline_id"])
        self.assertEqual(alpha_report["state"]["positions"][0]["location"]["location_id"],
                         "LOC-ROOM")
        self.assertEqual(beta_report["state"]["positions"][0]["location"]["location_id"],
                         "LOC-SITE")

    def test_enabled_world_history_does_not_change_legacy_replay_or_pack(self):
        try:  # Keep this usable under both package and discovery imports.
            from .test_world_history import WorldHistoryLoaderTests
        except ImportError:
            from test_world_history import WorldHistoryLoaderTests
        from scripts import world_state_reducer

        catalogs = ("characters", "locations", "items", "scenes")
        original_catalogs = {
            kind: (self.alpha / f"data/{kind}.json").read_bytes()
            for kind in catalogs
        }
        replay_before = self.cli("replay", "SC-002")
        pack_before = self.cli("pack", "SC-002")
        self.assertEqual(replay_before.returncode, 0, replay_before.stderr)
        self.assertEqual(pack_before.returncode, 0, pack_before.stderr)

        # Build S2 declarations around only the IDs already present in the
        # legacy story's unchanged catalogs: CHAR-001 owns four ITEM-001s and
        # LOC-001 has the explicit zero-balance destination row.
        helper = WorldHistoryLoaderTests(
            "test_real_evidence_loads_and_produces_only_an_unverified_proposal")
        event = helper.stack_event("EVENT-STACK", tick=1, amount=1)
        model, history = helper.prepare(self.alpha, events=[event])
        model["hierarchy"] = [row for row in model["hierarchy"]
                              if row["location_id"] == "LOC-001"]
        model["baseline"]["holdings"] = [row for row in model["baseline"]["holdings"]
                                          if row["item_id"] == "ITEM-001"]
        model["item_policies"] = [row for row in model["item_policies"]
                                  if row["item_id"] == "ITEM-001"]
        history["model_sha256"] = world_state_reducer.digest(model)
        helper.update_history(self.alpha, model, history)
        self.write(self.alpha / "data/world_model.json", model)
        for kind, content in original_catalogs.items():
            (self.alpha / f"data/{kind}.json").write_bytes(content)
        self.assertEqual({kind: (self.alpha / f"data/{kind}.json").read_bytes()
                          for kind in catalogs}, original_catalogs)

        preview = self.cli("world-preview", "--clock", CLOCK, "--tick", "2")
        self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
        report = json.loads(preview.stdout)
        self.assertEqual(report["availability"], "AVAILABLE")
        self.assertEqual(report["applied_event_ids"], ["EVENT-STACK"])

        replay_after = self.cli("replay", "SC-002")
        pack_after = self.cli("pack", "SC-002")

        self.assertEqual(replay_after.returncode, 0, replay_after.stderr)
        self.assertEqual(pack_after.returncode, 0, pack_after.stderr)
        self.assertEqual(replay_after.stdout, replay_before.stdout)
        self.assertEqual(pack_after.stdout, pack_before.stdout)
        self.assertEqual({kind: (self.alpha / f"data/{kind}.json").read_bytes()
                          for kind in catalogs}, original_catalogs)


if __name__ == "__main__":
    unittest.main()
