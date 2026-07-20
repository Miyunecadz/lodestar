# Extending Lodestar

Everything in Lodestar is a plain file. Adding capability means adding a catalog entry — no code changes. This guide shows how to add each kind.

---

## Add a guardrail

1. Copy an existing rule in `kit/catalog/guardrails/` to `kit/catalog/guardrails/<your-id>.md`.
2. Edit the frontmatter:
   - `severity: block` for safety (hard stop), `warn` for quality (informational).
   - `stacks:` — which stacks it applies to, or `[all]`.
   - `event` + `pattern` — the engine trigger (`file` events match the edited path; `bash` events match the command).
   - `emits: rule` for declarative rules (enforced by the bundled engine); `emits: settings-hook` only if it needs custom shell logic.
3. Write a message body that **redirects to the right action**, not just "denied."
4. Re-run `/lodestar-guardrails` and tick your new rule.

Example — block committing directly to `main`:

```markdown
---
id: warn-direct-main-edits
title: Warn on edits while on main/master
category: quality
severity: warn
recommended: false
stacks: [all]
event: bash
pattern: 'git commit'
emits: rule
---
You appear to be committing on a protected branch. Create a feature branch first:
`git switch -c feat/<name>`.
```

The picker writes this to `.claude/guardrails/warn-direct-main-edits.md`; the bundled engine (`.claude/hooks/lodestar-guardrails.py`) picks it up on the next tool call — no restart, no plugin.

## Add an agent role

1. Copy a role from `kit/catalog/agents/` to `kit/catalog/agents/<your-id>.md`.
2. Set the **tool profile** (`tools:`) to the minimum the role needs — this is the most important field. A read-only role gets no `Edit`/`Write`.
3. Keep the body **thin**: state the role, its repo scope, and which skills/docs to `load`. Do not restate conventions — reference the skill that owns them.
4. Write a crisp `description` (the delegation trigger). Make it non-overlapping with other roles.
5. Re-run `/lodestar-agents` and tick it.

Guardrail for yourself: if a new role's body starts duplicating a skill, stop — point at the skill instead (see [CONCEPTS.md §4](CONCEPTS.md)).

## Add a skill

1. Create `kit/catalog/skills/<name>/SKILL.md`.
2. The `description` is a *when-to-load* trigger — write it as a **task**, not a topic (see [CONCEPTS.md §1](CONCEPTS.md)).
3. Keep the body thin; point at `docs/…`.
4. It's picked up on the next `/lodestar-onboard` (for stack-scoped skills) or copied by `/lodestar-init` (for workspace-wide skills like planning).

## Add a stack detector

To support a new stack:
1. Add a detection signal to `/lodestar-onboard` (e.g. "`Cargo.toml` present → `rust`").
2. Tag relevant catalog entries with the new stack.
3. That's it — the pickers intersect detected stacks with entry `stacks` automatically.

## Add a stack pack

A "stack pack" is just a *set* of catalog entries that share stack tags for one ecosystem (e.g. the Python·Django pack: `python-django`, `drf`, `has-pytest`, `has-python-lint`). There is no special file — a pack is a naming/tagging convention. To add one:

1. Add its detectors to `/lodestar-onboard` (see above).
2. Author its guardrails, agents, and skills, tagging each with the pack's stacks. Mirror an existing pack's shape (a migration guardrail, a migration-writer agent, a backend-standards skill, an api-contract skill, a test-writer, an autolint rule).
3. If it has its own API style, add a `kit/templates/docs/_shared/<style>-api-contract.md` stub.
4. List the new entries in [`../kit/catalog/CATALOG.md`](../kit/catalog/CATALOG.md) under a new pack heading.

Packs compose: a workspace can activate several at once (e.g. a Django API behind a React admin panel).

## Add an MCP template

Drop a `<name>.mcp.json` in `kit/templates/mcp/` with a server list (no secrets). Document in the file's companion note which servers it includes and how to authenticate (`/mcp`). Users copy it to their workspace root as `.mcp.json` and supply their own tokens via local scope.

---

## Publishing your fork

1. Edit the catalog to your taste; delete entries you don't want as defaults.
2. Update `README.md` to describe your defaults.
3. Commit and push. Others `git clone` and run `install.sh` — your catalog becomes their starting point.

The manifest (`.claude/lodestar.manifest.json`) that a workspace produces is shareable too: commit it, and a teammate can reproduce your exact enabled set.
