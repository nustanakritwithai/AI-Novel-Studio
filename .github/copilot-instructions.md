# AI Novel Studio — GitHub Copilot instructions

This is a **Thai-language literary continuity project**, not a web game. See `AGENTS.md`, `STATE.md`, and `PROJECT.md` before writing. Markdown is the human-facing source; JSON in `data/` is the machine-readable ledger. Never treat old assistant proposals as LOCKED canon. Never treat planned scene beats as already approved prose. Make scoped edits on a feature branch; leave editor approval and merges to a human.

First run `python scripts/novelctl.py status`, `python scripts/novelctl.py brief SC-xxx`, then draft exactly that scene. After changes run `python scripts/novelctl.py check` and `python -m unittest discover -s tests -v`. Update affected scene, event and memory docs in the same reviewed PR if approved. `UNKNOWN != PASS`: distinguish actual gameplay evidence from fictional VR tournament rules.
