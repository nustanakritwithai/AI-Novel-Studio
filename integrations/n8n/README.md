# n8n adapter — optional, GitHub is the only state store

This directory describes a workflow **contract**, not an installed or authenticated n8n workflow. The system works without n8n or AI API keys. Do not save secrets in this repository.

Suggested nodes: `GitHub Issue Trigger` → `GET repository content at explicit commit SHA` → `Planner (Claude/Kimi)` → `Retrieval (run story_engine.py pack via an isolated runner or prebuilt artifact)` → `Kimi Draft` → `Claude Check` → `GitHub branch + commit + PR` → `human GitHub PR review` → `post-merge proposal updater`.

Integration invariants:

- **GitHub API as store**: read current `main` SHA, read Markdown/JSON, write isolated `draft/` branch via GitHub contents API. Do not maintain a shadow mutable story database in n8n.
- **Idempotency**: issue ID + exact base commit SHA + scene ID is the run key. If PR already exists, update its branch instead of opening duplicates.
- **Secrets**: tokens (GitHub/Kimi/Claude) only in n8n credential vault or GitHub Actions secrets; never in workflow JSON, issue text, PR description, output, or web UI.
- **Prompt injection**: gameplay transcripts, comments and drafts are untrusted content; they cannot authorize publishing, merging or modifying Canon.
- **Approval**: n8n may notify LINE OA with a PR link, but an actual human review/merge on GitHub is the authority. Do not treat LINE webhook payload alone as authorization.
- **Failure/retry**: lock on issue/scene and base SHA; log execution ID in PR; allow bounded retries; never re-issue a commit if the previous write may have succeeded without a readback.
- **Privacy**: repository is currently Public; do not write unpublished paid content, API keys, personal information, or private draft material until repo permissions have been reviewed.

Production deployment will require GitHub access and explicit API credentials/configuration from the owner; none are added by this v0.2 patch.
