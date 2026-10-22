# AI Novel Studio — reusable continuity engine

E1 separates engine code from story datasets. It does not generate prose or approve canon. Python 3.11+ and the standard library are sufficient.

```bash
python scripts/storyctl.py new my-story --title "My story"
python scripts/storyctl.py --story my-story check
python scripts/storyctl.py --story my-story status
# After human-authored scene metadata exists:
python scripts/storyctl.py --story my-story pack SC-001 --out context.md
```

`new` creates empty metadata registries, an empty approved ledger, and generic guidance. It writes no novel content and never overwrites an existing story. `story.json` uses versioned JSON to avoid introducing a YAML dependency. Gameplay mechanics/sources are an optional extension.

The legacy invocations still use the default story selected by `studio.json`:

```bash
python scripts/novelctl.py check
python scripts/story_engine.py pack SC-001 --out context.md
python -m unittest discover -s tests -v
```

See [the Thai E1 guide and E2–E7 acceptance criteria](ENGINE_E1.md), [engine instructions](AGENTS.md), and the [preserved Last Island example](stories/last-island/README.md). All 54 relocated example files are checked against a SHA-256 manifest of their original Git bytes. The original 43 regressions retain their assertions and now use the example root.

The existing Last Island dashboard is at [stories/last-island/index.html](stories/last-island/index.html); root `index.html` redirects there for compatibility. Serve the repository with `python -m http.server 8000`. Historical example documents retain their original bytes and command snippets; use this guide for current engine paths.

E1 does not implement historical state reconstruction, authenticated GitHub approval provenance, semantic prose checking, or autonomous LLM workflows. Existing structural validators are reused; a full schema and evaluation suite remain roadmap work.
