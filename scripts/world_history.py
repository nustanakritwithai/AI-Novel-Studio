"""Local, read-only loading boundary for S2 proposed world history.

History and evidence remain local declarations.  This module validates their
structure and exact bytes for checks/previews, but never applies state or
authenticates a local APPROVED label as human editorial approval.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

try:
    from scripts import registry_schema, story_config, world_history_schema
    from scripts import world_state_model, world_state_reducer
except ImportError:  # direct legacy CLI imports
    import registry_schema
    import story_config
    import world_history_schema
    import world_state_model
    import world_state_reducer


MODEL_PATH = world_state_model.MODEL_PATH
HISTORY_PATH = "data/world_history.json"
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_EVIDENCE_BYTES = 1024 * 1024

# Keep these public declarations aligned with the reducer's report contract.
HUMAN_APPROVAL = world_state_reducer.HUMAN_APPROVAL
APPROVAL_BASIS = world_state_reducer.APPROVAL_BASIS
PROPOSAL_STATUS = "PROPOSED"
CANON_CHANGE_AUTHORIZED = False
LEDGER_APPLY_AUTHORIZED = False


class _DuplicateJSONKey(ValueError):
    """A JSON object repeated a key, making its meaning parser-dependent."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKey("duplicate JSON object key")
        result[key] = value
    return result


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("non-finite JSON number")
    return parsed


def _reject_constant(_value: str) -> None:
    raise ValueError("non-finite JSON constant")


def _read_bounded_json(path: Path, label: str) -> object:
    """Read strict UTF-8 JSON within the shared 8 MiB input bound."""
    if not path.is_file():
        raise ValueError(f"{label}: expected a regular file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"{label} exceeds the {MAX_INPUT_BYTES}-byte input limit")
    try:
        source = raw.decode("utf-8", errors="strict")
        return json.loads(source, object_pairs_hook=_unique_object,
                          parse_constant=_reject_constant, parse_float=_finite_float)
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateJSONKey, ValueError,
            RecursionError) as exc:
        if isinstance(exc, _DuplicateJSONKey):
            reason = "duplicate object key"
        elif isinstance(exc, UnicodeDecodeError):
            reason = "invalid UTF-8"
        elif isinstance(exc, json.JSONDecodeError):
            reason = "invalid JSON"
        elif isinstance(exc, RecursionError):
            reason = "JSON nesting limit exceeded"
        else:
            reason = str(exc) or "invalid JSON value"
        raise ValueError(f"{label}: {reason}") from exc


def _selected(root: Path) -> tuple[Path, dict]:
    selected_root = story_config.resolve_root(root)
    config = story_config.load_config(selected_root)
    return selected_root, config


def _catalog_db(root: Path) -> dict:
    """Read and validate only the four fixed catalogs for the selected story."""
    db: dict = {}
    for kind in ("characters", "locations", "items", "scenes"):
        path = story_config.story_path(root, f"data/{kind}.json")
        if not path.is_file():
            raise ValueError(f"data/{kind}.json: expected a regular file")
        value = registry_schema.read_json(path)
        registry_schema.ensure_valid(kind, value)
        db[kind] = value
    return db


def _model_inputs(root: Path, config: dict, db: dict | None) -> tuple[dict, dict, list[str]]:
    model_path = story_config.story_path(root, MODEL_PATH)
    model = _read_bounded_json(model_path, MODEL_PATH)
    selected_db = _catalog_db(root) if db is None else db
    if not isinstance(selected_db, dict) or any(
            not isinstance(selected_db.get(kind), dict)
            for kind in ("characters", "locations", "items", "scenes")):
        raise ValueError("selected-story world-state catalogs are unavailable")
    errors = world_state_model.validation_errors(model, selected_db, config["slug"])
    return model, selected_db, errors


def _history_path(root: Path) -> Path:
    # story_path resolves symlinks for containment; detect a dangling link on
    # the fixed lexical path first so it cannot masquerade as absent history.
    raw_path = Path(root) / HISTORY_PATH
    if raw_path.is_symlink() and not raw_path.exists():
        raise ValueError(f"{HISTORY_PATH}: dangling symlink is not an absent optional file")
    return story_config.story_path(root, HISTORY_PATH)


def _history_missing(path: Path) -> bool:
    # Treat a dangling symlink as a bad selected file, not as absent history.
    return not path.exists() and not path.is_symlink()


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def _same_file(left: Path, right: Path) -> bool:
    try:
        return left.exists() and right.exists() and os.path.samefile(left, right)
    except OSError:
        return False


def _evidence_checker(root: Path):
    """Return a checker for bounded exact source bytes, with no content output."""
    model_path = story_config.story_path(root, MODEL_PATH)
    history_path = _history_path(root)

    def check(source: dict) -> None:
        if not isinstance(source, dict):
            raise ValueError("source declaration is malformed")
        relative = source.get("path")
        expected = source.get("sha256")
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("source digest is malformed")
        path = story_config.story_path(root, relative)
        if (_same_path(path, model_path) or _same_path(path, history_path)
                or _same_file(path, model_path) or _same_file(path, history_path)):
            raise ValueError("model/history cannot be used as source evidence")
        if not path.is_file():
            raise ValueError("source evidence is not a regular file")
        with path.open("rb") as stream:
            content = stream.read(MAX_EVIDENCE_BYTES + 1)
        if len(content) > MAX_EVIDENCE_BYTES:
            raise ValueError("source evidence exceeds the byte limit")
        if not content.strip():
            raise ValueError("source evidence is blank")
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError("source evidence SHA256 does not match")

    return check


