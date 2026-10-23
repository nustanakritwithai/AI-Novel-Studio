# Scene workflow v1 evidence

This folder records one synthetic, metadata-only evaluation of the supervised scene workflow. The sealed key was created before review dispatch; its pinned SHA-256 is `3e93a9854d86f436703d3196a45e4d98ed03330d84ba19f139afca217b0347d3`. `manifest.json` records the model runs, bounded adjudication, limitations, and byte lengths and SHA-256 hashes for every fixed JSON artifact in this folder except the manifest itself.

## Recorded result

The Q7 seeded report catches all five seeded critical faults as `CONTRADICTION` findings: K-CANON → Q7-001, K-KNOWLEDGE → Q7-002, K-INVENTORY → Q7-003, K-CONSTRUCTION → Q7-004, and K-APPROVAL → Q7-006. I compared each quoted draft locator with the numbered line in `packet-Q7.json`, then checked its context quote at `/author_planning_context/content`. The extra Q7-005 finding classifies the human-approval claim as `UNKNOWN`, because the packet cannot authenticate approval; it is recorded separately and is not counted as a critical hit.

The M2 clean control has zero findings and zero contradictions. The fresh R9 report after revision has zero findings. These counts describe only the reports preserved here; they are not an accuracy rate or a result across a broader set of scenes.

## Run and workflow boundaries

The recorded calls used `gpt-6-luna` with `xhigh` reasoning: a native planner, a requested synthetic fault writer, fresh fork-none Q7 and M2 reviewers, a native revision, and a fresh post-revision R9 rereviewer. The reviewers received an opaque packet and report contract. Fork-none blindness was procedural; shared-filesystem isolation was not enforced.

An initial fixture initialization failed its state contract before the sealed key was dispatched. Its failed material was retained privately and excluded; the preserved evaluation uses the corrected v2 fixture. A first native writer attempt referenced the wrong planner path and produced invalid output that was removed before evidence preservation. It was not used or scored. `raw/writer-v2.json` is the corrected output used in the recorded flow.

The flow ends at `OWNER_CHECKPOINT` with `BLOCKED_AUTHENTICATED_SIGNOFF_NOT_ESTABLISHED`. Human editorial approval is `UNVERIFIED`; historical source verification was not run; canon changes and ledger application remain unauthorized. The standalone proposal is `PROPOSED`, its world time is `UNKNOWN`, and its gate is blocked with apply false. The fixture Git anchor is local test data, not human approval. No human approval was run, and no changed post-merge workflow live proof exists.

The baseline commit was `cd548bdd93ed5f25562049fe7b43bdd6cca4ac3a`. Runtime code was uncommitted during capture; the final runtime working staged tree is `b64694118ea272f54c4bff8f2855fd7d91c80574`. The recorded model calls therefore reflect the captured local working tree, not an assertion that the runtime had been committed.

The tests in `tests/test_scene_workflow_evidence.py` verify the pinned key and artifact hashes, report-to-packet bindings and locators, recorded critical and clean-case counts, and the blocked owner/proposal boundary. They do not invoke a model, rerun semantic review, or authenticate human signoff.

Run them with:

```powershell
python -B -m unittest discover -s tests -p test_scene_workflow_evidence.py -v
```

The deterministic three-scene runner exercises its listed storyctl commands. It does not invoke scene-flow or review-check; those are covered by separate unit tests and the recorded native workflow artifacts above. Its PASS does not include model review or human approval.
