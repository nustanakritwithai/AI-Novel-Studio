"""Source-bound author memory tests; ChatGPT consent is not GitHub review."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import author_memory, story_engine

ROOT = Path(__file__).resolve().parents[1]
STORY = ROOT / "stories" / "last-island-active"
LEGACY = ROOT / "stories" / "last-island"


class AuthorAcceptedMemoryTests(unittest.TestCase):
    def fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        target = Path(tmp.name) / "last-island-active"
        shutil.copytree(STORY, target)
        return target

    def mutate_json(self, root, relative, updater):
        path = root / relative
        value = json.loads(path.read_text(encoding="utf-8"))
        updater(value)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_real_author_accepted_memory_validates_without_approving_ledger(self):
        self.assertEqual(author_memory.validate(STORY), [])
        errors, _warnings = story_engine.validate(STORY)
        self.assertEqual(errors, [])
        state = json.loads((STORY / "data/story_state.json").read_text(encoding="utf-8"))
        index = json.loads((STORY / "ledger/index.json").read_text(encoding="utf-8"))
        self.assertIsNone(state["approved_through_scene"])
        self.assertEqual(index["episodes"], [])
        self.assertEqual(index["chapters"], [])
        self.assertEqual(index["books"], [])

    def test_memory_for_continuing_work_contains_two_chapters_and_caveat(self):
        content = author_memory.render(STORY)
        self.assertIn("# EP-001 — บ้านหลังแรก", content)
        self.assertIn("# EP-002 — ธนูแรกและกำแพงหิน", content)
        self.assertIn("NOT GITHUB-REVIEW AUTHENTICATED", content)
        self.assertIn("SOURCE_GIT_BLOB:", content)
        self.assertIn("UNKNOWN", content)
        self.assertNotIn("No earlier approved episodes.", content)

    def test_episode_two_pack_has_only_earlier_accepted_episode(self):
        pack = story_engine.pack(STORY, "EP-002")
        self.assertIn("AUTHOR-ACCEPTED MEMORY", pack)
        self.assertIn("# EP-001 — บ้านหลังแรก", pack)
        self.assertNotIn("# EP-002 — ธนูแรกและกำแพงหิน", pack)
        self.assertIn("APPROVED EPISODE LEDGER", pack)
        self.assertIn("No earlier approved episodes.", pack)

    def test_first_episode_and_same_episode_scene_do_not_leak_future_memory(self):
        ep1 = story_engine.pack(STORY, "EP-001")
        self.assertNotIn("RECAP_STATUS:", ep1)
        ep2_scene = story_engine.pack(STORY, "SC-018")
        self.assertIn("# EP-001 — บ้านหลังแรก", ep2_scene)
        self.assertNotIn("# EP-002 — ธนูแรกและกำแพงหิน", ep2_scene)

    def test_memory_before_filter_and_recent_zero(self):
        only_first = author_memory.render(STORY, before="EP-002")
        self.assertIn("# EP-001 — บ้านหลังแรก", only_first)
        self.assertNotIn("# EP-002 — ธนูแรกและกำแพงหิน", only_first)
        before_first = author_memory.render(STORY, before="EP-001")
        self.assertIn("No eligible earlier author-accepted episodes.", before_first)
        self.assertNotIn("RECAP_STATUS:", before_first)
        none = author_memory.render(STORY, recent=0)
        self.assertIn("No eligible earlier author-accepted episodes.", none)
        with self.assertRaises(ValueError):
            author_memory.render(STORY, before="EP-999")
        with self.assertRaises(ValueError):
            author_memory.render(STORY, recent=21)

    def test_legacy_story_has_no_automatic_author_memory(self):
        self.assertEqual(author_memory.validate(LEGACY), [])
        self.assertEqual(author_memory.render(LEGACY), "")
        self.assertNotIn("AUTHOR-ACCEPTED MEMORY", story_engine.pack(LEGACY, "SC-001"))

    def test_mutating_accepted_manuscript_fails_closed(self):
        root = self.fixture()
        path = root / "drafts/EP-001/CH-01-FULL-DRAFT.md"
        path.write_bytes(path.read_bytes() + b"\nUNAPPROVED ALTERATION\n")
        failures = author_memory.validate(root)
        self.assertTrue(any("manuscript bytes have changed" in f for f in failures), failures)
        with self.assertRaises(ValueError):
            story_engine.pack(root, "EP-002")

    def test_modifying_summary_without_repinning_fails_closed(self):
        root = self.fixture()
        path = root / "author_memory/episodes/EP-002.md"
        path.write_bytes(path.read_bytes() + b"\nsecret extra fact")
        failures = author_memory.validate(root)
        self.assertTrue(any("summary bytes have changed" in f for f in failures), failures)

    def test_forged_author_decision_rejected(self):
        root = self.fixture()
        self.mutate_json(root, "data/decisions.json", lambda d: d["decisions"][-1].update(authority="ASSISTANT"))
        failures = author_memory.validate(root)
        self.assertTrue(failures)
        self.assertTrue(any("author decision" in f for f in failures), failures)

    def test_forged_merge_anchor_rejected(self):
        root = self.fixture()
        self.mutate_json(
            root, "editorial/AUTHOR_APPROVAL_2026-10-23.json",
            lambda d: d.update(merged_commit="1" * 40),
        )
        self.assertTrue(author_memory.validate(root))

    def test_duplicate_or_out_of_order_records_rejected(self):
        root = self.fixture()
        self.mutate_json(root, "author_memory/index.json",
                         lambda d: d["episodes"].reverse())
        self.assertTrue(author_memory.validate(root))
        root2 = self.fixture()
        self.mutate_json(root2, "author_memory/index.json",
                         lambda d: d["episodes"].append(dict(d["episodes"][1])))
        self.assertTrue(author_memory.validate(root2))

    def test_path_traversal_and_duplicate_json_keys_rejected(self):
        root = self.fixture()
        self.mutate_json(root, "author_memory/index.json",
                         lambda d: d["episodes"][0].update(summary_path="../../outside.md"))
        self.assertTrue(author_memory.validate(root))
        root2 = self.fixture()
        index = root2 / "author_memory/index.json"
        body = index.read_text(encoding="utf-8")
        index.write_text(body.replace('"schema_version": 1,', '"schema_version": 1, "schema_version": 1,', 1),
                         encoding="utf-8")
        self.assertTrue(author_memory.validate(root2))

    def test_cli_memory_filter_and_private_output_rules(self):
        cmd = [sys.executable, str(ROOT / "scripts/storyctl.py"),
               "--story", "last-island-active", "memory", "--before", "EP-002"]
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", timeout=35)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("# EP-001 — บ้านหลังแรก", result.stdout)
        self.assertNotIn("# EP-002 — ธนูแรกและกำแพงหิน", result.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "memory.md"
            result = subprocess.run(cmd + ["--out", str(outside)], cwd=ROOT,
                                    capture_output=True, text=True, encoding="utf-8", timeout=35)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(outside.exists())


if __name__ == "__main__":
    unittest.main()
