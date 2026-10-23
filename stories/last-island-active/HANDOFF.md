# HANDOFF — Last Island after author acceptance

**Working story:** `last-island-active`
**Latest author decision:** DEC-004 — "อนุมัติ" in ChatGPT, 2026-10-23.
**Source of accepted text:** merged [PR #13](https://github.com/nustanakritwithai/AI-Novel-Studio/pull/13), source head `3d0b3117b2a4a4029fe815899e5c7a28e69eb56f`, merge commit `5d32a9ff95b3b64953a792be3bd7fef078343a1f`.

## Phase 1 memory workflow

Run `python scripts/storyctl.py --story last-island-active memory` before planning future episodes. This reads the author-accepted **source-bound summaries** of EP-001 and EP-002. For EP-003 continuation context use `pack EP-003`, which includes earlier accepted-source EP-001 and EP-002 recaps but not new EP-003 accepted memory; `memory --before EP-002` intentionally excludes EP-002.

The trusted source is still the source manuscript pinned in `editorial/AUTHOR_APPROVAL_2026-10-23.json` and `author_memory/index.json`. These summaries are locally derived, not independently human-reviewed. They do **not** fill the GitHub-review-approved `ledger/index.json` and do not reconstruct approved `story_state`. Read `docs/AUTHOR_ACCEPTED_MEMORY_TH.md` for these two separate trust levels.

## Read first

1. `AGENTS.md`, `story.json`, `data/canon.json` and `data/characters.json`.
2. `editorial/AUTHOR_APPROVAL_2026-10-23.json` + `data/decisions.json`.
3. `drafts/EP-001/CH-01-FULL-DRAFT.md` and `drafts/EP-002/CH-02-FULL-DRAFT.md`.
4. `data/episodes.json`, `data/scenes.json`, `data/events.json`, `data/inventory_ledger.json`, `data/story_state.json`.
5. `drafts/PROPOSED_CONTINUITY_CH-01_02.json` for a **proposed** cross-chapter recap and `bible/CHARACTER_CONTINUITY_ADDENDUM.md`.
6. `ledger/index.json` only for **verified approved** episode recaps (currently empty).

## Operating rules

- Author has *accepted* both manuscript texts and approved integrating the package into `main`. Do not ask the author to reapprove those exact source blobs.
- The historical engine's accepted-prose status and formally approved ledger are different things: the repository requires evidence from an actual GitHub PR `APPROVE` review before marking the ledger as authenticated. None was observed for PR #13; do not invent a review or `approved_by`.
- Until the formal provenance workflow is completed, episode and scene registry status remains `DRAFT` and `approved_through_scene` remains null. This is a provenance limitation, **not** a denial of the author's consent.
- Do not update chronology, NPC identities, event outcomes, health or inventory counts beyond grounded details.
- EP-003 has author-directed plot DEC-005 and a complete DRAFT manuscript; see `plot/episodes/EP-003.md` and `drafts/EP-003/CH-03-FULL-DRAFT.md`. Do not promote its prose to Canon without editorial approval. EP-004 will begin with the first hunt; no animals or fat have been acquired yet.

## Commands

```bash
python scripts/storyctl.py --story last-island-active check
python scripts/storyctl.py --story last-island-active pack EP-003
python -m unittest discover -s tests -v
```

PR #11 and #12 were closed as superseded; main contains the selected two-chapter manuscripts.

## Next writer handoff — EP-003 to EP-004 (draft)

- EP-003: REAL rest/food/gamer clips → return to stone 2×2 base → road scrap crates/no oil → skilled bow duel → six-shot pistol death → respawn at home, road gear lost → alternative animal-fat oil plan.
- SC-019–SC-026 are DRAFT; DEC-005 confirms author plot but not prose wording; DEC-006 authorizes saving draft to engine.
- Do not reuse CHAR-004/005 as EP-003 foe: CHAR-006 is unverified new identity, and CHAR-007 gamer-chat friend is only PROPOSED.
- Never claim oil, furnace, iron, ammo, meat, hide or fat was gained in EP-003. A dark road crate's contents are UNKNOWN.
- EP-004 begins before the first animal hunt; species/quantity, exact hunting tactics and item yield require author direction. Keep accepted-source memory EP-001/002 untouched.
- `data/story_state.json.approved_through_scene` remains null and `ledger/index.json` remains empty.

## REQUIRED source-bound EP-003 continuity for all future writers

1. Read `drafts/EP-003/CH-03-FULL-DRAFT.md`, then `drafts/EP-003/EP-003-CONTINUITY-AUDIT.md`.
2. Read `data/draft_continuity_ep003.json`: **DRAFT only** source blob sha pinned; it is not a certified state replay.
3. Read `bible/BASE_TIMELINE.md` to avoid silently expanding 2×2 stone base into a full second floor or adding a furnace.
4. Read `research/EP003_GAMEPLAY_GAPS.md` before alleging any external game mechanic is verified.
5. Start with `plot/episodes/EP-004-HANDOFF-PROPOSED.md`; there are **no** EP-004 scenes in registry yet.
6. The enemy fired exactly six pistol rounds in this scene; all 6 are recorded as `INV-029` owned by CHAR-006. Do not transfer a pistol or ammo to protagonist or claim other ammo caches are known.
