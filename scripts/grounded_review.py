"""Source-bound, local packets for an external semantic reviewer.

This module performs no model calls. It freezes the exact working-tree draft
alongside the existing scene-only preparation, and later checks that a
reviewer's locators point into those frozen inputs. Locator validity does not
establish that a finding is true.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from scripts import novelctl, registry_schema, review_bundle, scene_prepare, story_config, story_engine
    from scripts.source_evidence import SourceReader
except ImportError:  # direct CLI import
    import novelctl, registry_schema, review_bundle, scene_prepare, story_config, story_engine
    from source_evidence import SourceReader

MAX_DRAFT_BYTES = 1024 * 1024
UNKNOWN = "UNKNOWN"
_SHA256_LENGTH = 64


def _canonical_bytes(value: Any) -> bytes:
    """Stable UTF-8 JSON encoding used for all packet and context identities."""
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("grounded review data cannot be canonically encoded") from exc


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _packet_id(packet: dict) -> str:
    body = {key: value for key, value in packet.items() if key != "packet_id"}
    return _sha256(_canonical_bytes(body))


def _source_key(root: Path, relative: str) -> str:
    path = root.joinpath(*PurePosixPath(relative).parts)
    return os.path.normcase(os.path.abspath(str(path)))


def _assert_exclusive_draft(root: Path, reader: SourceReader, scene_id: str,
                            draft_path: str, scene_rows: list[dict]) -> None:
    """Reject scene drafts that are also registered as another scene/source."""
    target = _source_key(root, draft_path)
    normalized = []
    for row in scene_rows:
        try:
            normalized.append(reader._normalize(row.get("draft_path")))
        except (TypeError, ValueError) as exc:
            raise ValueError("scene registry contains an unsafe draft path") from exc
    if sum(_source_key(root, path) == target for path in normalized) != 1:
        raise ValueError("shared scene draft source is ambiguous; grounded review requires one scene per source")

    # Episode/chapter/book summaries and source paths can represent a larger
    # unit of prose. A scene-level review cannot identify spans in those files.
    index = story_engine.load_index(root)
    for layer in ("episodes", "chapters", "books"):
        for row in index.get(layer, []):
            for field in ("summary_path", "source_path"):
                value = row.get(field)
                if value is None:
                    continue
                try:
                    candidate = reader._normalize(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("story index contains an unsafe source path") from exc
                if _source_key(root, candidate) == target:
                    raise ValueError("scene draft aliases a shared story source")


def _git_evidence(reader: SourceReader, draft_path: str, draft_text: str) -> dict:
    """Include a bounded HEAD comparison where a usable local Git anchor exists."""
    if reader._repo is None or reader.commit == UNKNOWN:
        return {
            "head_commit": UNKNOWN,
            "base_commit": UNKNOWN,
            "base_draft": {"availability": UNKNOWN, "sha256": UNKNOWN,
                           "byte_length": UNKNOWN, "git_blob_id": UNKNOWN},
            "diff": {"availability": UNKNOWN, "content": UNKNOWN,
                     "sha256": UNKNOWN, "byte_length": UNKNOWN},
        }

    repo = reader._repo
    repository_path = (reader.root / draft_path).relative_to(repo).as_posix()
    if PurePosixPath(repository_path).is_absolute() or ".." in PurePosixPath(repository_path).parts:
        raise ValueError("selected draft is outside the local Git repository")
    try:
        base_bytes, blob_id = review_bundle._base_blob(repo, reader.commit, repository_path)
        base_text = review_bundle._text(base_bytes, "HEAD draft")
        diff = review_bundle._diff(base_text, draft_text, repository_path, blob_id is not None)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise ValueError("cannot read bounded HEAD evidence for the selected draft") from exc
    diff_bytes = diff.encode("utf-8", errors="strict")
    if blob_id is None:
        base = {"availability": "MISSING", "sha256": None,
                "byte_length": None, "git_blob_id": None}
    else:
        base = {"availability": "AVAILABLE", "sha256": _sha256(base_bytes),
                "byte_length": len(base_bytes), "git_blob_id": blob_id}
    return {
        "head_commit": reader.commit,
        "base_commit": reader.commit,
        "base_draft": base,
        "diff": {"availability": "AVAILABLE", "content": diff,
                 "sha256": _sha256(diff_bytes), "byte_length": len(diff_bytes)},
    }


def build_packet(root: Path | str, scene_id: str, *, source_mode: str = "working-tree",
                 house_id: str | None = None, world_cursor: dict | None = None) -> dict:
    """Freeze one raw working-tree scene draft and its scene-only preparation.

    ``source_mode`` applies to the context preparation. The draft supplied for
    review is always read from exact working-tree bytes, including CRLF.
    """
    if source_mode not in ("working-tree", "committed"):
        raise ValueError("source mode must be 'working-tree' or 'committed'")
    selected_root = story_config.resolve_root(Path(root))
    before = scene_prepare._metadata_snapshot(selected_root)
    config = story_config.load_config(selected_root)
    db = novelctl.load(selected_root)
    scene_rows = novelctl.rows(db, "scenes")
    matches = [row for row in scene_rows if row.get("id") == scene_id]
    if len(matches) != 1:
        raise ValueError("grounded review requires exactly one selected scene")
    scene = matches[0]

    reader = SourceReader(selected_root, "working-tree")
    try:
        draft_path = reader._normalize(scene.get("draft_path"))
    except (TypeError, ValueError) as exc:
        raise ValueError("selected scene draft path is invalid") from exc
    if not draft_path.startswith("drafts/") or PurePosixPath(draft_path).suffix.lower() != ".md":
        raise ValueError("selected draft must be Markdown inside the selected story's drafts/ directory")
    _assert_exclusive_draft(selected_root, reader, scene_id, draft_path, scene_rows)

    draft_bytes = reader.read(draft_path, max_bytes=MAX_DRAFT_BYTES)
    draft_text = review_bundle._text(draft_bytes, "Working-tree draft")
    draft_sha = _sha256(draft_bytes)
    raw_identity = reader.identity(draft_path)
    source_evidence = reader.evidence()

    preparation = scene_prepare.build(
        selected_root, scene_id, house_id=house_id, source_mode=source_mode,
        world_cursor=world_cursor,
    )
    # scene_prepare has its own source and metadata race checks. These outer
    # checks bind its return value to the raw-draft read above as one packet.
    preparation_sha = _sha256(_canonical_bytes(preparation))
    git = _git_evidence(reader, draft_path, draft_text)
    if scene_prepare._metadata_snapshot(selected_root) != before:
        raise ValueError("Working-tree metadata changed during grounded review packet build")
    if reader.evidence() != source_evidence:
        raise ValueError("Selected working-tree draft changed during grounded review packet build")

    packet = {
        "schema_version": 1,
        "kind": "GROUNDED_REVIEW_PACKET",
        "status": "PROPOSED",
        "story_slug": config["slug"],
        "target": {"scene_id": scene_id, "draft_path": draft_path},
        "context_source_mode": source_mode,
        "raw_draft": {
            "origin": "WORKING_TREE",
            "path": draft_path,
            "content": draft_text,
            "sha256": draft_sha,
            "byte_length": len(draft_bytes),
            "git_blob_id": raw_identity["git_blob_id"],
            "raw_status": source_evidence["sources"][draft_path]["raw_status"],
        },
        "scene_preparation": {
            "content": preparation,
            "sha256": preparation_sha,
        },
        "git": git,
        "metadata_evidence": {
            "basis": "WORKING_TREE_REGISTRIES",
            "sha256": _sha256(_canonical_bytes(before)),
            "files": before,
        },
        "human_editorial_approval": "UNVERIFIED",
        "canon_change_authorized": False,
        "ledger_apply_authorized": False,
    }
    packet["packet_id"] = _packet_id(packet)
    _validate_schema("grounded_review_packet", packet)
    return packet


def _validate_schema(kind: str, value: object) -> None:
    try:
        registry_schema.ensure_valid(kind, value)
    except ValueError as exc:
        raise ValueError(f"grounded review {kind} schema validation failed: {exc}") from exc


def _validate_packet_integrity(packet: object) -> tuple[str, str, str]:
    if not isinstance(packet, dict):
        raise ValueError("packet must be an object")
    _validate_schema("grounded_review_packet", packet)
    packet_id = packet.get("packet_id")
    if not isinstance(packet_id, str) or packet_id != _packet_id(packet):
        raise ValueError("packet digest does not match its canonical contents")
    raw = packet.get("raw_draft")
    prepared = packet.get("scene_preparation")
    if not isinstance(raw, dict) or not isinstance(prepared, dict):
        raise ValueError("packet is missing its frozen draft or scene preparation")
    content = raw.get("content")
    preparation = prepared.get("content")
    if not isinstance(content, str) or not isinstance(preparation, dict):
        raise ValueError("packet frozen content has an invalid shape")
    try:
        raw_bytes = content.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ValueError("packet draft is not valid UTF-8 text") from exc
    draft_sha = _sha256(raw_bytes)
    if raw.get("sha256") != draft_sha or raw.get("byte_length") != len(raw_bytes):
        raise ValueError("packet raw draft hash or byte length is invalid")
    if prepared.get("sha256") != _sha256(_canonical_bytes(preparation)):
        raise ValueError("packet scene preparation digest is invalid")
    metadata = packet.get("metadata_evidence")
    if not isinstance(metadata, dict) or metadata.get("sha256") != _sha256(_canonical_bytes(metadata.get("files"))):
        raise ValueError("packet metadata evidence digest is invalid")
    target = packet.get("target")
    scene_cursor = preparation.get("scene_cursor")
    source_evidence = preparation.get("source_evidence")
    if (not isinstance(target, dict) or target.get("draft_path") != raw.get("path")
            or not isinstance(scene_cursor, dict)
            or scene_cursor.get("scene_id") != target.get("scene_id")
            or scene_cursor.get("boundary") != "BEFORE"
            or preparation.get("story") != packet.get("story_slug")
            or preparation.get("human_editorial_approval") != "UNVERIFIED"
            or preparation.get("canon_change_authorized") is not False
            or preparation.get("ledger_apply_authorized") is not False
            or not isinstance(source_evidence, dict)
            or source_evidence.get("mode") != packet.get("context_source_mode")
            or source_evidence.get("commit") != packet.get("git", {}).get("head_commit")
            or preparation.get("metadata_evidence", {}).get("files") != metadata.get("files")):
        raise ValueError("packet draft and scene preparation bindings do not match")
    git_blob_id = raw.get("git_blob_id")
    if isinstance(git_blob_id, str):
        algorithm = "sha256" if isinstance(packet.get("git", {}).get("head_commit"), str) and len(packet["git"]["head_commit"]) == 64 else "sha1"
        digest = hashlib.new(algorithm)
        digest.update(b"blob " + str(len(raw_bytes)).encode("ascii") + b"\0" + raw_bytes)
        if digest.hexdigest() != git_blob_id:
            raise ValueError("packet raw draft Git blob identity is invalid")
    if packet.get("context_source_mode") == "working-tree":
        evidence_record = source_evidence.get("sources", {}).get(raw.get("path"))
        if evidence_record is not None and (
                evidence_record.get("selected_sha256") != draft_sha
                or evidence_record.get("selected_byte_length") != len(raw_bytes)):
            raise ValueError("working-tree preparation source does not match the frozen raw draft")
    return packet_id, draft_sha, content


def validate_packet(packet: dict) -> dict:
    """Check packet digests and cross-field bindings without authenticating it."""
    packet_id, draft_sha, _ = _validate_packet_integrity(packet)
    return {
        "kind": "GROUNDED_REVIEW_PACKET_VALIDATION",
        "status": "PACKET_BINDINGS_VALID",
        "packet_id": packet_id,
        "draft_sha256": draft_sha,
        "semantic_assessment": "NOT_PERFORMED",
        "human_editorial_approval": "UNVERIFIED",
        "canon_change_authorized": False,
        "ledger_apply_authorized": False,
    }


def _lf_line_bounds(text: str) -> tuple[list[int], list[int]]:
    """Physical LF lines; CRLF's CR remains a byte but is a line terminator."""
    starts = [0]
    ends: list[int] = []
    position = 0
    while position < len(text):
        newline = text.find("\n", position)
        if newline < 0:
            break
        end = newline - 1 if newline > position and text[newline - 1] == "\r" else newline
        ends.append(end)
        position = newline + 1
        starts.append(position)
    ends.append(len(text))
    return starts, ends