def _load(root: Path, db: dict | None = None) -> tuple[dict, dict, dict] | None:
    """Load one enabled S1 model and its optional S2 history.

    Disabled S1 or an absent optional history returns ``None``. Once both
    declarations exist, strict parsing, S1 validation, history validation and
    cross-reference/digest validation fail closed with ``ValueError``. Evidence
    bytes are checked separately by ``validate`` or the preview callback.
    """
    selected_root, config = _selected(Path(root))
    if not config.get("world_state", {}).get("enabled", False):
        return None

    history_path = _history_path(selected_root)
    if _history_missing(history_path):
        return None
    model, selected_db, model_errors = _model_inputs(selected_root, config, db)
    if model_errors:
        raise ValueError("; ".join(model_errors))
    history = _read_bounded_json(history_path, HISTORY_PATH)

    errors = world_state_reducer.input_errors(model, history, selected_db)
    errors = list(dict.fromkeys([*model_errors, *errors]))
    if errors:
        raise ValueError("; ".join(errors))
    if not isinstance(model, dict) or not isinstance(history, dict):
        # The structural checks above normally provide this diagnostic; retain
        # a hard guard before exposing data to callers if validators ever change.
        raise ValueError("enabled world-state inputs must be JSON objects")
    return model, history, selected_db


def load(root: Path, db: dict | None = None) -> tuple[dict, dict, dict] | None:
    """Load declarations, normalizing filesystem failures to ``ValueError``."""
    try:
        return _load(Path(root), db)
    except (OSError, RuntimeError, RecursionError) as exc:
        raise ValueError(f"Unable to read selected world-state inputs ({type(exc).__name__}).") from exc


def validate(root: Path, db: dict | None = None) -> list[str]:
    """Check enabled history structure and all locally APPROVED source bytes."""
    try:
        selected_root, config = _selected(Path(root))
        if not config.get("world_state", {}).get("enabled", False):
            return []

        history_path = _history_path(selected_root)
        if _history_missing(history_path):
            return []

        model, selected_db, model_errors = _model_inputs(selected_root, config, db)
        history = _read_bounded_json(history_path, HISTORY_PATH)
        errors = world_state_reducer.input_errors(model, history, selected_db)
        errors = list(dict.fromkeys([*model_errors, *errors]))

        # Source paths/bytes are inspected only after pure structure/reference
        # validation has run. If a whole object fails schema validation, its
        # nested source values are not treated as safe path declarations.
        model_schema_errors = world_state_model.validator().iter_errors(model)
        history_schema_errors = world_history_schema.validate(history)
        if not list(model_schema_errors) and not history_schema_errors:
            evidence_check = _evidence_checker(selected_root)
            sources: list[tuple[str, object]] = []
            if isinstance(model, dict):
                baseline = model.get("baseline")
                if isinstance(baseline, dict) and baseline.get("local_status") == "APPROVED":
                    sources.append((str(baseline.get("id", "baseline")), baseline.get("source")))
            if isinstance(history, dict):
                coverage = history.get("coverage")
                if isinstance(coverage, dict) and coverage.get("local_status") == "APPROVED":
                    sources.append(("coverage", coverage.get("source")))
                deltas = history.get("deltas")
                if isinstance(deltas, list):
                    for event in deltas:
                        if isinstance(event, dict) and event.get("local_status") == "APPROVED":
                            sources.append((str(event.get("id", "event")), event.get("source")))
            for label, source in sources:
                try:
                    evidence_check(source)  # type: ignore[arg-type]
                except Exception as exc:
                    errors.append(f"{label}: source evidence check failed ({type(exc).__name__})")
        return list(dict.fromkeys(errors))
    except OSError as exc:
        return [f"data/world_history.json: input read failed ({type(exc).__name__})"]
    except (ValueError, KeyError, TypeError, RuntimeError, RecursionError) as exc:
        # Exceptions and diagnostics contain paths/declarations, never source
        # plaintext. Keep output bounded and avoid exposing absolute paths.
        return [str(exc)[:1000]]


def preview(root: Path, cutoff: object, db: dict | None = None) -> dict:
    """Run the pure S2 reducer with a real, selected-story evidence checker."""
    try:
        selected_root, config = _selected(Path(root))
        slug = config.get("slug")
        cursor_errors = world_history_schema.validate_cursor(cutoff)
        if cursor_errors:
            return world_state_reducer.unavailable(slug, cutoff,
                                                   "; ".join(cursor_errors), invalid=True)
        if not config.get("world_state", {}).get("enabled", False):
            return world_state_reducer.unavailable(slug, cutoff,
                                                   "S1 world state is disabled for the selected story.")

        loaded = load(selected_root, db)
        if loaded is None:
            return world_state_reducer.unavailable(slug, cutoff,
                                                   "No enabled S1 world model or optional S2 history is available.")
        model, history, selected_db = loaded
        return world_state_reducer.preview(model, history, selected_db, cutoff,
                                           evidence_check=_evidence_checker(selected_root))
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, RecursionError) as exc:
        try:
            slug = story_config.load_config(story_config.resolve_root(Path(root))).get("slug")
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, RecursionError):
            slug = None
        return world_state_reducer.unavailable(slug, cutoff,
                                               f"Enabled world-state input is invalid ({type(exc).__name__}).",
                                               invalid=True)
