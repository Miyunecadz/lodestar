# Catalog Index — Universal Core & Stack Packs

Lodestar's catalog is organized into a **universal core** that works on any stack, plus **stack packs** whose entries activate only when a matching stack is detected. The `stacks:` field on each entry is what the pickers filter on — an entry never appears (or fires) on a workspace whose stacks don't match.

> Adopting Lodestar on a new stack? You get the **universal core** immediately. Then either add a stack pack below (if one fits) or author your own — see [`../docs/EXTENDING.md`](../docs/EXTENDING.md). Packs compose: a Django API behind a React admin panel uses the **Python·Django** and **Node·GraphQL·RN** packs side by side.

Totals: **38 entries** — 17 universal · 14 Node·GraphQL·RN · 7 Python·Django.

---

## 🌐 Universal core — `stacks: [all]` (works on any stack)

| Kind | Entry | Purpose |
|---|---|---|
| guardrail | `block-destructive-commands` | block irreversible shell commands (`rm -rf`, `reset --hard`, `DROP …`) |
| guardrail | `protect-default-branch` | block `git push --force` to a shared branch |
| guardrail | `block-env-files` | block reading/writing real `.env*` files (secrets) |
| guardrail | `block-secret-files` | block reading/writing private keys & credential files |
| guardrail | `scan-secrets-before-commit` | remind to scan the staged diff for hardcoded secrets |
| guardrail | `no-hand-edit-lockfiles` | block hand-edits to lockfiles across JS/Python/Rust/Go/Ruby/PHP |
| guardrail | `protect-generated-files` | block edits to generated/binary artifacts |
| guardrail | `verifier-before-commit` | remind to run the reviewer on the staged diff |
| guardrail | `commit-message-style` | one-line commit messages, no co-author trailer |
| agent | `reviewer` | read-only staged-diff audit, findings by severity |
| agent | `security-auditor` | read-only deep security audit (adaptive: backends/APIs) |
| agent | `docs-writer` | keep docs/ & `_shared/` in sync with code changes |
| agent | `feature-planner` | decompose a feature into role-sized tasks |
| agent | `feature-orchestrator` | plan + dispatch specialist roles across repos |
| agent | `implementer` | cohesive multi-file change bounded to one feature |
| skill | `planning-workflow` | when scoping/spec'ing, before code |
| skill | `architecture-overview` | big-picture / cross-repo flow tracing |

> Adaptive picks: `/lodestar-agents` pre-checks `security-auditor` when a backend/API or `has-auth` is detected, and `ui-designer` + `accessibility-reviewer` when a frontend is detected — even though those last two are frontend-scoped (below). Detection feeds the picker; the catalog stays authoritative.

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
| `templates/hooks/lodestar-guardrails.py` | the bundled guardrail engine (`/lodestar-guardrails` copies it to `.claude/hooks/`) |
| `templates/mcp/*.mcp.json` | per-workspace MCP server sets |

The contract spine is always the file `docs/_shared/api-contract.md`. `/lodestar-init` seeds it from the **generic** stub (no API-style assumption); `/lodestar-onboard` may later enrich it from the GraphQL or REST seed **only if** that stack is actually detected and the file is still the untouched generic template. The other shared docs all link to the stable `api-contract.md` name.
