# Story Engine v0.2 — GitHub-only design and operating contract

**Scope:** Continue the existing AI Novel Studio repository, keeping Last Island as its first project. No external database. GitHub (versioned Markdown/JSON) is the authoritative store; GitHub PRs are the human approval boundary. n8n, Claude and Kimi are **optional callers**, not storage. There is no configured production API integration yet.

## Why separate source, narrative and approval?

1. **Story Canon** `data/canon.json` contains LOCKED writer decisions. `UNKNOWN ≠ PASS`. Do not mark AI suggestions as LOCKED.
2. **Narrative** `data/episodes.json`, `data/scenes.json`, `drafts/*` contain planned/draft/approved prose, with each scene's POV, time, items and story effects tracked.
3. **Approved ledger** `ledger/index.json` and linked Markdown contain recaps of approved prose only. Never invent a recap when an episode is still an outline.
4. **Gameplay evidence** `research/*`, `data/sources.json` and `data/mechanics.json` have access/verification levels; streaming footage is reference, not verbatim dialogue to copy.
5. **Style** `bible/STYLE_GUIDE.md` is a reusable writer/reviewer contract. Major deviations require editorial review.

The supplied alternate-story example about magic levels or Akasara belongs to a **separate book/story bible**, not Last Island. No accidental mixing of settings or lore.

## Process per episode / scene

```text
GitHub Issue (assigned SC-ID)
   ↓
Planner (scene beats, open questions; no canon write)
   ↓
Retriever (python scripts/story_engine.py pack SC-xxx)
   ↓
Kimi or other writer (drafts/... on draft branch)
   ↓
Claude or reviewer (Continuity Report, cite specific IDs)
   ↓
Revise (same branch; re-run check)
   ↓
GitHub PR + required human approval
   ↓
Merge approved draft; prepare recap + state delta (separate review if needed)
   ↓
Approved-only episode ledger and hierarchy updated with source PR provenance
```

**Important:** GitHub Actions `PASS` means structural checks passed, **not** that prose quality, authorship or approval passed. Configure branch protection/rulesets on `main` to *require at least one human review and passing checks*; the scripts cannot authenticate human intent merely from JSON.

## Prompt contracts

- Planner: must cite `SC-xxx`, `FACT-xxx`, `THREAD-xxx`, and show causal preconditions and knowledge/POV limits.
- Kimi Writer: write only requested scene, with narrative beat changes as PROPOSED.
- Claude Checker: report violations of LOCKED canon, implausible inventory changes, missing setup/payoff, gameplay claims without source, POV leakage, style drift.
- Human: GitHub PR review (or mobile GitHub app). `REQUEST_CHANGES` loops to revision; `APPROVE` plus merge authorizes integration.
- Updater: **only after approval** propose new ledger entry, index references, and state deltas with source scene IDs and PR provenance. Never silently merge.

`prompts/story-engine/` gives independent prompts for each role. `integrations/n8n/README.md` describes GitHub REST based optional workflow without a state database.

## Memory without token bloat

`story_engine.py pack SC-006 --recent 7` includes mandatory locked facts and focused scene card (via `novelctl`), style guide, last ≤7 approved episode summaries, and approved chapter/book rollups that **end before** the target. Drafts, planned future events and speculative lore are not promoted into approved memory. For first episode, prior-approved ledger is deliberately empty.

When context exceeds the explicit character budget the command fails instead of silently discarding protected facts. Use narrower target or fewer approved episodes.

## Onboarding next AI

1. Read `AGENTS.md`, `STATE.md`, `STORY_ENGINE_V02.md` and scene card.
2. Run `python scripts/novelctl.py status`, then `python scripts/story_engine.py pack SC-001 --out /tmp/SC-001-pack.md`.
3. Write SC-001 in a branch; never change `main` directly.
4. Run existing and new checks, then open PR and wait for author approval.

## Non-goals v0.2

- No full autonomous writing or API calls.
- No LINE approval implementation yet; GitHub PR approval is authoritative in this version.
- No automatic summarizer that falsely asserts a planned scene already occurred.
- No new central server or external state database.
