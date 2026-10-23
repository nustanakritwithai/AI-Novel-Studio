# Last Island — S1 World State + Author-Accepted Continuity Memory

Version: 2026-10-23. The human author accepted chapters EP-001 and EP-002 in ChatGPT, but PR #13 has NO native GitHub APPROVE review.

## Installed configuration

- The default story selected by studio.json is last-island-active. The historical last-island story remains frozen for the E1 byte-manifest tests.
- The opt-in S1 feature in last-island-active/story.json is enabled, using data/world_model.json.
- S1 has 18 source SHA256 pinned observations, one AFTER anchor per scene SC-001 through SC-018, for character positions and item holders where the manuscript provides evidence. All world times are UNKNOWN; unknown quantities are null, never invented.
- Site containment is declared only where grounded: LOC-005 site contains the initial house interior LOC-006 and upgraded house location LOC-009. This is not a travel graph.
- No S1 baseline is invented. All S1 local_status values remain PROPOSED despite chat author acceptance, because S1 cannot authenticate editorial reviewers.
- Independently, author-accepted episode memory is in editorial/author_accepted_index.json and editorial/accepted/EP-001.md and EP-002.md. It is source-Git-blob checked against DEC-004 and the author approval receipt.

## Continuity memory and trust boundaries

The Story Engine context pack now includes a specially labelled AUTHOR-ACCEPTED EPISODE MEMORY section for preceding accepted episodes only. When packing EP-002 it includes EP-001, not EP-002 or any future events. The source story approved-only ledger remains unchanged and empty. No authenticated GitHub review is invented, and the last approved-through-scene marker remains null.

The optional author-memory feature is inert for stories without an index and preserves the old context-pack bytes. Modified accepted manuscript bytes cause validation to fail rather than presenting stale narrative memory.

S1 data/world_model.json is independent observational input: it does not automatically update inventory, replay movements, calculate HP, or become approved history. Location UNKNOWN and quantity null mean facts not established; do not infer zero or safety.

## Run from repository root

    python scripts/storyctl.py check
    python scripts/storyctl.py pack EP-002
    python scripts/storyctl.py --story last-island-active check
    python scripts/storyctl.py --story last-island-active pack EP-002
    python scripts/novelctl.py --root stories/last-island check
    python -m unittest discover -s tests -v

Default-story commands now select the live active story. To validate historical example data, explicitly select last-island rather than changing studio.json back.

## End of EP-002 for the next writer

- CHAR-001 is a Thai male; real name, exact age, job and origin remain UNKNOWN.
- After SC-018, his real-world position is LOC-001 after logging out. The 2x2 base remains on the VR island, with stone walls, stairs and second-floor firing cover.
- The storage box, crafting table and bed exist in the home. A bow was crafted and used during EP-002, but its exact holder while offline and remaining arrows are UNKNOWN.
- EP-002 includes one death and bed respawn, then two opponents defeated near a possible party base 4x4; the bow opponent identity is still only a POV inference.
- Inventory quantities, precise HP, exact crafting recipes, and real-server loot/respawn rules remain UNKNOWN or UNVERIFIED.
- The championship with 100 competitors is future arc material only. EP-003 has no user-authored plot; do not invent it as canon.

## Character illustration master

- The author-confirmed fact is nationality Thai. The proposed facial specification is in bible/CHAR-001_VISUAL_LOCK_PROPOSED.json.
- A low-resolution WebP portrait is in assets/CHAR-001_PORTRAIT_THUMB.webp with a SHA256 identity test; it does not replace the high-resolution master sheet.
- Follow the author's preferred manga format: separate vertical shonen pages with multiple panels and editable Thai lettering.

## Explicit remaining limitations

1. Formal approved-only ledger records still require genuine native GitHub reviewer provenance under the original project policy.
2. S1 is observational, not a live world reducer/query system.
3. The high-resolution master art is not committed, only the derivative portrait and original file checksum.
4. Future plot and all truly unspecified item/character properties must await user story input.
