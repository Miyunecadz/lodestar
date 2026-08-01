# Catalog Index — Universal Core & Stack Packs

Lodestar's catalog is organized into a **universal core** that works on any stack, plus **stack packs** whose entries activate only when a matching stack is detected. The `stacks:` field on each entry is what the pickers filter on — an entry never appears on a workspace whose stacks don't match, and the guardrail engine re-checks `stacks` at match time so a pack rule cannot fire in the wrong repo of a mixed workspace.

> Adopting Lodestar on a new stack? You get the **universal core** immediately. Then either add a stack pack below (if one fits) or author your own — see [`../../docs/EXTENDING.md`](../../docs/EXTENDING.md). Packs compose: a Django API behind a React admin panel uses the **Python·Django** and **Node·GraphQL·RN** packs side by side.

Totals: **50 entries** — 18 universal · 15 Node·GraphQL·React·RN·frontend · 7 Python·Django · 7 Laravel·PHP · 3 Next.js.

---

## 🛡 Enforcement surface

A guardrail is only as universal as the hook that enforces it. Every entry declares a `surface`:

| `surface` | Enforced by | Holds for |
|---|---|---|
| `agent` | `lodestar-guardrails.py` (PreToolUse) | Claude's `Bash`/`Edit`/`Write`/`MultiEdit` |
| `commit` / `both` | `lodestar-precommit-check.py` (pre-commit) | **any committer** — teammate, IDE, CI |
| `permission` | Claude Code core, via `permissions.deny` | Claude tool-use, **every tool including `Read`** |

An entry may name several (`surface: [agent, commit, permission]`); `both` is the legacy spelling of `[agent, commit]`.

**Commit-surface entries**: `block-env-files` · `block-secret-files` · `block-edit-applied-migrations` · `block-edit-applied-migrations-django` · `block-commit-to-default-branch` · `scan-secrets-before-commit`. Installed into the repo's git-hook manager by `/lodestar-guardrails`.

**Permission-surface entries**: `block-env-files` · `block-secret-files` — the two rules whose titles promise "never **read** this", which a hook cannot deliver. Applied to `.claude/settings.json` by `lodestar-permissions.py`. Neither drops its hook surface: a deny glob has no negation, so it cannot express `block-env-files`' "allow `.env.local.example`" carve-out, and the precise regex stays responsible for the write side.

