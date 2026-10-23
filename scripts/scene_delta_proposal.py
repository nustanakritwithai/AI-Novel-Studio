"""Build private, source-located per-scene delta observations.

The assembler verifies exact draft locators and selected-story references. It
does not decide whether a quote supports a claim and never applies world state.
"""
from __future__ import annotations

import bisect
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from scripts import novelctl, registry_schema, scene_prepare, story_config, story_engine
    from scripts.source_evidence import SourceReader
except ImportError:  # direct CLI import
    import novelctl, registry_schema, scene_prepare, story_config, story_engine
    from source_evidence import SourceReader


MAX_HISTORY = 64
UNKNOWN = "UNKNOWN"
_REVISION_FIELDS = {
    "revision_id", "revision_sha256", "previous_revision_id",
    "previous_revision_sha256", "previous_chain_sha256", "revision_history",
    "revision_chain_sha256",
}


def _canonical(value: object) -> bytes:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("proposal input must be finite canonical JSON") from exc
    return text.encode("utf-8", errors="strict")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _schema_validate(kind: str, value: object, label: str) -> None:
    try:
        errors = registry_schema.validate(kind, value)
    except Exception as exc:
        raise ValueError(f"{label} schema validation is unavailable ({type(exc).__name__})") from exc
    if errors:
        raise ValueError("; ".join(errors[:8]))


def _read_registry(root: Path, kind: str) -> dict:
    path = story_config.story_path(root, f"data/{kind}.json")
    value = registry_schema.read_json(path)
    registry_schema.ensure_valid(kind, value)
    return value


def _rows(registry: dict, key: str) -> list[dict]:
    rows = registry.get(key)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"Selected-story {key} registry is malformed")
    return rows


def _line_bounds(text: str) -> tuple[list[int], list[int]]:
    """Return character offsets for physical lines without normalizing CRLF."""
    starts = [0]
    ends: list[int] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\r":
            ends.append(index)
            index += 2 if index + 1 < len(text) and text[index + 1] == "\n" else 1
            starts.append(index)
        elif char == "\n":
            ends.append(index)
            index += 1
            starts.append(index)
        else:
            index += 1
    ends.append(len(text))
    return starts, ends


def _check_locator(text: str, locator: dict) -> None:
    start_line, end_line, quote = (locator["start_line"], locator["end_line"], locator["quote"])
    if type(start_line) is not int or type(end_line) is not int or start_line > end_line:
        raise ValueError("locator line range is invalid")
    starts, ends = _line_bounds(text)
    if start_line > len(starts) or end_line > len(ends):
        raise ValueError("locator line range is outside the selected draft")
    window_start, window_end = starts[start_line - 1], ends[end_line - 1]
    window = text[window_start:window_end]
    first = window.find(quote)
    if first < 0 or window.find(quote, first + 1) >= 0:
        raise ValueError("locator quote is absent or ambiguous within the declared lines")
    quote_start = window_start + first
    quote_end = quote_start + len(quote)
    actual_start_line = bisect.bisect_right(starts, quote_start)
    actual_end_line = bisect.bisect_right(starts, quote_end - 1)
    if actual_start_line != start_line or actual_end_line != end_line:
        raise ValueError("locator quote does not occupy the declared exact line range")


def _catalogs(root: Path) -> dict[str, set[str]]:
    names = {"characters": "characters", "locations": "locations", "items": "items"}
    catalogs: dict[str, set[str]] = {}
    for kind, key in names.items():
        value = _read_registry(root, kind)
        ids = [row.get("id") for row in _rows(value, key)]
        if any(not isinstance(value, str) or not value for value in ids) or len(ids) != len(set(ids)):
            raise ValueError(f"Selected-story {kind} IDs are invalid or duplicated")
        catalogs[kind] = set(ids)
    return catalogs


def _check_ref(value: object, catalog: str, catalogs: dict[str, set[str]], label: str) -> None:
    if value == UNKNOWN:
        return
    if not isinstance(value, str) or value not in catalogs[catalog]:
        raise ValueError(f"{label} must reference a selected-story {catalog} ID or UNKNOWN")


def _check_subject(subject: dict, catalogs: dict[str, set[str]], label: str) -> None:
    kind, identity = subject["kind"], subject["id"]
    if kind == "UNKNOWN":
        if identity != UNKNOWN:
            raise ValueError(f"{label} unknown subject must use id UNKNOWN")
        return
    _check_ref(identity, {"CHARACTER": "characters", "LOCATION": "locations", "ITEM": "items"}[kind],
               catalogs, label)


