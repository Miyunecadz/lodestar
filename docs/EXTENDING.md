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
pattern: '(^|[;&|]\s*)git(\s+-\S+)*\s+commit\b'
only_on_default_branch: true
match: argv
emits: rule
---
You appear to be committing on a protected branch. Create a feature branch first:
`git switch -c feat/<name>`.
```

The picker writes this to `.claude/guardrails/warn-direct-main-edits.md`; the bundled engine (`.claude/hooks/lodestar-guardrails.py`) picks it up on the next tool call — no restart, no plugin.

### Context flags — when a pattern is not enough

A pattern only sees a string. Rules whose intent depends on state a regex cannot observe — is this file committed yet, which repo is it in, am I on trunk, is that `rm -rf` inside a quoted argument — opt into the engine's **context layer**:

| Flag | Event | Effect |
|---|---|---|
| `stacks: [a, b]` | both | Skip the rule unless the target repo's detected stacks (from the manifest) include one of these, or `all`. Without this the rule fires in every repo. |
| `allow_if_untracked: true` | `file` | Skip for a file git does not track yet — the "you may write the migration you just created" carve-out. |
| `only_on_default_branch: true` | `bash` | Fire only when HEAD is positively known to be the repo's default branch. |
| `match: argv` | `bash` | Match the command's *unquoted* words instead of the raw string, so quoted or echoed text that runs nothing cannot trip the rule. Payloads passed to a nested shell (`bash -c "…"`, `eval "…"`) are still matched. |
| `allow_paths: ['^/tmp/']` | `bash` | Skip when **every** operand is an absolute path matching one of these prefixes. Relative operands and compound commands (`&&`, `;`, `\|`, `$(…)`) never qualify. |
| `ignore_case: false` | both | Opt out of the default case-insensitive match — useful for a path pattern that should not also match `FOO.KEY`. |
| `requires_manifest_missing: a.b` | both | Fire only while that dotted manifest path is absent, `false`, or empty. Turns a rule into a **self-silencing reminder**: it nags while setup is missing and goes quiet once the manifest records it. Note the failure direction — no manifest at all counts as missing, so the reminder appears rather than suppressing itself. |

Two properties to preserve when adding a flag:

- **Fail protective.** Every probe is best-effort. No git, no manifest, an unparseable command, a detached HEAD — the rule must fall back to behaving as a plain pattern match (or stay silent, for a rule that *adds* blocking). It must never quietly drop an existing safety rule.
- **Never raise.** The engine allows the action on any internal error. A guardrail that crashes the hook would block every tool call in the workspace.

### Enforcement surface — who the rule holds for

The PreToolUse engine only fires when *Claude* is about to act. A teammate in their IDE, or CI, never touches that path, so a rule is only as universal as its **surface**:

| `surface` | Enforced by | Holds for |
|---|---|---|
| `agent` | `.claude/hooks/lodestar-guardrails.py` (PreToolUse) | Claude tool-use only |
| `commit` | `.claude/hooks/lodestar-precommit-check.py` (pre-commit) | any committer |
| `both` | both hooks | everyone |

A `commit`/`both` rule needs something the pre-commit checker can run — `commit_check`, or an `event: file` pattern (which defaults to `staged-paths`):

| `commit_check` | What it inspects |
|---|---|
| `staged-paths` | the rule `pattern` against staged paths. `allow_if_untracked` maps onto git status: `A` (new in this commit) is allowed, `M` (already committed) is not |
| `secret-scan` | the staged diff, via `gitleaks` when installed, else conservative built-in patterns |
| `default-branch` | whether HEAD is the repo's default branch |

`commit_severity` overrides `severity` on the commit surface only — use it where a rule should merely remind Claude but hard-stop a commit.

A rule that reminds rather than forbids should silence itself. Without `requires_manifest_missing` you get one of two bad outcomes: a permanent nag (which trains people to ignore every warn the engine emits) or a one-time message (which is indistinguishable from no rule at all). `design-guidance-on-ui-edits` is the reference: it fires on UI edits while `designGuidance.installed` is false, and never again once it is true.

**Choosing a surface is a judgement about false positives, not about how much you care.** Three rules that look like obvious commit-surface candidates are deliberately `agent`-only:

- **`protect-generated-files`** matches `graph.json`, which the freshness hook *intentionally* rebuilds and stages into the same commit. Enforcing at commit time would break the lockstep map.
- **`no-hand-edit-lockfiles`** and **`protect-dbmate-schema`** guard files that legitimate tooling commits constantly; a pre-commit hook cannot tell a `yarn add` rewrite from a hand-edit.
- **`commit-message-style`** needs the `commit-msg` event, which reads the message file rather than the staged diff.

The commit surface must **never break an unrelated commit**: the checker exits 1 only on a `block` match, and a missing tool, unreadable manifest, invalid regex, or internal error all exit 0. `git commit --no-verify` stays the documented bypass — which is also why a commit hook is not a substitute for server-side branch protection against a determined committer.

Frontmatter parsing is deliberately minimal: scalars and inline lists (`[a, b]`) only. A regex containing a comma cannot go in a list value — use a single scalar pattern instead.

`file` rules see the edited path; add `match: content` to test the edited text instead. Note the engine is registered for `Bash|Edit|Write|MultiEdit`, so a rule cannot intercept a `Read` — a rule body promising "never read this" is documenting intent for the model, not enforcing it.

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
1. Add a detection signal to `/lodestar-onboard` §2 (e.g. "`Cargo.toml` present → `rust`").
2. Tag relevant catalog entries with the new stack.
3. That's it — the pickers intersect detected stacks with entry `stacks` automatically.

A tag with no entries behind it is worse than no tag: the repo matches nothing and gets the universal core silently. So onboarding treats "detected a stack, matched no pack" as a reportable gap — it writes the unmatched tags into the manifest as `catalogGaps`, generates a workspace `docs/EXTENDING.md` from `kit/templates/docs/extending-gap.md`, and says so in its summary. If you add a detector, add at least a conventions skill with it.

### What a pack looks like

The Laravel pack is a good shape to copy — three guardrails (migrations that already ran, framework-generated paths, the formatter), three narrow agents (endpoint / migration / test writer), one conventions skill. Keep every piece **thin**: the skill points at `docs/REPO/`, and the agents point at the skill. A pack that restates framework documentation goes stale and burns context; a pack that names the repo's own conventions doc does not.

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
