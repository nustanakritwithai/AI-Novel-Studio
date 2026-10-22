# AI Novel Studio engine operating contract

This repository contains a reusable continuity engine and separate story datasets. Read `ENGINE_E3_E4.md` and `docs/AGENT_RUNBOOK.md` for the current local workflow, `ENGINE_E2.md` for schema/replay, and `ENGINE_E1.md` for story-root compatibility before engine work. Read the selected story's `AGENTS.md`, `story.json`, canon, rules, style, and state before touching its data. Story instructions apply only inside their story root.

- Core code lives in `scripts/`; story data, rules, styles, research, and prose live in `stories/<slug>/`.
- `studio.json` selects the default story for legacy CLI commands. Always pass an explicit story when working across datasets. Never fall back to another story after a missing reference or file.
- LOCKED human decisions take precedence over suggestions. Planned beats, draft prose, and structural validation do not establish approved history. UNKNOWN remains unknown.
- Do not change story content, promote canon, fabricate provenance, approve prose, or merge without the human user's explicit authorization for that action.
- Engine-only tasks must use synthetic metadata fixtures for new scenarios; do not write narrative prose.
- Scope changes to a feature branch. Reuse the existing validators and pack builder; do not add paid APIs, credentials, databases, or unrelated services.
- Use Python 3.11+ and install the pinned schema dependencies first with `python -m pip install --index-url https://pypi.org/simple --only-binary=:all: -r requirements.txt`. E2 is no longer stdlib-only. Schema validation uses the real Draft 2020-12 validator and local schema resources; do not fetch story-supplied remote schemas.
- Local review/Git diagnostics require a Git version supporting the global `--no-lazy-fetch` option. Unsupported Git must fail review or leave Git diagnostics UNKNOWN; do not fetch missing objects, install Git, or change persistent Git settings to hide the limitation.
- Run `python scripts/novelctl.py check`, `python scripts/story_engine.py check`, and `python -m unittest discover -s tests -v`. Verify legacy commands, story selection, replay boundaries, and preservation of example bytes when changing engine behavior.
- Optional state history replays only eligible local evidence strictly before the target. Incomplete explicit history stays UNKNOWN; with no history file, retain the documented legacy snapshot/UNKNOWN path. Never synthesize deltas from planned effects. Local APPROVED labels and fixture evidence are not authenticated GitHub human approval; that verification remains E5 work.
- Scope every writer, reviewer, and updater handoff to one explicit story root, target, and real commit/base anchors. A local review bundle describes the current working draft, which may differ from HEAD; use its draft digest and diff rather than claiming it is committed or reviewed. Machine output is advisory and never promotes canon.
- Keep review bundles and diagnostics local. New `brief-review` and `doctor` file output is restricted to the selected workspace's ignored `.local/` directory. Bundles can contain unpublished prose and full context; do not attach them to a public PR or send them externally without explicit user authorization.
- `brief-review` prepares local evidence, `propose` aliases `proposal`, and `doctor` reports local checks. They do not run a model, authenticate GitHub approval, verify repository settings or CODEOWNERS enforcement, or perform rollup. Preserve UNKNOWN for checks that were not performed.
- Draft PRs must report actual tests, remaining limits, changed files, and exact head/CI. Do not claim a complete engine from one milestone.

The Last Island example retains its original contract under `stories/last-island/AGENTS.md`. Its existing content is preserved; moving files does not approve any narrative or canon changes.
