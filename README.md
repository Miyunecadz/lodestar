# ⭐ Lodestar

**An AI-native workspace kit for Claude Code that turns a folder of repositories into one coordinated, self-documenting project — without a monorepo migration and without a `CLAUDE.md` in every repo.**

> A *lodestar* is the star you steer by. In a multi-repo workspace, the root is that fixed point: it holds the map of the whole system so the AI can orient itself, then hand narrow, well-scoped work to the right place. **Map at the top, hands at the bottom.**

---

## The problem

You have several repos in one folder — say a `backend`, a `frontend`, and a `mobile` app. You want Claude Code to understand the *whole system*, not one repo at a time. The naive fixes all hurt:

- **A `CLAUDE.md` in every repo** → duplicated conventions, drift, and no cross-repo picture.
- **One giant root `CLAUDE.md`** → tens of thousands of tokens loaded on *every* session, most of it irrelevant to the task at hand.
- **Hand-written architecture docs** → stale the moment code changes.

## The idea

Lodestar puts a **thin router** at the workspace root and moves all real knowledge into layers that **load only when relevant** — each one carrying an explicit *"when to load this"* trigger. A new repo is absorbed by running one command. Everything is plain files you can copy, publish, and modify.

```
your-workspace/                 ← launch Claude Code from here
├── CLAUDE.md                   ← thin router: repo registry + "load on demand"
├── docs/
│   ├── _shared/                ← cross-repo truth (the API contract, env tiers, auth…)
│   └── <repo>/architecture/    ← auto-generated code graph (Graphify)
├── .claude/
│   ├── skills/                 ← knowledge that loads only when the task matches
│   ├── agents/                 ← opt-in role workers you delegate to
│   ├── commands/               ← the generators (see below)
│   └── *.local.md              ← opt-in guardrails (enforced, not advisory)
├── backend/                    ← untouched, still its own git repo
├── frontend/                   ← untouched
└── mobile/                     ← untouched
```

## The five layers

Lodestar is deliberately layered. Each layer is optional and does exactly one job.

| Layer | What it is | Loads / fires | Advisory or enforced |
|---|---|---|---|
| **1. Router** | thin root `CLAUDE.md` | every session (tiny) | — |
| **2. Knowledge** | `docs/` + on-demand **skills** | when the task matches a skill's `description` | advisory |
| **3. Structure** | **Graphify** code graph per repo | queried on demand | advisory |
| **4. Guardrails** | **hookify** rules + settings hooks | deterministically, on every matching action | **enforced** |
| **5. Delegation** | role-based **agents** | when you (or an orchestrator) delegate | advisory |

The golden rule: **docs make the AI *informed*; guardrails make it *trustworthy*.** Use knowledge/skills for judgment and style; use guardrails for anything where a mistake has real cost (database migrations, secrets, generated files).

## The three generators

Everything self-extends through commands that share one engine: **detect the stacks present → filter a catalog → let you pick from a menu → write only what you chose → record it in a manifest.**

| Command | Produces | Destructive? |
|---|---|---|
| `/lodestar-init` | the router, `docs/_shared/` skeleton, `repo-map.md` | no |
| `/onboard-repo <path>` | a repo's docs + Graphify graph + matching skill | no (informational) |
| `/guardrails` | opt-in enforced rules (a checklist you tick) | writes rules |
| `/gen-agents` | opt-in role agents (a checklist you tick) | writes agents |

Add a new repo later? `/onboard-repo ./new-service` and it's absorbed — the router never changes.

## Quickstart

```bash
# 1. Clone Lodestar somewhere
git clone https://github.com/Miyunecadz/lodestar.git ~/tools/lodestar
# (or via SSH: git clone git@github.com:Miyunecadz/lodestar.git ~/tools/lodestar)

# 2. Install it into a workspace that contains your repos
~/tools/lodestar/install.sh ~/code/my-workspace

# 3. Launch Claude Code from the workspace root and initialize
cd ~/code/my-workspace
claude
> /lodestar-init
> /onboard-repo ./backend
> /onboard-repo ./frontend
> /guardrails        # tick the safety + quality rules you want
> /gen-agents        # tick the role agents you want
```

## Design principles (the short version)

1. **When-to-load is a first-class field.** Every skill and doc states the task it belongs to, so the AI never loads planning docs while coding, or coding standards while planning.
2. **Single source of truth.** Knowledge lives in one place (a skill/doc). Agents and commands *reference* it; they never copy it. Copies drift.
3. **Breadth at the top, depth in the workers.** The orchestrator holds the wide map; delegated agents are narrow roles with a crisp done-condition — narrow *task* scope, not narrow *domain*, is what prevents drift.
4. **Advisory vs enforced is a deliberate choice.** Not "please don't"; a hook that makes the wrong action impossible.
5. **Everything is a copyable file.** The catalog *is* the product. Fork it, delete what you dislike, add your own.

## What Lodestar is *not*

- Not a monorepo tool — your repos stay independent, with their own git history and CI.
- Not a replacement for Claude Code features — it's a disciplined way to *arrange* them (skills, hooks, agents, MCP scopes).
- Not opinionated about your stack — the catalog is a **universal core** (works anywhere) plus **stack packs** that activate only when detected. It ships a **Node·GraphQL·React·React Native** pack and a **Python·Django** pack; every entry is stack-tagged and easy to swap or extend. See [`catalog/CATALOG.md`](catalog/CATALOG.md).

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the full design and the rationale behind every decision.
- [`docs/CONCEPTS.md`](docs/CONCEPTS.md) — the mental models (advisory vs enforced, map/hands, the loading policy).
- [`docs/EXTENDING.md`](docs/EXTENDING.md) — how to add your own guardrails, agents, and skills to the catalog.
- [`catalog/README.md`](catalog/README.md) — the catalog entry format.
- [`catalog/CATALOG.md`](catalog/CATALOG.md) — the grouped index: universal core + stack packs.
- [`examples/walkthrough.md`](examples/walkthrough.md) — a concrete end-to-end example.

## Requirements

- [Claude Code](https://code.claude.com)
- Optional: [Graphify](https://github.com/Graphify-Labs/graphify) for auto-generated architecture graphs (`uv tool install graphifyy` or `pipx install`)
- Optional: [hookify](https://github.com/anthropics/claude-code) plugin for the declarative guardrail rules

## License

MIT — see [LICENSE](LICENSE). Built to be copied, published, and made your own.
