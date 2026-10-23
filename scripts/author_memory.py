"""Opt-in source-bound memory for author-accepted fiction.

This is deliberately NOT the GitHub-review-approved ledger. Its acceptance basis
is a locally recorded author decision from ChatGPT, pinned to exact Git blobs.
Local integrity checks do not authenticate the author or a GitHub reviewer.
No network calls, narrative generation, or data mutations occur here.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

try:
    from scripts import novelctl, source_evidence, story_config
except ImportError:  # invoked through scripts/story_engine.py as a CLI
    import novelctl
    import source_evidence
    import story_config

INDEX = "author_memory/index.json"
BASIS = "AUTHOR_CHAT_LOCAL_ATTESTATION_NOT_GITHUB_REVIEW"
ACCEPTED = "AUTHOR_ACCEPTED_IN_CHAT"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
MAX_INDEX = 128 * 1024
MAX_MANUSCRIPT = 1024 * 1024
MAX_SUMMARY = 32 * 1024
MAX_RECORDS = 100


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("Author memory: " + message)


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(_value):
    raise ValueError("Author memory: non-finite JSON value")


def _read(path: Path, cap: int) -> bytes:
    try:
        with path.open("rb") as handle:
            data = handle.read(cap + 1)
    except OSError as exc:
        raise ValueError("Author memory: missing or unreadable source file") from exc
    _require(len(data) <= cap, "source file exceeds limit")
    _require(bool(data.strip()), "empty source file")
    return data


def _json(path: Path, cap: int) -> dict:
    try:
        value = json.loads(
            _read(path, cap).decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_nonfinite,
        )
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise ValueError("Author memory: malformed or unsafe JSON") from exc
    _require(isinstance(value, dict), "expected a JSON object")
    return value


def _safe_path(root: Path, relative: str, prefix: str, suffix: str,
               require_file: bool = True) -> Path:
    _require(isinstance(relative, str) and bool(relative), "missing path")
    _require("\\" not in relative and not Path(relative).is_absolute(), "absolute or Windows-style path")
    components = relative.split("/")
    _require(all(part not in ("", ".", "..") for part in components), "unsafe path component")
    _require(relative.startswith(prefix + "/"), "path outside required directory")
    target = (root / relative).resolve()
    folder = (root / prefix).resolve()
    _require(folder.is_relative_to(root) and target.is_relative_to(folder), "path escaped story root")
    _require(target.suffix == suffix and (target.is_file() or not require_file),
             "missing file or wrong suffix")
    return target


def git_blob_sha(data: bytes) -> str:
    """Match Git's content-addressed SHA-1 blob identity."""
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\x00" + data).hexdigest()


def _sha(value) -> bool:
    return isinstance(value, str) and SHA40.fullmatch(value) is not None


def _reader_for(root: Path, source_reader=None):
    reader = source_reader or source_evidence.SourceReader(root, mode="working-tree")
    if Path(reader.root) != Path(root):
        raise ValueError("Author memory: source reader belongs to a different story")
    return reader


def _selected_blob_id(reader, relative: str) -> str | None:
    return reader.identity(relative).get("git_blob_id")


