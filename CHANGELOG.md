# Changelog

All notable changes to Lodestar are documented here.

## [0.2.1] — 2026-07-18

### Added
- `commit-message-style` guardrail (universal core): one-line commit messages, no `Co-Authored-By` trailer. Ships `warn` / not-recommended (opinionated style); flip to `block` / `recommended: true` to taste. Universal core is now 11 entries (30 total).

## [0.2.0] — 2026-07-18

### Added
- **Universal core vs stack packs** signposting: `catalog/CATALOG.md` groups every entry into a universal core (`stacks: [all]`) plus stack packs; `catalog/README.md` explains the tiers.
- **Python·Django stack pack** (7 entries): guardrails `block-edit-applied-migrations-django`, `python-autolint-on-edit`; agents `migration-writer-django`, `drf-endpoint-writer`, `test-writer-python`; skills `django-backend-standards`, `drf-api-contract`; plus a `rest-api-contract.md` shared-doc template.
- Stack detectors for `python-django`, `python`, `drf`, `has-pytest`, `has-python-lint` in `/onboard-repo`.

### Changed
- `no-hand-edit-lockfiles` broadened from JS-only to cover Python/Rust/Go/Ruby/PHP lockfiles, making the universal `[all]` tag honest.
- Catalog now totals **29 entries** — 10 universal, 12 Node·GraphQL·RN, 7 Python·Django.

## [0.1.0] — 2026-07-18

Initial release.

### Added
- **Five-layer architecture**: thin root router, on-demand knowledge (docs + skills), Graphify code graph, enforced guardrails, role-based agents.
- **Three generator commands** over one shared engine (detect → filter → pick → write → record):
  - `/lodestar-init` — scaffold the router, `docs/_shared/`, and `repo-map.md`.
  - `/onboard-repo` — detect a repo's stack, generate its Graphify graph, file docs, install matching skills.
  - `/guardrails` — stack-aware picker; hard-block safety rules, warn on quality.
  - `/gen-agents` — stack-aware picker for role-based agents.
- **Starter catalog**: 8 guardrails, 8 agent roles, 6 skills — defaults tuned for a Node/GraphQL + React + React Native workspace.
- **Templates**: thin `CLAUDE.md` router, `_shared/` doc stubs (API contract, env matrix, auth, runbook, glossary), `repo-map.md`, and per-workspace MCP configs.
- **Manifest** (`.claude/lodestar.manifest.json`) as a reproducible lockfile of enabled entries.
- `install.sh`, full docs (`ARCHITECTURE`, `CONCEPTS`, `EXTENDING`), and an end-to-end example.

[0.1.0]: https://github.com/OWNER/lodestar/releases/tag/v0.1.0
