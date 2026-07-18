# Changelog

All notable changes to Lodestar are documented here.

## [0.1.0] — Unreleased

Initial version — not yet published.

### Layers & commands
- Five-layer architecture: thin root router, on-demand knowledge (docs + skills), Graphify code graph, enforced guardrails, role-based agents.
- Four generator commands over one catalog + picker + manifest engine: `/lodestar-init`, `/onboard-repo`, `/guardrails`, `/gen-agents`.

### Catalog (30 entries)
- **Universal core (11)** — guardrails `block-env-files`, `no-hand-edit-lockfiles`, `protect-generated-files`, `verifier-before-commit`, `commit-message-style`; agents `reviewer`, `feature-planner`, `feature-orchestrator`, `implementer`; skills `planning-workflow`, `architecture-overview`.
- **Node·GraphQL·React·React Native pack (12)** — dbmate/GraphQL/CRACO/React Native guardrails, agents, and skills.
- **Python·Django pack (7)** — Django migration guard, python autolint, migration-writer / drf-endpoint-writer / pytest test-writer agents, django-backend-standards + drf-api-contract skills.
- Grouped index in `catalog/CATALOG.md`; core-vs-packs tiers documented in `catalog/README.md`.

### Templates & docs
- Thin `CLAUDE.md` router, `_shared/` doc stubs (GraphQL + REST API contract, env matrix, auth, runbook, glossary), `repo-map.md`, per-repo conventions, per-workspace MCP configs.
- `.claude/lodestar.manifest.json` reproducible lockfile; `install.sh`; docs (`ARCHITECTURE`, `CONCEPTS`, `EXTENDING`) and an end-to-end example.

[0.1.0]: https://github.com/OWNER/lodestar
