# AI Novel Studio — reusable continuity engine

E1 separates engine code from story datasets. E2 adds versioned registry schemas and optional state replay. The engine does not generate prose or approve canon. Use Python 3.11+ and install the pinned validation dependencies from official PyPI:

```bash
python -m pip install --index-url https://pypi.org/simple --only-binary=:all: -r requirements.txt
```

```bash
python scripts/storyctl.py new my-story --title "My story"
python scripts/storyctl.py --story my-story check
python scripts/storyctl.py --story my-story status
# After human-authored scene metadata exists:
python scripts/storyctl.py --story my-story pack SC-001 --out context.md
python scripts/storyctl.py --story my-story replay SC-001
```

`new` creates empty metadata registries, an empty approved ledger, and generic guidance. It writes no novel content and never overwrites an existing story. `story.json` uses versioned JSON to avoid introducing a YAML dependency. Gameplay mechanics/sources are an optional extension.

The legacy invocations still use the default story selected by `studio.json`:

```bash
python scripts/novelctl.py check
python scripts/story_engine.py pack SC-001 --out context.md
python -m unittest discover -s tests -v
```

See [the Thai E2 schema/replay guide and remaining roadmap](ENGINE_E2.md), [the E1 separation guide](ENGINE_E1.md), [engine instructions](AGENTS.md), and the [preserved Last Island example](stories/last-island/README.md). All 54 relocated example files are checked against a SHA-256 manifest of their original Git bytes. The original 43 regressions retain their assertions and now use the example root.

The existing Last Island dashboard is at [stories/last-island/index.html](stories/last-island/index.html); root `index.html` redirects there for compatibility. Serve the repository with `python -m http.server 8000`. Historical example documents retain their original bytes and command snippets; use this guide for current engine paths.

Optional `data/state_history.json` records explicit baseline evidence and per-scene deltas. Replay uses only complete locally approved evidence before the target; missing history is `UNKNOWN`, and contradictions fail. Without that file, legacy snapshot behavior remains. Local status fields do not authenticate GitHub approval. Semantic prose checking, authenticated provenance (E5), and autonomous LLM workflows remain outside this milestone. The bounded v1 schemas allow editorial extension fields; cross-record checks remain in the existing semantic validators.
