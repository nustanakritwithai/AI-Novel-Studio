"""Story selection and versioned configuration, using only the standard library."""
from __future__ import annotations

import json
import re
from pathlib import Path, PureWindowsPath

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SLUG = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
RESERVED_SLUGS = {"con", "prn", "aux", "nul"} | {
    f"{prefix}{number}" for prefix in ("com", "lpt") for number in range(1, 10)
}


def validate_slug(value: str) -> str:
    if (not isinstance(value, str) or len(value) > 63 or not SLUG.fullmatch(value)
            or value in RESERVED_SLUGS):
        raise ValueError("Story slug must be 1..63 lowercase letters/digits separated by hyphens, starting with a letter")
    return value


def _object(path: Path, root: Path) -> dict:
    if not path.resolve().is_relative_to(root):
        raise ValueError(f"Configuration path escapes story/workspace root: {path.name}")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read {path.name}: {exc}") from exc
    if not isinstance(result, dict):
        raise ValueError(f"{path.name}: configuration must be an object")
    return result


def load_config(root: Path) -> dict:
    """Read a direct story root; old standalone data roots remain compatible."""
    root = Path(root).resolve()
    path = root / "story.json"
    if not path.exists() and not path.is_symlink():
        if not (root / "data").is_dir():
            raise ValueError(f"No story.json or legacy data directory at {root}")
        return {
            "schema_version": 1,
            "slug": "legacy",
            "title": root.name,
            "extensions": {"gameplay": all((root / "data" / f"{kind}.json").is_file()
                                             for kind in ("mechanics", "sources"))},
            "rules": [],
        }
    result = _object(path, root)
    required = {"schema_version", "slug", "title", "extensions", "rules"}
    if not required <= set(result) or set(result) - required - {"world_state"}:
        raise ValueError("story.json: expected schema_version, slug, title, extensions, rules and optional world_state only")
    if type(result["schema_version"]) is not int or result["schema_version"] != 1:
        raise ValueError("story.json: unsupported schema_version (expected 1)")
    validate_slug(result["slug"])
    if not isinstance(result["title"], str) or not result["title"].strip():
        raise ValueError("story.json: title must be a nonempty string")
    extension = result["extensions"]
    if not isinstance(extension, dict) or set(extension) != {"gameplay"} or type(extension["gameplay"]) is not bool:
        raise ValueError("story.json: extensions.gameplay must be boolean")
    if "world_state" in result:
        model = result["world_state"]
        if (not isinstance(model, dict) or set(model) != {"schema_version", "enabled"}
                or type(model["schema_version"]) is not int or model["schema_version"] != 1
                or type(model["enabled"]) is not bool):
            raise ValueError("story.json: world_state requires schema_version 1 and boolean enabled")
    rules = result["rules"]
    if not isinstance(rules, list) or any(not isinstance(rule, str) or not rule.strip() for rule in rules):
        raise ValueError("story.json: rules must be a list of nonempty strings")
    return result


def _registered_root(workspace: Path, slug: str) -> Path:
    slug = validate_slug(slug)
    stories = (workspace / "stories").resolve()
    target = (stories / slug).resolve()
    if stories == workspace or not stories.is_relative_to(workspace) or not target.is_relative_to(stories):
        raise ValueError("Selected story path escapes workspace/stories")
    config = target / "story.json"
    if not config.is_file():
        raise ValueError(f"No configured story '{slug}' under {workspace / 'stories'}")
    if load_config(target)["slug"] != slug:
        raise ValueError(f"Selected story '{slug}' does not match story.json slug")
    return target


def resolve_root(root: Path, story: str | None = None) -> Path:
    """Select one story, never merge datasets or fall back after an invalid selection."""
    root = Path(root).resolve()
    if story is not None:
        return _registered_root(root, story)
    config = root / "story.json"
    if config.exists() or config.is_symlink():
        load_config(root)
        return root
    studio = root / "studio.json"
    if studio.exists() or studio.is_symlink():
        value = _object(studio, root)
        if set(value) != {"schema_version", "default_story"}:
            raise ValueError("studio.json: expected schema_version and default_story only")
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise ValueError("studio.json: unsupported schema_version (expected 1)")
        return _registered_root(root, value["default_story"])
    if (root / "data").is_dir():
        return root
    raise ValueError(f"No story selected at {root}; use --story or pass a story root")


def story_path(root: Path, relative: str) -> Path:
    """Resolve a story-relative resource without following a path into another story."""
    if (not isinstance(relative, str) or not relative.strip()
            or Path(relative).is_absolute() or PureWindowsPath(relative).drive):
        raise ValueError("Story resource path must be a nonempty relative path")
    base = Path(root).resolve()
    target = (base / relative.replace("\\", "/")).resolve()
    if target == base or not target.is_relative_to(base):
        raise ValueError(f"Story resource path escapes selected story: {relative}")
    return target
