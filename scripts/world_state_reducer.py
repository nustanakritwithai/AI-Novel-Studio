"""Pure, read-only preview of explicit S2 world-state history.

Local APPROVED labels only make declarations eligible for this proposal. This
module never authenticates editorial approval or applies state to canon.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable

try:
    from scripts import world_history_schema, world_state_model
except ImportError:  # direct legacy CLI imports
    import world_history_schema
    import world_state_model


HUMAN_APPROVAL = "UNVERIFIED"
APPROVAL_BASIS = "LOCAL_DECLARATIONS_NOT_AUTHENTICATED"


class _Unavailable(Exception):
    """A needed fact, ordering relation, or evidence check is unknown."""


class _Invalid(Exception):
    """A structural or contradictory declaration is invalid."""


def digest(value: object) -> str:
    """Return the contract's canonical JSON SHA256 digest."""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _path(error: object) -> str:
    """Render a JSON Schema error path without exposing machine paths."""
    result = "$"
    for part in getattr(error, "absolute_path", ()):
        result += f"[{part}]" if isinstance(part, int) else "[" + json.dumps(part, ensure_ascii=False) + "]"
    return result


def _catalog_ids(db: dict) -> dict[str, set[str]]:
    ids: dict[str, set[str]] = {}
    for kind in ("characters", "locations", "items", "scenes"):
        rows = db.get(kind, {}).get(kind)
        if not isinstance(rows, list):
            raise _Invalid(f"selected-story {kind} catalog is unavailable")
        ids[kind] = {row["id"] for row in rows}
    return ids


def _history_schema_errors(history: object) -> list[str]:
    """Call the engine-owned local history validator and normalize errors."""
    try:
        errors = world_history_schema.validate(history)
    except Exception as exc:  # schema/dependency failures fail closed as invalid input
        return [f"history schema validation failed ({type(exc).__name__})"]
    return [str(error) for error in errors]


def _cursor_errors(cursor: object) -> list[str]:
    try:
        return [str(error) for error in world_history_schema.validate_cursor(cursor)]
    except Exception as exc:
        return [f"cutoff cursor validation failed ({type(exc).__name__})"]


def _duplicate_event_ids(history: object) -> list[str]:
    if not isinstance(history, dict) or not isinstance(history.get("deltas"), list):
        return []
    seen: set[str] = set()
    emitted: set[str] = set()
    duplicates: list[str] = []
    for event in history["deltas"]:
        if not isinstance(event, dict) or not isinstance(event.get("id"), str):
            continue
        event_id = event["id"]
        if event_id in seen and event_id not in emitted:
            duplicates.append(event_id)
            emitted.add(event_id)
        seen.add(event_id)
    return duplicates


def _event_identity_errors(history: dict) -> list[str]:
    """Require repeated IDs to carry the exact same canonical event payload."""
    payloads: dict[str, str] = {}
    errors: list[str] = []
    for event in history["deltas"]:
        event_id = event["id"]
        try:
            payload = json.dumps(event, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError):
            # The JSON Schema validator reports non-JSON values as malformed;
            # do not let canonicalization hide that structural error.
            continue
        previous = payloads.get(event_id)
        if previous is not None and previous != payload:
            errors.append(f"conflicting event ID payload for {event_id}")
        else:
            payloads[event_id] = payload
    return errors


def _reference_errors(model: dict, history: dict, db: dict) -> list[str]:
    """Validate every history reference against the selected story catalogs."""
    catalogs = _catalog_ids(db)
    errors: list[str] = []

    baseline = model["baseline"]
    if baseline is not None and history["baseline_id"] != baseline["id"]:
        errors.append("history baseline_id does not match the S1 baseline")

    policies = {policy["item_id"]: policy["tracking"] for policy in model["item_policies"]}

    def ref(kind: str, value: str, context: str) -> None:
        if value not in catalogs[kind]:
            errors.append(f"{context}: missing selected-story {kind} reference {value}")

    for event in history["deltas"]:
        event_id = event["id"]
        ref("scenes", event["anchor"]["scene_id"], f"{event_id} anchor")
        for operation in event["operations"]:
            if operation["operation"] == "MOVE_CHARACTER":
                ref("characters", operation["character_id"], f"{event_id} move")
                ref("locations", operation["from_location_id"], f"{event_id} move source")
                ref("locations", operation["to_location_id"], f"{event_id} move destination")
                continue

            item_id = operation["item_id"]
            ref("items", item_id, f"{event_id} transfer")
            tracking = policies.get(item_id)
            if tracking is None:
                errors.append(f"{event_id} transfer: missing item policy {item_id}")
            if operation["from_holder"] == operation["to_holder"]:
                errors.append(f"{event_id} transfer source and destination must differ")
            for holder_name in ("from_holder", "to_holder"):
                holder = operation[holder_name]
                if holder["kind"] == "CHARACTER":
                    ref("characters", holder["character_id"], f"{event_id} {holder_name}")
                else:
                    ref("locations", holder["location_id"], f"{event_id} {holder_name}")
    return errors


