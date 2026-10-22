# Workflow — Writer → Checker → Editor

## Change types

- `research/...`: research only; never silently change canon
- `scenes/...`: outline scene cards; changes to locked beats require editor approval
- `drafts/...`: prose work (draft only)
- `data/canon.json`: LOCKED facts require user authority recorded in PR
- `data/story_state.json`: only advance to approved-scene after prose review
- `data/events.json`: must match scene effects; event status should be synchronized after approval

## Review checklist

- [ ] User LOCKED requirements unchanged
- [ ] Scene starts at logical place/time based on earlier approved scenes
- [ ] POV knows only events personally experienced or credibly learned
- [ ] Any resources gained/spent have a corresponding scene event
- [ ] Injuries/healing and base progress are carried forward
- [ ] New character names/relationships are proposed, not automatically locked
- [ ] Gameplay source has verified URL + timestamp + actual confidence level
- [ ] World tournament 100 participants not mistakenly treated as base game/current episode
- [ ] Unit tests and validator pass
- [ ] Human approval recorded before merge/canon promotion

## Retcon

Never erase a contradiction silently: add a change entry to `bible/RETCON_LOG.md` listing old text, new text, reason, affected scenes, and author approval. Update dependent cards and state in same PR.
