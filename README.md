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
│   └── <repo>/architecture/    ← code graph (Graphify) or a Markdown overview.md
├── .claude/
│   ├── skills/                 ← knowledge that loads only when the task matches
│   ├── agents/                 ← opt-in role workers you delegate to
│   ├── commands/               ← the generators (see below)
│   ├── hooks/                  ← the bundled guardrail engine (lodestar-guardrails.py)
│   └── guardrails/             ← opt-in guardrail rules (enforced, not advisory)
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
| **3. Structure** | **Graphify** code graph per repo (or a Markdown `overview.md` if Graphify isn't installed) | queried on demand | advisory |
| **4. Guardrails** | `.claude/guardrails/*.md` rules + a bundled engine (+ settings hooks) | deterministically, on every matching action | **enforced** |
| **5. Delegation** | role-based **agents** | when you (or an orchestrator) delegate | advisory |

The golden rule: **docs make the AI *informed*; guardrails make it *trustworthy*.** Use knowledge/skills for judgment and style; use guardrails for anything where a mistake has real cost (database migrations, secrets, generated files).

## The three generators

Everything self-extends through commands that share one engine: **detect the stacks present → filter a catalog → let you pick from a menu → write only what you chose → record it in a manifest.**

| Command | Produces | Destructive? |
|---|---|---|
| `/lodestar-init` | the router, `docs/_shared/` skeleton, `repo-map.md` | no |
| `/lodestar-onboard <path>` | a repo's docs + architecture map (Graphify graph or Markdown overview) + matching skill | no (informational) |
| `/lodestar-guardrails` | opt-in enforced rules (a checklist you tick) | writes rules |
| `/lodestar-agents` | opt-in role agents (a checklist you tick) | writes agents |

Add a new repo later? `/lodestar-onboard ./new-service` and it's absorbed — the router never changes.

**Updating.** Run **`/lodestar-update`** from the workspace. It fetches the latest **released version** and re-syncs the kit (catalog, templates, commands, guardrail engine) **without touching anything you generated** — your rules, agents, docs, and manifest are left as-is. New catalog entries appear the next time you re-run `/lodestar-guardrails` or `/lodestar-agents`.

Updates move between release tags, never to the tip of `main`, so they're reproducible and reversible: `/lodestar-update 0.5.0` pins or rolls back to a specific version.

## Quickstart

```bash
# 1. Install Lodestar into a workspace that contains your repos.
#    Fetches the latest release, copies the kit in, leaves no clone behind.
curl -fsSL https://raw.githubusercontent.com/Miyunecadz/lodestar/main/install.sh \
  | bash -s -- ~/code/my-workspace

# 2. Launch Claude Code from the workspace root and initialize
cd ~/code/my-workspace
claude
> /lodestar-init
> /lodestar-onboard ./backend
> /lodestar-onboard ./frontend
> /lodestar-guardrails    # tick the safety + quality rules you want
> /lodestar-agents        # tick the role agents you want
```

Prefer to read a script before running it? Download it first, or clone and install from the clone — both do the same thing:

```bash
curl -fsSLO https://raw.githubusercontent.com/Miyunecadz/lodestar/main/install.sh
less install.sh && bash install.sh ~/code/my-workspace
```

**Install from a clone (offline, air-gapped, or contributing).** The installer copies from a `kit/` directory next to itself when there is one, so this path needs no network at all:

```bash
git clone https://github.com/Miyunecadz/lodestar.git ~/tools/lodestar
# (or via SSH: git clone git@github.com:Miyunecadz/lodestar.git ~/tools/lodestar)
~/tools/lodestar/install.sh ~/code/my-workspace
```

A clone install records the clone's **path**, so `/lodestar-update` keeps doing `git pull` + re-install from it — offline updates keep working. A bootstrap install records the **repo URL and tag** instead, and updates re-fetch from there. Either way `.lodestar/` holds metadata, not a clone. Pin a specific version with `--ref`:

```bash
bash install.sh ~/code/my-workspace --ref v0.6.0     # any release from v0.5.0 onward
```

> **Users vs contributors.** As a user you never need a clone: bootstrap, then configure with the slash commands. As a contributor you want the clone — it's the product source, and this repo's own `.claude/` is dev tooling, not part of the kit (see [`CONTRIBUTING.md`](CONTRIBUTING.md)).

## Design principles (the short version)

1. **When-to-load is a first-class field.** Every skill and doc states the task it belongs to, so the AI never loads planning docs while coding, or coding standards while planning.
2. **Single source of truth.** Knowledge lives in one place (a skill/doc). Agents and commands *reference* it; they never copy it. Copies drift.
3. **Breadth at the top, depth in the workers.** The orchestrator holds the wide map; delegated agents are narrow roles with a crisp done-condition — narrow *task* scope, not narrow *domain*, is what prevents drift.
4. **Advisory vs enforced is a deliberate choice** — and *enforced for whom* is a second one. Safety rules declare a surface: Claude's tool calls, every committer's pre-commit, or both. A rule that only constrains the assistant is labelled as such rather than implying more.
5. **Everything is a copyable file.** The catalog *is* the product. Fork it, delete what you dislike, add your own.

## What Lodestar is *not*

- Not a monorepo tool — your repos stay independent, with their own git history and CI.
- Not a replacement for Claude Code features — it's a disciplined way to *arrange* them (skills, hooks, agents, MCP scopes).
- Not opinionated about your stack — the catalog is a **universal core** (works anywhere) plus **stack packs** that activate only when detected. It ships **Node·GraphQL·React·React Native**, **Python·Django**, **Laravel·PHP**, and **Next.js** packs; every entry is stack-tagged and easy to swap or extend. When a repo's stack has *no* pack, onboarding says so and generates a `docs/EXTENDING.md` describing how to add one, rather than quietly falling back to the universal core. See [`kit/catalog/CATALOG.md`](kit/catalog/CATALOG.md).

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the full design and the rationale behind every decision.
- [`docs/CONCEPTS.md`](docs/CONCEPTS.md) — the mental models (advisory vs enforced, map/hands, the loading policy).
- [`docs/EXTENDING.md`](docs/EXTENDING.md) — how to add your own guardrails, agents, and skills to the catalog.
- [`kit/catalog/README.md`](kit/catalog/README.md) — the catalog entry format.
- [`kit/catalog/CATALOG.md`](kit/catalog/CATALOG.md) — the grouped index: universal core + stack packs.
- [`examples/walkthrough.md`](examples/walkthrough.md) — a concrete end-to-end example.
- [`docs/CI.md`](docs/CI.md) — CI checks, trunk-based release automation, and the branch-protection ruleset.

## Requirements

- [Claude Code](https://code.claude.com)
- Optional: [Graphify](https://github.com/Graphify-Labs/graphify) for auto-generated architecture graphs — installs at **user level, no sudo** (`uv tool install graphifyy` or `pipx install graphifyy`, then `graphify install`). If it's absent, `/lodestar-onboard` offers to generate a Markdown `architecture/overview.md` instead, so it's never required.
- For guardrails: **Python 3** (stdlib only — no packages, no plugin). The engine (`.claude/hooks/lodestar-guardrails.py`) is bundled and installed by `/lodestar-guardrails`.
- **git** — for the workspace itself, and for the bootstrap installer and `/lodestar-update` to fetch a release. Installing from a clone needs git only for the clone.

## Cost & model guidance

Lodestar's commands are **deliberately thin** — the intelligence lives in the catalog and templates, and the commands mostly *detect signals and copy files verbatim*. So they run well on cheap models at low effort; there's little to "reason" about. Each command ships with a conservative `effort:` in its frontmatter (overridable per run), and you can add a `model:` there too — a model outside your org allowlist is ignored gracefully.

| Command | What it does | Suggested model | Effort (shipped) |
|---|---|---|---|
| `/lodestar-init` | copy templates, write the manifest | Haiku / Sonnet | `low` |
| `/lodestar-guardrails` | catalog → rule files + engine | Sonnet | `low` |
| `/lodestar-agents` | pick + copy agent files | Sonnet / Haiku | `low` |
| `/lodestar-onboard` | detect stack, file docs, install skills | Sonnet | `medium` |

**The one reasoning-heavy step** is generating the Markdown `architecture/overview.md` in `/lodestar-onboard` *when Graphify isn't installed* — real synthesis of a repo's structure. For that case, use a stronger model (Opus/Sonnet) at `medium`–`high`.

**Biggest budget saver: install Graphify.** It's a local, deterministic tree-sitter tool that costs **~0 model tokens** — it moves that one expensive step off the model entirely. Install it once and every Lodestar command runs cheaply. That saves far more than tuning the model does.

## License

MIT — see [LICENSE](LICENSE). Built to be copied, published, and made your own.