def _read_records(root: Path, db: dict | None = None, source_reader=None):
    root = story_config.resolve_root(root)
    if source_reader is not None and Path(source_reader.root) != Path(root):
        raise ValueError("Author memory: source reader belongs to a different story")
    index_path = root / INDEX
    if not index_path.exists() and not index_path.is_symlink():
        return [], None
    reader = _reader_for(root, source_reader)
    _require(index_path.is_file() and not index_path.is_symlink(), "index must be a regular file")
    index = _json(index_path, MAX_INDEX)
    _require(
        set(index) == {"schema_version", "story_slug", "basis", "approval_record", "episodes"},
        "invalid author memory index fields",
    )
    config = story_config.load_config(root)
    _require(type(index["schema_version"]) is int and index["schema_version"] == 1, "unsupported schema version")
    _require(index["story_slug"] == config["slug"], "wrong story selected")
    _require(index["basis"] == BASIS, "wrong approval provenance basis")
    entries = index["episodes"]
    _require(isinstance(entries, list) and 0 < len(entries) <= MAX_RECORDS, "invalid episode index length")

    db = novelctl.load(root) if db is None else db
    episodes = novelctl.rows(db, "episodes")
    episode_ids = [episode["id"] for episode in episodes]
    by_episode = {episode["id"]: episode for episode in episodes}
    state = db["story_state"]
    decisions = {record["id"]: record for record in novelctl.rows(db, "decisions")}
    approval_path = _safe_path(root, index["approval_record"], "editorial", ".json")
    approval = _json(approval_path, MAX_INDEX)
    decision_id = approval.get("decision_id")
    decision = decisions.get(decision_id)
    _require(
        approval.get("status") == "AUTHOR_APPROVED_IN_CHAT"
        and approval.get("authorization_channel") == "ChatGPT conversation"
        and approval.get("github_review", {}).get("state") == "NOT_OBSERVED",
        "author chat decision is not a verified Github approval",
    )
    _require(
        type(approval.get("pull_request")) is int and approval["pull_request"] > 0
        and _sha(approval.get("approved_head_commit"))
        and _sha(approval.get("merged_commit")),
        "invalid PR and commit source anchors",
    )
    _require(
        isinstance(decision, dict)
        and decision.get("authority") == "USER"
        and decision.get("status") == "APPROVED_BY_USER"
        and decision.get("source_channel") == "ChatGPT"
        and decision.get("source_artifact") == index["approval_record"]
        and decision.get("approved_head_commit") == approval["approved_head_commit"]
        and decision.get("merge_commit") == approval["merged_commit"],
        "missing or inconsistent author decision metadata",
    )
    _require(
        isinstance(state.get("author_approval"), dict)
        and state["author_approval"].get("decision_id") == decision_id
        and state["author_approval"].get("source_head") == approval["approved_head_commit"]
        and state["author_approval"].get("merge_commit") == approval["merged_commit"],
        "author acceptance in story_state does not match source",
    )

    declared = approval.get("manuscript_sources")
    _require(isinstance(declared, list) and len(declared) == len(entries), "approval source count mismatch")
    source_by_episode = {}
    for source in declared:
        _require(isinstance(source, dict) and isinstance(source.get("episode_id"), str),
                 "invalid approved manuscript source")
        _require(source["episode_id"] not in source_by_episode, "duplicate approved source")
        source_by_episode[source["episode_id"]] = source

    checked = []
    ids_seen = set()
    for position, entry in enumerate(entries):
        _require(isinstance(entry, dict), "malformed episode memory entry")
        _require(
            set(entry) == {
                "episode_id", "decision_id", "status", "scene_ids",
                "source_path", "source_blob_sha", "summary_path", "summary_blob_sha"
            },
            "unexpected author memory entry fields",
        )
        eid = entry["episode_id"]
        _require(isinstance(eid, str) and eid not in ids_seen, "duplicate or invalid episode ID")
        ids_seen.add(eid)
        _require(position < len(episode_ids) and eid == episode_ids[position],
                 "author-accepted episodes must form a contiguous chronological prefix")
        episode = by_episode[eid]
        _require(entry["decision_id"] == decision_id and entry["status"] == ACCEPTED,
                 "unaccepted or mismatched episode memory entry")
        _require(entry["scene_ids"] == episode.get("scene_ids")
                 and isinstance(entry["scene_ids"], list) and len(entry["scene_ids"]) > 0,
                 "scene sequence differs from registered episode")
        _require(eid in state["author_approval"].get("scope", []), "episode outside author decision scope")
        metadata = episode.get("author_decision")
        source = source_by_episode.get(eid)
        _require(isinstance(metadata, dict) and isinstance(source, dict),
                 "missing episode acceptance metadata")
        _require(
            metadata.get("status") == ACCEPTED
            and metadata.get("decision_id") == decision_id
            and metadata.get("source_path") == entry["source_path"]
            and metadata.get("source_blob_sha") == entry["source_blob_sha"]
            and metadata.get("source_pr") == approval["pull_request"]
            and metadata.get("source_pr_head") == approval["approved_head_commit"]
            and metadata.get("merge_commit") == approval["merged_commit"]
            and metadata.get("github_pr_reviewer_provenance") == "NOT_OBSERVED",
            "episode is not bound to the recorded author decision",
        )
        _require(
            source.get("path") == "stories/" + config["slug"] + "/" + entry["source_path"]
            and source.get("blob_sha") == entry["source_blob_sha"],
            "approved manuscript path or blob mismatch",
        )
        _require(entry["source_path"].startswith("drafts/" + eid + "/"),
                 "manuscript belongs to another episode")
        _require(_sha(entry["source_blob_sha"]) and _sha(entry["summary_blob_sha"]),
                 "invalid Git blob SHA")
        _safe_path(root, entry["source_path"], "drafts", ".md",
                   require_file=reader.mode == "working-tree")
        reader.text(entry["source_path"], max_bytes=MAX_MANUSCRIPT)
        _require(_selected_blob_id(reader, entry["source_path"]) == entry["source_blob_sha"],
                 "accepted manuscript bytes have changed")
        _safe_path(root, entry["summary_path"], "author_memory/episodes", ".md",
                   require_file=reader.mode == "working-tree")
        _require(entry["summary_path"] == "author_memory/episodes/" + eid + ".md",
                 "summary path does not match episode")
        summary_data = reader.read(entry["summary_path"], max_bytes=MAX_SUMMARY)
        _require(_selected_blob_id(reader, entry["summary_path"]) == entry["summary_blob_sha"],
                 "episode summary bytes have changed")
        try:
            summary = summary_data.decode("utf-8")
        except UnicodeError as exc:
            raise ValueError("Author memory: summary is not UTF-8") from exc
        _require(summary.startswith("# " + eid + " ") and "AUTHOR_ACCEPTED_IN_CHAT" in summary,
                 "summary has no author-accepted source label")
        _require("TODO" not in summary and "PLACEHOLDER" not in summary,
                 "summary contains placeholder text")
        checked.append((eid, entry, summary))

    _require(set(source_by_episode) == ids_seen, "approval contains unindexed manuscript sources")
    reader.evidence()
    return checked, index


