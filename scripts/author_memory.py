"""Optional author-accepted chapter memory, distinct from authenticated GitHub-review ledger.

Never infers authorization from a merge or CI run. Validates immutable Git
blob identities against an existing user-decision receipt in this story root.
This opt-in index is not an approved-state reducer, verified PR review, or
proof of real-world game mechanics. Other stories without the index are inert.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

try:
    from scripts import story_config, novelctl
except ImportError:
    import story_config
    import novelctl

INDEX = "editorial/author_accepted_index.json"
EXPECTED_BASIS = "AUTHOR_ACCEPTED_IN_CHAT_NOT_GITHUB_REVIEW"


def _document(root: Path, relative: str, directory: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("invalid author-memory path")
    target = story_config.story_path(root, relative)
    allowed = (root / directory).resolve()
    if not target.is_relative_to(allowed) or target.suffix != ".md":
        raise ValueError("author memory path outside " + directory)
    return target


def _git_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def load(root: Path, db: dict | None = None) -> dict | None:
    root = story_config.resolve_root(root)
    p = root / INDEX
    if not p.is_file():
        return None
    if db is None:
        db = novelctl.load(root)
    try:
        index = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(index, dict) or index.get("schema_version") != 1:
            raise ValueError("unsupported author-memory index schema")
        if index.get("basis") != EXPECTED_BASIS:
            raise ValueError("author-memory basis is not chat-accepted")
        if index.get("story_slug") != root.name:
            raise ValueError("author-memory story scope mismatch")
        if index.get("receipt_path") != "editorial/AUTHOR_APPROVAL_2026-10-23.json":
            raise ValueError("author-memory must reference the actual author receipt")
        entries = index.get("episodes")
        if not isinstance(entries, list) or not entries:
            raise ValueError("author-memory episodes missing")
        receipt = json.loads(story_config.story_path(root, index["receipt_path"]).read_text(encoding="utf-8"))
        if (receipt.get("status") != "AUTHOR_APPROVED_IN_CHAT" or
                receipt.get("github_review", {}).get("state") != "NOT_OBSERVED"):
            raise ValueError("author-memory provenance is not the recorded chat decision")
        receipt_sources = {x["episode_id"]: x for x in receipt.get("manuscript_sources", [])}
        if len(receipt_sources) != len(receipt.get("manuscript_sources", [])):
            raise ValueError("duplicate receipt episode source")
        decisions = {x["id"]: x for x in db["decisions"]["decisions"]}
        decision = decisions.get(receipt["decision_id"])
        if (not decision or decision.get("status") != "APPROVED_BY_USER" or
                decision.get("authority") != "USER" or
                decision.get("approved_head_commit") != receipt.get("approved_head_commit") or
                decision.get("merge_commit") != receipt.get("merged_commit")):
            raise ValueError("author-memory decision does not match the receipt")
        episodes = {x["id"]: x for x in db["episodes"]["episodes"]}
        names = set()
        for row in entries:
            if not isinstance(row, dict) or set(row) != {"id", "summary_path", "source_path", "source_blob_sha", "decision_id", "basis"}:
                raise ValueError("unexpected author-memory record shape")
            eid = row["id"]
            if eid in names or eid not in episodes:
                raise ValueError("duplicate or unknown author-memory episode")
            names.add(eid)
            if row["basis"] != EXPECTED_BASIS or row["decision_id"] != receipt["decision_id"]:
                raise ValueError("author-memory record authority mismatch")
            source = receipt_sources.get(eid)
            expected_source = f"stories/{root.name}/{row['source_path']}"
            if (not source or source.get("path") != expected_source or
                    source.get("blob_sha") != row["source_blob_sha"] or
                    episodes[eid].get("author_decision", {}).get("source_blob_sha") != row["source_blob_sha"]):
                raise ValueError(f"{eid}: manuscript identity differs from author-approved source")
            story_source = _document(root, row["source_path"], "drafts")
            if _git_sha(story_source.read_bytes()) != row["source_blob_sha"]:
                raise ValueError(f"{eid}: author-accepted manuscript bytes changed")
            summary = _document(root, row["summary_path"], "editorial/accepted")
            content = summary.read_text(encoding="utf-8")
            if len(content.strip()) < 120 or "TODO" in content:
                raise ValueError(f"{eid}: summary is empty or unreviewed placeholder")
        if set(receipt_sources) != names:
            raise ValueError("author-memory index does not cover approved receipt episodes")
        return index
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        raise ValueError("author-memory validation failed: " + str(exc)) from exc


def validate(root: Path, db: dict | None = None) -> list[str]:
    try:
        load(root, db)
        return []
    except (OSError, ValueError) as exc:
        return [str(exc)]


def render_before(root: Path, target: str, keep: int, db: dict | None = None) -> str:
    """Show only preceding chat-accepted episode recaps with a visible trust label."""
    root = story_config.resolve_root(root)
    if db is None:
        db = novelctl.load(root)
    index = load(root, db)
    if index is None or keep == 0:
        return ""
    ordered = [e["id"] for e in db["episodes"]["episodes"]]
    scene = next((s for s in db["scenes"]["scenes"] if s["id"] == target), None)
    target_episode = scene["episode_id"] if scene else target
    if target_episode not in ordered:
        raise ValueError("unknown author-memory target")
    predecessors = set(ordered[:ordered.index(target_episode)])
    history = [r for r in index["episodes"] if r["id"] in predecessors][-keep:]
    if not history:
        return ""
    parts = ["## AUTHOR-ACCEPTED EPISODE MEMORY — CHAT CONSENT, NOT GITHUB REVIEW",
             "The author accepted the exact prose in ChatGPT. GitHub APPROVE reviewer provenance is NOT OBSERVED. "
             "This section informs continuity but is not the approved-only ledger, authentication, or real-game mechanics evidence."]
    for row in history:
        summary = _document(root, row["summary_path"], "editorial/accepted")
        parts.extend([f"### {row['id']} — AUTHOR ACCEPTED IN CHAT (not a GitHub review)",
                      summary.read_text(encoding="utf-8")])
    return "\n\n".join(parts)
