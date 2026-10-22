# Recorded E6 synthetic evaluation

This record separates the command workflow from an actual independent review of synthetic assertion metadata. No real novel, human editorial approval, or model-quality score is supplied. Baseline engine: PR #7, commit `3d915241203aa762f2b3c8fc3d3c68170ba5189e`. Final command/test/CI evidence belongs to the E6/E7 draft PR.

## Blind input and sealing

The [answer key](answer_key.json) was written and hashed before dispatching either reviewer. SHA-256: `d71842f3fe3a3a2679f8eb45df65561d97ce45fe2b9d781802f4f3b94593322f`. It has not been changed after seeing the findings. [Manifest](manifest.json) binds both packets and the normalized SC-002 context pack.

Two separate fresh native agents used `fork_turns=none`. Each received only its own packet path, a neutral review contract and its report destination. Neither received the key, author reasoning, candidate role, expected fault count or the other report. Both raw reports state that only their assigned packet was consulted. This is procedural blindness on a shared filesystem, not OS-enforced isolation or a human review.

| Input | Reviewer task | Raw output | SHA-256 |
| --- | --- | --- | --- |
| [A94](packets/A94.json) | `/root/review_a94` | [A94 report](raw/A94.json) | `05e49bda1680907bc9b2facbbc743d8192b85e674a9461f2cbc931ddf0d05e94` |
| [B17](packets/B17.json) | `/root/review_b17` | [B17 report](raw/B17.json) | `c94e1839ce8e085ea2a4c224875b93edbfc6a02dc12dac74ac4b850320d7c0c3` |

The scoped `.gitattributes` rule preserves exact evaluation bytes across Windows/Linux checkouts. Hashes detect later byte changes; they do not prove secrecy or reviewer identity.

## Actual findings and misses

After both reports completed, the implementation agent compared their evidence with the sealed key. This manual [adjudication](adjudication.json) is separate from the reviewers' preserved raw output.

| Seeded fault | Actual finding | Result |
| --- | --- | --- |
| C-01: gate opens remotely without physical token | F-01 cites FACT-GATE's physical-token-only rule and no override | Caught |
| C-02: Unit A already knows the code before SC-002 | F-02 cites FACT-KNOWLEDGE and `token_code_known: false`; UNKNOWN does not grant knowledge | Caught |
| C-03: two tokens at SC-002 opening | F-03 compares assertion with replay balance zero and no eligible gain | Caught |
| C-04: local labels/claimed Git commit establish human-approved canon | F-04 rejects this inference, preserves UNKNOWN, and refuses promotion | Caught |
| C-05: fixed red gate is blue | F-05 cites FACT-COLOR and red state; reviewer assigned medium severity, retained verbatim | Caught |

All five planted faults were identified; no seeded miss or additional finding was recorded. The pre-sealed key treated all five as critical to its constraints; finding severity is the reviewer's own prioritization and was not rewritten to match it.

The B17 clean control returned `findings: []`: **zero reported false positives**. Its separate uncertainty about actual human review history is retained and is appropriate to the packet's unauthenticated approval boundary. No statistical generalization follows from one control.

## Command acceptance and readiness

Run `python scripts/acceptance.py --out .local/e6-acceptance` in a fresh output directory. The runner exercises actual CLI commands and records exit codes, synthetic Git anchors, artifact hashes and unchanged source manifests. It always labels its own semantic evaluation NOT_RUN and human editorial approval BLOCKED; it does not fabricate the independent findings above.

The actual Windows/Python 3.12.14 run at `.local/e6-workflow-proof` passed all **17 command steps**: empty new/check, fixture new/check, four local Git preparation/anchor reads, pack, brief-review, propose, three scene-start replays, rollup, doctor, and final check. [Command evidence](command_run.json) retains every actual exit code (all zero), eight output digests and the unchanged 53-file synthetic source manifest. Only machine-specific executable/engine/run paths are replaced by declared placeholders for publication. The real local fixture anchor is `f4957f2985ca9201c6fb060118d88bf19ff5f0ac`; it is not a GitHub merge or human decision. The final runner's normalized SC-002 pack was recomputed and matches the pre-dispatch packet's context hash `77c83c8db3f066bf4e29fb35550217551bb71fe8037fa076794593bcb232c23b`.

The Thai onboarding guide's separate fresh-workspace smoke passed seven checks: new, empty check, status and doctor succeed; duplicate new, pack of an absent target and missing-story check reject as expected. [Onboarding evidence](onboarding_run.json) retains actual command results with machine paths replaced. All 21 scaffold source files remained unchanged. No dependency installation or network access was needed for either exercise; existing pinned task dependencies were used.

This bounded semantic case passed for explicit metadata assertions only. It does not test literary prose, style quality, every language, multiple seeds or repeated reviewers. CI can recheck artifact integrity and command tests; it does not call a reviewer again. Human signoff remains **BLOCKED/NOT SUPPLIED**. See [readiness gates](../../docs/ENGINE_READINESS.md) and [E6 procedure](../../ENGINE_E6.md) before claiming broader readiness.
