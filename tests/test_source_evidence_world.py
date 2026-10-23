"""Committed source reads preserve pins while state/world metadata stays local."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    from . import test_world_history as world_history_fixtures
except ImportError:
    import test_world_history as world_history_fixtures

from scripts import source_evidence, state_replay, world_history, world_state_model


class TrackingReader:
    def __init__(self, reader):
        self.reader = reader
        self.root = reader.root
        self.reads: list[str] = []
        self.texts: list[str] = []

    def read(self, relative: str, max_bytes: int = 1024 * 1024) -> bytes:
        self.reads.append(relative)
        return self.reader.read(relative, max_bytes=max_bytes)

    def text(self, relative: str, max_bytes: int = 1024 * 1024) -> str:
        self.texts.append(relative)
        return self.reader.text(relative, max_bytes=max_bytes)

    def evidence(self) -> dict:
        return self.reader.evidence()


def initialize_repo(repo: Path) -> None:
    """Create only a local synthetic fixture commit; no remote is configured."""
    (repo / ".gitattributes").write_text("* -text\n", encoding="utf-8")
    commands = (
        ["git", "init", "--quiet"],
        ["git", "config", "user.name", "Synthetic Test"],
        ["git", "config", "user.email", "synthetic@example.invalid"],
        ["git", "add", "-A"],
        ["git", "commit", "--quiet", "-m", "synthetic metadata fixture"],
    )
    for command in commands:
        subprocess.run(command, cwd=repo, check=True, capture_output=True, text=True)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def to_crlf(path: Path) -> None:
    raw = path.read_bytes()
    path.write_bytes(raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))


class SourceEvidenceWorldTests(unittest.TestCase):
    def test_state_replay_reads_pinned_text_without_future_scene_leaks(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            root = repo / "stories" / "alpha"
            (root / "data").mkdir(parents=True)
            (root / "bible").mkdir()
            (root / "drafts").mkdir()
            write_json(root / "story.json", {
                "schema_version": 1, "slug": "alpha", "title": "Synthetic fixture",
                "extensions": {"gameplay": False}, "rules": [],
            })
            (root / "bible/INITIAL_STATE.md").write_bytes(b"Synthetic initial-state evidence.\n")
            scenes = [
                {"id": "SC-A", "episode_id": "EP-A", "order": 1,
                 "status": "APPROVED", "draft_path": "drafts/SC-A.md"},
                {"id": "SC-B", "episode_id": "EP-A", "order": 2,
                 "status": "APPROVED", "draft_path": "drafts/SC-B.md"},
                {"id": "SC-C", "episode_id": "EP-B", "order": 1,
                 "status": "APPROVED", "draft_path": "drafts/SC-C.md"},
            ]
            db = {
                "episodes": {"episodes": [{"id": "EP-A"}, {"id": "EP-B"}]},
                "scenes": {"scenes": scenes},
            }
            for scene in scenes:
                (root / scene["draft_path"]).write_bytes(
                    f"Synthetic evidence for {scene['id']}.\n".encode("utf-8"))
            history = {
                "schema_version": 1,
                "baseline": {"before_scene": "SC-A", "status": "APPROVED",
                             "evidence_path": "bible/INITIAL_STATE.md",
                             "state": {"marker": "START"}},
                "deltas": [
                    {"id": "DELTA-A", "scene_id": "SC-A", "status": "APPROVED", "changes": [
                        {"path": ["marker"], "operation": "SET", "before_exists": True,
                         "before": "START", "value": "AFTER_A"}]},
                    {"id": "DELTA-B", "scene_id": "SC-B", "status": "APPROVED", "changes": [
                        {"path": ["marker"], "operation": "SET", "before_exists": True,
                         "before": "AFTER_A", "value": "AFTER_B"}]},
                    {"id": "DELTA-C", "scene_id": "SC-C", "status": "APPROVED", "changes": [
                        {"path": ["marker"], "operation": "SET", "before_exists": True,
                         "before": "AFTER_B", "value": "FUTURE_ONLY"}]},
                ],
            }
            write_json(root / "data/state_history.json", history)
            initialize_repo(repo)
            for relative in ("bible/INITIAL_STATE.md", "drafts/SC-A.md", "drafts/SC-B.md", "drafts/SC-C.md"):
                to_crlf(root / relative)

            reader = TrackingReader(source_evidence.SourceReader(root, mode="committed"))
            replay = state_replay.replay_before(root, "SC-C", db, source_reader=reader)
            self.assertEqual(replay["availability"], "KNOWN")
            self.assertEqual(replay["state"]["marker"], "AFTER_B")
            self.assertNotIn("FUTURE_ONLY", json.dumps(replay))
            self.assertEqual(set(reader.texts), {
                "bible/INITIAL_STATE.md", "drafts/SC-A.md", "drafts/SC-B.md",
            })
            self.assertEqual(state_replay.validate(root, db, source_reader=reader), [])
            self.assertIn("drafts/SC-C.md", reader.texts)

            evidence = reader.evidence()
            self.assertEqual(evidence["mode"], "committed")
            self.assertTrue(all(item["raw_status"] == "DIFFERENT"
                                for item in evidence["sources"].values()))
            (root / "drafts/SC-A.md").write_bytes(b"Changed raw source after committed read.\r\n")
            with self.assertRaisesRegex(ValueError, "changed"):
                reader.evidence()

    def test_world_pins_callbacks_story_isolation_and_future_event_cutoff(self):
        fixture = world_history_fixtures.WorldHistoryLoaderTests()
        fixture.setUp()
        self.addCleanup(fixture.story_roots.tearDown)
        workspace = fixture.workspace
        alpha = fixture.alpha
        beta_secret = beta_source = fixture.beta / "evidence/PRIVATE.txt"
        beta_secret.parent.mkdir(parents=True, exist_ok=True)
        beta_secret.write_bytes(b"Synthetic other-story evidence.\n")
        model, _history = fixture.prepare(
            alpha, events=[fixture.move_event("EVENT-FUTURE", tick=11)])
        initialize_repo(workspace)

        for relative in ("evidence/baseline.txt", "evidence/coverage.txt",
                         "evidence/EVENT-FUTURE.txt"):
            to_crlf(alpha / relative)

        reader = TrackingReader(source_evidence.SourceReader(alpha, mode="committed"))
        loaded_model = world_state_model.load(alpha, source_reader=reader)
        self.assertEqual(loaded_model["baseline"]["source"]["sha256"],
                         hashlib.sha256(b"S2 synthetic evidence\n").hexdigest())
        self.assertIn("evidence/baseline.txt", reader.reads)
        self.assertEqual(world_history.validate(alpha, source_reader=reader), [])
        self.assertIn("evidence/coverage.txt", reader.reads)
        self.assertIn("evidence/EVENT-FUTURE.txt", reader.reads)

        before_preview = len(reader.reads)
        report = world_history.preview(alpha, {
            "clock_id": "CLOCK-MAIN", "tick": 5, "suborder": 0, "boundary": "AFTER",
        }, source_reader=reader)
        preview_reads = reader.reads[before_preview:]
        self.assertEqual(report["availability"], "AVAILABLE", report)
        self.assertNotIn("evidence/EVENT-FUTURE.txt", preview_reads)

        wrong = json.loads((alpha / world_state_model.MODEL_PATH).read_text(encoding="utf-8"))
        wrong["baseline"]["source"]["sha256"] = "0" * 64
        write_json(alpha / world_state_model.MODEL_PATH, wrong)
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            world_state_model.load(alpha, source_reader=reader)

        other_story_reader = source_evidence.SourceReader(fixture.beta, mode="committed")
        with self.assertRaisesRegex(ValueError, "source reader does not match"):
            world_state_model.load(alpha, source_reader=other_story_reader)
        self.assertNotIn("evidence/PRIVATE.txt", reader.reads)
        self.assertEqual(beta_source.read_bytes(), b"Synthetic other-story evidence.\n")

        (alpha / "evidence/baseline.txt").write_bytes(b"Changed raw source after committed read.\r\n")
        with self.assertRaisesRegex(ValueError, "changed"):
            reader.evidence()


if __name__ == "__main__":
    unittest.main()
