# SC-002 — Trial Continuity Review / DRAFT

**Story:** last-island | **Episode:** EP-001 บ้านหลังแรก | **Target:** SC-002 บทเรียนแรก
**Candidate prose:** `stories/last-island/drafts/EP-001/SC-002.md`
**Status:** UNREVIEWED / PROPOSED / NOT CANON
**Narrative predecessor:** `SC-001` draft from [PR #11](https://github.com/nustanakritwithai/AI-Novel-Studio/pull/11), file blob SHA `3051f4f0bbe0947ec54613c48055a9d32935be6e` (provisional dependency, not approved)
**Current approved boundary:** `approved_through_scene: null` in `data/story_state.json`. No prior prose is approved.

## Input files actually reviewed

- `stories/last-island/AGENTS.md` and `SC-001-WRITER-BRIEF.md`
- `stories/last-island/scenes/SC-002.md`
- `stories/last-island/plot/episodes/EP-001.md`
- `stories/last-island/bible/STYLE_GUIDE.md`
- `stories/last-island/data/canon.json`, `characters.json`, `mechanics.json`, `items.json`, `inventory_ledger.json`, `scenes.json`, `story_state.json`
- The **unapproved** candidate SC-001 prose from PR #11 for transitional voice and staging, not as approved memory.

## Story contract / canonical beats

- FACT-001: Full-Dive VR futuristic premise.
- FACT-002: private gameplay precedes any global tournament.
- FACT-004: beginner tutorial instructs wood gathering, house building and bed making.
- FACT-005: protagonist plans a **2×2 single-story house**.
- The selected scene begins with the translucent “ภารกิจเริ่มต้น” notice at the end of SC-001.
- The narrative stops before SC-003's discovery of many rookie houses, and before SC-004's map search and baseball-bat crafting.

## Proposed state transition (fiction draft only)

| Dimension | Predecessor candidate SC-001 ending | SC-002 ending in this draft |
|---|---|---|
| Realm | VR, unspecified starter area (LOC-002) | VR, same broad starting area (LOC-002) |
| Character | CHAR-001, unnamed Thai protagonist | Same single limited-POV protagonist |
| Knowledge | Saw beginner-task notification; does not know objectives yet | Learns tutorial asks for wood, shelter and bed; forms 2×2 single-floor design |
| Inventory | No approved quantity or equipment evidence | Gains wood, **quantity UNKNOWN**; no bat, firearms, loot crate, or bed |
| Buildings | No construction yet | House **planned**, not placed or built |
| Health / injuries | UNKNOWN | UNKNOWN; no violence |
| Relationships | No newly confirmed relationships | None; distant repeated sound is unidentified |
| Flags | No approved flags | PROPOSED effects: tutorial_received=true, wood_gathered=true, base_plan_2x2=true; do not apply to canonical state |

## Gameplay evidence and uncertainty

- `MECH-001` wood gathering/crafting is `TRANSCRIPT_SUPPORTED` by `SRC-001`, *not* visually verified or universal for all server modes.
- `MECH-005` bed tutorial requirement is `UNVERIFIED` gameplay but LOCKED by author as a fiction beat. The draft does not imply that the bed has been built or that respawn mechanics are proven.
- The translucent tutorial window, cutting feedback, prompted gathering method, user-interface inventory depiction, tactile wood and distant rhythmic sounds are **FICTIONAL STAGING / PROPOSED** rather than claims about authentic mobile UI.
- Tool type, exact harvesting recipe, wood stack quantity, XP, health, starter biome and base construction cost are intentionally unspecified.
- No exact visual identity or permanent personal name, age, job, city, date, or server name is invented.
- Protagonist being Thai comes from a user directive; visual features from generated character sheets are not silently canonized.

## Dependency and editorial blockers

1. **PR #11 is not yet approved.** This scene is a continuation candidate based on its ending. Changes to SC-001 may require revising the entrance and sensory descriptions in this draft.
2. Historic E1 sample is hash-pinned. `stories/last-island/data/scenes.json`, `scenes/SC-002.md`, `data/story_state.json`, `ledger/index.json` and the frozen example files stay byte-identical; this PR **only adds two new draft files**.
3. The SC-002 scene registry therefore stays `PLANNED` by baseline design even though a candidate draft file exists. Treat the candidate as external editorial material until explicit migration/approval.
4. Human review required for style, pacing, facts and approval. CI success is structural, not literary approval.

## Review prompts for human editor

- Is the timber harvesting passage sufficiently grounded in your actual Last Island play without forcing an unverified tool/recipe?
- Is the protagonist's 2×2 single-story choice clear and reasonably motivated?
- Does the final sound cue lead naturally into SC-003 without revealing rookie houses too early?
- Are the voice and pacing consistent with the SC-001 candidate?
