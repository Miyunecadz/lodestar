# `.claude/` — this repo's own Claude Code config

This folder is **Lodestar's development setup**, not part of what Lodestar ships.

- **What Lodestar ships** lives under [`../kit/`](../kit/) — the catalog, templates, and
  the `lodestar-*` command specs that `install.sh` copies into a target workspace.
- **This folder** is for building Lodestar itself: dev-only agents, skills, workflows,
  and settings. Anything here is safe to add without affecting the product — `install.sh`
  only ever copies from `kit/`, never from `.claude/`.

So contributors can drop `.claude/agents/`, `.claude/skills/`, `.claude/workflows/`, or a
`settings.json` here freely. `settings.local.json` (personal, gitignored) also lives here.

## What is set up

| Path | What it does |
|---|---|
| `settings.json` | registers the guardrail engine (PreToolUse) and the two dev hooks (PostToolUse); holds the allow-list for the CI gates and the `permissions.deny` block |
| `guardrails/` | four dogfooded rules — this repo runs its own product against itself |
| `hooks/lodestar-*.py` | copies of the three shipped surface hooks, so a rule change is exercised here before it ships |
| `hooks/dev-*.py` | **dev-only**, no kit equivalent: run `validate.py` after a catalog edit and `shellcheck` after a shell edit, so a CI failure surfaces at the edit instead of at push |
| `agents/` | `gate-runner` (run every CI gate, report only failures), `kit-boundary-reviewer` (the invariants CI cannot check) |
| `skills/` | `catalog-entry-authoring`, `hook-engine-invariants` — loaded on demand when a task matches |
| `lodestar.manifest.json` | records which deny entries `lodestar-permissions.py` owns; **do not hand-edit** |

**Dogfooding is the point.** A guardrail that misfires here is a bug in the catalog entry
users will get. Three surfaces are live: the PreToolUse engine, `permissions.deny`, and
the pre-commit checker — the last one needs wiring per clone, see
[`../CONTRIBUTING.md`](../CONTRIBUTING.md).

See [`../CONTRIBUTING.md`](../CONTRIBUTING.md) for the full layout.