def _normalized_world_time(value: dict | None) -> dict:
    if value is None or value.get("status", UNKNOWN) == UNKNOWN:
        return {"status": UNKNOWN}
    if value.get("status") != "KNOWN":
        raise ValueError("world_time status must be UNKNOWN or KNOWN")
    # The claims schema requires the complete four-coordinate declaration.
    return {"status": "KNOWN", "clock_id": value["clock_id"], "tick": value["tick"],
            "suborder": value["suborder"], "boundary": value["boundary"]}


def _holder(value: dict | None, catalogs: dict[str, set[str]], label: str) -> dict:
    if value is None or value.get("kind", UNKNOWN) == UNKNOWN:
        return {"kind": UNKNOWN, "id": UNKNOWN}
    kind = value["kind"]
    if kind not in ("CHARACTER", "LOCATION"):
        raise ValueError(f"{label} holder kind must be CHARACTER, LOCATION or UNKNOWN")
    catalog = "characters" if kind == "CHARACTER" else "locations"
    identity = value["id"]
    _check_ref(identity, catalog, catalogs, label)
    if identity == UNKNOWN:
        return {"kind": UNKNOWN, "id": UNKNOWN}
    return {"kind": kind, "id": identity}


def _candidate(observation: dict, catalogs: dict[str, set[str]]) -> dict:
    value = observation.get("candidate") or {}
    category = observation["category"]
    world_time = _normalized_world_time(value.get("world_time"))
    if category == "MOVE":
        fields = {
            "character_id": value.get("character_id", UNKNOWN),
            "from_location_id": value.get("from_location_id", UNKNOWN),
            "to_location_id": value.get("to_location_id", UNKNOWN),
        }
        _check_ref(fields["character_id"], "characters", catalogs, "candidate character_id")
        _check_ref(fields["from_location_id"], "locations", catalogs, "candidate from_location_id")
        _check_ref(fields["to_location_id"], "locations", catalogs, "candidate to_location_id")
        return {**fields, "world_time": world_time}
    if category == "TRANSFER":
        item_id = value.get("item_id", UNKNOWN)
        _check_ref(item_id, "items", catalogs, "candidate item_id")
        quantity = value.get("quantity", UNKNOWN)
        if quantity != UNKNOWN and (type(quantity) is not int or quantity < 1):
            raise ValueError("candidate quantity must be a positive integer or UNKNOWN")
        return {"item_id": item_id,
                "from_holder": _holder(value.get("from_holder"), catalogs, "candidate from_holder"),
                "to_holder": _holder(value.get("to_holder"), catalogs, "candidate to_holder"),
                "quantity": quantity, "world_time": world_time}
    target_kind = value.get("target_kind", UNKNOWN)
    target_id = value.get("target_id", UNKNOWN)
    if target_kind == UNKNOWN:
        if target_id != UNKNOWN:
            raise ValueError("candidate target_id must be UNKNOWN when target_kind is UNKNOWN")
    else:
        kind_to_catalog = {"CHARACTER": "characters", "LOCATION": "locations", "ITEM": "items"}
        if target_kind not in kind_to_catalog:
            raise ValueError("candidate target_kind must be a selected catalog kind or UNKNOWN")
        _check_ref(target_id, kind_to_catalog[target_kind], catalogs, "candidate target_id")
        if target_id == UNKNOWN:
            target_kind = UNKNOWN
    component_id = value.get("component_id", UNKNOWN)
    aspect = value.get("aspect", UNKNOWN)
    return {"target_kind": target_kind, "target_id": target_id,
            "component_id": component_id, "aspect": aspect, "world_time": world_time}


def _validate_observation_consistency(category: str, subject: dict, candidate: dict,
                                      label: str) -> None:
    """Reject incompatible known subject/candidate identities without inference."""
    subject_kind, subject_id = subject["kind"], subject["id"]
    if category == "MOVE":
        if subject_kind not in ("CHARACTER", "UNKNOWN"):
            raise ValueError(f"{label} MOVE subject must be CHARACTER or UNKNOWN")
        candidate_id = candidate["character_id"]
        if subject_kind == "CHARACTER" and candidate_id != UNKNOWN and candidate_id != subject_id:
            raise ValueError(f"{label} MOVE subject and candidate character IDs must match when known")
    elif category == "TRANSFER":
        if subject_kind not in ("ITEM", "UNKNOWN"):
            raise ValueError(f"{label} TRANSFER subject must be ITEM or UNKNOWN")
        candidate_id = candidate["item_id"]
        if subject_kind == "ITEM" and candidate_id != UNKNOWN and candidate_id != subject_id:
            raise ValueError(f"{label} TRANSFER subject and candidate item IDs must match when known")
    elif subject_kind != "UNKNOWN" and candidate["target_kind"] != "UNKNOWN":
        if (subject_kind, subject_id) != (candidate["target_kind"], candidate["target_id"]):
            raise ValueError(f"{label} physical subject and candidate target must match when known")


