# HANDOFF — Last Island after author acceptance

**Working story:** `last-island-active`
**Latest author decision:** DEC-004 — "อนุมัติ" in ChatGPT, 2026-10-23.
**Source of accepted text:** merged [PR #13](https://github.com/nustanakritwithai/AI-Novel-Studio/pull/13), source head `3d0b3117b2a4a4029fe815899e5c7a28e69eb56f`, merge commit `5d32a9ff95b3b64953a792be3bd7fef078343a1f`.

## Phase 1 memory workflow

Run `python scripts/storyctl.py --story last-island-active memory` before planning future episodes. This reads the author-accepted **source-bound summaries** of EP-001 and EP-002. For EP-007 continuation context use `pack EP-007`, which includes only author-accepted source memory for EP-001 and EP-002; EP-003/004 remain DRAFT and are not in the accepted memory index; `memory --before EP-002` intentionally excludes EP-002.

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
python scripts/storyctl.py --story last-island-active pack EP-007
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
- For future scenes, read `data/draft_continuity_ep004.json`, `bible/BASE_TIMELINE.md`, `plot/episodes/EP-004.md` and `research/EP004_GAMEPLAY_GAPS.md`. EP-005 events now exist in the author-accepted-for-ingest working manuscript; refer to the newer EP-005 handoff below.

## CURRENT handoff — EP-005 → potential EP-006 (accepted for ingest in chat)

- Start with `drafts/EP-005/CH-05-FULL-DRAFT.md`, `data/draft_continuity_ep005.json`, `plot/episodes/EP-005.md`, scene cards SC-039–047 and `data/decisions.json` DEC-008/009.
- CHAR-004/005 returned after EP004, clashed near stone house. Two opponents defeated once, then both returned to the forest edge and withdrew following exactly ONE warning round from the upper platform; no additional fatal encounter during the second visit.
- First pistol is recovered mid-scene from the first defeated rival, second pistol is recovered after the second is defeated: **two pistols in total**. He observed **100 ammunition rounds on looting** and spent one more warning round; the final balance must remain UNKNOWN because loaded/loose ammunition is not specified.
- A basic leather set was looted but the quantity of pieces isn't defined. Neither raider's hammer/pistol role is individually assigned to CHAR-004 vs CHAR-005; their motive is only protagonist suspicion.
- End: hero alive at the existing 2×2 stone base's open upper firing platform, furnace still running and no completed iron/gunpowder/bullets collected; horse's condition not shown. No fortified layers or stable have been built.
- The thought of hardening the base is a **future motivation**, not an already completed construction step. The next EP-006 plot has now been drafted separately; see the newer handoff below.
- DEC-009 records the author's chat acceptance and explicit request to ingest. It is **not** a substitute for authenticated GitHub `APPROVE` reviewer evidence, so do not edit the approved ledger, replay state or source memory index without their separate gates.

## CURRENT handoff — EP-006 → future episode (DRAFT)

- EP-006 has user-directed plot DEC-010 and assistant-written complete DRAFT `drafts/EP-006/CH-06-FULL-DRAFT.md`. Consult `data/draft_continuity_ep006.json`, `plot/episodes/EP-006.md` and `research/EP006_GAMEPLAY_GAPS.md` before writing anything later.
- Horse CHAR-008 was alive again and ridden at SC-048; subsequently **killed in SC-055** by one of the new armed motorcycle riders. Do not resurrect it or provide replacement silently.
- CHAR-009 is the bat ambusher on EP-006 road; matching with EP-001 ambusher CHAR-002 is UNKNOWN. At the refinery, CHAR-010/011/012 are three NEW unidentified armed riders with **three motorcycles and light machine guns**; they are not proven to be the earlier two-person rivals from EP-002/005.
- Hero looted one green keycard ITEM-034 (UNUSED), some ready oil ITEM-014 (exact amount UNKNOWN), a crude barrel ITEM-035. Crude barrel was inserted into the refinery ITEM-036 and processing **STARTED but hero withdrew without finished output**. Other group is *heard saying* they will collect oil; whether they did remains UNKNOWN.
- Zombies CHAR-013 are aggregated NPC population, number and respawn unverified. Hero cleared observed area but did not prove entire region permanently safe. Ammo spent on zombies and bat ambush UNKNOWN; pistols from EP-005 still two, no extra pistol, automatic weapon or motorcycle gained.
- Hero retreated outside refinery and reached original 2×2 stone house **ON FOOT**. His suspicion that the crew controls the refinery or has a large fuel supply is **INFERENCE**, not established ownership.
- No current proof of furnace finished iron/gunpowder or completed newer base upgrades; no EP-007 plot is yet written/approved. Author-directed plot is not equivalent to author-approved prose or GitHub reviewer-approved Canon.

## Latest author floor-plan directive — 4×4 GROUND FLOOR OPEN LOOP (NOT BUILT)

- The author specified the **future 4×4** encasing the original 2×2. All **12 perimeter floor cells** on **ground floor** form one **open, connected, continuous corridor** one floor unit wide. It MUST be possible to walk a complete loop around the 2×2 core, including corners, with no cross-corridor partition blocking the ring.
- This does NOT add a third wall line: side defenses are outer 4×4 wall / ring corridor / original 2×2 wall / inner room. Door connections from outside and from corridor to the core are still TBD.
- Upper perimeter of story 2 is intended as a firing walk with low parapet; one central support pillar; no triangle extensions; roof and internal stairs details remain unspecified.
- The target **has not been constructed** anywhere up to SC-058. Future scenes must record precise construction steps and keep partial progress partial.
- Source-of-truth plan: `bible/BASE_EXPANSION_4X4_TARGET.md`; machine-readable grid: `data/base_expansion_4x4_target.json`; author decision DEC-011 / design fact FACT-067. Story-approved state remains unchanged.

## CURRENT — EP-007 author-accepted-in-chat manuscript and future handoff

- Read `drafts/EP-007/CH-07-FULL-DRAFT.md`, `data/draft_continuity_ep007.json`, `bible/BASE_CONSTRUCTION_EP007_DRAFT.md`, `plot/episodes/EP-007.md` and the unchanged 4×4 target `data/base_expansion_4x4_target.json`. DEC-012 records user plan; DEC-013 records user's request to ingest the just-written source into Engine.
- EP007 stage order: SC059 returned after refinery; SC060 learning-system upgrade and LMG recipe learned, **spring required=2 / already stored=1 / still missing=1**; SC061–063 plan the base, inspect/organize supplies; SC064–065 partial ring floors; **SC066 all 12 ground ring tiles BUILT and full walk verified**; SC067 exterior 4×4 wall **only partially built**; SC068 same partial outer wall while observing from **old inner upper firing platform**.
- Ground walkway all four sides/corners is connected, 1 floor tile wide, no partitions. Outer 4×4 protective wall is NOT continuous/defensive-ready; new second-floor outer firing terrace is NOT built. Door and stair locations and pillar installation remain TBD, no roof invented. Do not conflate a completed floor ring with the fully fortified two-story base.
- Material totals, wall segment count and coordinates UNKNOWN. The one stored spring must not be logged as newly found EP007 loot or spent on construction; no LMG owned. Older furnace iron/gunpowder never confirmed as obtained.
- First horse CHAR-008 died SC055, no replacement. Other protagonists and NPC identities unchanged. All EP007 scenes still DRAFT despite chat acceptance for ingest; official `data/story_state.json`, `ledger/index.json` and `author_memory/index.json` not changed.
- **DON'T EDIT `bible/BASE_TIMELINE.md` casually**: it is SHA-pinned evidence for the house-card/engine source trust system. Future addenda go in `bible/BASE_CONSTRUCTION_EP007_DRAFT.md`.