def validate(root: Path, db: dict | None = None, source_reader=None) -> list[str]:
    """Validate only opt-in author memory; unconfigured stories are unchanged."""
    try:
        _read_records(root, db, source_reader)
        return []
    except (ValueError, TypeError, KeyError, OSError, IndexError, RecursionError) as exc:
        return [str(exc)[:350]]


def render(root: Path, before: str | None = None, recent: int = 7, source_reader=None) -> str:
    """Render locally attested accepted recaps, optionally STRICTLY before a target.

    Without a target, the command returns all currently accepted history for
    future-author planning. A target prevents future episode leakage.
    """
    _require(type(recent) is int and 0 <= recent <= 20, "recent must be 0..20")
    root = story_config.resolve_root(root)
    checked, index = _read_records(root, source_reader=source_reader)
    if index is None:
        return ""
    db = novelctl.load(root)
    episodes = novelctl.rows(db, "episodes")
    if before is not None:
        scene = novelctl.get(db, "scenes", before)
        target = scene["episode_id"] if scene is not None else before
        ids = [record["id"] for record in episodes]
        _require(target in ids, "unknown memory cutoff episode/scene")
        cutoff = ids.index(target)
        checked = checked[:cutoff]
    checked = checked[-recent:] if recent else []
    output = [
        "## AUTHOR-ACCEPTED MEMORY — LOCAL CHAT DECLARATION, NOT GITHUB-REVIEW AUTHENTICATED",
        "The original author consent is recorded in ChatGPT and source-blob pinned.",
        "This does not populate the separate GitHub-review-approved ledger or prove remote account identity.",
        "Only accepted episode recaps strictly before the selected target are shown when a cutoff is provided.",
    ]
    if not checked:
        output.append("No eligible earlier author-accepted episodes.")
    for eid, entry, summary in checked:
        output.append(
            "### " + eid + " — accepted source " + entry["source_path"]
            + " (Git blob " + entry["source_blob_sha"] + ")"
        )
        output.append(summary)
    return "\n\n".join(output) + "\n"
