# AI Novel Studio — GitHub Copilot instructions

This repository contains a reusable continuity engine and separate story roots. Read root `AGENTS.md` and `ENGINE_E1.md` for engine work; story-specific instructions and data live under `stories/<slug>/`. Never import another story's rules, style, or history. Engine-only tasks must use synthetic metadata and create no narrative prose.

Use `python scripts/storyctl.py --story <slug> check`, `pack <scene-id>`, or `status`. Legacy invocations resolve the default from `studio.json`; explicit `--root` datasets remain supported. Run both validators and `python -m unittest discover -s tests -v`. Structural checks do not authenticate human approval or assess prose quality. Never promote proposals or planned beats into approved history.