def _identity(story_slug: str, scene_id: str, draft_path: str) -> str:
    return "SDP-" + _sha256({"story_slug": story_slug, "scene_id": scene_id,
                            "draft_path": draft_path})


def _body(report: dict) -> dict:
    return {key: value for key, value in report.items() if key not in _REVISION_FIELDS}


def _revision_sha(report: dict) -> str:
    return _sha256(_body(report))


def _revision_id(identity: str, revision_sha: str, previous_id: str | None) -> str:
    return "SDR-" + _sha256({"proposal_identity": identity,
                             "revision_sha256": revision_sha,
                             "previous_revision_id": previous_id})


def _chain_sha(identity: str, entry: dict) -> str:
    return _sha256({"proposal_identity": identity,
                    "revision_id": entry["revision_id"],
                    "revision_sha256": entry["revision_sha256"],
                    "previous_revision_id": entry["previous_revision_id"],
                    "previous_revision_sha256": entry["previous_revision_sha256"],
                    "previous_chain_sha256": entry["previous_chain_sha256"]})


def _record(report: dict) -> dict:
    return {key: report[key] for key in (
        "revision_id", "revision_sha256", "previous_revision_id",
        "previous_revision_sha256", "previous_chain_sha256", "revision_chain_sha256")}


def _validate_chain(records: list[dict], identity: str) -> tuple[str | None, str | None, str | None]:
    if len(records) > MAX_HISTORY:
        raise ValueError("predecessor revision history exceeds the 64-revision bound")
    previous_id = previous_sha = previous_chain = None
    seen: set[str] = set()
    for row in records:
        if (row["previous_revision_id"] != previous_id
                or row["previous_revision_sha256"] != previous_sha
                or row["previous_chain_sha256"] != previous_chain):
            raise ValueError("predecessor revision history chain is discontinuous")
        if row["revision_id"] != _revision_id(identity, row["revision_sha256"], previous_id):
            raise ValueError("predecessor revision history contains an invalid revision identity")
        if row["revision_id"] in seen or row["revision_chain_sha256"] != _chain_sha(identity, row):
            raise ValueError("predecessor revision history contains a duplicate or invalid chain hash")
        seen.add(row["revision_id"])
        previous_id = row["revision_id"]
        previous_sha = row["revision_sha256"]
        previous_chain = row["revision_chain_sha256"]
    return previous_id, previous_sha, previous_chain


def _validate_previous(previous: dict, identity: str, story_slug: str,
                       scene_id: str, draft_path: str) -> tuple[list[dict], dict]:
    if not isinstance(previous, dict):
        raise ValueError("previous proposal must be a proposal object")
    _schema_validate("scene_delta_proposal", previous, "previous proposal")
    if (previous["proposal_identity"] != identity or previous["story_slug"] != story_slug
            or previous["target"] != {"scene_id": scene_id, "draft_path": draft_path}):
        raise ValueError("previous proposal belongs to a different story, scene or draft")
    source = previous["source"]
    if source["path"] != previous["target"]["draft_path"]:
        raise ValueError("previous proposal source path does not match its target draft")
    seen_observation_ids: set[str] = set()
    for observation in previous["observations"]:
        observation_id = observation["id"]
        if observation_id in seen_observation_ids:
            raise ValueError("previous proposal observation IDs must be unique")
        seen_observation_ids.add(observation_id)
        evidence = observation["evidence"]
        if (evidence["path"] != source["path"]
                or evidence["draft_sha256"] != source["selected_sha256"]):
            raise ValueError("previous proposal observation evidence does not match its selected source")
        _validate_observation_consistency(observation["category"], observation["subject"],
                                          observation["candidate"],
                                          f"previous observation {observation_id}")
    expected_sha = _revision_sha(previous)
    if previous["revision_sha256"] != expected_sha:
        raise ValueError("previous proposal content digest does not match")
    if previous["revision_id"] != _revision_id(identity, expected_sha, previous["previous_revision_id"]):
        raise ValueError("previous proposal revision identity does not match")
    history = previous["revision_history"]
    history_last = _validate_chain(history, identity)
    if (previous["previous_revision_id"], previous["previous_revision_sha256"],
            previous["previous_chain_sha256"]) != history_last:
        raise ValueError("previous proposal does not match its revision history")
    record = _record(previous)
    if previous["revision_chain_sha256"] != _chain_sha(identity, record):
        raise ValueError("previous proposal chain digest does not match")
    if previous["revision_id"] in {row["revision_id"] for row in history}:
        raise ValueError("previous proposal revision identity repeats in its history")
    return history, previous