def input_errors(model: object, history: object, db: object) -> list[str]:
    """Return schema, selected-story reference, and identity errors."""
    errors: list[str] = []
    if not isinstance(history, dict):
        errors.append("history must be an object")
    else:
        errors.extend(_history_schema_errors(history))

    if not isinstance(db, dict):
        errors.append("selected-story catalogs must be an object")
        db_valid = False
    else:
        db_valid = True

    if not isinstance(model, dict):
        errors.append("world model must be an object")
        model_valid = False
    elif not db_valid:
        model_valid = False
    else:
        selected_slug = model.get("story_slug")
        if not isinstance(selected_slug, str):
            selected_slug = history.get("story_slug", "") if isinstance(history, dict) else ""
        try:
            model_errors = world_state_model.validation_errors(model, db, selected_slug)
        except Exception as exc:
            model_errors = [f"S1 world model validation failed ({type(exc).__name__})"]
        errors.extend(str(error) for error in model_errors)
        model_valid = not model_errors

    history_valid = isinstance(history, dict) and not _history_schema_errors(history)
    if isinstance(history, dict) and isinstance(model, dict):
        if isinstance(history.get("story_slug"), str) and isinstance(model.get("story_slug"), str):
            if history["story_slug"] != model["story_slug"]:
                errors.append("history story_slug does not match the S1 world model")
        try:
            model_hash = digest(model)
        except (TypeError, ValueError):
            model_hash = None
            errors.append("S1 world model is not canonical finite JSON")
        try:
            digest(history)
        except (TypeError, ValueError):
            errors.append("world history is not canonical finite JSON")
        if history_valid and model_hash is not None and history.get("model_sha256") != model_hash:
            errors.append("history model_sha256 does not match the canonical S1 world model")

    if model_valid and history_valid and db_valid:
        errors.extend(_reference_errors(model, history, db))
        errors.extend(_event_identity_errors(history))

    # Preserve useful diagnostics while avoiding duplicate schema messages.
    return list(dict.fromkeys(errors))


def _report(story_slug: object, cutoff: object, availability: str, reason: str | None,
            *, model_sha256: str | None = None, history_sha256: str | None = None,
            baseline_id: str | None = None, duplicate_event_ids: list[str] | None = None) -> dict:
    return {
        "schema_version": 1,
        "kind": "WORLD_STATE_PREVIEW",
        "availability": availability,
        "proposal_status": "PROPOSED",
        "human_editorial_approval": HUMAN_APPROVAL,
        "approval_basis": APPROVAL_BASIS,
        "canon_change_authorized": False,
        "ledger_apply_authorized": False,
        "story_slug": story_slug,
        "cutoff": copy.deepcopy(cutoff),
        "model_sha256": model_sha256,
        "history_sha256": history_sha256,
        "baseline_id": baseline_id,
        "applied_event_ids": [],
        "duplicate_event_ids": list(duplicate_event_ids or []),
        "state": None,
        **({"reason": reason} if reason is not None else {}),
    }


def unavailable(story_slug: str, cutoff: object, reason: str, invalid: bool = False) -> dict:
    """Build the standard failed preview report without reading any inputs."""
    return _report(story_slug, cutoff, "INVALID" if invalid else "UNKNOWN", reason)


def _worldpoint(world_time: dict) -> tuple[int, int]:
    return world_time["tick"], world_time["suborder"]


def _cursorpoint(cursor: dict) -> tuple[int, int, int]:
    side = 0 if cursor["boundary"] == "BEFORE" else 1
    return cursor["tick"], cursor["suborder"], side


def _statepoint(point: tuple[int, int], boundary: str) -> tuple[int, int, int]:
    return point[0], point[1], 0 if boundary == "BEFORE" else 1


