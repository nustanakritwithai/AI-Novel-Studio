"""Read-only local diagnostics; local labels never authenticate GitHub approval."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

try:
    from scripts import novelctl, registry_schema, state_replay, story_config, story_engine
except ImportError:  # direct CLI imports
    import novelctl
    import registry_schema
    import state_replay
    import story_config
    import story_engine


LOCAL_ERRORS = (OSError, ValueError, TypeError, KeyError, RuntimeError)


def _git(root: Path) -> dict:
    """Inspect only HEAD and this selected root; never read remotes or credentials."""
    result = {"status": "UNKNOWN", "head": "UNKNOWN", "selected_root_dirty": "UNKNOWN",
              "dirty_scope": "Selected story root; submodule working-tree changes ignored."}
    # Inherited Git overrides must not redirect the selected root elsewhere.
    # The process-only fsmonitor setting prevents status invoking a local hook;
    # it never changes repository or user configuration.
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", GIT_NO_LAZY_FETCH="1",
                       GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.fsmonitor", GIT_CONFIG_VALUE_0="false")
    base = ["git", "--no-optional-locks", "--no-lazy-fetch", "-C", str(root)]
    try:
        head = subprocess.run(base + ["rev-parse", "--verify", "HEAD"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=5, check=False, env=environment)
        value = head.stdout.strip()
        if head.returncode != 0 or not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", value):
            result["reason"] = "No readable local Git HEAD is available."
            return result
        result["head"] = value
        status = subprocess.run(base + ["status", "--porcelain", "--untracked-files=normal", "--ignore-submodules=all", "--", "."],
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=5, check=False, env=environment)
        if status.returncode != 0:
            result["reason"] = "Local Git HEAD is known; selected-root working-tree status is unavailable."
            return result
        result.update(status="KNOWN", selected_root_dirty=bool(status.stdout.strip()))
        return result
    except (OSError, subprocess.SubprocessError):
        result["reason"] = "Local Git diagnostics are unavailable."
        return result


def diagnose(root: Path, target: str | None = None, story: str | None = None) -> dict:
    """Return deterministic local facts and explicit unknowns without changing files.

    A valid local registry or KNOWN replay is not authenticated human approval.
    Missing Git metadata and unchecked online controls are unknowns, not failures.
    """
    result = {
        "schema_version": 1, "kind": "LOCAL_DOCTOR_REPORT",
        "errors": [], "warnings": [], "local_validation_status": "NOT_RUN",
        "story_slug": "UNKNOWN", "selected_root": "UNKNOWN",
        "schema": {"status": "NOT_CHECKED", "dependencies": "UNKNOWN",
                   "version": 1, "validator": "Draft202012Validator"},
        "git": {"status": "UNKNOWN", "head": "UNKNOWN", "selected_root_dirty": "UNKNOWN"},
        "state": {"history": "UNKNOWN", "target": target, "availability": "NOT_CHECKED",
                  "approval_basis": state_replay.APPROVAL_BASIS},
        "github": {"check_status": "NOT_CHECKED", "authentication": "NOT_CHECKED", "approval_provenance": "UNKNOWN",
                   "settings": "UNKNOWN", "security": "UNKNOWN",
                   "codeowners_enforcement": "UNKNOWN",
                   "reason": "No authenticated online check was performed."},
    }
    selected = None
    try:
        selected = story_config.resolve_root(root, story)
        configuration = story_config.load_config(selected)
        result["story_slug"] = configuration["slug"]
        result["selected_root"] = str(selected)
    except LOCAL_ERRORS as exc:
        result["errors"].append(f"Story configuration: {exc}")

    try:
        # Probe even with cached validators: optional format dependencies must
        # never silently disappear from a supposedly successful diagnostic.
        registry_schema._dependencies()
        result["schema"]["dependencies"] = "AVAILABLE"
        for kind in registry_schema.SCHEMA_KINDS:
            registry_schema.validator(kind)
        result["schema"]["status"] = "PASS"
    except LOCAL_ERRORS as exc:
        result["schema"]["status"] = "ERROR"
        if result["schema"]["dependencies"] == "UNKNOWN":
            result["schema"]["dependencies"] = "ERROR"
        result["schema"]["detail"] = str(exc)
        result["errors"].append(f"Schema validation unavailable: {exc}")

    if selected is None or result["selected_root"] == "UNKNOWN":
        if target is not None:
            result["state"].update(availability="ERROR", reason="Story configuration is invalid.")
        return result

    result["git"] = _git(selected)
    try:
        history = story_config.story_path(selected, state_replay.HISTORY_PATH)
        present = history.exists() or (selected / state_replay.HISTORY_PATH).is_symlink()
        result["state"]["history"] = "PRESENT" if present else "LEGACY"
    except LOCAL_ERRORS as exc:
        result["state"]["reason"] = str(exc)

    if result["schema"]["status"] != "PASS":
        if target is not None:
            result["state"].update(availability="ERROR", reason="Schema validation is unavailable.")
        return result

    try:
        errors, warnings = story_engine.validate(selected)
        result["errors"].extend(errors)
        result["warnings"].extend(warnings)
        result["local_validation_status"] = "FAIL" if errors else "PASS"
    except LOCAL_ERRORS as exc:
        result["errors"].append(f"Local validation failed: {exc}")
        result["local_validation_status"] = "FAIL"

    if target is None:
        return result
    if result["errors"]:
        result["state"].update(availability="ERROR", reason="Local validation failed; target state was not evaluated.")
        return result

    try:
        state = novelctl.state_before_target(selected, target)
        availability = state.get("availability", "KNOWN")
        result["state"]["availability"] = availability
        if "reason" in state:
            result["state"]["reason"] = state["reason"]
        if availability == "KNOWN":
            result["state"]["as_of_scene"] = state.get("as_of_scene", state.get("approved_through_scene"))
            if result["state"]["history"] == "LEGACY":
                result["state"]["reason"] = "Legacy local snapshot or initial baseline; no explicit delta history."
    except LOCAL_ERRORS as exc:
        result["state"].update(availability="ERROR", reason=str(exc))
        result["errors"].append(f"Target state: {exc}")
        result["local_validation_status"] = "FAIL"
    return result
