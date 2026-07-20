# Changelog

All notable changes to Lodestar are documented here.

## [0.5.0] — Unreleased

Repo layout pass — separate what Lodestar *ships* from how this repo is *built*. Purely structural: the installed workspace is byte-identical to 0.4.0.

### Changed
- **Kit source now lives under `kit/`.** `catalog/`, `templates/`, and the `lodestar-*` command specs (previously in `.claude/commands/`) moved to `kit/catalog/`, `kit/templates/`, `kit/commands/`. `install.sh`, the CI validator, the engine smoke test, and doc/README links were repointed. The target-workspace layout it produces (`.lodestar/…`, `.claude/commands/…`) is unchanged.
- **Root `.claude/` is now this repo's own dev tooling**, not a product surface — free for contributor agents/skills/workflows/settings. See `CONTRIBUTING.md`. `install.sh` only ever copies from `kit/`, so nothing in `.claude/` can leak into the product. (Side effect: the `lodestar-*` commands are no longer live while developing this repo — install into a scratch workspace to exercise them.)

## [0.4.0] — Unreleased

Graph-freshness pass — the onboarded architecture map now stays in sync with the code instead of silently drifting. Because `CLAUDE.md` tells agents to *trust* the graph over re-reading source, a stale map was a correctness risk, not just staleness. Closes the core of #2.

### Added
- **`/lodestar-freshness`** — opt-in, transport-aware installer for map freshness. Detects the repo's git-hook manager (lefthook / husky / `core.hooksPath` / plain `.git/hooks`) and wires freshness in **without clobbering** existing hooks.
- **graphify lockstep pre-commit rebuild** (`templates/hooks/lodestar-graph-refresh.sh`) — on commit, rebuilds any graphify repo with **staged** code and stages the refreshed `graph.json`/`GRAPH_REPORT.md`/`graph.html` into the *same* commit, so code and map move together on every branch/checkout/pull. Monorepo-aware (only changed repos rebuild), offline (~1s), and **never blocks a commit** — a missing `graphify` CLI or a failure degrades to a hint (`--no-verify`/`LEFTHOOK=0` remain the escape hatch).
- **Union merge driver** for graphs (`templates/git/gitattributes-graphify`) — `.gitattributes` marks `graph.json`/`GRAPH_REPORT.md` for `merge=graphify-union` so two branches that both rebuilt a graph merge cleanly; falls back to normal 3-way merge where the per-clone driver isn't registered.
- **Markdown-mode drift detection** (`templates/hooks/lodestar-freshness-check.py`) — offline, stdlib-only. Diffs `mapping.lastMappedSha..HEAD` for code under each repo and reports drift (with `--exit-code` for a CI gate). No silent LLM rebuilds.
- **`/lodestar-refresh <repo>`** — on-demand re-map for markdown repos (re-runs the mapping pass, preserving human prose) and manual graphify rebuilds; re-stamps the fingerprint.
- **Freshness fingerprint in the manifest** — `/lodestar-onboard` now records each repo's `architecture`, `docs` path, and `mapping` (`lastMappedSha`/`lastMappedAt`); `/lodestar-freshness` records a `freshness` block (hook manager, lockstep vs drift-checked repos, merge driver).

### Changed
- **`install.sh` / `/lodestar-update`** re-sync the freshness hooks (`lodestar-graph-refresh.sh`, `lodestar-freshness-check.py`) — but only if a workspace already installed them, mirroring the guardrail-engine refresh. Generated content (manifest, `.gitattributes`, git-hook wiring) is never touched.
- `docs/ARCHITECTURE.md` documents the freshness layer, the manifest fingerprint, and updates the roadmap; `catalog/CATALOG.md` lists the new templates.

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

[0.5.0]: https://github.com/Miyunecadz/lodestar
[0.4.0]: https://github.com/Miyunecadz/lodestar
[0.3.0]: https://github.com/Miyunecadz/lodestar
[0.2.0]: https://github.com/Miyunecadz/lodestar
[0.1.0]: https://github.com/Miyunecadz/lodestar
