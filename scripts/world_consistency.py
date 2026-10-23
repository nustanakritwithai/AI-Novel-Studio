"""Opt-in S3 diagnostics for bounded S2 world-state operations.

This module classifies only explicit S2 movement and custody preconditions. It
does not create a second reducer, infer missing facts, or apply state to canon.
"""
from __future__ import annotations

import copy
from functools import lru_cache
from pathlib import Path

try:
    from scripts import registry_schema, story_config, world_history
    from scripts import world_history_schema, world_state_reducer
except ImportError:  # direct legacy CLI imports
    import registry_schema
    import story_config
    import world_history
    import world_history_schema
    import world_state_reducer


RULES_PATH = "data/world_rules.json"
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "world_state" / "world_rules.schema.json"
SCHEMA_ID = "https://ai-novel-studio.local/schemas/world_state/world_rules.schema.json"
RULE_IDS = ("MOVE_ORIGIN", "UNIQUE_CUSTODY", "STACK_BALANCE")
STATUSES = ("PASS", "CONTRADICTION", "UNKNOWN")


def _digest(value: object) -> str | None:
    try:
        return world_state_reducer.digest(value)
    except (TypeError, ValueError):
        return None


def _slug(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _cursor_errors(cutoff: object) -> list[str]:
    try:
        return world_history_schema.validate_cursor(cutoff)
    except Exception as exc:
        return [f"cutoff cursor validation failed ({type(exc).__name__})"]


@lru_cache(maxsize=1)
def _rules_validator():
    """Build a real Draft 2020-12 validator from one fixed local schema."""
    Draft202012Validator, _, Registry, Resource, NoSuchResource = registry_schema._dependencies()

    def refuse_remote(uri):
        raise NoSuchResource(ref=uri)

    try:
        schema = registry_schema.read_json(SCHEMA_PATH)
        Draft202012Validator.check_schema(schema)
        if schema.get("$id") != SCHEMA_ID:
            raise ValueError("engine schema identity does not match the fixed rules schema")
        resource = Resource.from_contents(schema)
        registry = Registry(retrieve=refuse_remote).with_resource(SCHEMA_ID, resource)
        return Draft202012Validator(schema, registry=registry)
    except Exception as exc:
        raise ValueError(f"engine world rules schema is invalid ({type(exc).__name__})") from exc


def _rules_errors(rules: object) -> list[str]:
    try:
        validator = _rules_validator()
        errors = sorted(validator.iter_errors(rules),
                        key=lambda error: (tuple(str(part) for part in error.absolute_path), error.message))
    except Exception as exc:
        return [f"world rules validation failed ({type(exc).__name__})"]
    return [f"data/world_rules.json {registry_schema._path(error)}: {error.message}"
            for error in errors]


def _base_report(story_slug: object, cutoff: object, *, status: str,
                 rules_sha256: str | None = None, enabled_rules: list[str] | None = None,
                 model_sha256: str | None = None, history_sha256: str | None = None,
                 preview_availability: str | None = None, diagnostics: list[dict] | None = None,
                 complete: bool = False, reason: str | None = None) -> dict:
    result = {
        "schema_version": 1,
        "kind": "WORLD_STATE_DIAGNOSTICS",
        "status": status,
        "proposal_status": "PROPOSED",
        "human_editorial_approval": "UNVERIFIED",
        "approval_basis": "LOCAL_DECLARATIONS_NOT_AUTHENTICATED",
        "canon_change_authorized": False,
        "ledger_apply_authorized": False,
        "usable_world_state": False,
        "state": None,
        "story_slug": _slug(story_slug),
        "cutoff": copy.deepcopy(cutoff),
        "enabled_rules": list(enabled_rules or []),
        "model_sha256": model_sha256,
        "history_sha256": history_sha256,
        "rules_sha256": rules_sha256,
        "preview_availability": preview_availability,
        "diagnostics": copy.deepcopy(diagnostics or []),
        "summary": {
            "pass": sum(item.get("result") == "PASS" for item in (diagnostics or [])),
            "contradiction": sum(item.get("result") == "CONTRADICTION" for item in (diagnostics or [])),
            "unknown": sum(item.get("result") == "UNKNOWN" for item in (diagnostics or [])),
        },
        "complete": complete,
    }
    if reason is not None:
        result["reason"] = reason
    return result


def _invalid(story_slug: object, cutoff: object, reason: str, *, rules_sha256: str | None = None,
             rules: object = None) -> dict:
    requested = rules.get("rules", []) if isinstance(rules, dict) else []
    active = requested if isinstance(rules, dict) and rules.get("enabled") is True else []
    if not isinstance(active, list) or any(not isinstance(rule, str) for rule in active):
        active = []
    return _base_report(story_slug, cutoff, status="INVALID", rules_sha256=rules_sha256,
                        enabled_rules=active, reason=reason)


def _diagnose(model: object, history: object, db: object, cutoff: object,
              rules: object, evidence_check=None, *, selected_slug: str | None = None) -> dict:
    if rules is None:
        cursor_errors = _cursor_errors(cutoff)
        if cursor_errors:
            return _invalid(selected_slug, cutoff, "; ".join(cursor_errors))
        return _base_report(selected_slug, cutoff, status="DISABLED")

    rules_hash = _digest(rules)
    rule_errors = _rules_errors(rules)
    story_slug = rules.get("story_slug") if isinstance(rules, dict) else selected_slug
    if rule_errors:
        return _invalid(selected_slug or story_slug, cutoff, "; ".join(rule_errors),
                        rules_sha256=rules_hash, rules=rules)

    cursor_errors = _cursor_errors(cutoff)
    if cursor_errors:
        return _invalid(selected_slug or story_slug, cutoff, "; ".join(cursor_errors),
                        rules_sha256=rules_hash, rules=rules)

    assert isinstance(rules, dict)
    if selected_slug is not None and rules["story_slug"] != selected_slug:
        return _invalid(selected_slug, cutoff,
                        "data/world_rules.json story_slug does not match the selected story.",
                        rules_sha256=rules_hash, rules=rules)

    if rules["enabled"] is not True or not rules["rules"]:
        return _base_report(selected_slug or rules["story_slug"], cutoff, status="DISABLED",
                            rules_sha256=rules_hash)

    model_hash = _digest(model) if model is not None else None
    history_hash = _digest(history) if history is not None else None
    if isinstance(model, dict) and model.get("story_slug") != rules["story_slug"]:
        return _invalid(selected_slug or rules["story_slug"], cutoff,
                        "data/world_rules.json story_slug does not match the S1 world model.",
                        rules_sha256=rules_hash, rules=rules)

    try:
        inspected = world_state_reducer.inspect_preview(
            model, history, db, cutoff, evidence_check=evidence_check)
        preview = inspected["preview"]
        diagnostics = [copy.deepcopy(item) for item in inspected["diagnostics"]
                       if item.get("rule_id") in rules["rules"]]
    except Exception as exc:
        return _invalid(selected_slug or rules["story_slug"], cutoff,
                        f"World-state diagnostic input is invalid ({type(exc).__name__}).",
                        rules_sha256=rules_hash, rules=rules)

    availability = preview.get("availability")
    model_hash = preview.get("model_sha256", model_hash)
    history_hash = preview.get("history_sha256", history_hash)
    if availability == "INVALID":
        status = "INVALID"
    elif any(item.get("result") == "CONTRADICTION" for item in diagnostics):
        status = "CONTRADICTION"
    elif availability == "UNKNOWN" or any(item.get("result") == "UNKNOWN" for item in diagnostics):
        status = "UNKNOWN"
    elif availability == "AVAILABLE" and diagnostics and all(item.get("result") == "PASS" for item in diagnostics):
        status = "PASS"
    else:
        status = "NO_CHECKS"

    reason = preview.get("reason") if availability != "AVAILABLE" else None
    return _base_report(selected_slug or rules["story_slug"], cutoff, status=status,
                        rules_sha256=rules_hash, enabled_rules=rules["rules"],
                        model_sha256=model_hash, history_sha256=history_hash,
                        preview_availability=availability, diagnostics=diagnostics,
                        complete=availability == "AVAILABLE", reason=reason)


def diagnose(model: object, history: object, db: object, cutoff: object,
             rules: object, evidence_check=None) -> dict:
    """Purely classify selected S2 operation preconditions using parsed inputs."""
    return _diagnose(model, history, db, cutoff, rules, evidence_check=evidence_check)


def _rules_path(root: Path) -> Path:
    raw_path = Path(root) / RULES_PATH
    if raw_path.is_symlink() and not raw_path.exists():
        raise ValueError("data/world_rules.json: dangling symlink is not an absent optional file")
    return story_config.story_path(root, RULES_PATH)


def _rules_evidence_checker(root: Path, rules_path: Path):
    checker = world_history._evidence_checker(root)

    def check(source: dict) -> None:
        if isinstance(source, dict) and isinstance(source.get("path"), str):
            evidence_path = story_config.story_path(root, source["path"])
            if (world_history._same_path(evidence_path, rules_path)
                    or world_history._same_file(evidence_path, rules_path)):
                raise ValueError("world rules cannot be used as source evidence")
        checker(source)

    return check


def build(root: Path, cutoff: object, db: dict | None = None) -> dict:
    """Build diagnostics from exactly one selected story and its bounded files."""
    selected_slug = None
    try:
        selected_root, config = world_history._selected(Path(root))
        selected_slug = config.get("slug")
        rules_path = _rules_path(selected_root)
        if not rules_path.exists() and not rules_path.is_symlink():
            return _diagnose(None, None, db, cutoff, None, selected_slug=selected_slug)

        rules = world_history._read_bounded_json(rules_path, RULES_PATH)
        rules_hash = _digest(rules)
        rule_errors = _rules_errors(rules)
        if rule_errors:
            return _invalid(selected_slug, cutoff, "; ".join(rule_errors),
                            rules_sha256=rules_hash, rules=rules)
        if not isinstance(rules, dict) or rules.get("story_slug") != selected_slug:
            return _invalid(selected_slug, cutoff,
                            "data/world_rules.json story_slug does not match the selected story.",
                            rules_sha256=rules_hash, rules=rules)

        # diagnose validates the cursor before deciding that an explicit but
        # disabled/empty rule file needs no world-model or history reads.
        staged = _diagnose(None, None, db, cutoff, rules, selected_slug=selected_slug)
        if staged["status"] in ("INVALID", "DISABLED"):
            return staged

        loaded = world_history.load(selected_root, db)
        if loaded is None:
            return _diagnose(None, None, db, cutoff, rules,
                             evidence_check=None, selected_slug=selected_slug)
        model, history, selected_db = loaded
        return _diagnose(model, history, selected_db, cutoff, rules,
                         evidence_check=_rules_evidence_checker(selected_root, rules_path),
                         selected_slug=selected_slug)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, RecursionError) as exc:
        return _invalid(selected_slug, cutoff,
                        f"Selected world-state input is invalid ({type(exc).__name__}).")
