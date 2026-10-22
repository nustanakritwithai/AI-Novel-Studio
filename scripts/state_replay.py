"""Replay explicit local state evidence, never planned effects or inferred history.

An APPROVED label in these files is a local declaration, not an authenticated
GitHub review. The engine never changes that label or writes any state.
"""
from __future__ import annotations

import copy
from pathlib import Path

try:
    from scripts import registry_schema, story_config
except ImportError:  # direct legacy CLI imports
    import registry_schema
    import story_config

APPROVED_SCENES = {"APPROVED", "CANON"}
APPROVAL_BASIS = "LOCAL_RECORDS_NOT_GITHUB_AUTHENTICATED"
HISTORY_PATH = "data/state_history.json"


def _load(root: Path) -> tuple[Path, dict | None]:
    root = story_config.resolve_root(root)
    original = root / HISTORY_PATH
    path = story_config.story_path(root, HISTORY_PATH)
    if not original.exists() and not original.is_symlink():
        return root, None
    try:
        history = registry_schema.read_json(path)
    except (OSError, ValueError) as exc:
        raise ValueError(f"{HISTORY_PATH}: cannot read history ({exc})") from exc
    registry_schema.ensure_valid("state_history", history)
    return root, history


def _sequence(db: dict) -> tuple[list[dict], dict[str, int]]:
    """Use episode registry order and numeric scene order, never names or IDs."""
    try:
        episodes = {episode["id"]: n for n, episode in enumerate(db["episodes"]["episodes"])}
        scenes = sorted(db["scenes"]["scenes"], key=lambda scene: (episodes[scene["episode_id"]], scene["order"]))
        positions = {scene["id"]: n for n, scene in enumerate(scenes)}
        if len(positions) != len(scenes):
            raise ValueError("duplicate scene IDs")
        return scenes, positions
    except (KeyError, TypeError) as exc:
        raise ValueError(f"{HISTORY_PATH}: scene chronology is unavailable ({exc})") from exc


def _structure(history: dict, db: dict) -> tuple[list[dict], dict[str, int], list[str]]:
    scenes, positions = _sequence(db)
    errors, ids, scene_ids = [], set(), set()
    baseline = history["baseline"]
    if baseline is not None and baseline["before_scene"] not in positions:
        errors.append(f"{HISTORY_PATH}: baseline references unknown scene {baseline['before_scene']}")
    previous = -1
    for delta in history["deltas"]:
        if delta["id"] in ids:
            errors.append(f"{HISTORY_PATH}: duplicate delta ID {delta['id']}")
        ids.add(delta["id"])
        sid = delta["scene_id"]
        if sid in scene_ids:
            errors.append(f"{HISTORY_PATH}: multiple deltas for scene {sid}")
        scene_ids.add(sid)
        if sid not in positions:
            errors.append(f"{HISTORY_PATH}: {delta['id']} references unknown scene {sid}")
            continue
        position = positions[sid]
        if position < previous:
            errors.append(f"{HISTORY_PATH}: deltas must follow episode/scene chronology")
        previous = position
        if baseline is not None and baseline["before_scene"] in positions and position < positions[baseline["before_scene"]]:
            errors.append(f"{HISTORY_PATH}: {delta['id']} precedes the explicit baseline")
    return scenes, positions, errors


def _read_evidence(root: Path, relative: str, context: str, drafts_only: bool = False) -> None:
    try:
        path = story_config.story_path(root, relative)
        if path == story_config.story_path(root, HISTORY_PATH):
            raise ValueError("history cannot cite itself as independent evidence")
        if drafts_only:
            drafts = story_config.story_path(root, "drafts")
            if not path.is_relative_to(drafts) or path.suffix != ".md":
                raise ValueError("approved scene evidence must be Markdown inside this story's drafts/")
        if not path.read_text(encoding="utf-8").strip():
            raise ValueError("evidence is blank")
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError(f"{HISTORY_PATH}: {context}: unreadable source evidence ({exc})") from exc


def _read_baseline_evidence(root: Path, baseline: dict, db: dict) -> None:
    """A declared initial state needs independent evidence, never scene prose."""
    path = story_config.story_path(root, baseline["evidence_path"])
    operational = [story_config.story_path(root, directory)
                   for directory in ("data", "scenes", "drafts", "ledger")]
    if any(path.is_relative_to(directory) for directory in operational) or any(
            scene.get("draft_path") and path == story_config.story_path(root, scene["draft_path"])
            for scene in db["scenes"]["scenes"]):
        raise ValueError(f"{HISTORY_PATH}: baseline requires independent state evidence outside live registries, cards, drafts and ledgers; "
                         "scene evidence must use chronological deltas")
    _read_evidence(root, baseline["evidence_path"], "baseline")


