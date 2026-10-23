# AGENTS.md — Last Island Active Story / operational instructions

Story root: \`stories/last-island-active\`. Canonical approved history is **EMPTY**. Source content in \`stories/last-island\` is an immutable, byte-pinned E1 historical example. Do not edit it to fix this story.

## Read order
1. \`story.json\` and \`data/canon.json\` (LOCKED user-directed story beats override all generated prose).
2. \`data/story_state.json\` (approved history marker is null; never mistake a DRAFT for approved).
3. \`data/episodes.json\`, \`data/scenes.json\`, \`data/events.json\`, \`data/characters.json\`, \`data/inventory_ledger.json\`.
4. \`bible/STYLE_GUIDE.md\`, \`bible/CHARACTER_CONTINUITY_ADDENDUM.md\`, \`HANDOFF.md\`.
5. Target-specific \`scenes/SC-xxx.md\`, \`drafts/EP-xxx/SC-xxx.md\`, full chapter drafts.
6. \`drafts/PROPOSED_CONTINUITY_CH-01_02.json\` is advisory/unapproved memory, not approved ledger.

## CLI (from repository root)
\`\`\`bash
python scripts/storyctl.py --story last-island-active check
python scripts/storyctl.py --story last-island-active status
python scripts/storyctl.py --story last-island-active brief EP-002
python scripts/storyctl.py --story last-island-active pack EP-002
python scripts/storyctl.py --story last-island-active replay SC-018
\`\`\`

## Rules
- Every drafted scene carries DRAFT status and cannot enter approved ledger without explicit human review/provenance.
- The protagonist is Thai and still has no approved personal name, fixed age, job or precise year.
- EP-001: private Full-Dive VR start → wood → 2×2 plan → crowded rookie base → relocation/map → first wooden baseball bat → exactly one roadside scrap crate → narrowly survive bat ambush → loot stone/scrap → basic wooden house shell.
- EP-002: crafting table → recipe discovery → storage/bed → mine stone → archer flank kill → bed respawn → craft bow → 4×4 party base → shoot archer first then fleeing bat user → recover loot → upgrade stone 2×2 base with second-level firing position → log off.
- Numbers of wood, stone, scrap, arrows and HP are UNKNOWN. No fabrication.
- Game mechanics are fictional story directives until verified by separate evidence from the selected game mode. UNKNOWN ≠ PASS.
- The bow-wielder discovered at 4×4 might be the original shooter: treat matching as POV suspicion until supported.
- 100-player global tournament belongs in a later arc; no early competitive opening.
- SC-001/SC-002 alternative prose remains in PR #11/#12; this dataset adopts the two full chapter drafts in PR #13 as the **candidate literary edition**, not approved.
- No silent edits to \`data/story_state.json\`, \`ledger/index.json\` or human-approved canon. A CI pass is not editorial approval.

## Current Engine: S1 + author-accepted history

- Default studio story is last-island-active; use --story last-island for the frozen E1 sample.
- Read data/world_model.json for S1 source-anchored positions and item holders. S1 is PROPOSED observational data, not replay or certified truth.
- Read editorial/author_accepted_index.json and editorial/accepted/EP-001.md and EP-002.md; their source Git hashes are bound to author receipt DEC-004.
- Story Engine pack EP-002 includes the prior author-accepted EP-001 summary, labelled CHAT ACCEPTANCE, NOT NATIVE GITHUB REVIEW.
- The user already accepted the exact chapter text in chat. Do not request duplicate consent or invent GitHub reviewer APPROVE; the approved-only ledger remains separate.
- The portrait thumbnail and proposed visual values are in bible/CHAR-001_VISUAL_REFERENCE.md; only Thai nationality is currently locked.
- See docs/LAST_ISLAND_S1_MEMORY_TH.md in the repository root.
