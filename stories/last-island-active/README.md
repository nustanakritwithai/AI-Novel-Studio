# LAST ISLAND — Active Writing Dataset

This is the **working** Last Island story for AI Novel Studio. The original \`stories/last-island/\` is retained as an immutable sample for the E1 migration test; no original data was overwritten.

## Current content
| Episode | Title | Scenes | Status |
| --- | --- | ---: | --- |
| EP-001 | บ้านหลังแรก | 8 | DRAFT |
| EP-002 | ธนูแรกและกำแพงหิน | 10 | DRAFT |

- Complete manuscripts are in \`drafts/EP-001/CH-01-FULL-DRAFT.md\` and \`drafts/EP-002/CH-02-FULL-DRAFT.md\`.
- Per-scene drafts are \`drafts/EP-001/SC-001.md\`–\`SC-008.md\`, \`drafts/EP-002/SC-009.md\`–\`SC-018.md\`.
- \`data/\` now registers both episodes, causal flags, POV, entities and item transitions.
- \`drafts/PROPOSED_CONTINUITY_CH-01_02.json\` is a candidate recap, **never** approved ledger state.

## Smoke test from repo root
\`\`\`bash
python scripts/storyctl.py --story last-island-active check
python scripts/storyctl.py --story last-island-active pack EP-002
python -m unittest discover -s tests -v
\`\`\`

## Important
DRAFT metadata says a candidate script is available; it is not evidence of human editorial approval. \`data/story_state.json.approved_through_scene\` is null and \`ledger/index.json\` is empty until explicit review. Gameplay mechanics remain UNVERIFIED until independent mode-specific evidence.