def _check_draft_locator(text: str, locator: dict) -> None:
    start_line, end_line, quote = (locator["start_line"], locator["end_line"], locator["quote"])
    if (type(start_line) is not int or type(end_line) is not int
            or start_line < 1 or end_line < start_line):
        raise ValueError("draft locator line range is invalid")
    starts, ends = _lf_line_bounds(text)
    if start_line > len(starts) or end_line > len(ends):
        raise ValueError("draft locator line range is outside the frozen draft")
    left, right = starts[start_line - 1], ends[end_line - 1]
    window = text[left:right]
    first = window.find(quote)
    if first < 0 or window.find(quote, first + 1) >= 0:
        raise ValueError("draft locator quote is absent or ambiguous within the declared lines")
    quote_start = left + first
    quote_end = quote_start + len(quote)
    actual_start = text.count("\n", 0, quote_start) + 1
    actual_end = text.count("\n", 0, max(quote_start, quote_end - 1)) + 1
    if actual_start != start_line or actual_end != end_line:
        raise ValueError("draft locator quote does not occupy the declared LF line range")


def _unescape_pointer(part: str) -> str:
    output = []
    index = 0
    while index < len(part):
        if part[index] != "~":
            output.append(part[index])
            index += 1
            continue
        if index + 1 >= len(part) or part[index + 1] not in "01":
            raise ValueError("context locator contains an invalid JSON Pointer escape")
        output.append("~" if part[index + 1] == "0" else "/")
        index += 2
    return "".join(output)