def validate(root: Path, db: dict) -> list[str]:
    """Check schema, chronological pointers and readable eligible source files.

    Value preconditions are target-specific and checked by replay_before. A
    proposed delta or an unapproved source scene never becomes replay-eligible.
    """
    try:
        root, history = _load(root)
        if history is None:
            return []
        scenes, _, errors = _structure(history, db)
        by_scene = {scene["id"]: scene for scene in scenes}
        baseline = history["baseline"]
        if baseline is not None and baseline["status"] == "APPROVED":
            try:
                _read_baseline_evidence(root, baseline, db)
            except ValueError as exc:
                errors.append(str(exc))
        for delta in history["deltas"]:
            scene = by_scene.get(delta["scene_id"])
            if delta["status"] == "APPROVED" and scene and scene["status"] in APPROVED_SCENES:
                try:
                    _read_evidence(root, scene.get("draft_path"), delta["id"], drafts_only=True)
                except ValueError as exc:
                    errors.append(str(exc))
        return errors
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [str(exc)]


def _unknown(target: str, reason: str) -> dict:
    return {"availability": "UNKNOWN", "before_scene": target,
            "as_of_scene": None, "approval_basis": APPROVAL_BASIS, "reason": reason}


def _equal(left, right) -> bool:
    """Type-sensitive JSON equality: booleans cannot satisfy numeric evidence."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    return left == right


def _apply(state: dict, change: dict, delta_id: str) -> None:
    parent = state
    for segment in change["path"][:-1]:
        if not isinstance(parent, dict) or segment not in parent or not isinstance(parent[segment], dict):
            raise ValueError(f"{HISTORY_PATH}: {delta_id}: missing/object parent at {change['path']}")
        parent = parent[segment]
    leaf = change["path"][-1]
    exists = leaf in parent
    if exists != change["before_exists"] or (exists and not _equal(parent[leaf], change["before"])):
        raise ValueError(f"{HISTORY_PATH}: {delta_id}: inconsistent before condition at {change['path']}")
    if change["operation"] == "REMOVE":
        del parent[leaf]
    else:
        parent[leaf] = copy.deepcopy(change["value"])


def replay_before(root: Path, target: str, db: dict) -> dict | None:
    """Return strict scene-start state, UNKNOWN, or None for legacy fallback.

    Each scene in the requested interval needs one locally approved delta and
    an approved source scene with readable prose evidence. Empty changes record
    an explicit no-change scene. Gaps return no partial state.
    """
    root, history = _load(root)
    if history is None:
        return None
    scenes, positions, errors = _structure(history, db)
    if errors:
        raise ValueError("; ".join(errors))
    if target not in positions:
        episodes = [episode for episode in db["episodes"]["episodes"] if episode["id"] == target]
        if not episodes:
            raise ValueError(f"{HISTORY_PATH}: unknown target {target}")
        episode_scenes = [scene for scene in scenes if scene["episode_id"] == target]
        if not episode_scenes:
            raise ValueError(f"{HISTORY_PATH}: target episode has no scenes")
        target = episode_scenes[0]["id"]
    cutoff = positions[target]
    baseline = history["baseline"]
    if baseline is None or baseline["status"] != "APPROVED":
        return _unknown(target, "No locally approved explicit baseline is available.")
    start = positions[baseline["before_scene"]]
    if cutoff < start:
        return _unknown(target, "The explicit baseline is later than the requested scene.")
    _read_baseline_evidence(root, baseline, db)
    state = copy.deepcopy(baseline["state"])
    deltas = {delta["scene_id"]: delta for delta in history["deltas"]}
    applied, last = [], None
    for scene in scenes[start:cutoff]:
        sid = scene["id"]
        delta = deltas.get(sid)
        if scene["status"] not in APPROVED_SCENES or delta is None or delta["status"] != "APPROVED":
            return _unknown(target, f"No eligible approved state delta/source for preceding scene {sid}.")
        _read_evidence(root, scene.get("draft_path"), delta["id"], drafts_only=True)
        for change in delta["changes"]:
            _apply(state, change, delta["id"])
        applied.append(delta["id"])
        last = sid
    return {"availability": "KNOWN", "before_scene": target, "as_of_scene": last,
            "baseline_before_scene": baseline["before_scene"], "approval_basis": APPROVAL_BASIS,
            "applied_delta_ids": applied, "state": state}
