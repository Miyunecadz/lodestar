# `.claude/` — this repo's own Claude Code config

This folder is **Lodestar's development setup**, not part of what Lodestar ships.

- **What Lodestar ships** lives under [`../kit/`](../kit/) — the catalog, templates, and
  the `lodestar-*` command specs that `install.sh` copies into a target workspace.
- **This folder** is for building Lodestar itself: dev-only agents, skills, workflows,
  and settings. Anything here is safe to add without affecting the product — `install.sh`
  only ever copies from `kit/`, never from `.claude/`.

So contributors can drop `.claude/agents/`, `.claude/skills/`, `.claude/workflows/`, or a
`settings.json` here freely. `settings.local.json` (personal, gitignored) also lives here.

See [`../CONTRIBUTING.md`](../CONTRIBUTING.md) for the full layout.