def _pointer_value(document: object, pointer: str) -> object:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("context locator must be a JSON Pointer into scene preparation")
    value = document
    for encoded in pointer[1:].split("/"):
        part = _unescape_pointer(encoded)
        if isinstance(value, dict):
            if part not in value:
                raise ValueError("context locator JSON Pointer does not resolve")
            value = value[part]
        elif isinstance(value, list):
            if not part.isascii() or not part.isdecimal() or (len(part) > 1 and part.startswith("0")):
                raise ValueError("context locator array index is invalid")
            index = int(part)
            if index >= len(value):
                raise ValueError("context locator JSON Pointer does not resolve")
            value = value[index]
        else:
            raise ValueError("context locator JSON Pointer does not resolve")
    return value


def _check_context_locator(preparation: dict, locator: dict) -> None:
    value = _pointer_value(preparation, locator["pointer"])
    quote = locator["quote"]
    if not isinstance(value, str):
        raise ValueError("context locator JSON Pointer must select a text value")
    first = value.find(quote)
    if first < 0 or value.find(quote, first + 1) >= 0:
        raise ValueError("context locator quote is absent or ambiguous at its JSON Pointer")


def validate_report(packet: dict, report: dict) -> dict:
    """Validate report structure and exact locators without assessing meaning.

    A valid empty report remains an advisory with no semantic pass implied.
    """
    packet_id, draft_sha, draft_text = _validate_packet_integrity(packet)
    _validate_schema("grounded_review_report", report)
    if report["packet_id"] != packet_id:
        raise ValueError("report packet_id does not match the frozen packet")
    if report["draft_sha256"] != draft_sha:
        raise ValueError("report draft_sha256 does not match the frozen raw draft")

    seen_ids: set[str] = set()
    preparation = packet["scene_preparation"]["content"]
    for finding in report["findings"]:
        if finding["id"] in seen_ids:
            raise ValueError("finding IDs must be unique")
        seen_ids.add(finding["id"])
        _check_draft_locator(draft_text, finding["draft_locator"])
        _check_context_locator(preparation, finding["context_locator"])

    return {
        "schema_version": 1,
        "kind": "GROUNDED_REVIEW_VALIDATION",
        "status": "BOUND_ADVISORY_NOT_APPROVAL",
        "packet_id": packet_id,
        "draft_sha256": draft_sha,
        "finding_count": len(report["findings"]),
        "report": json.loads(_canonical_bytes(report).decode("utf-8")),
        "semantic_assessment": "MODEL_DEPENDENT_NOT_AUTHENTICATED",
        "human_editorial_approval": "UNVERIFIED",
        "canon_change_authorized": False,
        "ledger_apply_authorized": False,
    }