def _source_record(reader: SourceReader, draft_path: str) -> tuple[dict, dict]:
    evidence = reader.evidence()
    item = evidence["sources"][draft_path]
    identity = reader.identity(draft_path)
    return ({"path": draft_path, "mode": evidence["mode"], "commit": evidence["commit"],
            "metadata_basis": evidence["metadata_basis"],
            "selected_sha256": identity["selected_sha256"],
            "selected_byte_length": identity["selected_byte_length"],
            "git_blob_id": identity["git_blob_id"], "raw_sha256": item["raw_sha256"],
            "raw_byte_length": item["raw_byte_length"], "raw_status": item["raw_status"]}, evidence)


def _source_key(root: Path, relative: str) -> str:
    """Compare normalized filesystem identities with platform case rules."""
    path = root.joinpath(*PurePosixPath(relative).parts)
    return os.path.normcase(os.path.abspath(str(path)))


def _reject_aggregate_alias(reader: SourceReader, root: Path, selected_key: str,
                            value: object) -> None:
    """Reject a scene draft also registered as a larger manuscript/source."""
    try:
        relative = reader._normalize(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("registered aggregate source path is unsafe") from exc
    if _source_key(root, relative) == selected_key:
        raise ValueError("selected scene draft aliases a registered aggregate source")


def build(root: Path | str, scene_id: str, claims: dict, *, source_mode: str = "working-tree",
          previous: dict | None = None) -> dict:
    """Return a deterministic, private proposal from one exact scene draft.

    A successful quote check establishes locator validity only. The claim's
    semantic support is never assessed by this function.
    """
    if not isinstance(claims, dict):
        raise ValueError("claims must be an object")
    _schema_validate("scene_delta_claims", claims, "scene delta claims")
    if claims["scene_id"] != scene_id:
        raise ValueError("claims scene_id does not match the requested target scene")

    selected_root = story_config.resolve_root(Path(root))
    before = scene_prepare._metadata_snapshot(selected_root)
    config = story_config.load_config(selected_root)
    db = novelctl.load(selected_root)
    scene_rows = novelctl.rows(db, "scenes")
    matching_scenes = [row for row in scene_rows if row.get("id") == scene_id]
    if len(matching_scenes) != 1:
        raise ValueError("target must identify exactly one selected-story scene")
    scene = matching_scenes[0]

    reader = SourceReader(selected_root, source_mode)
    try:
        registered_path = reader._normalize(scene.get("draft_path"))
        claimed_path = reader._normalize(claims["draft_path"])
    except (TypeError, ValueError) as exc:
        raise ValueError("selected scene draft path is invalid") from exc
    if registered_path != claimed_path:
        raise ValueError("claims draft_path must match the selected scene's registered draft")
    if (not registered_path.startswith("drafts/") or PurePosixPath(registered_path).suffix.lower() != ".md"):
        raise ValueError("selected source must be a Markdown draft inside the selected story's drafts/")

    normalized_scene_paths = []
    for row in scene_rows:
        try:
            normalized_scene_paths.append(reader._normalize(row.get("draft_path")))
        except (TypeError, ValueError) as exc:
            raise ValueError("scene registry contains an unsafe draft path") from exc
    target_source_key = _source_key(selected_root, registered_path)
    if sum(_source_key(selected_root, path) == target_source_key for path in normalized_scene_paths) != 1:
        raise ValueError("shared scene draft source is ambiguous; explicit source spans are required")

    # A scene draft cannot alias a registered aggregate manuscript or recap.
    index = story_engine.load_index(selected_root)
    for layer in ("episodes", "chapters", "books"):
        for row in index.get(layer, []):
            for field in ("summary_path", "source_path"):
                if field in row and row[field] is not None:
                    _reject_aggregate_alias(reader, selected_root, target_source_key, row[field])

    # Episode decisions can register the full manuscript separately from the
    # ledger summaries. Treat that explicit source path as an aggregate too.
    for episode in _rows(db["episodes"], "episodes"):
        decision = episode.get("author_decision")
        if isinstance(decision, dict) and "source_path" in decision:
            _reject_aggregate_alias(reader, selected_root, target_source_key,
                                    decision["source_path"])

    catalogs = _catalogs(selected_root)
    selected_text = reader.text(registered_path)
    source, captured_source_evidence = _source_record(reader, registered_path)
    if claims["source_sha256"] != source["selected_sha256"]:
        raise ValueError("claims source_sha256 does not match the exact selected draft bytes")
    identity = _identity(config["slug"], scene_id, registered_path)
    if previous is not None:
        previous_history, checked_previous = _validate_previous(
            previous, identity, config["slug"], scene_id, registered_path)
    else:
        previous_history, checked_previous = [], None

    observations = []
    seen_observation_ids: set[str] = set()
    for observation in claims["observations"]:
        observation_id = observation["id"]
        if observation_id in seen_observation_ids:
            raise ValueError("observation IDs must be unique within a proposal")
        seen_observation_ids.add(observation_id)
        _check_locator(selected_text, observation["locator"])
        _check_subject(observation["subject"], catalogs, f"observation {observation_id} subject")
        candidate = _candidate(observation, catalogs)
        _validate_observation_consistency(observation["category"], observation["subject"], candidate,
                                          f"observation {observation_id}")
        observations.append({
            "id": observation_id,
            "category": observation["category"],
            "claim": observation["claim"],
            "subject": copy.deepcopy(observation["subject"]),
            "candidate": candidate,
            "evidence": {
                "path": registered_path,
                "draft_sha256": source["selected_sha256"],
                "quote": observation["locator"]["quote"],
                "start_line": observation["locator"]["start_line"],
                "end_line": observation["locator"]["end_line"],
                "locator_status": "EXACT_QUOTE_AT_LINES",
                "semantic_assessment": "NOT_EVALUATED",
            },
        })

    if len(previous_history) >= MAX_HISTORY:
        raise ValueError("revision history is at its 64-revision bound")
    body = {
        "schema_version": 1,
        "kind": "SCENE_DELTA_PROPOSAL",
        "status": "PROPOSED",
        "proposal_scope": "OBSERVATIONS_ONLY",
        "story_slug": config["slug"],
        "target": {"scene_id": scene_id, "draft_path": registered_path},
        "source": source,
        "proposal_identity": identity,
        "observations": observations,
        "human_editorial_approval": "UNVERIFIED",
        "canon_change_authorized": False,
        "ledger_apply_authorized": False,
        "world_state_application": "NOT_RUN",
    }
    if checked_previous is not None and _body(checked_previous) == body:
        after = scene_prepare._metadata_snapshot(selected_root)
        if before != after:
            raise ValueError("Working-tree metadata changed during scene-delta proposal build")
        if reader.evidence() != captured_source_evidence:
            raise ValueError("Selected draft source evidence changed during scene-delta proposal build")
        # Repeated identical work is idempotent and keeps its existing history.
        return copy.deepcopy(checked_previous)

    revision_sha = _sha256(body)
    parent_id = checked_previous["revision_id"] if checked_previous is not None else None
    revision_id = _revision_id(identity, revision_sha, parent_id)
    if checked_previous is None:
        history = []
        parent_sha = parent_chain = None
    else:
        history = copy.deepcopy(previous_history) + [_record(checked_previous)]
        parent_sha = checked_previous["revision_sha256"]
        parent_chain = checked_previous["revision_chain_sha256"]
    record = {"revision_id": revision_id, "revision_sha256": revision_sha,
              "previous_revision_id": parent_id, "previous_revision_sha256": parent_sha,
              "previous_chain_sha256": parent_chain}
    report = {
        **body,
        "revision_id": revision_id,
        "revision_sha256": revision_sha,
        "previous_revision_id": parent_id,
        "previous_revision_sha256": parent_sha,
        "previous_chain_sha256": parent_chain,
        "revision_history": history,
        "revision_chain_sha256": _chain_sha(identity, record),
    }
    after = scene_prepare._metadata_snapshot(selected_root)
    if before != after:
        raise ValueError("Working-tree metadata changed during scene-delta proposal build")
    if reader.evidence() != captured_source_evidence:
        raise ValueError("Selected draft source evidence changed during scene-delta proposal build")
    _schema_validate("scene_delta_proposal", report, "scene delta proposal")
    return report
