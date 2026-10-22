---
applyTo: "stories/*/drafts/**/*.md,stories/*/scenes/**/*.md"
---

# Story-scoped narrative file rules

Resolve the story root from the file being edited. Read root `AGENTS.md`, that story's `AGENTS.md` and `story.json`, and its configured rules, style, canon, and state. Do not use another story's instructions, characters, mechanics, or history. Use the language, tone, scene structure, and source requirements declared by the selected story.

Work only on the scene and files authorized by the user. Engine-only work does not authorize writing prose. Build context with `python scripts/storyctl.py --story <slug> pack <scene-id>` after the human-authored metadata exists. Respect LOCKED facts and the requested scene's chronological boundary; POV characters cannot use future or unavailable knowledge. Missing history remains UNKNOWN.

List new facts, state changes, and knowledge changes as proposals with their evidence and uncertainty. Gameplay mechanics/sources checks apply only when that story enables the extension. Never invent evidence, reviewer scores, approval provenance, or friction entries. Draft prose, plans, fixture labels, and passing local checks do not establish canon or authenticated human approval.

Use `brief-review` and the writer/reviewer/updater contracts in `docs/AGENT_RUNBOOK.md` for a scoped handoff. Keep bundles containing draft/context text in workspace `.local/` unless the user explicitly authorizes publication. Human approval is required before promoting proposals or updating approved history; the tools do not approve, merge, or roll up changes.
