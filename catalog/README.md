# The Lodestar Catalog

The catalog is the reusable, publishable heart of Lodestar. It is three folders of **templates** that the generator commands read, filter by stack, and let you pick from:

```
catalog/
├── guardrails/     # enforced rules (one .md per rule)
├── agents/         # role-based agent templates (one .md per role)
└── skills/         # skill templates (one folder per skill, each with SKILL.md)
```

Everything here is plain Markdown with YAML frontmatter. Fork it, delete what you dislike, add your own. The commands never hard-code any entry — they only read this folder.

## Universal core vs stack packs

Entries fall into two tiers, distinguished by the `stacks:` field:

- **Universal core** (`stacks: [all]`) — works on any stack, active everywhere.
- **Stack packs** (`stacks: [<specific tags>]`) — activate only when a matching stack is detected. Ships with a **Node·GraphQL·React·React Native** pack and a **Python·Django** pack; add your own the same way.

See **[CATALOG.md](CATALOG.md)** for the full grouped index of every entry. Packs compose — a Django backend behind a React admin panel uses both packs at once.

---

## Shared frontmatter conventions

Every catalog entry declares which stacks it applies to and whether it's recommended by default:

- **`stacks:`** a list of stack tags (see below), or `[all]` for stack-agnostic entries. The picker shows an entry only if the workspace has at least one matching stack.
- **`recommended:`** `true` pre-checks the entry in the picker menu. Reserve `true` for high-value, low-regret entries (safety guardrails, core roles).

### Stack tags produced by `/lodestar-onboard`

| Tag | Detected from |
|---|---|
| `node-dbmate` | `dbmate.yml` present |
| `graphql-apollo-server` | `apollo-server-*` in deps |
| `graphql-apollo-client` | `@apollo/client` in deps |
| `react-craco` | `@craco/craco` in deps |
| `react-native` | `react-native` in deps |
| `has-husky` | `.husky/` present |
| `has-eslint` | eslint config or dep present |
| `redis-queue` | `bull` / `ioredis` in deps |
| `python-django` | `manage.py` present |
| `python` | `requirements.txt` / `pyproject.toml` / `Pipfile` |
| `drf` | `djangorestframework` in deps |
| `has-pytest` | `pytest` dep or `pytest.ini` / `conftest.py` |
| `has-python-lint` | `ruff` / `black` / `flake8` config or dep |
| `all` | matches any workspace |

Add your own tags freely — just detect them in `/lodestar-onboard` and reference them in entries.

---

## Guardrail entry format (`catalog/guardrails/<id>.md`)

```markdown
---
id: block-edit-applied-migrations
title: Block edits to applied DB migrations
category: database            # safety | database | secrets | dependencies | quality | generated
severity: block               # block | warn
recommended: true
stacks: [node-dbmate]
event: file                   # engine event: file (matches edited path) | bash (matches command)
pattern: 'db/migrations/.*\.sql$'   # regex the event is matched against
emits: rule                   # rule | settings-hook
---

Message shown to Claude when the rule fires. Explain WHAT is blocked and,
crucially, WHAT TO DO INSTEAD. A good guardrail teaches the right action.
```

The picker writes `emits: rule` entries to `.claude/guardrails/<id>.md` (with `enabled: true`), enforced by Lodestar's self-contained engine (`.claude/hooks/lodestar-guardrails.py`, registered as a PreToolUse hook — no external plugin). `emits: settings-hook` entries go straight into `.claude/settings.json` hooks and are reserved for rules needing shell logic (e.g. a per-repo lint router).

## Agent entry format (`catalog/agents/<id>.md`)

```markdown
---
id: reviewer
title: Reviewer (read-only diff audit)
axis: cross-repo              # cross-repo | stack-scoped
recommended: true
stacks: [all]
tools: [Read, Grep, Glob, Bash]     # the generated agent's tool allowlist
loads: []                    # skills/docs the agent should load on start
description: >                # becomes the agent's delegation trigger
  Use to audit a staged diff before commit. Read-only.
---

# Thin system prompt body. References skills/docs — never copies their content.
```

The picker writes `.claude/agents/<id>.md` with proper Claude Code agent frontmatter (`name`, `description`, `tools`) plus this body, parameterized with the target repo where relevant.

## Skill entry format (`catalog/skills/<name>/SKILL.md`)

Standard Claude Code skill. The `description` is the *when-to-load* trigger (write it as a task, not a topic). The body should be thin and point at `docs/…` rather than restating content.

```markdown
---
name: planning-workflow
description: Use when scoping or spec'ing a feature, BEFORE any code is written. Not for implementation.
---

# Body: the workflow, and pointers to docs/_shared and docs/<repo>.
```

---

## Adding your own entries

See [`../docs/EXTENDING.md`](../docs/EXTENDING.md) for a step-by-step guide. In short: copy an existing entry, change the frontmatter, write the body, and re-run the relevant picker. No code changes required.
