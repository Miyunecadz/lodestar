# Catalog Index — Universal Core & Stack Packs

Lodestar's catalog is organized into a **universal core** that works on any stack, plus **stack packs** whose entries activate only when a matching stack is detected. The `stacks:` field on each entry is what the pickers filter on — an entry never appears (or fires) on a workspace whose stacks don't match.

> Adopting Lodestar on a new stack? You get the **universal core** immediately. Then either add a stack pack below (if one fits) or author your own — see [`../docs/EXTENDING.md`](../docs/EXTENDING.md). Packs compose: a Django API behind a React admin panel uses the **Python·Django** and **Node·GraphQL·RN** packs side by side.

Totals: **30 entries** — 11 universal · 12 Node·GraphQL·RN · 7 Python·Django.

---

## 🌐 Universal core — `stacks: [all]` (works on any stack)

| Kind | Entry | Purpose |
|---|---|---|
| guardrail | `block-env-files` | block reading/writing real `.env*` files (secrets) |
| guardrail | `no-hand-edit-lockfiles` | block hand-edits to lockfiles across JS/Python/Rust/Go/Ruby/PHP |
| guardrail | `protect-generated-files` | block edits to generated/binary artifacts |
| guardrail | `verifier-before-commit` | remind to run the reviewer on the staged diff |
| guardrail | `commit-message-style` | one-line commit messages, no co-author trailer |
| agent | `reviewer` | read-only staged-diff audit, findings by severity |
| agent | `feature-planner` | decompose a feature into role-sized tasks |
| agent | `feature-orchestrator` | plan + dispatch specialist roles across repos |
| agent | `implementer` | cohesive multi-file change bounded to one feature |
| skill | `planning-workflow` | when scoping/spec'ing, before code |
| skill | `architecture-overview` | big-picture / cross-repo flow tracing |

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
| `templates/docs/_shared/graphql-contract.md` | shared API spine (GraphQL workspaces) |
| `templates/docs/_shared/rest-api-contract.md` | shared API spine (REST/DRF workspaces) |
| `templates/docs/_shared/{env-matrix,auth-model,local-setup,glossary}.md` | cross-repo docs |
| `templates/docs/repo-conventions.md` | per-repo conventions stub |
| `templates/mcp/*.mcp.json` | per-workspace MCP server sets |

Keep the API-contract stub matching your workspace (GraphQL **or** REST) and delete the other.