def _holder_equal(left: dict, right: dict) -> bool:
    """JSON type-sensitive holder comparison (schema keeps holders scalar)."""
    return (type(left) is type(right) and left.keys() == right.keys()
            and all(type(left[key]) is type(right[key]) and left[key] == right[key]
                    for key in left))


def _find_position(state: dict, character_id: str) -> dict | None:
    return next((row for row in state["positions"]
                 if row["character_id"] == character_id), None)


def _find_holding(state: dict, item_id: str, holder: dict) -> dict | None:
    return next((row for row in state["holdings"]
                 if row["item_id"] == item_id and _holder_equal(row["holder"], holder)), None)


def _apply_operation(state: dict, operation: dict, policies: dict[str, str], event_id: str) -> None:
    if operation["operation"] == "MOVE_CHARACTER":
        position = _find_position(state, operation["character_id"])
        if (position is None or position["location"].get("status") != "KNOWN"
                or position["location"].get("location_id") != operation["from_location_id"]):
            raise _Unavailable(f"{event_id}: character position precondition is unknown or does not match")
        position["location"] = {"status": "KNOWN", "location_id": operation["to_location_id"]}
        return

    item_id = operation["item_id"]
    source_holder = operation["from_holder"]
    destination_holder = operation["to_holder"]
    source = _find_holding(state, item_id, source_holder)
    destination = _find_holding(state, item_id, destination_holder)
    tracking = policies[item_id]
    amount = operation["quantity"]

    if tracking == "UNIQUE":
        item_rows = [row for row in state["holdings"] if row["item_id"] == item_id]
        if (len(item_rows) != 1 or source is None or source["quantity"] is None
                or type(source["quantity"]) is not int or source["quantity"] != 1
                or type(amount) is not int or amount != 1):
            raise _Unavailable(f"{event_id}: UNIQUE holding precondition is unknown or does not match")
        source["holder"] = copy.deepcopy(destination_holder)
        return

    if (source is None or destination is None or source["quantity"] is None
            or destination["quantity"] is None
            or type(source["quantity"]) is not int or type(destination["quantity"]) is not int
            or type(amount) is not int or source["quantity"] < amount):
        raise _Unavailable(f"{event_id}: STACK holding precondition is unknown or does not match")
    source["quantity"] -= amount
    destination["quantity"] += amount


def _deduplicated_events(history: dict) -> list[dict]:
    events: list[dict] = []
    seen: set[str] = set()
    for event in history["deltas"]:
        if event["id"] in seen:
            continue
        seen.add(event["id"])
        events.append(event)
    return events


def _check_evidence(evidence_check: Callable[[dict], object] | None, source: dict, label: str) -> None:
    if evidence_check is None:
        raise _Unavailable("No evidence checker was supplied; local evidence remains unchecked.")
    try:
        evidence_check(copy.deepcopy(source))
    except Exception as exc:
        raise _Unavailable(f"{label} source evidence is missing, stale, or unreadable ({type(exc).__name__}).") from exc


