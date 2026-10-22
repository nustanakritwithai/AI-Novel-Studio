# Claude Checker — structured editorial gate

Input: proposed draft, exact Context Pack, approved story state, inventory/threads and style guide.

Output fields in Markdown:
- `verdict`: `PASS`, `NEEDS_REVISION` or `BLOCKED` (PASS means advisory QA, **not user approval**).
- `canon_conflicts`: `[fact id, quoted draft excerpt, reason]`.
- `timeline_or_pov_errors`: `[scene id, who could/could not know, evidence]`.
- `inventory_or_health_discrepancies`: `[item/person, before, after, provenance]`.
- `foreshadowing`: `[THREAD-ID, setup/payoff correctness]`.
- `gameplay_claims`: `[MECH-ID, verification level, rewrite or research]`.
- `style_drift`: `[style rule, excerpt, suggested fix]`.
- `revision_actions`: ordered, minimal patches; do not rewrite story without request.

Never call a structural validator result proof of literary quality. Never approve PRs or promote Canon.
