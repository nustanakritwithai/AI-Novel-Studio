# Continuity Ledger — approved material only

`ledger/index.json` is an **approved-only index**. An empty index means no complete episode has been approved. Never pre-populate planned story beats as episode summaries.

- `episodes/EP-xxx.md`: 150–300 Thai-word editorial target; record what *actually happened* in the approved prose, knowledge boundaries, health/location/inventory deltas, and open/closed plot threads. Count by an editor; the standard-library validator cannot count Thai words accurately.
- `chapters/CH-xxx.md`: curated hierarchical summaries of *approved* episode summaries; chapter entry must reference its component episode IDs.
- `books/BK-xxx.md`: curated book-level summaries; must not spoil episodes beyond target.
- `index.json`: each entry is a pointer to a file plus GitHub PR review provenance. No draft appears here.

Sample index entry **only after human review and merge**:

```json
{
  "id": "EP-001",
  "scene_ids": ["SC-001", "SC-002", "SC-003", "SC-004", "SC-005", "SC-006", "SC-007", "SC-008"],
  "summary_path": "ledger/episodes/EP-001.md",
  "approval": {
    "pr_number": 23,
    "approved_by": "ACTUAL_GITHUB_REVIEWER",
    "merge_commit": "0123456789abcdef0123456789abcdef01234567",
    "approved_at": "2026-10-22T12:00:00+07:00"
  }
}
```

These sample values are placeholders, **not a real approval**. Locally checking these fields does not prove GitHub review; use protected `main` with required reviewer approval for integrity. The approval record should be created from a real merged PR and reviewed in a separate update if merge SHA was unknown beforehand.

Commands:

```bash
python scripts/story_engine.py check
python scripts/story_engine.py pack SC-001 --recent 7 --out /tmp/context.md
python scripts/story_engine.py proposal EP-001 --out /tmp/EP-001-proposal.md
```

No database, API key or external service required. Draft proposals belong in a PR, not in this approved-only index.
