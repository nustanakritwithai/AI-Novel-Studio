#!/usr/bin/env python3
"""GitHub-only Story Engine v0.2: approved ledgers, scoped packs, proposals.

Works with the existing novelctl.py registries. Never calls AI, database or web.
This program NEVER marks material approved, updates canon, or pushes to GitHub.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from scripts import novelctl, author_memory
except ImportError:  # called as `python scripts/story_engine.py`
    import novelctl
    import author_memory

ROOT = Path(__file__).resolve().parent.parent
SHA40 = re.compile(r"^[0-9a-fA-F]{40}$")
APPROVED = {"APPROVED", "CANON"}


def load_index(root: Path, validate_schema: bool = True) -> dict:
    root = novelctl.story_config.resolve_root(root)
    result = novelctl.registry_schema.read_json(novelctl.story_config.story_path(root, "ledger/index.json"))
    if validate_schema:
        novelctl.registry_schema.ensure_valid('ledger', result)
    return result


def within(root: Path, relpath: str, prefix: str) -> Path:
    """Require a relative path inside a specific repository directory."""
    root = novelctl.story_config.resolve_root(root)
    if not isinstance(relpath, str) or not relpath or Path(relpath).is_absolute():
        raise ValueError("invalid ledger path")
    base = (root / prefix).resolve()
    target = (root / relpath).resolve()
    if not base.is_relative_to(root) or not target.is_relative_to(base) or target.suffix != ".md":
        raise ValueError(f"ledger path outside {prefix}: {relpath}")
    return target


def approved_prose(root: Path, scene: dict) -> str:
    """Read the source evidence for an approved scene, or fail explicitly."""
    try:
        path = within(root, scene.get("draft_path"), "drafts")
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            raise ValueError("source prose is blank")
        return content
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError(f"{scene['id']}: cannot read approved source prose ({exc})") from exc


def validate(root: Path) -> tuple[list[str], list[str]]:
    # The manual workflow and pack command must enforce the same base checks as CI.
    errors, warnings = novelctl.validate(root)
    if errors:
        return ["Base registry invalid: " + error for error in errors], warnings
    try:
        root = novelctl.story_config.resolve_root(root)
        idx, db = load_index(root, validate_schema=False), novelctl.load(root)
        errors.extend(novelctl.registry_schema.validate('ledger', idx))
    except (OSError, ValueError, KeyError) as exc:
        return [f"Unable to load story engine index or registry: {exc}"], warnings
    if not isinstance(idx, dict):
        return ["ledger/index.json: index must be an object"], warnings
    if type(idx.get("schema_version")) is not int or idx.get("schema_version") != 1:
        errors.append("ledger/index.json: unsupported schema_version")
    eps = novelctl.rows(db, "episodes")
    episode_ids = [e["id"] for e in eps]
    by_ep = {e["id"]: e for e in eps}
    by_scene = {s["id"]: s for s in novelctl.rows(db, "scenes")}
    for scene in by_scene.values():
        if scene.get("status") in APPROVED:
            try:
                approved_prose(root, scene)
            except ValueError as exc:
                errors.append(str(exc))
    approval_ids = set()
    for layer in ("episodes", "chapters", "books"):
        records = idx.get(layer)
        if not isinstance(records, list):
            errors.append(f"ledger/index.json: {layer} must be a list")
            continue
        used = set()
        for record in records:
            if not isinstance(record, dict):
                errors.append(f"{layer}: record must be an object")
                continue
            rid = record.get("id")
            if not isinstance(rid, str) or not rid:
                errors.append(f"{layer}: missing id")
                continue
            if rid in used:
                errors.append(f"{layer}: duplicate {rid}")
            used.add(rid)
            approval_ids.add((layer, rid))
            if layer == "episodes":
                if rid not in by_ep:
                    errors.append(f"{rid}: unknown episode")
                elif not by_ep[rid].get("scene_ids"):
                    errors.append(f"{rid}: approved episode has no source scenes")
                elif by_ep[rid].get("status") not in APPROVED:
                    errors.append(f"{rid}: ledger cannot include an unapproved episode")
                elif any(by_scene[s].get("status") not in APPROVED for s in by_ep[rid].get("scene_ids", [])):
                    errors.append(f"{rid}: not all scenes are approved")
                if record.get("scene_ids") != by_ep.get(rid, {}).get("scene_ids"):
                    errors.append(f"{rid}: approved scene list mismatch")
            else:
                component = record.get("episode_ids")
                if not isinstance(component, list) or not component:
                    errors.append(f"{rid}: episode_ids must be nonempty")
                elif any(not isinstance(e, str) or not e for e in component):
                    errors.append(f"{rid}: episode_ids must contain nonempty strings")
                elif len(set(component)) != len(component):
                    errors.append(f"{rid}: duplicate episode_ids")
                elif any(e not in by_ep for e in component):
                    errors.append(f"{rid}: unknown episode in rollup")
                elif any(("episodes", e) not in approval_ids for e in component):
                    errors.append(f"{rid}: rollup contains an episode not in approved ledger")
            approval = record.get("approval")
            if not isinstance(approval, dict) or not isinstance(approval.get("pr_number"), int) or isinstance(approval.get("pr_number"), bool) or approval["pr_number"] <= 0:
                errors.append(f"{rid}: missing human approval PR number")
            elif not isinstance(approval.get("approved_by"), str) or not approval["approved_by"].strip():
                errors.append(f"{rid}: missing reviewer identity")
            elif not isinstance(approval.get("merge_commit"), str) or not SHA40.fullmatch(approval["merge_commit"]):
                errors.append(f"{rid}: missing/invalid merged commit SHA")
            elif not isinstance(approval.get("approved_at"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*", approval["approved_at"]):
                errors.append(f"{rid}: missing approved_at ISO timestamp")
            path = record.get("summary_path")
            try:
                file_path = within(root, path, f"ledger/{layer}")
                content = file_path.read_text(encoding="utf-8").strip()
                if not content or "TODO" in content or "PLACEHOLDER" in content:
                    errors.append(f"{rid}: approved summary is blank or has placeholder")
                if content and len(content) < 100:
                    warnings.append(f"{rid}: summary may be too short; human editorial review required")
            except (OSError, ValueError, TypeError) as exc:
                errors.append(f"{rid}: cannot read approved summary ({exc})")
    if not all(isinstance(idx.get(k), list) for k in ("episodes", "chapters", "books")):
        return errors, warnings
    approved_ids = [r["id"] for r in idx.get("episodes", []) if isinstance(r, dict)
                    and isinstance(r.get("id"), str) and r["id"]]
    if approved_ids != sorted(approved_ids, key=lambda v: episode_ids.index(v) if v in episode_ids else len(episode_ids)):
        errors.append("approved episode ledger must follow series order")
    if approved_ids and approved_ids != episode_ids[:len(approved_ids)]:
        errors.append("approved episodes must be contiguous from the beginning")
    if approved_ids and all(rid in by_ep and by_ep[rid].get("scene_ids") for rid in approved_ids):
        last_approved = by_ep[approved_ids[-1]]["scene_ids"][-1]
        marker = db["story_state"].get("approved_through_scene")
        if marker is None:
            errors.append(f"story_state: approved_through_scene missing after approved {last_approved}")
        elif marker not in {s["id"] for s in novelctl.rows(db, "scenes") if s["id"] == last_approved or (s["episode_id"] in episode_ids[episode_ids.index(approved_ids[-1])+1:] and s["status"] in APPROVED)}:
            errors.append("story_state: approved_through_scene precedes latest approved episode")
        if db["story_state"].get("phase", "").startswith("OUTLINE"):
            errors.append("story_state phase cannot remain OUTLINE after full episode approval")
    if not approved_ids and db["story_state"].get("approved_through_scene"):
        warnings.append("An approved scene exists, but no fully approved episode ledger yet")
    errors.extend(author_memory.validate(root, db))
    return errors, warnings


def render_approved_history(root: Path, target: str, keep: int = 7) -> str:
    """Only summaries approved before the target, never future spoilers or drafts."""
    idx, db = load_index(root), novelctl.load(root)
    sequence = [e["id"] for e in novelctl.rows(db, "episodes")]
    scene = novelctl.get(db, "scenes", target)
    ep_id = scene["episode_id"] if scene else target
    if ep_id not in sequence:
        raise ValueError(f"unknown target: {target}")
    previous = set(sequence[:sequence.index(ep_id)])
    entries = [x for x in idx.get("episodes", []) if x["id"] in previous]
    entries = entries[-keep:] if keep else []
    output = ["## APPROVED EPISODE LEDGER (RECENT ONLY)"]
    for item in entries:
        src = within(root, item["summary_path"], "ledger/episodes")
        output.extend([f"### {item['id']} — {src.name}", src.read_text(encoding="utf-8")])
    if not entries:
        output.append("No earlier approved episodes. Planned beats are not canon prose.")
    for layer in ("books", "chapters"):
        records = [r for r in idx.get(layer, []) if set(r.get("episode_ids", [])) <= previous]
        if records:
            output.append(f"## APPROVED {layer.upper()} ROLLUPS")
            for r in records:
                src = within(root, r["summary_path"], f"ledger/{layer}")
                output.extend([f"### {r['id']}", src.read_text(encoding="utf-8")])
    return "\n\n".join(output)


def approved_scene_tail(root: Path, target: str, max_scenes: int = 2, max_each: int = 2400) -> str:
    """Attach approved immediately preceding prose, not future scene text."""
    db = novelctl.load(root)
    scene = novelctl.get(db, "scenes", target)
    if scene is None:
        return "## PRIOR APPROVED SCENE EXCERPTS\nNone (episode pack or unknown scene)."
    earlier = sorted((s for s in novelctl.rows(db, "scenes")
                      if s["episode_id"] == scene["episode_id"]
                      and s["order"] < scene["order"]
                      and s["status"] in APPROVED), key=lambda s: s["order"])
    parts = ["## PRIOR APPROVED SCENE EXCERPTS (SAME EPISODE)"]
    for s in earlier[-max_scenes:]:
        content = approved_prose(root, s)
        parts.append(f"### {s['id']}\n" + content[-max_each:])
    if not earlier:
        parts.append("No previously approved scenes in this episode.")
    return "\n\n".join(parts)


def pack(root: Path, target: str, keep: int = 7, max_chars: int = 25000) -> str:
    errors, _ = validate(root)
    if errors:
        raise ValueError("Story Engine validation failed: " + "; ".join(errors[:5]))
    root = novelctl.story_config.resolve_root(root)
    base = novelctl.build_brief(root, target)
    style = novelctl.story_config.story_path(root, "bible/STYLE_GUIDE.md").read_text(encoding="utf-8")
    recent = render_approved_history(root, target, keep)
    author_accepted = author_memory.render_before(root, target, keep, novelctl.load(root))
    content = (
        "# STORY ENGINE / SELECTED-STORY LOCAL CONTEXT PACK\n"
        f"Target: {target} | Max approved recent episodes: {keep}\n"
        "INPUT BASIS: Selected-story local registries and source records. Approval labels are local declarations; "
        "GitHub main and human approval have not been authenticated. Drafts and proposals do not establish canon.\n"
        "Do not use information from future episodes. Do not silently update canon.\n\n"
        + "## REQUIRED WRITING STYLE\n" + style + "\n\n"
        + recent + "\n\n" + (author_accepted + "\n\n" if author_accepted else "") + approved_scene_tail(root, target) + "\n\n" + base
    )
    if len(content) > max_chars:
        raise ValueError(f"Context size {len(content)} chars exceeds cap {max_chars}. Narrow target/keep; never silently truncate LOCKED canon.")
    return content


def proposal(root: Path, ep_id: str) -> str:
    """Produce an unapproved editorial worksheet; never touches canon."""
    db = novelctl.load(root)
    ep = novelctl.get(db, "episodes", ep_id)
    if ep is None:
        raise ValueError(f"Unknown episode: {ep_id}")
    if ep_id in {x["id"] for x in load_index(root).get("episodes", [])}:
        raise ValueError("Episode already exists in approved ledger")
    return "\n".join([
        f"# {ep_id} — CONTINUITY PROPOSAL (NOT CANON)",
        "Status: PROPOSED — human approval required; never merge automatically.",
        f"Title: {ep['title']}",
        f"Scene IDs: {', '.join(ep['scene_ids'])}",
        "", "## Episode summary (human editorial review required)",
        "[เขียนหลังอ่านฉบับร่างทั้งหมด ห้ามคาดเดาจาก outline]", "",
        "## Character knowledge & relationships changed", "[source scene IDs, before → after]", "",
        "## Inventory and physical state deltas", "[scene ID, amount or UNKNOWN]", "",
        "## Plot threads opened / resolved", "[thread ID, setup or payoff scene]", "",
        "## Proposed canon facts (NOT LOCKED)", "[fact IDs, evidence, approval requirement]", "",
        "## Continuity and style checker findings", "[errors, warnings, unknowns]", "",
        "## Human approval evidence (only after real PR review)",
        "[PR number, human reviewer, merge commit, timestamp]",
    ]) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Story Engine v0.2 — GitHub only, no external database")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--story", help="Story slug under --root/stories (otherwise use workspace default)")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("check")
    context = subs.add_parser("pack")
    context.add_argument("target")
    context.add_argument("--recent", type=int, default=7)
    context.add_argument("--max-chars", type=int, default=25000)
    context.add_argument("--out", type=Path)
    draft = subs.add_parser("proposal")
    draft.add_argument("episode")
    draft.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        root = novelctl.story_config.resolve_root(args.root, args.story)
        if args.command == "check":
            errors, warnings = validate(root)
            for w in warnings:
                print("WARN:", w)
            for e in errors:
                print("ERROR:", e)
            print(f"{'PASS' if not errors else 'FAIL'} | {len(errors)} errors; {len(warnings)} warnings")
            return 1 if errors else 0
        if args.command == "pack":
            if args.recent < 0 or args.recent > 20 or args.max_chars < 1000:
                raise ValueError("--recent must be 0..20 and --max-chars >=1000")
            output = pack(root, args.target, args.recent, args.max_chars)
        else:
            output = proposal(root, args.episode)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(output, encoding="utf-8")
            print("Wrote:", args.out)
        else:
            print(output)
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
