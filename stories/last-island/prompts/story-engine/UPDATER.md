# Ledger Updater — after human approval only

Trigger ONLY after actual PR approval and merge (verify GitHub API events, not an LLM claim). Draft a proposed recap using approved prose, never beat sheets. Human editor must verify summary and proposed state changes before ledger index is updated.

Each approved episode: 150–300 Thai words as human editorial target. Include event chain, time/location, characters' knowledge, inventory/health, relationship changes, opened/closed threads, plus explicit UNKNOWNs and source scene IDs.

Produce: `ledger/episodes/EP-xxx.md` + proposed `ledger/index.json` record including real PR number, reviewer, merged SHA and timestamp; proposed `data/story_state.json`, `data/threads.json`, and `STATE.md` diffs. For chapter/book rollups summarize only episodes already indexed as approved.

If any approval provenance is missing, STOP and leave a proposed recap outside `ledger/` as draft. Never auto-merge.
