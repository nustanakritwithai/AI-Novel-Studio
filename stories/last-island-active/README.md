# LAST ISLAND — Active Story Dataset

Thai survival fiction manuscripts and their scene/continuity data: chapters 1–2 integrated from [PR #13](https://github.com/nustanakritwithai/AI-Novel-Studio/pull/13) into `main` after explicit author acceptance in ChatGPT on **2026-10-23**.

| Episode | Thai title | Scenes | Literary decision | Operational engine status |
| --- | --- | ---: | --- | --- |
| EP-001 | บ้านหลังแรก | 8 | Author accepted | DRAFT pending distinct GitHub-review provenance |
| EP-002 | ธนูแรกและกำแพงหิน | 10 | Author accepted | DRAFT pending distinct GitHub-review provenance |
| EP-003 | หกนัดบนถนน | 8 | User-directed plot; prose approval pending | DRAFT, not approved |
| EP-004 | วันยาวนานของพรานมือใหม่ | 12 | User-directed plot; prose approval pending | DRAFT, not approved |

## Phase 1 — author-accepted source memory

Author-accepted manuscripts now have an opt-in, byte-pinned recap index at `author_memory/index.json`. Read it using `python scripts/storyctl.py --story last-island-active memory`. The summary is explicitly **derived** from source text accepted in chat, not a separate GitHub `APPROVE` review or an automatic Canon/World State update. `pack EP-002` may include EP-001's accepted-source recap but not EP-002's future recap. See [Phase 1 guide](../../docs/AUTHOR_ACCEPTED_MEMORY_TH.md).

The EP-003 draft source is at `drafts/EP-003/CH-03-FULL-DRAFT.md`, with eight scene drafts, cards and proposed continuity registry additions. It is NOT in author-accepted memory or the approved-only ledger. EP-004 has a complete 12-scene **draft manuscript** and proposed continuity snapshot; hunting, horse capture, raid and furnace are depicted in this draft, not approved history.

Read the source manuscripts at `drafts/EP-001/CH-01-FULL-DRAFT.md` and `drafts/EP-002/CH-02-FULL-DRAFT.md`. Exact editorial consent evidence is in `editorial/AUTHOR_APPROVAL_2026-10-23.json` and `data/decisions.json` (DEC-004).

The approved ledger is intentionally empty because PR #13 has no independently submitted GitHub `APPROVE` review. It would be misleading to forge one. All 54 byte-pinned historical example files in `stories/last-island/` remain untouched.

## Quick verification
```bash
python scripts/storyctl.py --story last-island-active check
python scripts/storyctl.py --story last-island-active pack EP-004
python -m unittest discover -s tests -v
```

For continued writing follow `HANDOFF.md`, `data/draft_continuity_ep003.json` and `bible/BASE_TIMELINE.md`. The active dashboard at `index.html` lists all four episode manuscripts instead of showing only the opening.

For direct chapter reading use [reading order chapters 1–4](drafts/READING_ORDER_CH-01_04.md) and [EP-003 continuity audit](drafts/EP-003/EP-003-CONTINUITY-AUDIT.md). Game mechanics are fiction directives unless verified against actual selected-server gameplay; item counts remain UNKNOWN.

## EP-004 source-bound draft

- Complete manuscript: `drafts/EP-004/CH-04-FULL-DRAFT.md`
- Draft snapshot: `data/draft_continuity_ep004.json` (source Git blob pinned)
- Species/encounter register: `data/wildlife_ep004.json`
- 12 scenes SC-027–038; 38 scenes/events in all four registered episodes
- At end: base 2×2 repaired and furnace built; animal-fat oil prepared; iron/gunpowder material processing **IN PROGRESS**, no finished bullets or gunpowder, horse captured but no stable built
- `data/story_state.json`, `ledger/index.json` and accepted-source `author_memory/index.json` remain unchanged
