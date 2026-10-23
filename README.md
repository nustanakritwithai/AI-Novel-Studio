# AI Novel Studio — reusable continuity engine

A continuity engine with isolated story datasets and explicit read-only GitHub provenance checks. E1 separates story roots, E2 adds versioned schemas/state replay, E3/E4 adds local review evidence and generic workflow contracts, and bounded E5 adds merged metadata/source verification plus deterministic rollup proposals. Start with the [Thai E7 onboarding guide](ENGINE_E7.md) and [fillable story input template](templates/STORY_INPUT_TH.md). The [E0–E7 readiness report](docs/ENGINE_READINESS.md) separates implemented capabilities from unmet gates, including authenticated human editorial approval and actual postmerge rollout. The [artifact-only postmerge workflow](docs/POSTMERGE_PROPOSALS.md) keeps its live trigger NOT_RUN until owner-authorized deployment. The engine does not generate prose or approve canon.

**Phase 1 author-accepted memory (opt-in):** [Thai guide](docs/AUTHOR_ACCEPTED_MEMORY_TH.md). Source-blob-pinned recaps from author-accepted manuscripts can appear as a clearly separate section in scoped packs, with their local ChatGPT attestation label; they are NOT authenticated GitHub-review-approved ledger records. Use `python scripts/storyctl.py --story last-island-active memory` to review the two accepted-source recaps, or `... memory --before EP-002` to avoid future episode leakage. No behavior changes for unconfigured stories.

Use Python 3.11+ and install the pinned validation dependencies from official PyPI:

```bash
python -m pip install --index-url https://pypi.org/simple --only-binary=:all: -r requirements.txt
python scripts/storyctl.py new my-story --title "My story"
python scripts/storyctl.py --story my-story check
python scripts/storyctl.py --story my-story status
python scripts/storyctl.py --story my-story doctor --out .local/doctor.json
```

`new` creates empty metadata registries, an empty approved ledger, and generic guidance. It writes no novel content and never overwrites an existing story. An empty scaffold has no target scenes: humans must supply the required story/scene metadata before target-specific commands can succeed. `story.json` uses versioned JSON. Gameplay mechanics/sources are an optional extension.

The optional [S1 world model](docs/WORLD_STATE_S1_TH.md) adds source-bound declarations of character positions, item holders, room containment and explicit world-time coordinates. Enable `world_state: {"schema_version": 1, "enabled": true}` in `story.json` and supply `data/world_model.json`; the existing `check` command validates it. This model does not replay events, answer world-state queries, change v1 knowledge/context, or establish human approval. Existing stories remain unchanged when the option is absent or disabled.

The [S2 world preview](docs/WORLD_STATE_S2_TH.md) optionally adds `data/world_history.json` with explicit baseline binding, coverage and movement/custody deltas. `storyctl --story my-story world-preview --clock CLOCK-MAIN --tick 2 --boundary AFTER` produces a read-only PROPOSED result at an explicit world cursor. UNKNOWN facts and failed preconditions remain unresolved; no partial result or canon update is emitted. Local APPROVED declarations and matching evidence hashes do not authenticate human approval. The preview is separate from v1 replay and context packs; broad queries/maps, genre invariants and extraction remain deferred.

[S3 diagnostics](docs/WORLD_STATE_S3_TH.md) add opt-in `data/world_rules.json` and `storyctl --story my-story lintstate --clock CLOCK-MAIN --tick 2 --boundary AFTER`. The same S2 execution path reports explicit movement/custody precondition contradictions separately from insufficient information, with event/scene, before/requested/after values and source references. Missing rules are DISABLED; UNKNOWN and unperformed checks never become PASS. Reports remain proposals, authorize no canon/ledger updates and add no genre-specific facts, context integration or extraction.

After the selected story has valid human-authored metadata and a readable target draft:

```bash
python scripts/storyctl.py --story my-story brief SC-001
python scripts/storyctl.py --story my-story pack SC-001 --out context.md
python scripts/storyctl.py --story my-story replay SC-001
python scripts/storyctl.py --story my-story brief-review SC-001 --base HEAD --out .local/reviews/SC-001.json
python scripts/storyctl.py --story my-story doctor --target SC-001 --out .local/doctor.json
python scripts/storyctl.py --story my-story propose EP-001
```

`brief-review` records actual local HEAD/base anchors, the current working draft and its digest, a diff, and target context. The draft may differ from HEAD. The bundle starts unreviewed; it is evidence for a reviewer, never canon approval or proof that its text was committed. `propose` aliases the existing `proposal` command and does not apply a proposal. `doctor` inspects local data and reports unavailable GitHub approval/settings checks as UNKNOWN. Neither command calls a model or changes approved story data.