Everything else is `agent`-only, each for a stated reason in its body — usually that legitimate tooling commits those files (`yarn.lock`, `db/schema.sql`, and the freshness hook's own `graph.json`), so a commit-time block would stop correct work. See [`docs/EXTENDING.md`](../../docs/EXTENDING.md).

## 🌐 Universal core — `stacks: [all]` (works on any stack)

| Kind | Entry | Purpose |
|---|---|---|
| guardrail | `block-destructive-commands` | block irreversible shell commands (`rm -rf`, `reset --hard`, `DROP …`) |
| guardrail | `protect-default-branch` | block bare `git push --force` on any branch |
| guardrail | `block-commit-to-default-branch` | block committing/pushing while on trunk (branch-aware) |
| guardrail | `block-env-files` | block writes to real `.env*` files; **deny reads** of them via `permissions.deny` |
| guardrail | `block-secret-files` | block writes to private keys & credential files; **deny reads** of them via `permissions.deny` |
| guardrail | `scan-secrets-before-commit` | remind to scan the staged diff for hardcoded secrets |
| guardrail | `no-hand-edit-lockfiles` | block hand-edits to lockfiles across JS/Python/Rust/Go/Ruby/PHP |
| guardrail | `protect-generated-files` | block edits to generated/binary artifacts |
| guardrail | `verifier-before-commit` | remind to run the reviewer on the staged diff |
| guardrail | `commit-message-style` | one-line commit messages, no co-author trailer |
| guardrail | `design-guidance-on-ui-edits` | warn on UI edits while no design guidance is installed (`has-frontend`, self-silencing) |
| agent | `reviewer` | read-only staged-diff audit, findings by severity |
| agent | `security-auditor` | read-only deep security audit (adaptive: backends/APIs) |
| agent | `docs-writer` | keep docs/ & `_shared/` in sync with code changes |
| agent | `feature-planner` | decompose a feature into role-sized tasks |
| agent | `feature-orchestrator` | plan + dispatch specialist roles across repos |
| agent | `implementer` | cohesive multi-file change bounded to one feature |
| skill | `planning-workflow` | when scoping/spec'ing, before code |
| skill | `architecture-overview` | big-picture / cross-repo flow tracing |

> Adaptive picks: `/lodestar-agents` pre-checks `security-auditor` when a backend/API or `has-auth` is detected, and `ui-designer` + `accessibility-reviewer` when a frontend is detected — even though those last two are frontend-scoped (below). Detection feeds the picker; the catalog stays authoritative.
>
> `ui-designer` is `recommended: true` **and** frontend-scoped, so a detected frontend gets a design role by default and a backend-only workspace never sees it. Skip it anyway and `design-guidance-on-ui-edits` keeps saying so on UI edits until guidance is recorded in the manifest — declining is allowed, going silently unguided is not.

## ⬡ Node · GraphQL · React · React Native pack

Detected via `node-dbmate`, `graphql-apollo-server`, `graphql-apollo-client`, `react-craco`, `react-native`, `has-eslint`.

| Kind | Entry | Stacks |
|---|---|---|
| guardrail | `block-edit-applied-migrations` | `node-dbmate` |
| guardrail | `protect-dbmate-schema` | `node-dbmate` |
| guardrail | `mobile-use-patch-package` | `react-native` |
| guardrail | `autolint-on-edit` | `has-eslint` |
| agent | `migration-writer` | `node-dbmate` |
| agent | `resolver-writer` | `graphql-apollo-server` |
| agent | `test-writer` | `react-native` |
| agent | `release-runner` | `react-native` |
| agent | `ui-designer` | `react-craco`, `react-native`, `has-frontend` — loads the `frontend-design` plugin skill |
| agent | `accessibility-reviewer` | `react-craco`, `react-native`, `has-frontend` — read-only WCAG 2.2 AA audit |
| skill | `backend-standards` | `graphql-apollo-server`, `node-dbmate` |
| skill | `graphql-contract` | `graphql-apollo-server`, `graphql-apollo-client` |
| skill | `frontend-standards` | `react-craco` |
| skill | `mobile-standards` | `react-native` |

## 🐘 Laravel · PHP pack

Activates on `laravel` (an `artisan` file or `laravel/framework` in `composer.json`).

| Kind | Entry | Purpose |
|---|---|---|
| guardrail | `block-edit-applied-migrations-laravel` | block edits to migrations that already ran (new ones stay writable) |
| guardrail | `protect-laravel-generated` | block edits to `bootstrap/cache/`, `storage/framework/`, Vite/Mix output |
| guardrail | `php-autolint-on-edit` | run Pint on the edited file (`has-pint`) |
| agent | `laravel-endpoint-writer` | route + controller + FormRequest + API Resource + policy, contract updated |
| agent | `eloquent-migration-writer` | new migration with a real `down()`, model updated to match |
| agent | `test-writer-php` | Pest or PHPUnit, matching the repo's existing style |
| skill | `laravel-backend-standards` | Eloquent, FormRequests, Resources, policies, `env()`-in-config, queues |

## ▲ Next.js pack

Activates on `nextjs` (`next` in deps or a `next.config.*` file).

| Kind | Entry | Purpose |
|---|---|---|
| guardrail | `nextjs-no-public-secrets` | warn when a `NEXT_PUBLIC_` variable looks like a secret (it ships to the browser) |
| agent | `nextjs-route-writer` | route or handler with a deliberate server/client boundary |
| skill | `nextjs-frontend-standards` | App vs Pages Router, Server/Client Components, `NEXT_PUBLIC_`, data fetching |

> Onboarding also records **which router** a Next.js repo uses (`app/` vs `pages/`) in its conventions doc — the two have different files and different data-fetching APIs, and an agent that guesses writes code that never runs.

## 🐍 Python · Django pack

Detected via `python-django`, `python`, `drf`, `has-pytest`, `has-python-lint`.

| Kind | Entry | Stacks |
|---|---|---|
| guardrail | `block-edit-applied-migrations-django` | `python-django` |
| guardrail | `python-autolint-on-edit` | `has-python-lint` |
| agent | `migration-writer-django` | `python-django` |
| agent | `drf-endpoint-writer` | `drf` |
| agent | `test-writer-python` | `has-pytest` |
| skill | `django-backend-standards` | `python-django` |
| skill | `drf-api-contract` | `drf` |

---

## Doc & MCP templates (not stack-filtered)

| Template | For |
|---|---|
| `templates/CLAUDE.md` | the thin root router |
| `templates/repo-map.md` | the repo registry |
| `templates/docs/_shared/api-contract.md` | shared API spine — **generic, seeded at init** (stack-neutral) |
| `templates/docs/_shared/graphql-contract.md` | GraphQL seed for the spine (used only if a GraphQL stack is detected) |
| `templates/docs/_shared/rest-api-contract.md` | REST/DRF seed for the spine (used only if a DRF stack is detected) |
| `templates/docs/_shared/{env-matrix,auth-model,local-setup,glossary}.md` | cross-repo docs (stack-neutral) |
| `templates/docs/repo-conventions.md` | per-repo conventions stub |
| `templates/docs/extending-gap.md` | workspace `docs/EXTENDING.md`, generated when a stack has no catalog pack |
| `templates/hooks/lodestar-guardrails.py` | the bundled guardrail engine (`/lodestar-guardrails` copies it to `.claude/hooks/`) |
| `templates/hooks/lodestar-graph-refresh.sh` | graphify-mode **lockstep** pre-commit graph rebuild (`/lodestar-freshness`) |
| `templates/hooks/lodestar-freshness-check.py` | offline drift detector for architecture maps (`/lodestar-freshness`, `/lodestar-refresh`) |
| `templates/hooks/lodestar-precommit-check.py` | commit-surface guardrail enforcement for any committer (`/lodestar-guardrails`) |
| `templates/hooks/lodestar-graph-coverage.py` | graph **completeness** assertion: on-disk code vs graph nodes (`/lodestar-onboard`, `/lodestar-refresh`) |
| `templates/hooks/lodestar-permissions.py` | permission surface: merges rule `permission_rules` into `settings.json` `permissions.deny` (`/lodestar-guardrails`) |
| `templates/git/gitattributes-graphify` | union-merge `.gitattributes` for `graph.json` (`/lodestar-freshness`) |
| `templates/mcp/*.mcp.json` | per-workspace MCP server sets |

The contract spine is always the file `docs/_shared/api-contract.md`. `/lodestar-init` seeds it from the **generic** stub (no API-style assumption); `/lodestar-onboard` may later enrich it from the GraphQL or REST seed **only if** that stack is actually detected and the file is still the untouched generic template. The other shared docs all link to the stable `api-contract.md` name.
