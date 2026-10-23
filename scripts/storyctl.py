#!/usr/bin/env python3
"""Generic story workspace commands; creates metadata, never narrative prose."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

try:
    from scripts import novelctl, story_config, story_engine, doctor, review_bundle, provenance, rollup, world_history, world_consistency
except ImportError:  # called as `python scripts/storyctl.py`
    import novelctl
    import story_config
    import story_engine
    import doctor
    import review_bundle
    import provenance
    import rollup
    import world_history
    import world_consistency


def new_story(workspace: Path, slug: str, title: str | None = None) -> Path:
    """Build an empty scaffold, reserving the destination without overwriting it."""
    slug = story_config.validate_slug(slug)
    title = slug if title is None else title
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Story title must be a nonempty string")
    workspace = Path(workspace).resolve()
    if not workspace.is_dir():
        raise ValueError("Workspace must be an existing directory")
    stories = (workspace / "stories").resolve()
    if stories == workspace or not stories.is_relative_to(workspace):
        raise ValueError("Story directory escapes workspace")
    target = stories / slug
    if target.exists() or target.is_symlink():
        raise ValueError(f"Story already exists: {target}")
    config = {
        "schema_version": 1, "slug": slug, "title": title.strip(),
        "extensions": {"gameplay": False}, "rules": [],
    }
    data = {kind: {"schema_version": 1, kind: []} for kind in novelctl.CORE_DATA}
    data["canon"] = {"schema_version": 1, "project": title.strip(), "facts": []}
    data["inventory_ledger"] = {"schema_version": 1, "entries": []}
    data["story_state"] = {
        "schema_version": 1, "approved_through_scene": None, "active_episode": None,
        "phase": "OUTLINE_NOT_CANON_PROSE", "flags": {}, "pending_review": [],
    }
    stories.mkdir(exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{slug}-", dir=stories))
    reserved = False
    try:
        def write_json(path, value):
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        (staging / "data").mkdir()
        for kind, value in data.items():
            write_json(staging / "data" / f"{kind}.json", value)
        write_json(staging / "story.json", config)
        for directory in ("scenes", "drafts", "ledger/episodes", "ledger/chapters", "ledger/books"):
            path = staging / directory
            path.mkdir(parents=True)
            (path / ".gitkeep").write_text("", encoding="utf-8")
        write_json(staging / "ledger/index.json", {
            "schema_version": 1, "episodes": [], "chapters": [], "books": [],
        })
        (staging / "bible").mkdir()
        (staging / "bible/STYLE_GUIDE.md").write_text(
            "# Writing style contract\n\nHuman style decisions: UNKNOWN.\n"
            "Record approved style requirements here before narrative work.\n"
            "Do not infer story facts from this scaffold.\n", encoding="utf-8")
        (staging / "AGENTS.md").write_text(
            "# Story operating contract\n\n"
            "This scaffold contains no narrative, scene plan, approved facts, or approval provenance.\n"
            "Read story.json and this story's registries before working. Keep all reads and writes in this story root.\n"
            "LOCKED human decisions outrank proposals. UNKNOWN is not verified.\n"
            "Drafts and planned effects do not become approved state without human review.\n"
            "Use the workspace storyctl check and pack commands with this story selected.\n"
            "Read the repository docs/AGENT_RUNBOOK.md for writer, reviewer, and updater contracts.\n"
            "Review bundles are private local artifacts; never publish them without explicit authorization.\n"
            "Never invent review provenance, approve canon, or merge automatically.\n", encoding="utf-8")
        # Validate before exposing the destination. No default story is changed.
        story_config.load_config(staging)
        target.mkdir()  # Exclusive reservation also protects an existing empty directory.
        reserved = True
        for child in staging.iterdir():
            child.rename(target / child.name)
        return target
    except Exception:
        if reserved:
            # Only the newly reserved destination belongs to this operation.
            if target.parent.resolve() == stories and target.resolve().is_relative_to(stories):
                shutil.rmtree(target)
        raise
    finally:
        if staging.parent.resolve() == stories and staging.name.startswith(f".{slug}-"):
            shutil.rmtree(staging)


def _emit_private_artifact(workspace: Path, out: Path | None, output: str) -> None:
    """Keep new review/diagnostic artifacts separate from all story sources."""
    if out is None:
        print(output)
        return
    workspace = Path(workspace).resolve()
    local = workspace / '.local'
    if local.resolve() != local:
        raise ValueError('Private artifact directory .local must not be a symlink')
    destination = out.resolve()
    if destination == local or not destination.is_relative_to(local):
        raise ValueError('Private artifact --out must be inside --workspace/.local/; source files are read-only')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.artifact-', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(output.encode('utf-8'))
        # Replacing the directory entry also preserves any source file that an
        # existing artifact happened to hardlink, unlike truncating that inode.
        os.replace(temporary, destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    print('Wrote private local artifact:', out)


def _offline_evidence(path: Path) -> tuple[dict, dict]:
    """Load bounded untrusted evidence; its digest never authenticates it."""
    with path.open('rb') as handle:
        raw = handle.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('Offline evidence exceeds the 8 MiB limit')

    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate evidence keys')
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError('Non-finite evidence value')

    try:
        evidence = json.loads(raw.decode('utf-8'), object_pairs_hook=object_pairs, parse_constant=nonfinite)
        if not isinstance(evidence, dict):
            raise ValueError('Evidence must be an object')
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ValueError('Offline evidence must be a UTF-8 JSON object with unique keys and finite values') from exc
    return evidence, {'sha256': hashlib.sha256(raw).hexdigest(), 'byte_length': len(raw),
                      'authenticity': 'UNVERIFIED_OFFLINE_INPUT'}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generic story engine workspace (JSON Schema validation)")
    parser.add_argument("--workspace", type=Path, default=story_config.WORKSPACE_ROOT)
    parser.add_argument("--story", help="Explicit story slug; otherwise use studio.json default_story")
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new", help="Create empty metadata; never write a story")
    new.add_argument("slug")
    new.add_argument("--title")
    commands.add_parser("check")
    commands.add_parser("status")
    memory = commands.add_parser("memory", help="Read-only, source-pinned author-accepted recaps; not a GitHub PR approval")
    memory.add_argument("--before", help="Show only accepted episodes strictly before this episode or scene")
    memory.add_argument("--recent", type=int, default=7)
    memory.add_argument("--out", type=Path)
    diagnose = commands.add_parser('doctor', help='Read-only local diagnostics; GitHub settings remain UNKNOWN')
    diagnose.add_argument('--target', help='Optional scene/episode for state availability')
    diagnose.add_argument('--out', type=Path)
    review = commands.add_parser('brief-review', help='Local exact draft/diff/context bundle; never approves or publishes')
    review.add_argument('target', help='Scene ID to review')
    review.add_argument('--base', default='HEAD', help='Local Git commit/ref for the draft comparison (default HEAD)')
    review.add_argument('--out', type=Path)
    verify = commands.add_parser('verify-provenance', help='Read-only GitHub metadata/hash check using existing gh authentication; offline evidence stays unverified')
    verify.add_argument('--repo', '--repository', dest='repository', required=True)
    verify.add_argument('--pr', dest='pr_number', type=int, required=True)
    verify.add_argument('--head', dest='head_commit', required=True)
    verify.add_argument('--merge', dest='merge_commit', required=True)
    verify.add_argument('--source', dest='source_path')
    verify.add_argument('--sha256', dest='source_sha256')
    verify.add_argument('--evidence', type=Path, help='Offline fixture/cache JSON; never live verification (exit 2 if consistent)')
    verify.add_argument('--out', type=Path)
    assembly = commands.add_parser('rollup', help='Deterministic recap assembly proposal; never approves or changes canon')
    assembly.add_argument('episode_ids', nargs='+')
    assembly.add_argument('--repo', '--repository', dest='repository')
    assembly.add_argument('--verify-remote', action='store_true', help='Require fresh read-only GitHub metadata and immutable source-hash checks')
    assembly.add_argument('--out', type=Path)
    replay = commands.add_parser("replay", help="State before target from local evidence; no GitHub approval authentication")
    replay.add_argument("target")
    replay.add_argument("--out", type=Path)
    world = commands.add_parser('world-preview', help='Read-only proposed world state at an explicit world cursor; never applies canon')
    world.add_argument('--clock', required=True, help='Explicit world clock ID; no narrative-order inference')
    world.add_argument('--tick', type=int, required=True)
    world.add_argument('--suborder', type=int, default=0)
    world.add_argument('--boundary', choices=('BEFORE', 'AFTER'), default='BEFORE')
    world.add_argument('--out', type=Path)
    lint = commands.add_parser('lintstate', help='Read-only opt-in world precondition diagnostics; UNKNOWN is not PASS')
    lint.add_argument('--clock', required=True, help='Explicit world clock ID; no narrative-order inference')
    lint.add_argument('--tick', type=int, required=True)
    lint.add_argument('--suborder', type=int, default=0)
    lint.add_argument('--boundary', choices=('BEFORE', 'AFTER'), default='BEFORE')
    lint.add_argument('--out', type=Path)
    pack = commands.add_parser("pack")
    pack.add_argument("target")
    pack.add_argument("--recent", type=int, default=7)
    pack.add_argument("--max-chars", type=int, default=25000)
    pack.add_argument("--out", type=Path)
    brief = commands.add_parser("brief")
    brief.add_argument("target")
    brief.add_argument("--out", type=Path)
    proposal = commands.add_parser("proposal", aliases=['propose'])
    proposal.add_argument("episode")
    proposal.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "new":
            if args.story is not None:
                raise ValueError("Use new SLUG without --story")
            print("Created empty story scaffold:", new_story(args.workspace, args.slug, args.title))
            return 0
        if args.command == 'verify-provenance':
            if args.story is not None:
                raise ValueError('verify-provenance uses explicit repository/PR/source identifiers without --story; use rollup for story-bound checks')
            evidence, fingerprint = None, None
            if args.evidence is not None:
                if args.out is not None and args.out.resolve() == args.evidence.resolve():
                    raise ValueError('Provenance output cannot replace its evidence input')
                evidence, fingerprint = _offline_evidence(args.evidence)
            report = provenance.verify(args.repository, args.pr_number, args.head_commit, args.merge_commit,
                                       source_path=args.source_path, source_sha256=args.source_sha256,
                                       offline_evidence=evidence)
            if fingerprint is not None:
                report['offline_input'] = fingerprint
            _emit_private_artifact(args.workspace, args.out, json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            if report['errors']:
                return 1
            return 0 if report['status'] == 'OBSERVED_MERGED_METADATA' else 2
        if args.command == 'doctor':
            report = doctor.diagnose(args.workspace, args.target, story=args.story)
            output = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
            _emit_private_artifact(args.workspace, args.out, output)
            return 1 if report['errors'] else 0
        root = story_config.resolve_root(args.workspace, args.story)
        if args.command == 'lintstate':
            cutoff = {'clock_id': args.clock, 'tick': args.tick,
                      'suborder': args.suborder, 'boundary': args.boundary}
            report = world_consistency.build(root, cutoff)
            _emit_private_artifact(args.workspace, args.out, json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            return {'PASS': 0, 'CONTRADICTION': 1, 'INVALID': 1,
                    'UNKNOWN': 2, 'DISABLED': 2, 'NO_CHECKS': 2}[report['status']]
        if args.command == 'world-preview':
            cutoff = {'clock_id': args.clock, 'tick': args.tick,
                      'suborder': args.suborder, 'boundary': args.boundary}
            report = world_history.preview(root, cutoff)
            _emit_private_artifact(args.workspace, args.out, json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            return {'AVAILABLE': 0, 'UNKNOWN': 2, 'INVALID': 1}[report['availability']]
        if args.command == 'rollup':
            report = rollup.build(root, args.episode_ids, args.repository, args.verify_remote)
            _emit_private_artifact(args.workspace, args.out, json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            return 0
        if args.command == 'brief-review':
            output = json.dumps(review_bundle.build(root, args.target, args.base), ensure_ascii=False, indent=2) + '\n'
            _emit_private_artifact(args.workspace, args.out, output)
            return 0
        if args.command == "check":
            errors, warnings = story_engine.validate(root)
            for warning in warnings:
                print("WARN:", warning)
            for error in errors:
                print("ERROR:", error)
            print(f"{'PASS' if not errors else 'FAIL'} | {len(errors)} errors; {len(warnings)} warnings")
            return 1 if errors else 0
        if args.command == "status":
            print(novelctl.status(root))
            return 0
        if args.command == "memory":
            if not 0 <= args.recent <= 20:
                raise ValueError("--recent must be 0..20")
            errors, _ = story_engine.validate(root)
            if errors:
                raise ValueError("Story validation failed: " + "; ".join(errors[:5]))
            output = story_engine.author_memory.render(root, before=args.before, recent=args.recent)
            if not output:
                output = "No author-accepted memory is configured for this story.\n"
            _emit_private_artifact(args.workspace, args.out, output)
            return 0
        if args.command == "pack":
            if not 0 <= args.recent <= 20 or args.max_chars < 1000:
                raise ValueError("--recent must be 0..20 and --max-chars >=1000")
            output = story_engine.pack(root, args.target, args.recent, args.max_chars)
        elif args.command == "brief":
            output = novelctl.build_brief(root, args.target)
        elif args.command == "replay":
            output = json.dumps(novelctl.state_before_target(root, args.target), ensure_ascii=False, indent=2) + "\n"
        else:
            output = story_engine.proposal(root, args.episode)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(output, encoding="utf-8")
            print("Wrote:", args.out)
        else:
            print(output)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
