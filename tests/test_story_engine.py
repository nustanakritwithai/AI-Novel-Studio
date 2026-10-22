"""v0.2 Story Engine regression tests, no credentials/network required."""
import copy
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import story_engine

ROOT = Path(__file__).resolve().parent.parent


class StoryEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ("data", "ledger", "bible", "scenes", "drafts"):
            shutil.copytree(ROOT / name, self.root / name)
        # Git does not retain empty directories, even though local fixtures may.
        for layer in ("episodes", "chapters", "books"):
            (self.root / "ledger" / layer).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp.cleanup()

    def read_index(self):
        return story_engine.load_index(self.root)

    def write_index(self, index):
        (self.root / "ledger/index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")

    def approve_first_scene(self):
        scene_path = self.root / "data/scenes.json"
        scenes = json.loads(scene_path.read_text(encoding="utf-8"))
        scene = scenes["scenes"][0]
        scene["status"] = "APPROVED"
        scene_path.write_text(json.dumps(scenes, ensure_ascii=False), encoding="utf-8")
        source = self.root / scene["draft_path"]
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("Approved first-scene source evidence.", encoding="utf-8")
        state_path = self.root / "data/story_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["phase"] = "APPROVED_PROSE"
        state["approved_through_scene"] = scene["id"]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        return source

    def test_check_and_pack_enforce_base_registry_validation(self):
        scene_path = self.root / "data/scenes.json"
        scenes = json.loads(scene_path.read_text(encoding="utf-8"))
        scenes["scenes"][0]["canon_refs"].append("FACT-MISSING")
        scene_path.write_text(json.dumps(scenes), encoding="utf-8")
        errors, _ = story_engine.validate(self.root)
        self.assertTrue(any("FACT-MISSING" in error for error in errors))
        with self.assertRaisesRegex(ValueError, "Base registry invalid"):
            story_engine.pack(self.root, "SC-001")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            result = story_engine.main(["--root", str(self.root), "check"])
        self.assertEqual(result, 1)
        self.assertIn("FAIL", output.getvalue())

    def test_missing_approved_source_blocks_manual_pack_without_artifact(self):
        source = self.approve_first_scene()
        source.unlink()
        output = self.root / "context-pack.md"
        with contextlib.redirect_stderr(io.StringIO()) as error:
            result = story_engine.main(["--root", str(self.root), "pack", "SC-002", "--out", str(output)])
        self.assertEqual(result, 1)
        self.assertIn("SC-001", error.getvalue())
        self.assertFalse(output.exists())

    def test_blank_approved_source_rejected_by_check_and_pack(self):
        source = self.approve_first_scene()
        source.write_text(" \n\t", encoding="utf-8")
        errors, _ = story_engine.validate(self.root)
        self.assertTrue(any("SC-001" in error and "blank" in error for error in errors))
        with self.assertRaisesRegex(ValueError, "approved source prose"):
            story_engine.pack(self.root, "SC-002")

    def test_unreadable_approved_excerpt_raises_instead_of_warning(self):
        source = self.approve_first_scene()
        original_read = Path.read_text

        def read(path, *args, **kwargs):
            if path.resolve() == source.resolve():
                raise PermissionError("source not readable")
            return original_read(path, *args, **kwargs)

        with patch.object(Path, "read_text", read):
            with self.assertRaisesRegex(ValueError, "SC-001: cannot read approved source prose"):
                story_engine.approved_scene_tail(self.root, "SC-002")
            with self.assertRaisesRegex(ValueError, "approved source prose"):
                story_engine.pack(self.root, "SC-002")

    def test_approved_excerpt_preserves_source_text(self):
        source = self.approve_first_scene()
        result = story_engine.pack(self.root, "SC-002")
        self.assertIn(source.read_text(encoding="utf-8"), result)

    def test_unknown_approved_episode_reports_error(self):
        idx = self.read_index()
        idx["episodes"].append({"id": "EP-999", "scene_ids": [],
                                "summary_path": "ledger/episodes/EP-999.md"})
        self.write_index(idx)
        errors, _ = story_engine.validate(self.root)
        self.assertTrue(any("unknown episode" in error for error in errors))

    def test_empty_approved_history_is_valid(self):
        self.assertEqual(story_engine.validate(self.root)[0], [])

    def test_malformed_ledger_shapes_fail_clearly(self):
        cases = [
            ([], 'index must be an object'),
            ({'schema_version': 1, 'episodes': [{'id': []}], 'chapters': [], 'books': []}, 'missing id'),
            ({'schema_version': 1, 'episodes': [], 'chapters': [
                {'id': 'CH-001', 'episode_ids': [{}]}], 'books': []}, 'nonempty strings'),
        ]
        for index, expected in cases:
            with self.subTest(index=index):
                self.write_index(index)
                errors, _ = story_engine.validate(self.root)
                self.assertTrue(any(expected in error for error in errors), errors)
                with self.assertRaisesRegex(ValueError, 'Story Engine validation failed'):
                    story_engine.pack(self.root, 'SC-001')

    def test_pack_includes_style_and_locked_user_facts(self):
        pack = story_engine.pack(self.root, "SC-001")
        self.assertIn("REQUIRED WRITING STYLE", pack)
        self.assertIn("No earlier approved episodes", pack)
        self.assertIn("WORLD-CHAMPIONSHIP", pack.upper())

    def test_approved_episode_requires_source_scenes(self):
        path = self.root / 'data/episodes.json'
        episodes = json.loads(path.read_text(encoding='utf-8'))
        empty = copy.deepcopy(episodes['episodes'][0])
        empty.update(id='EP-EMPTY', scene_ids=[], status='APPROVED')
        episodes['episodes'].append(empty)
        path.write_text(json.dumps(episodes), encoding='utf-8')
        idx = self.read_index()
        idx['episodes'].append({
            'id': 'EP-EMPTY', 'scene_ids': [],
            'summary_path': 'ledger/episodes/EP-EMPTY.md',
            'approval': {'pr_number': 12, 'approved_by': 'editor',
                         'merge_commit': 'a' * 40, 'approved_at': '2026-10-22T13:00:00+07:00'},
        })
        self.write_index(idx)
        (self.root / 'ledger/episodes/EP-EMPTY.md').write_text(
            'Summary alone cannot replace source scenes. ' * 5, encoding='utf-8')
        errors, _ = story_engine.validate(self.root)
        self.assertIn('EP-EMPTY: approved episode has no source scenes', errors)
        with self.assertRaisesRegex(ValueError, 'no source scenes'):
            story_engine.pack(self.root, 'SC-001')

    def test_unknown_scene_rejected(self):
        with self.assertRaises(ValueError):
            story_engine.pack(self.root, "SC-999")

    def test_proposal_is_not_approval(self):
        result = story_engine.proposal(self.root, "EP-001")
        self.assertIn("NOT CANON", result)
        self.assertEqual(self.read_index()["episodes"], [])

    def test_unapproved_episode_cannot_enter_ledger(self):
        idx = self.read_index()
        idx["episodes"].append({"id": "EP-001", "scene_ids": [],
                                "summary_path": "ledger/episodes/EP-001.md"})
        self.write_index(idx)
        errs, _ = story_engine.validate(self.root)
        self.assertTrue(any("unapproved episode" in s for s in errs))

    def test_path_escape_fails(self):
        with self.assertRaises(ValueError):
            story_engine.within(self.root, "../outside.md", "ledger/episodes")

    def test_unknown_episode_in_proposal_fails(self):
        with self.assertRaises(ValueError):
            story_engine.proposal(self.root, "EP-999")

    def test_recent_pack_does_not_use_proposal_draft_as_approved(self):
        (self.root / "ledger/episodes/EP-001.md").write_text("SECRET FUTURE ENDING", encoding="utf-8")
        text = story_engine.pack(self.root, "SC-001")
        self.assertNotIn("SECRET FUTURE ENDING", text)

    def test_valid_approved_episode_summary_and_provenance(self):
        eps_path = self.root / "data/episodes.json"
        episodes = json.loads(eps_path.read_text(encoding="utf-8"))
        episodes["episodes"][0]["status"] = "APPROVED"
        eps_path.write_text(json.dumps(episodes, ensure_ascii=False), encoding="utf-8")
        scene_path = self.root / "data/scenes.json"
        scenes = json.loads(scene_path.read_text(encoding="utf-8"))
        for scene in scenes["scenes"]:
            scene["status"] = "APPROVED"
            path = self.root / scene["draft_path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("ร่างฉบับอนุมัติ " * 100, encoding="utf-8")
        scene_path.write_text(json.dumps(scenes, ensure_ascii=False), encoding="utf-8")
        state_path = self.root / "data/story_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["phase"] = "APPROVED_PROSE"
        state["approved_through_scene"] = "SC-008"
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        summary_path = self.root / "ledger/episodes/EP-001.md"
        summary_path.write_text("เหตุการณ์ที่อนุมัติแล้ว " * 50, encoding="utf-8")
        idx = self.read_index()
        idx["episodes"].append({
            "id": "EP-001", "scene_ids": episodes["episodes"][0]["scene_ids"],
            "summary_path": "ledger/episodes/EP-001.md",
            "approval": {"pr_number": 12, "approved_by": "editor",
                         "merge_commit": "a" * 40, "approved_at": "2026-10-22T13:00:00+07:00"}
        })
        self.write_index(idx)
        self.assertEqual(story_engine.validate(self.root)[0], [])
        self.assertNotIn("เหตุการณ์ที่อนุมัติแล้ว", story_engine.render_approved_history(self.root, "SC-008"))

    def test_approval_missing_provenance_rejected(self):
        eps_file = self.root / "data/episodes.json"
        eps = json.loads(eps_file.read_text(encoding="utf-8"))
        eps["episodes"][0]["status"] = "APPROVED"
        eps_file.write_text(json.dumps(eps, ensure_ascii=False), encoding="utf-8")
        scfile = self.root / "data/scenes.json"
        sc = json.loads(scfile.read_text(encoding="utf-8"))
        for s in sc["scenes"]:
            s["status"] = "APPROVED"
            source = self.root / s["draft_path"]
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("Approved scene source evidence.", encoding="utf-8")
        scfile.write_text(json.dumps(sc, ensure_ascii=False), encoding="utf-8")
        idx = self.read_index()
        idx["episodes"].append({"id": "EP-001", "scene_ids": eps["episodes"][0]["scene_ids"],
                                "summary_path": "ledger/episodes/EP-001.md", "approval": {}})
        self.write_index(idx)
        (self.root / "ledger/episodes/EP-001.md").write_text("ฉากผ่านแล้ว"*100, encoding="utf-8")
        errs, _ = story_engine.validate(self.root)
        self.assertTrue(any("approval" in s for s in errs))


if __name__ == "__main__":
    unittest.main()
