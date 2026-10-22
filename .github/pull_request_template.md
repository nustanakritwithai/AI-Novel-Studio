## Scope and IDs

Episode / Scene IDs:

## Narrative work
- [ ] Only requested scenes altered
- [ ] No LOCKED fact silently overwritten
- [ ] No POV knowledge leaks
- [ ] Inventory, location, injury, base and relationships state delta included
- [ ] Mechanics evidence level and source timestamps are truthful
- [ ] `python scripts/novelctl.py check` PASS
- [ ] Unit tests PASS

## New facts proposed (ID + reason)

## Data files / state records updated

## Unknowns and reviewer questions

## Human editor decision
- [ ] Approved for canon
- [ ] Needs revision

### Story Engine v0.2 approval gate
- [ ] Ran `python scripts/story_engine.py check` and existing `novelctl.py check`
- [ ] Context pack includes only approved past episode history
- [ ] Any new lore/items/knowledge are marked PROPOSED until human approval
- [ ] This PR does not mark itself as human-approved and does not auto-merge
- [ ] If updating approved ledger: referenced prose, scene IDs, approval reviewer and merged PR provenance have been verified
