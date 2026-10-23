# LAST ISLAND — Active Story Dataset

Two Thai survival fiction manuscripts and their scene/continuity data, integrated from [PR #13](https://github.com/nustanakritwithai/AI-Novel-Studio/pull/13) into `main` after explicit author acceptance in ChatGPT on **2026-10-23**.

| Episode | Thai title | Scenes | Literary decision | Operational engine status |
| --- | --- | ---: | --- | --- |
| EP-001 | บ้านหลังแรก | 8 | Author accepted | DRAFT pending distinct GitHub-review provenance |
| EP-002 | ธนูแรกและกำแพงหิน | 10 | Author accepted | DRAFT pending distinct GitHub-review provenance |

Read the source manuscripts at `drafts/EP-001/CH-01-FULL-DRAFT.md` and `drafts/EP-002/CH-02-FULL-DRAFT.md`. Exact editorial consent evidence is in `editorial/AUTHOR_APPROVAL_2026-10-23.json` and `data/decisions.json` (DEC-004).

The approved ledger is intentionally empty because PR #13 has no independently submitted GitHub `APPROVE` review. It would be misleading to forge one. All 54 byte-pinned historical example files in `stories/last-island/` remain untouched.

## Quick verification
```bash
python scripts/storyctl.py --story last-island-active check
python scripts/storyctl.py --story last-island-active pack EP-002
python -m unittest discover -s tests -v
```

For continued writing follow `HANDOFF.md`. Game mechanics are fiction directives unless verified against actual selected-server gameplay; item counts remain UNKNOWN.

## Integrated into current Story Engine

Studio defaults to this story. S1 world model is enabled with 18 source-pinned observations and UNKNOWN times and quantities.
Prior author-chat-accepted chapter recaps are now visible in packs with explicit trust labeling. The approved-only GitHub-review ledger remains empty.
Character portrait preview and proposed visual lock: assets/CHAR-001_PORTRAIT_THUMB.webp and bible/CHAR-001_VISUAL_REFERENCE.md.
See docs/LAST_ISLAND_S1_MEMORY_TH.md at repository root.
