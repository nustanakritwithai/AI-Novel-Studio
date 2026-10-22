# SC-001 — Continuity & Editorial Review Notes

**Target:** stories/last-island/drafts/EP-001/SC-001.md
**Status:** DRAFT / UNREVIEWED / NOT CANON
**POV:** CHAR-001 limited third person
**Context:** stories/last-island/SC-001-WRITER-BRIEF.md, scenes/SC-001.md, scene registry, bible/WORLD.md, STYLE_GUIDE.md
**Scope:** opening scene only; no tutorial progress, resource gathering, construction, combat, or championship

## Continuity table (proposed draft transition)

| Dimension | Before SC-001 | After SC-001 in this DRAFT |
|---|---|---|
| World | REAL, LOC-001 personal room | Began VR session; surroundings of spawn not fixed |
| Knowledge | New to the current play session; mechanics not demonstrated | Knows he can move and perceive the Full-Dive world; sees a beginner-task notice (does not know the tasks yet) |
| Inventory | UNKNOWN | UNKNOWN; no item acquisition described |
| Equipment | No in-game weapon established | No in-game weapon established |
| Health | UNKNOWN | UNKNOWN; no combat or injuries |
| Relationships | UNKNOWN | No new relationship established |
| Buildings / bed | Nothing approved as built | Nothing built |
| Episode flags | No approved flags | logged_in=true in the DRAFT event only; DO NOT update approved story_state |

## Canon alignment

- FACT-001: Full-Dive VR world — respects LOCKED premise.
- FACT-002: opens privately in protagonist's room — respects LOCKED chronology.
- FACT-003: 100-player world competition belongs to later arcs — not introduced.
- Thai protagonist: directly specified by the human author in conversation; not yet present as a separate locked fact in the repository. Proposed registry sync is a distinct editorial task, not an implicit update here.
- Avoided unapproved first name (including 'บอส'), age, occupation, city, precise year, award money and specific device design.

## Proposed / decorative only, not auto-canon

- A generic game-entry prompt and connection notification.
- Ambient light/sounds, hand and body movement during the VR transition.
- An unspecified open area with distant trees at login; exact geography and spawn point remain UNKNOWN.
- Character's short inner dialogue and immediate emotional response.
- A 'ภารกิจเริ่มต้น' notification is a fictional dramatization that transitions into SC-002; content of tutorial is reserved for that next scene.

## Game authenticity

No particular crafting recipe, loot drop, item count, server mode or HP mechanic is asserted. UI text and Full-Dive sensory transition are fictional worldbuilding, not claims about the original mobile game's UI.

## Suggested editorial checks

1. Confirm this is the desired dramatic pace and character voice.
2. Confirm whether the avatar should resemble the proposed character visual or have a different look.
3. After explicit approval, integrate the Thai nationality directive into the character registry for future AI consistency.
4. Do not upgrade this draft, ledger, or story_state to APPROVED or CANON merely because GitHub CI passed.

## Changed files in the draft PR

- drafts/EP-001/SC-001.md — narrative prose DRAFT
- drafts/EP-001/SC-001-REVIEW.md — state delta, proposed facts and uncertainty register
- data/scenes.json — intentionally unchanged (E1 byte-preservation tests pin this example source)
- scenes/SC-001.md — intentionally unchanged (original example Scene Card is SHA-256 pinned)

## E1 baseline preservation / actual draft state
The added prose file is **DRAFT / UNREVIEWED** and exists on this PR branch, but the historical example scene registry continues to say `PLANNED` on purpose. E1 regression tests enforce the original 54 relocated example files as immutable. A separate author-approved migration of the example baseline/manifest would be needed to synchronize the registry field. Do not infer `APPROVED`, `CANON`, or actual playback from the presence of a proposed draft.
