# AGENTS.md — Last Island Active Story / operational instructions

Story root: `stories/last-island-active`. Canonical approved history is **EMPTY**. Source content in `stories/last-island` is an immutable, byte-pinned E1 historical example. Do not edit it to fix this story.

## Read order
1. `story.json` and `data/canon.json` (LOCKED user-directed story beats override all generated prose).
2. `data/story_state.json` (approved history marker is null; never mistake a DRAFT for approved).
3. `data/episodes.json`, `data/scenes.json`, `data/events.json`, `data/characters.json`, `data/inventory_ledger.json`.
4. `bible/STYLE_GUIDE.md`, `bible/CHARACTER_CONTINUITY_ADDENDUM.md`, `HANDOFF.md`.
5. Target-specific `scenes/SC-xxx.md`, `drafts/EP-xxx/SC-xxx.md`, full chapter drafts.
6. `drafts/PROPOSED_CONTINUITY_CH-01_02.json` is advisory/unapproved memory, not approved ledger.

## CLI (from repository root)
```bash
python scripts/storyctl.py --story last-island-active check
python scripts/storyctl.py --story last-island-active status
python scripts/storyctl.py --story last-island-active brief EP-002
python scripts/storyctl.py --story last-island-active pack EP-006
python scripts/storyctl.py --story last-island-active replay SC-018
```

## Rules
- Every drafted scene carries DRAFT status and cannot enter approved ledger without explicit human review/provenance.
- The protagonist is Thai and still has no approved personal name, fixed age, job or precise year.
- EP-001: private Full-Dive VR start → wood → 2×2 plan → crowded rookie base → relocation/map → first wooden baseball bat → exactly one roadside scrap crate → narrowly survive bat ambush → loot stone/scrap → basic wooden house shell.
- EP-002: crafting table → recipe discovery → storage/bed → mine stone → archer flank kill → bed respawn → craft bow → 4×4 party base → shoot archer first then fleeing bat user → recover loot → upgrade stone 2×2 base with second-level firing position → log off.
- Numbers of wood, stone, scrap, arrows and HP are UNKNOWN. No fabrication.
- Game mechanics are fictional story directives until verified by separate evidence from the selected game mode. UNKNOWN ≠ PASS.
- The bow-wielder discovered at 4×4 might be the original shooter: treat matching as POV suspicion until supported.
- 100-player global tournament belongs in a later arc; no early competitive opening.
- SC-001/SC-002 alternative prose remains in PR #11/#12; EP-001/002 exact full chapters in PR #13 were author-accepted in chat under DEC-004 but the separate GitHub reviewer-approved ledger is still pending.
- No silent edits to `data/story_state.json`, `ledger/index.json` or human-approved canon. A CI pass is not editorial approval.

## Phase 1 author-accepted memory addendum

- Always validate `author_memory/index.json` and bound source Git blob hashes before using locally attested accepted recaps.
- `python scripts/storyctl.py --story last-island-active memory` includes EP-001/EP-002 recaps for *future* planning, each visibly labelled as **derived from author-accepted source**, not GitHub-approved ledger evidence.
- `pack EP-002` includes only earlier EP-001 author-accepted memory; never leak future EP-002 recap into its own context.
- `ledger/index.json` is still **GitHub-review-approved-only** and cannot be auto-populated from a ChatGPT assertion. GitHub review/account authentication is outside the scope of these local checks.
- The old `stories/last-island/` sample and its 54 byte-pinned files remain immutable.

## EP-003 draft addition — never confuse a plotted chapter with approved prose

- EP-003 (SC-019–SC-026) is a stored DRAFT; author directed real-world gamer rest, an oil-crate search on the road, tactical bow duel nearly won, a six-shot pistol reversal and respawn, then planning animal-fat hunting for EP-004.
- The hero did NOT obtain oil, craft a furnace or iron, make ammunition, or hunt any animals in EP-003; amounts of resources carried/used/lost remain UNKNOWN.
- CHAR-006 is the road pistol/bow rival with UNKNOWN identity; CHAR-007 is a PROPOSED chat friend, not a locked permanent character.
- DEC-005 locks plot beats only; DEC-006 authorizes draft ingest only. EP-001/EP-002 accepted prose, author_memory and all approved-only ledgers must remain unchanged without fresh editorial direction.

## Draft snapshot / base time history

- Before writing EP-004 load `data/draft_continuity_ep003.json` and verify its `source.git_blob_sha` against the actual EP-003 manuscript; this is DRAFT memory, never official `data/story_state.json`.
- `bible/BASE_TIMELINE.md` records stage-by-stage house evolution: wooden 2×2 → workbench/bed/storage → same 2×2 in stone → upper open firing platform → no new EP-003 construction.
- Read `research/EP003_GAMEPLAY_GAPS.md` for EP-003 rules and `research/EP004_GAMEPLAY_GAPS.md` for EP-004 wildlife, taming, raid and furnace rules. The prior EP-004 handoff was a pre-draft plan and is superseded by the 12 written scenes.
- Inventory register has exact **6** pistol shots expended by CHAR-006 in SC-024 (INV-029); all other unspecified amounts must remain UNKNOWN. If a writer changes the EP-003 manuscript, the draft snapshot source hash must be reviewed/rebound, not silently trusted.

