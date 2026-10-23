# HANDOFF — Last Island after author acceptance

**Working story:** `last-island-active`
**Latest author decision:** DEC-004 — "อนุมัติ" in ChatGPT, 2026-10-23.
**Source of accepted text:** merged [PR #13](https://github.com/nustanakritwithai/AI-Novel-Studio/pull/13), source head `3d0b3117b2a4a4029fe815899e5c7a28e69eb56f`, merge commit `5d32a9ff95b3b64953a792be3bd7fef078343a1f`.

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
- The future episode 3 has no author-supplied plot. Wait for actual story directives instead of generating canon plot events.

## Commands

```bash
python scripts/storyctl.py --story last-island-active check
python scripts/storyctl.py --story last-island-active pack EP-002
python -m unittest discover -s tests -v
```

PR #11 and #12 were closed as superseded; main contains the selected two-chapter manuscripts.

## Writer handoff — current engine

1. Default route: python scripts/storyctl.py check ; python scripts/storyctl.py pack EP-002.
2. The pack includes EP-001 chat-accepted recap only (no future spoilers); see editorial/accepted for EP-002 after completion.
3. Read data/world_model.json for S1 observations of positions and item holders. This model is not an inventory calculation or world-time simulation.
4. Read bible/CHAR-001_VISUAL_REFERENCE.md for the low-resolution visual proposal. Never set age, height, occupation or other unknown biographical facts as canonical without user approval.
5. Formal approved-only ledger is still empty because PR #13 lacked a native GitHub APPROVE reviewer; never invent a reviewer or approved_by.
6. For the full method and limitations see docs/LAST_ISLAND_S1_MEMORY_TH.md.
