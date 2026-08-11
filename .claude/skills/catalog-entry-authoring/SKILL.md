---
name: catalog-entry-authoring
description: The contract for adding or editing a Lodestar catalog entry — guardrail, agent, or skill. Apply when writing anything under kit/catalog/, when choosing a rule's severity or enforcement surface, or when a validate.py failure mentions frontmatter, CATALOG.md, or totals.
user-invocable: false
---

# Authoring a catalog entry

`.github/scripts/validate.py` is the contract in executable form. Read it when in doubt;
this is the shape of what it enforces plus the judgement it cannot.

## Four obligations, every time

1. The entry file with required frontmatter (below).
2. The id listed in `kit/catalog/CATALOG.md` **in backticks** — an unlisted entry is
   invisible to the pickers' menu.
3. The `Totals: **N entries**` line in CATALOG.md updated. It counts guardrails + agents +
   skills.
4. `docs/EXTENDING.md` updated for any **new** flag, surface, or stack detector.

## Required frontmatter

**Guardrail** — `id title category severity recommended stacks event pattern emits surface`

| Field | Values |
|---|---|
| `severity` | `block` (hard stop) · `warn` (advisory) |
| `event` | `file` (matches the edited path) · `bash` (matches the command) · `all` |
| `emits` | `rule` (declarative, run by the bundled engine) · `settings-hook` (custom shell logic — last resort) |
| `surface` | `agent` · `commit` · `permission` · a list · `both` (legacy for `[agent, commit]`) |
| `pattern` | must compile as a Python regex |

`surface: commit`/`both` additionally needs `commit_check: staged-paths|secret-scan|default-branch`,
or `event: file` (which defaults to `staged-paths`). `commit_severity` overrides `severity`
on the commit surface only.

**Agent** — `id`/`name` plus `stacks tools description`. `tools` is the most important
field: the minimum the role needs. A read-only role gets no `Edit`/`Write`.

**Skill** — `name description`. The `description` is a *when-to-load* trigger: write it as
a **task** ("Use when editing the backend repo — resolvers, migrations…"), never a topic.

## Choosing a surface

One rule set, three mechanisms, not interchangeable:

| `surface` | Enforced by | Holds for |
|---|---|---|
| `agent` | `lodestar-guardrails.py` (PreToolUse, `Bash\|Edit\|Write\|MultiEdit`) | Claude's tool calls |
| `commit` | `lodestar-precommit-check.py` (pre-commit) | any committer |
| `permission` | `permissions.deny`, merged by `lodestar-permissions.py` | every tool, **including `Read`** |

The engine cannot see a `Read` at all. A rule body promising "never read this" on the
agent surface is documenting intent, not enforcing it — it needs `permission`.

**Surface choice is a judgement about false positives, not about how much the rule
matters.** Four rules that look like obvious commit-surface candidates are deliberately
`agent`-only, and the reasons are the model to copy: `protect-generated-files` (the
freshness hook intentionally rebuilds and stages `graph.json`), `no-hand-edit-lockfiles`
and `protect-dbmate-schema` (a pre-commit hook cannot tell a `yarn add` rewrite from a
hand-edit), `commit-message-style` (needs the `commit-msg` event, which reads the message
file, not the staged diff).

## Context flags — when a pattern is not enough

`stacks: [a, b]` · `allow_if_untracked: true` (file) · `only_on_default_branch: true`
(bash) · `match: argv` (bash — match unquoted words, so quoted text that runs nothing
cannot trip the rule) · `match: content` (file — test the edited text, not the path) ·
`allow_paths: ['^/tmp/']` (bash) · `ignore_case: false` ·
`requires_manifest_missing: a.b` (self-silencing reminder). Full semantics live in
`docs/EXTENDING.md` — read it before adding a flag, and update it when you add one.
A **new** flag means editing the engine; `hook-engine-invariants` owns those rules.

## Writing the body

- A `block` message must **redirect to the correct alternative**, not just deny. "Create a
  feature branch first: `git switch -c feat/<name>`" beats "committing to main is denied."
- State the surface and its limits plainly. Every shipped rule ends with a paragraph
  saying who it holds for and what bypasses it; match that honesty.
- Link related entries with `[[other-rule-id]]`.
- Never restate a convention a skill or doc owns — point at it.

## Frontmatter parsing is minimal

Scalars and inline lists (`[a, b]`) only, in all three hooks and the validator. **A regex
containing a comma cannot go in a list value** — use a single scalar pattern.

## Then

Add a case for each surface the entry touches: `test-engine.sh` (agent),
`test-precommit.sh` (commit), `test-permissions.sh` (permission).
