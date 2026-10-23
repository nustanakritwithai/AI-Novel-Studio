# House-card evidence isolation before EP-007 registry growth

## Why this boundary exists

The house-card pilot at `data/house_references.json` originally pinned the complete Git blob SHA of `data/characters.json` and `data/scenes.json` as local reference evidence for older scenes. Appending legitimate new EP-007 characters' knowledge and scene rows changes these **mutable working registries' complete blobs**. It does **not** change the truth of the old evidence, but naïvely leaving the house-card sources pointed to the new file contents makes every old house reference fail immutable hash verification.

## Safe migration performed with this chapter

Exactly **two pre-EP-007 original source files** are copied byte-for-byte from the repository's pre-EP007 `main` snapshot and verified against the original source SHA:

| House source | Original SHA (unchanged) | Frozen source at EP007 |
| --- | --- | --- |
| SRC-CHARACTERS | `9d321f7898e59db31b819e69fa1cd87e4f7b755e` | `data/house_evidence/characters_pre_ep007.json` |
| SRC-SCENES | `63fcb7e21d69824f4235e8f042608a4b6e6cc486` | `data/house_evidence/scenes_pre_ep007.json` |

`house_references.json` changes **only these two source paths**, NOT their `git_blob_sha`, source statuses, supporting source lists, evidence locators, claims, view/cursor boundaries, character knowledge or editorial classification. Because the exact JSON blob bytes are the same, all old JSON Pointers continue to point at the same old records.

Mutable working `data/scenes.json` and `data/characters.json` can now contain EP-007 updates without making the original house-card evidence unresolvable or retroactively treating new scenes as source evidence for old facts.

## Rules for future agents

- Frozen files in `data/house_evidence/` are **immutable evidence bytes**. Do not edit to reflect newer story data.
- New house-card views after SC-058 require **new source IDs and independent evidence**; they must not silently reuse older `SRC-CHARACTERS`/`SRC-SCENES` as proof for EP-007 new claims.
- No human GitHub approval has been implied or retroactively created. Old statuses `AUTHOR_ACCEPTED_SOURCE_NOT_GITHUB_APPROVED`, `DRAFT_SOURCE`, `LOCAL_REFERENCE` retain their meanings.
- The separate SHA-pinned `bible/BASE_TIMELINE.md` stays unchanged. The new building stage is tracked by `bible/BASE_CONSTRUCTION_EP007_DRAFT.md` and source bound `data/draft_continuity_ep007.json`.
- Regression coverage in `tests/test_ep007_draft.py` protects both frozen snapshots and the live appended registries.
