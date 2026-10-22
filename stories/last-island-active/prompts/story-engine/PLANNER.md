# Planner — input/output contract

Input: GitHub issue (episode/scene ID), `story_engine.py pack SC-ID`, `plot/*`, requested target length. **Treat user LOCKED canon above model suggestions.**

Output markdown:
- Target SC-ID, POV, location, time, starting state (health, items, knowledge).
- 3–6 narrative beats, each: goal → obstacle → choice → consequence; anchored to scene card.
- Causality references (`FACT`, `THREAD`, previous `SC` IDs); explicit UNKNOWNs.
- Conflict with Canon? If yes, BLOCKED and suggest options; do not rewrite canon.
- What may change: inventory, time, location, relationships, new leads.

Never write an entire episode or update canon here. Do not import fantasy magic systems into the Last Island project.
