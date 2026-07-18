# Changelog

All notable changes to Lodestar are documented here.

## [0.3.0] — Unreleased

Distribution & updatability pass — Lodestar is now branded, collision-safe, and updatable in place (no more delete-and-re-clone).

### Added
- **`/lodestar-update`** — pulls the latest source and re-syncs the kit (catalog, templates, commands, guardrail engine) **without touching anything you generated** (rules, agents, docs, manifest). Reports new catalog entries to adopt.
- **Re-runnable installer** — `install.sh` is now idempotent (no directory nesting), refreshes an already-installed guardrail engine, cleans up pre-rename command files, and records the source path + version so updates are a one-command re-sync.
- **CI / release pipeline** (`.github/`) — trunk-based: `ci.yml` (shellcheck, catalog + `VERSION`↔`CHANGELOG` validation, guardrail-engine smoke test) gates PRs; `release.yml` auto-tags and cuts a GitHub Release when `VERSION` bumps on `main`; `guard-default-branch.yml` is a direct-push backstop. A `protect-main` branch ruleset (`.github/rulesets/`) enforces PR-before-merge + the `ci` check + no force-push. See [`docs/CI.md`](docs/CI.md).

### Changed
- **Branded, collision-safe commands** — namespaced under a `lodestar-` prefix: `/onboard-repo` → `/lodestar-onboard`, `/guardrails` → `/lodestar-guardrails`, `/gen-agents` → `/lodestar-agents` (`/lodestar-init` unchanged). Avoids clashing with other tools' commands. Existing installs pick up the rename on the next `/lodestar-update`.

## [0.2.0] — Unreleased

Architecture, portability, and adaptivity pass over the 0.1.0 baseline. Catalog now **38 entries** — 17 universal · 14 Node·GraphQL·RN · 7 Python·Django.

### Added
- **Self-contained guardrail engine** — `emits: rule` guardrails now live in `.claude/guardrails/*.md` (a folder, not the `.claude/` root) enforced by a bundled PreToolUse hook (`templates/hooks/lodestar-guardrails.py`). **No external plugin dependency**; needs only Python 3 (stdlib). Tested against every catalog pattern.
- **Adaptive pickers** — `/lodestar-guardrails` and `/lodestar-agents` now recommend entries from repo signals, not just a static `recommended` flag. New capability detectors in `/lodestar-onboard`: `has-gitleaks`, `has-precommit`, `has-prettier`, `has-frontend`, `has-auth`.
- **Universal agents (+4)** — `security-auditor` (read-only OWASP-shaped audit; can call `/security-review`) and `docs-writer` (keep docs in sync), both `stacks: [all]`; plus frontend-scoped `ui-designer` (loads the `frontend-design` plugin skill) and `accessibility-reviewer` (WCAG 2.2 AA). `/lodestar-agents` resolves an agent's `loads:` dependencies and prompts to install a missing plugin (install-or-proceed).
- **Markdown architecture fallback** — when Graphify is absent, `/lodestar-onboard` offers to generate `architecture/overview.md` instead of requiring the tool (install-or-proceed prompt). Graphify confirmed to install at user level, no sudo.
- **Cost & model guidance** — per-command `effort` defaults (`low` for scaffolding, `medium` for onboard) and a README section; the biggest budget saver is installing Graphify (offloads the one reasoning-heavy step).
- **Evidence-based doc pre-fill** — `/lodestar-onboard` now fills the per-repo and `_shared/` docs from *cited* repo evidence (deps, routes/resolvers/serializers, `.env.example`, the graph) and leaves `TODO` only for the genuinely unknowable (TTLs, prod URLs, domain semantics, "why"), instead of dropping blank stubs. Never invents — a wrong doc is worse than an honest TODO.

### Changed
- **Stack-neutral universal core** — shared docs no longer assume GraphQL. The contract spine is a single stable `docs/_shared/api-contract.md`, seeded generic at init and enriched to GraphQL/REST only when that stack is actually detected. `repo-map`, `auth-model`, `env-matrix`, `local-setup`, and `glossary` de-GraphQL'd.
- Renamed the guardrail emit keyword `emits: hookify` → `emits: rule`.

### Fixed
- `block-env-files` carve-out now actually allows template files (`.env.example`/`.sample`/`.template`/`.dist`/`.defaults`) — the old regex blocked them.
- File guardrails now match the edited **path** as intended (the previous plugin matched edited *content*, so path-based rules never fired).
- Corrected stale `<api>-contract.md` placeholders and a Graphify output filename in the docs.

## [0.1.0] — Unreleased

Initial version — not yet published.

### Layers & commands
- Five-layer architecture: thin root router, on-demand knowledge (docs + skills), Graphify code graph, enforced guardrails, role-based agents.
- Four generator commands over one catalog + picker + manifest engine: `/lodestar-init`, `/lodestar-onboard`, `/lodestar-guardrails`, `/lodestar-agents`.

### Catalog (34 entries)
- **Universal core (15)** — guardrails `block-env-files`, `no-hand-edit-lockfiles`, `protect-generated-files`, `verifier-before-commit`, `commit-message-style`, `block-destructive-commands`, `block-secret-files`, `protect-default-branch`, `scan-secrets-before-commit`; agents `reviewer`, `feature-planner`, `feature-orchestrator`, `implementer`; skills `planning-workflow`, `architecture-overview`.
- **Node·GraphQL·React·React Native pack (12)** — dbmate/GraphQL/CRACO/React Native guardrails, agents, and skills.
- **Python·Django pack (7)** — Django migration guard, python autolint, migration-writer / drf-endpoint-writer / pytest test-writer agents, django-backend-standards + drf-api-contract skills.
- Grouped index in `catalog/CATALOG.md`; core-vs-packs tiers documented in `catalog/README.md`.

### Templates & docs
- Thin `CLAUDE.md` router, `_shared/` doc stubs (GraphQL + REST API contract, env matrix, auth, runbook, glossary), `repo-map.md`, per-repo conventions, per-workspace MCP configs.
- `.claude/lodestar.manifest.json` reproducible lockfile; `install.sh`; docs (`ARCHITECTURE`, `CONCEPTS`, `EXTENDING`) and an end-to-end example.

[0.3.0]: https://github.com/Miyunecadz/lodestar
[0.2.0]: https://github.com/Miyunecadz/lodestar
[0.1.0]: https://github.com/Miyunecadz/lodestar
