# AI Novel Studio — reusable continuity engine

A local continuity engine with isolated story datasets. E1 separates story roots, E2 adds versioned registry schemas and optional state replay, and E3/E4 adds local review evidence, diagnostics, and generic human workflow contracts. Schema migration, authenticated GitHub approval, rollup, and full workflow evaluation remain deferred. The engine does not generate prose or approve canon.

Use Python 3.11+ and install the pinned validation dependencies from official PyPI:

```bash
python -m pip install --index-url https://pypi.org/simple --only-binary=:all: -r requirements.txt
python scripts/storyctl.py new my-story --title "My story"
python scripts/storyctl.py --story my-story check
python scripts/storyctl.py --story my-story status
python scripts/storyctl.py --story my-story doctor --out .local/doctor.json
```

`new` creates empty metadata registries, an empty approved ledger, and generic guidance. It writes no novel content and never overwrites an existing story. An empty scaffold has no target scenes: humans must supply the required story/scene metadata before target-specific commands can succeed. `story.json` uses versioned JSON. Gameplay mechanics/sources are an optional extension.

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

New review/doctor file output is restricted to the selected workspace's ignored `.local/` directory (stdout is also available). Bundles can contain unpublished draft and context text. Do not attach them to a public PR or send them externally without explicit user authorization.

The legacy invocations still use the default story selected by `studio.json`:

```bash
python scripts/novelctl.py check
python scripts/story_engine.py check
python scripts/story_engine.py pack SC-001 --out context.md
python -m unittest discover -s tests -v
```

See the [Thai E3/E4 guide and capability coverage](ENGINE_E3_E4.md), [agent handoff runbook](docs/AGENT_RUNBOOK.md), [E2 schema/replay contract](ENGINE_E2.md), [E1 separation guide](ENGINE_E1.md), [engine instructions](AGENTS.md), and [preserved Last Island example](stories/last-island/README.md). All 54 relocated example files are checked against a SHA-256 manifest of their original Git bytes. The original 43 regressions retain their assertions and use the example root. Record actual final tests and exact-head CI in each PR; these commands are not a test result.

The existing Last Island dashboard is at [stories/last-island/index.html](stories/last-island/index.html); root `index.html` redirects there for compatibility. Serve the repository with `python -m http.server 8000`. Historical example documents retain their original bytes and command snippets; use the current guides for engine paths.

Optional `data/state_history.json` records explicit baseline evidence and per-scene deltas. Replay uses only complete locally approved evidence before the target; missing history is UNKNOWN, and contradictions fail. Without that file, legacy snapshot behavior remains. Local status fields do not authenticate GitHub approval. The bounded v1 schemas allow editorial extension fields; cross-record checks remain in the semantic validators.