## EP-004 (latest) locked plot / draft prose rules

- Read `drafts/EP-004/CH-04-FULL-DRAFT.md`, `data/draft_continuity_ep004.json` and `data/wildlife_ep004.json` before planning further work.
- The scattered wildlife farm took substantial travel/search/wait time. Prey: chicken, rabbit, deer; dangerous wolf/bear were avoided. Horse CHAR-008 captured with hide glove after weakening. No stable constructed.
- At campfire hero cooks meat; wall-explosion notification makes him ride back, hide behind hill and watch CHAR-004/005 (from EP-002) raid his home. He opts not to fight, waits for their departure then repairs the entrance.
- Oil from animal fat and furnace are obtained/built within **EP-004 DRAFT**; however iron/gunpowder/bullet outputs are NOT ready because processing requires time. Do not auto-complete these in later scenes without new instructions.
- House footprint stays 2×2, no full second room; amount looted from house UNKNOWN. Exact counts/durations are not invented.
- Treat EP-004 as DRAFT, not approved prose. No edits to `author_memory/index.json`, `ledger/index.json`, `data/story_state.json` without separately verified authorization.

## Latest author-ingested EP-005 working manuscript

- Full author-chat accepted text: `drafts/EP-005/CH-05-FULL-DRAFT.md`, with revised ending. Scenes SC-039–047 (9), decision DEC-008/009. Engine scene status stays DRAFT until formal reviewer approval.
- Returning attackers are pair CHAR-004/005 from EP-002/004, not the earlier independent pistol archer CHAR-006. **Two defeated**, then **both return and retreat without further defeats**.
- Pistol inventory: exactly two pistols in total, one taken earlier from first fallen rival and one from second; 100 rounds observed from collected loot, then one warning round. Final magazine and ammo balance UNKNOWN.
- Chapter 5 begins and ends with furnace operating, but no finished iron/gunpowder/furnace ammunition is retrieved. Original 2×2 stone base, stairs and upper open firing position unchanged; no new multilayer fortification or full upper room built.
- Horse's exact current state, rival weapon-account mapping, exact pistol duel ammo and door durability still UNKNOWN; selected-game mechanics UNVERIFIED.
- Before EP006 consult `data/draft_continuity_ep005.json`, `plot/episodes/EP-005.md`, and `research/EP005_GAMEPLAY_GAPS.md`. Scene/story acceptance in chat is **not** authenticated GitHub PR APPROVE; keep `ledger/index.json` and official story state protected.

## EP-006 continuation guardrails (DRAFT, not prose-approved)

- Load `drafts/EP-006/CH-06-FULL-DRAFT.md`, `data/draft_continuity_ep006.json`, and `research/EP006_GAMEPLAY_GAPS.md` after prior source manuscript.
- Chapter starts with hero still having two pistols, leather equipment and first horse CHAR-008 alive. He rides to road, defeats one bat ambusher (CHAR-009), and later enters an abandoned oil refinery with dispersed melee zombies.
- 1 GREEN ACCESS CARD and some ready oil are retained; **card not used**. One crude barrel inserted into refinery process; **processed oil is not collected** when hero withdraws.
- 3 motorcycle riders CHAR-010/011/012 arrive with light machine guns and kill first horse CHAR-008. Hero does NOT fight these three and does NOT gain motorcycle/LMG; he escapes and walks home.
- The motorcyclists' refinery control or later receipt of the processed oil is UNKNOWN, not a verified fact. The bat-wielding opponent's connection to CHAR-002 is UNKNOWN.
- End EP-006: hero alive at original stone 2×2, on foot, first horse dead, green card retained. Precise HP, gun ammunition, zombie body count, refinery results and quantities UNKNOWN. Distinguish fiction rules from real game evidence (UNKNOWN ≠ PASS).
- EP-006 prose still DRAFT; authenticated GitHub approved ledger, `data/story_state.json` and EP-001/002 accepted prose remain guarded.

## AUTHOR DESIGN DIRECTIVE DEC-011 — Walkable 4×4 ground ring (future only)

- Required floor target: 4×4 footprint / 2×2 original core / **12 open ground-level corridor cells forming a fully connected walkable loop** 1 floor tile wide. The continuous ring must allow walking around all sides and corners without partitions.
- Defensive outer 4×4 wall and existing inner 2×2 wall give two lateral barriers separated by the walkable corridor (not a fixed number of raid hits).
- Keep one central pillar only. Outer upper level is a low-parapet firing perimeter; don't invent enclosed rooms, extra pillars, triangle additions, detailed roof, extra stair positions or new doors.
- DESIGN ≠ CONSTRUCTED: current last manuscript SC-058 still has only the original stone 2×2 with previous upper firing position. No ring/4×4 external wall has been built in the story yet.
- Always read `bible/BASE_EXPANSION_4X4_TARGET.md` and `data/base_expansion_4x4_target.json` before drafting later base-construction scenes; track when each tile, wall and circulation connection actually becomes available.
