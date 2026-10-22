# Editorial review bundle — CH-01 + CH-02

**Review status:** UNREVIEWED / DRAFT (2026-10-23)
**Project:** LAST ISLAND — AI Novel Studio
**Target prose:** \`drafts/EP-001/CH-01-FULL-DRAFT.md\` and \`drafts/EP-002/CH-02-FULL-DRAFT.md\`
**Approved history:** none; \`data/story_state.json.approved_through_scene == null\`
**Human authorization:** requested to **save chapters into Engine**; no explicit approval to mutate Canon/approved ledger or merge this narrative PR

## Human-confirmed plot beats retained

### Chapter 1 (original EP-001 eight scene cards)
- Starts with private Full-Dive VR session in protagonist's room, not world esports championship.
- Guided wood harvesting, planning a modest 2×2 single-storey base.
- Sees many similar rookie houses; checks map and relocates.
- Crafts a first baseball bat using wood; walks along road and finds exactly one scrap box.
- Ambushed with an identical baseball bat, wins barely, collects stones and scrap, returns to house site.

### Chapter 2 (newly user-directed outline)
- Opens inside 2×2; uses scavenged materials to craft table.
- Sees bed, small storage box, medicine and research table recipes and further locked knowledge.
- Sets goal to upgrade home to stone; makes small storage, bed and stone-gathering tool.
- While mining, archer ambushes, protagonist hides behind rock, archer flanks and kills him; held items drop.
- Respawns at home bed; gathers wood and crafts bow, returns to death site.
- Encounters 4×4 house with a bow-wielder and baseball bat companion; attacks archer first, then fleeing bat wielder.
- Takes back loot, returns safely, strengthens base to stone and builds stair, second-level firing area and low cover walls; logs off.

## Change boundary for this PR

All proposed prose and summaries are **new files under drafts/**. No engine source code, test baselines, historical sample files, \`data/canon.json\`, \`data/story_state.json\`, \`data/episodes.json\`, \`data/scenes.json\`, \`data/inventory_ledger.json\`, \`ledger/index.json\` or approved recap are modified. The existing E1 byte manifest for 54 relocated files remains authoritative.

This matters because the existing E1 test \`test_example_integrity.py\` explicitly fails if historic sample files are edited. Adding a new chapter draft is permitted, but it is NOT equivalent to registering approved chapter EP-002.

## Draft-to-draft relationship

CH-01 full draft was composed to retain its confirmed scene order. For CH-02 to begin inside the wooden house, CH-01 completes a **basic 2×2 wooden shell** (floor/walls/door/roof) without a bed or crafting table. Earlier \`STATE.md\` marked exact house completion UNKNOWN, so this bridge requires editorial decision. It is PROPOSED and does not rewrite the locked outline.

PR #11 for SC-001 and PR #12 for SC-002 contain **different, still-unapproved prose candidates**. Future consolidation must choose which writing, if any, to keep rather than silently claiming there is one official version.

## POV / knowledge / relationships

- Protagonist is Thai and limited-POV; surname, given name, age, permanent appearance and year remain UNKNOWN in canonical repository registry.
- First-chapter melee attacker is \`CHAR-002\`. Chapter-2 bow and bat enemies are two other **unregistered proposed** characters; do not assume an identity match between the attacks in different chapters.
- The protagonist suspects the bow opponent at the 4×4 base is his earlier killer, but this suspicion is not omniscient proof.
- No livestream, team membership or esports invitations have happened.
- Any tactile VR sensations, notifications and internal monologue are FICTIONAL details open to revision.

## State delta proposal (NOT approved state)

| Category | At end CH-01 | At end CH-02 |
|---|---|---|
| Health | Survived close fight, exact HP UNKNOWN | One death and respawn, end HP UNKNOWN |
| Home | 2×2 basic wood shell (PROPOSED) | 2×2 stone structure + stair and firing level + low cover (PROPOSED) |
| Weapon | Baseball bat crafted, final equipment count UNKNOWN | Bow crafted and used; arrow count UNKNOWN |
| Items | Wood, roadside scrap, opponent stone/scrap; quantities UNKNOWN | Storage and bed crafted; mined stone, died, recovered loot; quantities UNKNOWN |
| Enemy encounters | One baseball bat opponent defeated | Bow opponent and bat companion defeated |
| Real-world state | Private VR session ongoing | Logged out to rest |

## Unverified game mechanics

The user specified these for **the fictional game depicted in the novel**: baseball bat crafted from wood, roadside material box, bed respawn, drop-on-death behavior, bow crafting, stone base upgrade and elevated firing platform. They must not be promoted to universal Last Island of Survival gameplay claims without timestamped mode-specific game footage.

## Editorial acceptance checklist

- [ ] Author approves or revises CH-01 wording and the completed-house bridge
- [ ] Author approves or revises CH-02 wording, combat pacing and point-of-view
- [ ] Identity/appearance naming is intentionally resolved or left UNKNOWN
- [ ] CH-02 recipe/bed/loot/stone base authenticity gaps resolved if claiming game-accurate
- [ ] Only after explicit approval: plan registry schema migration for EP-002 and state/ledger updates, with source provenance
- [ ] No auto-merge or Canon promotion from passing CI

## Authoring provenance

Manuscripts are **ChatGPT editorial reconstructions** faithfully following the story beats discussed in chat, not exact byte-for-byte transcripts of earlier model responses. This dossier allows corrections before treating either chapter as a definitive literary edition.
