# HANDOFF — Active Last Island

**TARGET:** Continue editorial review and then plan future story (do not invent EP-003 without author plot instructions). Working engine: \`last-island-active\`.

## One-pass work
1. Run \`python scripts/storyctl.py --story last-island-active check\` and \`... pack EP-002\`.
2. Read \`data/canon.json\`, \`data/characters.json\`, \`data/story_state.json\`, \`bible/STYLE_GUIDE.md\`.
3. Read \`drafts/EP-001/CH-01-FULL-DRAFT.md\`, \`drafts/EP-002/CH-02-FULL-DRAFT.md\`.
4. Inspect \`drafts/PROPOSED_CONTINUITY_CH-01_02.json\`; it has 19 proposal events including a CH-01 bridge, not 19 approved events.
5. Check per-scene cards \`scenes/SC-001.md\` through \`SC-018.md\` and segmented prose in \`drafts/EP-001/\` and \`drafts/EP-002/\`.
6. Consult \`drafts/EDITORIAL_CLOSEOUT.md\` and request/obtain explicit literary approval before promoting chapters into the approved ledger or declaring them canonical.

## Unresolved editorial matters
- Does the author accept a fully enclosed wooden 2×2 house at end of EP-001? The later author-provided EP-002 starts inside this house, so the bridge is editorially coherent but should not be retroactively claimed as approved prose.
- Identity of archer at 4×4 base remains protagonist inference.
- Quantities unknown; do not fill.
- Exact real game's crafting and respawn details are not verified.
- Streaming/global tournament future only.

## Compatibility
The old sample is **not** a production-edit target and remains byte-pinned. Use the active story slug only. The live tests in this PR verify episode 2 packs from the active story; they do not authenticate approval.
