# HANDOFF — Last Island after author acceptance

**Working story:** `last-island-active`
**Latest author decision:** DEC-004 — "อนุมัติ" in ChatGPT, 2026-10-23.
**Source of accepted text:** merged [PR #13](https://github.com/nustanakritwithai/AI-Novel-Studio/pull/13), source head `3d0b3117b2a4a4029fe815899e5c7a28e69eb56f`, merge commit `5d32a9ff95b3b64953a792be3bd7fef078343a1f`.

## Phase 1 memory workflow

Run `python scripts/storyctl.py --story last-island-active memory` before planning future episodes. This reads the author-accepted **source-bound summaries** of EP-001 and EP-002. For EP-004 continuation context use `pack EP-004`, which includes only author-accepted source memory for EP-001 and EP-002; EP-003/004 remain DRAFT and are not in the accepted memory index; `memory --before EP-002` intentionally excludes EP-002.

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
- EP-003 has author-directed plot DEC-005 and a complete DRAFT manuscript; see `plot/episodes/EP-003.md` and `drafts/EP-003/CH-03-FULL-DRAFT.md`. Do not promote its prose to Canon without editorial approval. The first hunt has now been written in the EP-004 DRAFT; source is `drafts/EP-004/CH-04-FULL-DRAFT.md`. It has not been separately accepted as prose.

## Commands

```bash
python scripts/storyctl.py --story last-island-active check
python scripts/storyctl.py --story last-island-active pack EP-004
python -m unittest discover -s tests -v
```

PR #11 and #12 were closed as superseded; main contains the selected two-chapter manuscripts.

## Next writer handoff — EP-003 to EP-004 (draft)

- EP-003: REAL rest/food/gamer clips → return to stone 2×2 base → road scrap crates/no oil → skilled bow duel → six-shot pistol death → respawn at home, road gear lost → alternative animal-fat oil plan.
- SC-019–SC-026 are DRAFT; DEC-005 confirms author plot but not prose wording; DEC-006 authorizes saving draft to engine.
- Do not reuse CHAR-004/005 as EP-003 foe: CHAR-006 is unverified new identity, and CHAR-007 gamer-chat friend is only PROPOSED.
- Never claim oil, furnace, iron, ammo, meat, hide or fat was gained in EP-003. A dark road crate's contents are UNKNOWN.
- This instruction describes the **end of EP-003** only. The subsequent EP-004 DRAFT depicts farming, taming a horse, the raid and furnace; exact animal counts and yields remain UNKNOWN. Keep accepted-source memory EP-001/002 untouched.
- `data/story_state.json.approved_through_scene` remains null and `ledger/index.json` remains empty.

## REQUIRED source-bound EP-003 continuity for all future writers

1. Read `drafts/EP-003/CH-03-FULL-DRAFT.md`, then `drafts/EP-003/EP-003-CONTINUITY-AUDIT.md`.
2. Read `data/draft_continuity_ep003.json`: **DRAFT only** source blob sha pinned; it is not a certified state replay.
3. Read `bible/BASE_TIMELINE.md` to avoid silently expanding 2×2 stone base into a full second floor or adding a furnace.
4. Read `research/EP003_GAMEPLAY_GAPS.md` before alleging any external game mechanic is verified.
5. For EP-004, use `plot/episodes/EP-004.md`, scene cards SC-027–038 and `data/draft_continuity_ep004.json`; do **not** use the older pre-draft planning note as the current episode state.
6. The enemy fired exactly six pistol rounds in this scene; all 6 are recorded as `INV-029` owned by CHAR-006. Do not transfer a pistol or ammo to protagonist or claim other ammo caches are known.

## MUST READ — EP-004 to future continuation (DRAFT)

- User plot directive DEC-007; complete but unapproved prose: `drafts/EP-004/CH-04-FULL-DRAFT.md`; 12 scene cards SC-027..038.
- Read `data/draft_continuity_ep004.json`, `data/wildlife_ep004.json`, `plot/episodes/EP-004.md`, `bible/BASE_TIMELINE.md`, `research/EP004_GAMEPLAY_GAPS.md`.
- Horse CHAR-008 was tamed using a hide glove after weakening, brought toward home. No stable yet. Hunting consumes extensive in-game travel time; exact counts/times UNKNOWN.
- Blast at wall/entrance is during hunting while hero online, not proof of intrusion on a prior offline night. Two raiders are CHAR-004/005 from EP-002, **not** CHAR-002 or CHAR-006. Hero hides, does NOT kill them, and repairs after they depart. Exact stolen supplies UNKNOWN.
- Fat→oil and **furnace built** by SC-038. Timed iron and game wood/sulfur gunpowder-material processing is only STARTED; no ready iron/gunpowder/bullets at EP-004 end.
- The house footprint remains 2×2 stone plus upper firing platform. Approval of the new prose has not been received; never auto-apply `data/story_state.json` or the approved ledger.

## Current latest: EP-004 DRAFT

- Author-directed outline DEC-007; complete scene sources SC-027..SC-038 and manuscript `drafts/EP-004/CH-04-FULL-DRAFT.md`.
- Wildlife/taming: `data/wildlife_ep004.json`; horse CHAR-008, no stable built.
- Raiding duo are CHAR-004 and CHAR-005 (EP-002), not the separate pistol foe CHAR-006 (EP-003). No PvP kill in EP-004.
- Blast during active hunting, hero hides behind hill until they leave and repairs the 2×2 stone base entrance. Loot possibly stolen is UNKNOWN.
- End: fat-derived oil produced and furnace built; iron and gunpowder precursor processing has started but finished iron, gunpowder and bullets are NOT ready.
- For future scenes, read `data/draft_continuity_ep004.json`, `bible/BASE_TIMELINE.md`, `plot/episodes/EP-004.md` and `research/EP004_GAMEPLAY_GAPS.md`. Do not invent EP-005 events.
