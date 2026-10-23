# LAST ISLAND — Active Story Dataset

Thai survival fiction manuscripts and their scene/continuity data: chapters 1–2 integrated from [PR #13](https://github.com/nustanakritwithai/AI-Novel-Studio/pull/13) into `main` after explicit author acceptance in ChatGPT on **2026-10-23**.

| Episode | Thai title | Scenes | Literary decision | Operational engine status |
| --- | --- | ---: | --- | --- |
| EP-001 | บ้านหลังแรก | 8 | Author accepted | DRAFT pending distinct GitHub-review provenance |
| EP-002 | ธนูแรกและกำแพงหิน | 10 | Author accepted | DRAFT pending distinct GitHub-review provenance |
| EP-003 | หกนัดบนถนน | 8 | User-directed plot; prose approval pending | DRAFT, not approved |
| EP-004 | วันยาวนานของพรานมือใหม่ | 12 | User-directed plot; prose approval pending | DRAFT, not approved |
| EP-005 | ค้อนที่หน้าประตู | 9 | Revised ending accepted for ingest in chat | DRAFT; GitHub-reviewed Canon pending |

## Phase 1 — author-accepted source memory

Author-accepted manuscripts now have an opt-in, byte-pinned recap index at `author_memory/index.json`. Read it using `python scripts/storyctl.py --story last-island-active memory`. The summary is explicitly **derived** from source text accepted in chat, not a separate GitHub `APPROVE` review or an automatic Canon/World State update. `pack EP-002` may include EP-001's accepted-source recap but not EP-002's future recap. See [Phase 1 guide](../../docs/AUTHOR_ACCEPTED_MEMORY_TH.md).

The EP-003 draft source is at `drafts/EP-003/CH-03-FULL-DRAFT.md`, with eight scene drafts, cards and proposed continuity registry additions. It is NOT in author-accepted memory or the approved-only ledger. EP-004 has a complete 12-scene **draft manuscript** and proposed continuity snapshot; hunting, horse capture, raid and furnace are depicted in this draft, not approved history.

Read the source manuscripts at `drafts/EP-001/CH-01-FULL-DRAFT.md` and `drafts/EP-002/CH-02-FULL-DRAFT.md`. Exact editorial consent evidence is in `editorial/AUTHOR_APPROVAL_2026-10-23.json` and `data/decisions.json` (DEC-004).

The approved ledger is intentionally empty because PR #13 has no independently submitted GitHub `APPROVE` review. It would be misleading to forge one. All 54 byte-pinned historical example files in `stories/last-island/` remain untouched.

## Quick verification
```bash
python scripts/storyctl.py --story last-island-active check
python scripts/storyctl.py --story last-island-active pack EP-005
python -m unittest discover -s tests -v
```

For continued writing follow `HANDOFF.md`, `data/draft_continuity_ep003.json` and `bible/BASE_TIMELINE.md`. The active dashboard at `index.html` lists all five episode manuscripts instead of showing only the opening.

For direct chapter reading use [reading order chapters 1–5](drafts/READING_ORDER_CH-01_05.md) and [EP-003 continuity audit](drafts/EP-003/EP-003-CONTINUITY-AUDIT.md). Game mechanics are fiction directives unless verified against actual selected-server gameplay; item counts remain UNKNOWN.

## EP-004 source-bound draft

- Complete manuscript: `drafts/EP-004/CH-04-FULL-DRAFT.md`
- Draft snapshot: `data/draft_continuity_ep004.json` (source Git blob pinned)
- Species/encounter register: `data/wildlife_ep004.json`
- 12 scenes SC-027–038; 38 scenes/events in all four registered episodes
- At end: base 2×2 repaired and furnace built; animal-fat oil prepared; iron/gunpowder material processing **IN PROGRESS**, no finished bullets or gunpowder, horse captured but no stable built
- `data/story_state.json`, `ledger/index.json` and accepted-source `author_memory/index.json` remain unchanged

## EP-005 latest — accepted for ingest, not approved-only ledger

- Full joined manuscript: `drafts/EP-005/CH-05-FULL-DRAFT.md`, 9 scenes SC-039–SC-047.
- User accepted the revised ending in chat and asked to add it; the formal engine registry remains DRAFT while GitHub reviewer provenance is separate.
- Draft source-bound snapshot: `data/draft_continuity_ep005.json` and [plot/handoff](plot/episodes/EP-005.md).
- Two known recurring opponents CHAR-004/005 are defeated, then return again but withdraw following one warning round. New loot: two pistols in total, basic leather gear, 100 observed rounds; exact ammunition left at chapter end UNKNOWN.
- House remains 2×2 stone with open upper firing platform and working furnace. Finished iron/gunpowder ammunition is not acquired in EP-005; fortification upgrades are only a thought.
- Engine approved-only ledger and official story_state are unchanged. Existing accepted-source memory is still EP-001/002 only.