Review bundles require readable local Git anchors and include hashes/byte lengths of selected-story inputs. Each source read, including registry/style/evidence files and the base draft blob, is limited to 1 MiB; the existing pack context cap also applies. Oversized or changing inputs fail instead of being silently truncated. Context hashes describe working-tree data and do not authenticate the engine code or a committed context version.

Local review/Git diagnostics require Git supporting the global [`--no-lazy-fetch` option](https://git-scm.com/docs/git). Older unsupported Git fails review or reports Git diagnostics UNKNOWN. These commands read local objects without fetching missing objects or changing persistent Git settings; they do not install Git.

New review, doctor, provenance, and rollup file output is restricted to the selected workspace's ignored `.local/` directory (stdout is also available). Bundles can contain unpublished draft and context text. Do not attach them to a public PR or send them externally without explicit user authorization.

## Provenance and rollup proposals

`verify-provenance` reads live GitHub metadata through existing `gh` authentication unless `--evidence` supplies offline JSON. Replace the uppercase placeholders with the intended repository, PR number, immutable commit SHAs, path, and digest; these are not approval examples:

```bash
python scripts/storyctl.py verify-provenance --repo OWNER/REPO --pr PR_NUMBER --head HEAD_SHA --merge MERGE_SHA --source REPO_PATH --sha256 SHA256 --out .local/provenance.json
python scripts/storyctl.py verify-provenance --repo OWNER/REPO --pr PR_NUMBER --head HEAD_SHA --merge MERGE_SHA --evidence .local/cached-pr.json --out .local/offline-provenance.json
python scripts/storyctl.py --story my-story rollup EP-001 EP-002 --out .local/rollup.json
python scripts/storyctl.py --story my-story rollup EP-001 EP-002 --repo OWNER/REPO --verify-remote --out .local/remote-rollup.json
```

Live verification checks observed merged metadata against the exact repository/PR/head/merge, and optionally an immutable Git tree/blob source hash. It never authenticates human editorial approval. Exit codes are 0 only for live `OBSERVED_MERGED_METADATA`, 2 for consistent `OFFLINE_UNVERIFIED` evidence, and 1 for failure. Cached JSON and fixtures never become live verification. No login, credential creation, permission change, or automatic post-merge workflow is provided.

A matching path/hash at the merge commit proves presence and bytes there; it does not prove that the identified PR changed the file or that a human reviewed/approved its narrative content. File-change attribution and editorial authorization remain outside this bounded check.

`rollup` concatenates existing eligible local ledger recaps into a `PROPOSED` output. Default provenance is `UNVERIFIED_LOCAL_DECLARATIONS`; `--verify-remote` explicitly checks each source record online. Missing/unapproved source records fail. The output is never applied to canon, state, or the ledger, and no novel prose is generated. An observed software PR merge is not novel approval.

The legacy invocations still use the default story selected by `studio.json`:

```bash
python scripts/novelctl.py check
python scripts/story_engine.py check
python scripts/story_engine.py pack SC-001 --out context.md
python -m unittest discover -s tests -v
```

See the [Thai E7 onboarding guide](ENGINE_E7.md), [E6 acceptance procedure](ENGINE_E6.md), [actual semantic-review results](evaluation/e6/RESULTS.md), [E0–E7 readiness report](docs/ENGINE_READINESS.md), [Thai E5 provenance/ledger guide](ENGINE_E5.md), [E3/E4 local workflow guide](ENGINE_E3_E4.md), [agent handoff runbook](docs/AGENT_RUNBOOK.md), [E2 schema/replay contract](ENGINE_E2.md), [E1 separation guide](ENGINE_E1.md), [engine instructions](AGENTS.md), and [preserved Last Island example](stories/last-island/README.md). All 54 relocated example files are checked against a SHA-256 manifest of their original Git bytes. The original 43 regressions retain their assertions and use the example root. Record actual final tests and exact-head CI in each PR; these commands are not a test result.

The **active** four-chapter Last Island dashboard is at [stories/last-island-active/index.html](stories/last-island-active/index.html), and root `index.html` now redirects to it. The original example is still preserved at [stories/last-island/index.html](stories/last-island/index.html). Serve the repository with `python -m http.server 8000`. `studio.json.default_story` intentionally remains `last-island` for legacy CLI compatibility; writers must explicitly pass `--story last-island-active`. The latest manuscripts, draft continuity and next handoff are in [stories/last-island-active/README.md](stories/last-island-active/README.md); these files do not imply automatic Canon or editorial approval.

Optional `data/state_history.json` records explicit baseline evidence and per-scene deltas. Replay uses only complete locally approved evidence before the target; missing history is UNKNOWN, and contradictions fail. Without that file, legacy snapshot behavior remains. Local status fields do not authenticate GitHub approval. The bounded v1 schemas allow editorial extension fields; cross-record checks remain in the semantic validators.
