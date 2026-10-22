"""Author-accepted exact manuscript bytes, without pretending GitHub PR review exists."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "stories" / "last-island-active"

class LastIslandAuthorDecisionTests(unittest.TestCase):
    def test_accepted_source_blob_identity_and_decision_are_consistent(self):
        evidence = json.loads((ROOT / "editorial" / "AUTHOR_APPROVAL_2026-10-23.json").read_text(encoding="utf-8"))
        decisions = json.loads((ROOT / "data" / "decisions.json").read_text(encoding="utf-8"))["decisions"]
        approved = next(x for x in decisions if x["id"] == evidence["decision_id"])
        episodes = json.loads((ROOT / "data" / "episodes.json").read_text(encoding="utf-8"))["episodes"]
        self.assertEqual(approved["authority"], "USER")
        self.assertEqual(approved["status"], "APPROVED_BY_USER")
        self.assertEqual(evidence["status"], "AUTHOR_APPROVED_IN_CHAT")
        self.assertEqual(evidence["pull_request"], 13)
        self.assertEqual(approved["approved_head_commit"], evidence["approved_head_commit"])
        self.assertEqual(approved["merge_commit"], evidence["merged_commit"])
        self.assertEqual({s["episode_id"] for s in evidence["manuscript_sources"]}, {"EP-001", "EP-002"})
        for item in evidence["manuscript_sources"]:
            self.assertTrue(item["path"].startswith("stories/last-island-active/drafts/"))
            path = ROOT.parents[1] / item["path"]
            blob = path.read_bytes()
            actual = hashlib.sha1(f"blob {len(blob)}".encode("ascii") + b"\\x00" + blob).hexdigest()
            # Use Git's object identity encoding for immutable manuscript tracking.
            self.assertEqual(actual, item["blob_sha"], item["path"])
            ep = next(e for e in episodes if e["id"] == item["episode_id"])
            decision = ep["author_decision"]
            self.assertEqual(decision["source_blob_sha"], actual)
            self.assertEqual(decision["decision_id"], evidence["decision_id"])
            self.assertEqual(decision["status"], "AUTHOR_ACCEPTED_IN_CHAT")

    def test_verified_github_review_boundary_is_not_faked(self):
        evidence = json.loads((ROOT / "editorial" / "AUTHOR_APPROVAL_2026-10-23.json").read_text(encoding="utf-8"))
        state = json.loads((ROOT / "data" / "story_state.json").read_text(encoding="utf-8"))
        ledger = json.loads((ROOT / "ledger" / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["github_review"]["state"], "NOT_OBSERVED")
        self.assertIsNone(state["approved_through_scene"])
        self.assertEqual(ledger["episodes"], [])
        self.assertEqual(ledger["chapters"], [])
        self.assertEqual(ledger["books"], [])
        self.assertEqual(state["author_approval"]["decision_id"], evidence["decision_id"])

if __name__ == "__main__":
    unittest.main()
