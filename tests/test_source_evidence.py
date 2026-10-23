"""Synthetic checks for story-scoped exact source reading."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts import author_memory, house_cards, review_bundle, source_evidence


class SourceReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / "story-a"
        (self.root / "data").mkdir(parents=True)

    def _write(self, relative: str, content: bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def _git(self, *args: str) -> str:
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_TERMINAL_PROMPT="0", GIT_NO_LAZY_FETCH="1")
        result = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True,
                                check=False, env=env, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        return result.stdout.decode("utf-8", errors="strict").strip()

    def _commit_file(self, relative: str, content: bytes) -> str:
        path = self._write(relative, content)
        if not (self.root / ".git").exists():
            self._git("init")
            self._git("config", "user.email", "test@example.invalid")
            self._git("config", "user.name", "Synthetic Test")
        self._git("add", relative)
        self._git("commit", "-m", "synthetic source fixture")
        return path

    def test_non_git_working_tree_reads_exact_raw_bytes(self):
        content = b"Synthetic metadata only\r\nsecond line"
        self._write("reference/notes.md", content)
        reader = source_evidence.SourceReader(self.root)
        self.assertEqual(reader.root, self.root.resolve())
        self.assertEqual(reader.commit, "UNKNOWN")
        self.assertEqual(reader.read("reference/notes.md"), content)
        evidence = reader.evidence()
        self.assertEqual(evidence["mode"], "working-tree")
        self.assertEqual(evidence["metadata_basis"], "WORKING_TREE_REGISTRIES")
        source = evidence["sources"]["reference/notes.md"]
        self.assertEqual(source["raw_status"], "MATCH")
        self.assertEqual(source["selected_sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(source["raw_sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(source["git_blob_id"], hashlib.sha1(
            b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest())
        self.assertNotIn("content", str(evidence))

    def test_committed_mode_uses_exact_blob_and_reports_crlf_raw_difference(self):
        committed = b"Synthetic metadata; LF line.\n"
        path = self._commit_file("reference/notes.md", committed)
        path.write_bytes(committed.replace(b"\n", b"\r\n"))
        reader = source_evidence.SourceReader(self.root, mode="committed")
        self.assertEqual(reader.read("reference/notes.md"), committed)
        self.assertEqual(reader.text("reference/notes.md"), committed.decode("utf-8"))
        item = reader.evidence()["sources"]["reference/notes.md"]
        self.assertEqual(item["raw_status"], "DIFFERENT")
        self.assertEqual(item["selected_byte_length"], len(committed))
        self.assertNotEqual(item["selected_sha256"], item["raw_sha256"])
        self.assertEqual(item["git_blob_id"], hashlib.sha1(
            b"blob " + str(len(committed)).encode("ascii") + b"\0" + committed).hexdigest())

    def test_committed_reader_reports_missing_raw_without_falling_back(self):
        committed = b"Pinned synthetic source\n"
        path = self._commit_file("reference/pinned.md", committed)
        path.unlink()
        reader = source_evidence.SourceReader(self.root, mode="committed")
        self.assertEqual(reader.read("reference/pinned.md"), committed)
        self.assertEqual(reader.evidence()["sources"]["reference/pinned.md"]["raw_status"], "MISSING")

        self._write("reference/new-untracked.md", b"Must not substitute this raw text")
        with self.assertRaisesRegex(ValueError, "absent from the pinned commit"):
            reader.read("reference/new-untracked.md")

    def test_path_bounds_reject_other_story_absolute_and_parent_paths(self):
        outside = self.workspace / "story-b"
        outside.mkdir()
        (outside / "secret.md").write_bytes(b"Synthetic fixture")
        reader = source_evidence.SourceReader(self.root)
        for unsafe in ("../story-b/secret.md", str(outside / "secret.md"), "C:/story-b/secret.md"):
            with self.subTest(path=unsafe), self.assertRaises(ValueError):
                reader.read(unsafe)

    def test_symlink_sources_are_rejected(self):
        target = self.workspace / "outside.md"
        target.write_bytes(b"Synthetic fixture")
        link = self.root / "reference" / "link.md"
        link.parent.mkdir(parents=True)
        try:
            link.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")
        reader = source_evidence.SourceReader(self.root)
        with self.assertRaises(ValueError):
            reader.read("reference/link.md")

    def test_limits_utf8_and_repeated_raw_reads_fail_closed(self):
        oversize = b"x" * (source_evidence.MAX_SOURCE_BYTES + 1)
        self._write("reference/large.md", oversize)
        self._write("reference/binary.md", b"\xff")
        raw = b"First synthetic version\n"
        path = self._write("reference/changing.md", raw)
        reader = source_evidence.SourceReader(self.root)
        with self.assertRaisesRegex(ValueError, "byte limit"):
            reader.read("reference/large.md")
        with self.assertRaisesRegex(ValueError, "UTF-8"):
            reader.text("reference/binary.md")
        self.assertEqual(reader.read("reference/changing.md"), raw)
        path.write_bytes(b"Second synthetic version\n")
        with self.assertRaisesRegex(ValueError, "changed"):
            reader.read("reference/changing.md")

    def test_committed_reader_detects_raw_change_after_read_and_head_race(self):
        committed = b"Pinned base version\n"
        path = self._commit_file("reference/notes.md", committed)
        reader = source_evidence.SourceReader(self.root, mode="committed")
        self.assertEqual(reader.read("reference/notes.md"), committed)
        path.write_bytes(b"Working tree changed after observation\n")
        with self.assertRaisesRegex(ValueError, "changed after it was read"):
            reader.evidence()

        reader = source_evidence.SourceReader(self.root, mode="committed")
        self.assertEqual(reader.read("reference/notes.md"), committed)
        self._write("reference/notes.md", b"Next committed version\n")
        self._git("add", "reference/notes.md")
        self._git("commit", "-m", "advance synthetic HEAD")
        with self.assertRaisesRegex(ValueError, "HEAD changed"):
            reader.evidence()

    def test_committed_mode_requires_git_and_unknown_mode_is_rejected(self):
        self._write("reference/notes.md", b"Synthetic metadata")
        with self.assertRaisesRegex(ValueError, "requires a local Git repository"):
            source_evidence.SourceReader(self.root, mode="committed")
        with self.assertRaises(ValueError):
            source_evidence.SourceReader(self.root, mode="implicit")

    def test_raw_mode_survives_unavailable_git_but_committed_mode_fails(self):
        content = b"Synthetic raw fixture with unavailable Git\n"
        self._write("reference/notes.md", content)
        with mock.patch.object(review_bundle, "_git",
                                side_effect=ValueError("unsupported local Git option")):
            reader = source_evidence.SourceReader(self.root, mode="working-tree")
            self.assertEqual(reader.commit, "UNKNOWN")
            self.assertEqual(reader.read("reference/notes.md"), content)
            self.assertEqual(reader.evidence()["sources"]["reference/notes.md"]["raw_status"], "MATCH")
            with self.assertRaises(ValueError):
                source_evidence.SourceReader(self.root, mode="committed")

    def test_house_validation_without_manifest_does_not_require_git(self):
        with mock.patch.object(review_bundle, "_git",
                                side_effect=AssertionError("unexpected Git access")):
            self.assertEqual(house_cards.validate(self.root), [])

    def test_author_memory_without_index_does_not_require_git(self):
        with mock.patch.object(review_bundle, "_git",
                                side_effect=AssertionError("unexpected Git access")):
            self.assertEqual(author_memory.validate(self.root), [])
            self.assertEqual(author_memory.render(self.root), "")

    def test_author_memory_uses_supplied_committed_reader_for_pinned_sources(self):
        slug = "synthetic-memory"
        (self.root / "story.json").write_text(json.dumps({
            "schema_version": 1, "slug": slug, "title": "Synthetic memory",
            "extensions": {"gameplay": False}, "rules": ["Metadata fixture only"],
        }), encoding="utf-8")
        manuscript = b"Synthetic accepted manuscript fixture.\n"
        summary = b"# EP-001 Synthetic recap\nAUTHOR_ACCEPTED_IN_CHAT\n"
        manuscript_path = self._write("drafts/EP-001/final.md", manuscript)
        summary_path = self._write("author_memory/episodes/EP-001.md", summary)
        self._git("init")
        self._git("config", "user.email", "test@example.invalid")
        self._git("config", "user.name", "Synthetic Test")
        self._git("add", "drafts/EP-001/final.md", "author_memory/episodes/EP-001.md")
        self._git("commit", "-m", "synthetic accepted source")

        blob = lambda data: hashlib.sha1(
            b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        source_path = "drafts/EP-001/final.md"
        recap_path = "author_memory/episodes/EP-001.md"
        approval_path = "editorial/approval.json"
        decision_id = "DEC-SYNTHETIC"
        head, merge = "a" * 40, "b" * 40
        entry = {
            "episode_id": "EP-001", "decision_id": decision_id,
            "status": "AUTHOR_ACCEPTED_IN_CHAT", "scene_ids": ["SC-001"],
            "source_path": source_path, "source_blob_sha": blob(manuscript),
            "summary_path": recap_path, "summary_blob_sha": blob(summary),
        }
        approval = {
            "status": "AUTHOR_APPROVED_IN_CHAT", "authorization_channel": "ChatGPT conversation",
            "github_review": {"state": "NOT_OBSERVED"}, "pull_request": 1,
            "approved_head_commit": head, "merged_commit": merge,
            "decision_id": decision_id,
            "manuscript_sources": [{
                "episode_id": "EP-001", "path": f"stories/{slug}/{source_path}",
                "blob_sha": blob(manuscript),
            }],
        }
        (self.root / approval_path).parent.mkdir(parents=True)
        (self.root / approval_path).write_text(json.dumps(approval), encoding="utf-8")
        (self.root / author_memory.INDEX).parent.mkdir(parents=True, exist_ok=True)
        (self.root / author_memory.INDEX).write_text(json.dumps({
            "schema_version": 1, "story_slug": slug, "basis": author_memory.BASIS,
            "approval_record": approval_path, "episodes": [entry],
        }), encoding="utf-8")
        scene = {"id": "SC-001"}
        episode = {
            "id": "EP-001", "scene_ids": ["SC-001"],
            "author_decision": {
                "status": author_memory.ACCEPTED, "decision_id": decision_id,
                "source_path": source_path, "source_blob_sha": blob(manuscript),
                "source_pr": 1, "source_pr_head": head, "merge_commit": merge,
                "github_pr_reviewer_provenance": "NOT_OBSERVED",
            },
        }
        decision = {
            "id": decision_id, "authority": "USER", "status": "APPROVED_BY_USER",
            "source_channel": "ChatGPT", "source_artifact": approval_path,
            "approved_head_commit": head, "merge_commit": merge,
        }
        db = {
            "episodes": {"episodes": [episode]}, "scenes": {"scenes": [scene]},
            "decisions": {"decisions": [decision]},
            "story_state": {"author_approval": {
                "decision_id": decision_id, "source_head": head, "merge_commit": merge,
                "scope": ["EP-001"],
            }},
        }

        manuscript_path.write_bytes(manuscript.replace(b"\n", b"\r\n"))
        summary_path.write_bytes(summary.replace(b"\n", b"\r\n"))
        with mock.patch("scripts.author_memory.novelctl.load", return_value=db):
            raw_errors = author_memory.validate(self.root, db=db)
            self.assertTrue(any("manuscript bytes have changed" in item for item in raw_errors), raw_errors)
            reader = source_evidence.SourceReader(self.root, mode="committed")
            self.assertEqual(author_memory.validate(self.root, db=db, source_reader=reader), [])
            rendered = author_memory.render(self.root, source_reader=reader)
            self.assertIn("# EP-001 Synthetic recap", rendered)
            evidence = reader.evidence()["sources"]
        self.assertEqual(evidence[source_path]["raw_status"], "DIFFERENT")
        self.assertEqual(evidence[recap_path]["raw_status"], "DIFFERENT")


if __name__ == "__main__":
    unittest.main()
