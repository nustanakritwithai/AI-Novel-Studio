---
name: "Draft a scene"
about: "Scope a human-authorized scene task within one story"
title: "[SCENE] story-slug / SC-XXX — "
labels: []
assignees: []
---

## Authorized scope

Story slug and root:
Scene / episode IDs:
Allowed files and requested outcome:
Base / HEAD commit anchors:

## Read before work

- [ ] Root `AGENTS.md` and `docs/AGENT_RUNBOOK.md`.
- [ ] Selected story's `AGENTS.md`, `story.json`, configured rules/style, canon, and state.
- [ ] `python scripts/storyctl.py --story <slug> check`.
- [ ] Target-specific `brief` / `pack` after required metadata exists.

## Writer contract

Respect this story's LOCKED facts, style, chronological boundary, and POV knowledge. Do not copy another story's rules or assume missing history. List new facts, state/knowledge changes, evidence, and UNKNOWNs as proposals. Mechanics/source requirements apply only if this story enables that extension. No canon promotion, invented provenance, or automatic approval.

## Deliverable and review handoff

Requested files, all within the selected story root:
Proposed changes and evidence:
Unresolved continuity questions:

Prepare local evidence with `python scripts/storyctl.py --story <slug> brief-review <scene-id> --base <base-ref> --out .local/reviews/scene-review.json`. Record its actual resolved commit anchors and current draft digest; a working draft may differ from HEAD. The bundle is unreviewed evidence and may contain unpublished text: keep it under the selected workspace's ignored `.local/` directory unless the user explicitly authorizes sharing it. A reviewer reports findings; an authorized human decides approval before any updater promotes history.