def preview(model: object, history: object, db: object, cutoff: object,
            evidence_check: Callable[[dict], object] | None = None) -> dict:
    """Return an atomic, deterministic PROPOSED projection or a failed report."""
    duplicates = _duplicate_event_ids(history)
    story_slug = history.get("story_slug") if isinstance(history, dict) else None
    if not isinstance(story_slug, str) and isinstance(model, dict):
        story_slug = model.get("story_slug")
    if not isinstance(story_slug, str):
        story_slug = None

    model_hash = history_hash = baseline_id = None
    try:
        if isinstance(model, dict):
            model_hash = digest(model)
        if isinstance(history, dict):
            history_hash = digest(history)
            if isinstance(history.get("baseline_id"), str):
                baseline_id = history["baseline_id"]
    except (TypeError, ValueError):
        # input_errors below turns non-canonical JSON input into INVALID.
        pass

    def failed(availability: str, reason: str) -> dict:
        return _report(story_slug, cutoff, availability, reason,
                       model_sha256=model_hash, history_sha256=history_hash,
                       baseline_id=baseline_id, duplicate_event_ids=duplicates)

    if model is None or history is None:
        return failed("UNKNOWN", "No enabled S1 world model or optional S2 history is available.")

    errors = input_errors(model, history, db)
    cursor_errors = _cursor_errors(cutoff)
    if errors or cursor_errors:
        details = errors + cursor_errors
        return failed("INVALID", "; ".join(details))

    # From this point the local schemas and selected-story references make all
    # accesses below safe and the report identities are known.
    assert isinstance(model, dict) and isinstance(history, dict) and isinstance(db, dict)
    baseline = model["baseline"]
    if baseline is None:
        return failed("UNKNOWN", "No explicit S1 baseline is available.")
    if baseline["local_status"] != "APPROVED":
        return failed("UNKNOWN", "The explicit baseline is not locally approved.")
    if baseline["anchor"]["world_time"]["status"] != "KNOWN":
        return failed("UNKNOWN", "The explicit baseline has no known world-clock coordinate.")

    coverage = history["coverage"]
    if coverage["local_status"] != "APPROVED":
        return failed("UNKNOWN", "The explicit history coverage declaration is not locally approved.")

    baseline_time = baseline["anchor"]["world_time"]
    target_clock = cutoff["clock_id"]
    coverage_cursor = coverage["through"]
    if baseline_time["clock_id"] != target_clock or coverage_cursor["clock_id"] != target_clock:
        return failed("UNKNOWN", "The baseline, target, and coverage do not share one explicit world clock.")

    baseline_point = _worldpoint(baseline_time)
    baseline_statepoint = _statepoint(baseline_point, history["baseline_boundary"])
    target_statepoint = _cursorpoint(cutoff)
    coverage_statepoint = _cursorpoint(coverage_cursor)
    if target_statepoint < baseline_statepoint:
        return failed("UNKNOWN", "The target cutoff is earlier than the explicit baseline.")
    if target_statepoint > coverage_statepoint:
        return failed("UNKNOWN", "The target cutoff is beyond the declared history coverage.")

    events = _deduplicated_events(history)
    interval: list[tuple[tuple[int, int], dict]] = []
    for event in events:
        world_time = event["anchor"]["world_time"]
        if world_time["status"] != "KNOWN":
            return failed("UNKNOWN", f"{event['id']}: event has no known world-clock coordinate.")
        if world_time["clock_id"] != target_clock:
            return failed("UNKNOWN", f"{event['id']}: event uses an incomparable world clock.")
        point = _worldpoint(world_time)
        event_statepoint = _statepoint(point, "AFTER")
        # The event's narrative boundary is deliberately not consulted here.
        after_baseline = event_statepoint > baseline_statepoint
        before_target = event_statepoint < target_statepoint or (
            point == (cutoff["tick"], cutoff["suborder"])
            and cutoff["boundary"] == "AFTER")
        if after_baseline and before_target:
            interval.append((point, event))

    by_coordinate: dict[tuple[int, int], str] = {}
    for point, event in interval:
        previous_id = by_coordinate.get(point)
        if previous_id is not None and previous_id != event["id"]:
            return failed("INVALID", f"distinct events {previous_id} and {event['id']} share a world-clock coordinate")
        by_coordinate[point] = event["id"]

    interval.sort(key=lambda item: (item[0], item[1]["id"]))
    for _, event in interval:
        if event["local_status"] != "APPROVED":
            return failed("UNKNOWN", f"{event['id']}: an included proposed event leaves a history gap.")

    # A complete preview requires source checks for the baseline and coverage,
    # then for every included locally approved event. Excluded event evidence is
    # intentionally never opened or hashed.
    try:
        _check_evidence(evidence_check, baseline["source"], "Baseline")
        _check_evidence(evidence_check, coverage["source"], "Coverage")
        for _, event in interval:
            _check_evidence(evidence_check, event["source"], event["id"])
    except _Unavailable as exc:
        return failed("UNKNOWN", str(exc))

    state = {"positions": copy.deepcopy(baseline["positions"]),
             "holdings": copy.deepcopy(baseline["holdings"])}
    policies = {policy["item_id"]: policy["tracking"] for policy in model["item_policies"]}
    applied: list[str] = []
    try:
        for _, event in interval:
            candidate = copy.deepcopy(state)
            for operation in event["operations"]:
                _apply_operation(candidate, operation, policies, event["id"])
            state = candidate
            applied.append(event["id"])
    except _Unavailable as exc:
        result = failed("UNKNOWN", str(exc))
        result["applied_event_ids"] = []
        result["state"] = None
        return result

    result = failed("AVAILABLE", "")
    result.pop("reason", None)
    result["applied_event_ids"] = applied
    result["state"] = state
    return result
