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
3. Write a message body that **redirects to the right action**, not just "denied." Put the redirect first, then a bare `---` line, then the design rationale — see below.
4. **Check it with `--explain`** against inputs it must and must not match — see below.
5. **Add fixtures** to `.github/fixtures/guardrails.tsv` — at least one case showing it fires and one showing what it must not match. CI rejects a guardrail with neither.
6. Re-run `/lodestar-guardrails` and tick your new rule.

### The authoring loop: `--explain`

Install the rule, then ask the engine what it does. This is the recommended inner loop — seconds per iteration, no live session, and safe for a rule whose whole job is to block something destructive:

```bash
python3 .claude/hooks/lodestar-guardrails.py --explain --bash 'rm -rf /tmp/scratch'
python3 .claude/hooks/lodestar-guardrails.py --explain --file api/.env.local.example
```

```
input     bash: rm -rf /tmp/scratch
rules     1 applying to a bash event, from /w/.claude/guardrails

block-destructive-commands  [block]
  field       argv     rm -rf /tmp/scratch
  pattern     matched  (\brm\s+-[a-zA-Z]*[rf]|\bgit\s+reset\s+--hard)
  probe       allow_paths — operands ['/tmp/scratch']
  verdict     ALLOW — matched, then suppressed by `allow_paths`

verdict   ALLOW
```

The last two lines are the point. **Why a rule did *not* fire is invisible in normal use** — a pattern that never matched and a match silenced by a context flag look identical from the outside, and they need opposite fixes. `--explain` names the flag.

| Flag | What it does |
|---|---|
| `--bash '<command>'` | explain a Bash command |
| `--file <path>` | explain an `Edit`/`Write` on that path |
| `--content '<text>'` | with `--file`: the edited text, for a `match: content` rule |
| `--rule <name>` | narrow to one rule; exits 1 if no enabled `agent` rule has that name |
| `--json` | machine-readable — the same trace, plus the overall verdict |

Two things it deliberately does:

- **Reads the installed rules, not the catalog.** It loads `$CLAUDE_PROJECT_DIR/.claude/guardrails/`, so it explains the rule *as the picker installed it* — which is what enforces. A rule that lost a context field on install shows up here as behaviour, not as a diff.
- **Shares one code path with the hook.** Both go through `evaluate()`, so the explanation cannot drift from the decision. `test-engine.sh` asserts they agree on the same input; an explainer describing an engine nobody runs would be worse than none.

It writes nothing and needs no session — every probe it consults is a read.

### Behaviour fixtures

`validate.py` checks that a pattern *compiles*. That is not the same as checking it matches what the rule's title claims, and the gap is silent: a tightened regex that accidentally stops matching looks exactly like a working one.

`.github/scripts/test-catalog.py` closes it by installing the **real** `kit/catalog/guardrails/<id>.md` — applying the same `id:` → `name:` transform `/lodestar-guardrails` §5 does — and running the shipped engine against it. Hand-written copies of a rule in a test file cannot do this: if the copy and the catalog drift apart, both keep passing.

The table is tab-separated:

```
rule-id <TAB> verdict <TAB> input <TAB> context

  verdict  DENY | WARN | ALLOW
  input    a file path for `event: file`, a command for `event: bash`
  context  optional key=value,key=value —
             branch=default   run with HEAD on the repo's default branch
             untracked=1      leave the file untracked, for `allow_if_untracked`
             path=<path>      for `match: content` rules: the file being edited
                              (the input is then the edited content)
```

The harness builds a workspace whose manifest declares **one repo per stack the catalog targets**, so a stack-scoped rule has both a repo it belongs in and a repo it must stay out of. One rule is installed at a time — several rules match `git commit`, and a shared rule set would blur which one produced the verdict.

Two things worth knowing when adding cases:

- **A negative case must fail for the reason you think.** Every file path is committed unless the row says `untracked=1`, because an untracked file is skipped by `allow_if_untracked` rules for a reason unrelated to the pattern or the stack. Mutation-testing this harness caught exactly that: widening a migration rule to `stacks: [all]` failed nothing, because its wrong-stack negative was passing on untracked-ness.
- **`emits: settings-hook` entries never reach the engine.** The picker writes a `settings.json` PostToolUse hook, and a hook `matcher` selects on *tool name*, not on a path — so the pattern lands inside the shell logic the hook runs, where nothing pins its shape. Those rows therefore assert the pattern directly; asserting an engine verdict would test a path that does not exist in production. The same absence of a pinned shape is why `lodestar-rule-check.py` reports an adopted settings-hook entry as *not compared* rather than comparing it.

Prefer cases that pin a claim the rule body already makes — the negative lookahead, the stack scope, the quoted-argument exemption. A case that merely re-states "this regex matches this string" adds a line and no confidence.

### The `---` split: redirect above, rationale below

A rule file has two readers with opposite needs. The model wants the redirect — what to do instead — and nothing else. A person opening the catalog wants the reasoning: why this surface, how the matcher works, what the rule deliberately does not cover. Both belong in the file; only the first belongs in the message.

A bare `---` line separates them. Everything above it is sent when the rule fires; everything below stays in the file for whoever reads it:

```markdown
Applied migrations are immutable — create a NEW migration with `yarn db:new <name>`
and write your forward/rollback SQL there.

---

**Surface: `both`.** Also enforced for every committer: staging a modification to a
migration git already tracks blocks the commit, while adding a new one is allowed.
```

The test for what goes above: **would the model need this to take the right next action?** Design notes, surface justifications, and matcher internals fail it. So does anything describing when the rule *doesn't* fire — an `allow_if_untracked` paragraph explains a case the model never sees, because the rule stayed silent.

`validate.py` caps the block-time payload at **900 characters**. That is a ceiling, not a target; the shipped rules run 223–829. A rule with no separator sends its whole body, so older and hand-written rule files keep working unchanged.

Both fields the engine emits on a block carry different payloads, because they have different readers: `permissionDecisionReason` goes to the model and carries the redirect; `systemMessage` goes to the **user** and is a one-line "Lodestar blocked this — `<rule>`". Sending the same body to both was pure duplication; sending only one would leave the user with an unexplained block.

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
- **Never hang.** Never-raise is an *inner* guarantee: it only holds for code that reaches its own exception handler. A hook wedged on a stalled network mount never gets there, and Claude Code's default timeout for a `command` hook is **600 seconds**. So the registration in `/lodestar-guardrails` sets `"timeout": 5` — the outer layer of the same promise. Measured latency is ~25 ms with eight rules, so the ceiling has roughly 200× headroom; it exists to bound a pathological environment, not a normal one. Any hook the kit registers needs the field.

#### One rule failing vs. the whole rule set failing

These two are not the same event, and conflating them is how "enforced, not advisory" quietly stops being true. Failing protective is scoped to **one rule**: the rest of the set still enforces, so degrading that rule is a proportionate response. A failure that takes out **every** rule is different — the engine has no decision to make, so the action proceeds, and the workspace has no guardrails at all while looking exactly like a clean pass.

So the engine treats them differently:

| Event | Behaviour |
|---|---|
| One rule file unreadable or malformed | Skipped. The remaining rules load and enforce. |
| Rule files exist but **none** load | `RuleSetError` → a `systemMessage` beginning **`⛔ LODESTAR GUARDRAILS ARE NOT ENFORCING`**. |
| Interpreter below `MIN_PYTHON` | Same message, checked before anything else runs. |
| No rule files at all | `{}`. Nothing to enforce is a legitimate state, not a failure. |

**Python floor.** Both enforcement hooks declare `MIN_PYTHON = (3, 8)` — Ubuntu 20.04 LTS and RHEL 8 ship 3.8 as `python3`. The floor is not decorative: this class of bug produces no stack trace a user will see, only silence. A dict-union expression (`a | b`, 3.9+) once made `load_rules` raise for every file, and the whole rule set went inert behind one easily-missed line of `systemMessage`. CI runs `test-engine.sh` and `test-precommit.sh` against the floor and the current release; both take `LODESTAR_TEST_PYTHON` so you can do the same locally. Raising the floor means changing `MIN_PYTHON` in both hooks, the CI matrix, and the README Requirements table together.

### Enforcement surface — who the rule holds for

The PreToolUse engine only fires when *Claude* is about to act. A teammate in their IDE, or CI, never touches that path, so a rule is only as universal as its **surface**:

| `surface` | Enforced by | Holds for |
|---|---|---|
| `agent` | `.claude/hooks/lodestar-guardrails.py` (PreToolUse) | Claude's `Bash`/`Edit`/`Write`/`MultiEdit` calls |
| `commit` | `.claude/hooks/lodestar-precommit-check.py` (pre-commit) | any committer |
| `permission` | Claude Code core, via `permissions.deny` in `settings.json` | Claude tool-use, **every tool including `Read`** |
| `both` | both hooks | the legacy spelling of `[agent, commit]` |

`surface` accepts a scalar or an inline list, so a rule can name several: `surface: [agent, commit, permission]`. `both` predates the permission surface and still means `[agent, commit]`, so rule files installed by an older version keep working.

**A rule that does not include `agent` is skipped by the engine.** Before the permission surface existed, nothing declared a non-agent surface, so the engine ignored the field and ran every rule it found. It now filters — which matters the moment a rule is `permission`-only, since otherwise it would be enforced twice and reported twice.

### `permission` — the strongest surface, where it fits

`permissions.deny` beats a hook on three counts: it applies to **every tool** (a PreToolUse matcher can be extended to `Read`, but the deny list is there already), deny rules **merge across settings scopes** so a local file cannot loosen a project one, and there is **no interpreter to crash** — the engine deliberately allows the action on an internal error, which is correct for a hook and wrong for a secret.

It is not a superset, though, and the difference decides what belongs there:

| | Hook pattern | `permissions.deny` |
|---|---|---|
| Expressiveness | full regex, including negative lookahead | gitignore-style globs, no negation |
| Context | branch, tracked status, repo stacks, shell words | none — static path matching |
| Message | your redirect text | a generic denial |

So a rule with an **exception** cannot be ported wholesale. `block-env-files` must allow `.env.local.example` while blocking `.env.local`; no deny glob expresses that, so its `permission_rules` name only files that can never be a template and the regex keeps the rest. `block-secret-files` has no such carve-out, so its deny list mirrors its regex.

Because the translation is a judgement, the author writes it out:

```yaml
surface: [agent, commit, permission]
permission_rules: [Read(./.env), Read(./**/.env)]
```

Each entry is a `Tool(pattern)` rule in Claude Code's own permission syntax; `validate.py` rejects anything that is not. Entries cannot contain a comma — frontmatter lists split on it.

Applying them is a script, not a prose instruction, because the merge has to be idempotent and reversible:

```bash
python3 .claude/hooks/lodestar-permissions.py --dry-run   # plan
python3 .claude/hooks/lodestar-permissions.py             # apply
python3 .claude/hooks/lodestar-permissions.py --check     # exit 1 if out of sync (CI)
```

It preserves hand-written deny entries, never duplicates on a re-run, and when a rule is unticked removes exactly the entries that rule contributed — it knows which are its own from `guardrailSurfaces.permission.entries` in the manifest. Never hand-edit that key.

A `commit`/`both` rule needs something the pre-commit checker can run — `commit_check`, or an `event: file` pattern (which defaults to `staged-paths`):

| `commit_check` | What it inspects |
|---|---|
| `staged-paths` | the rule `pattern` against staged paths. `allow_if_untracked` maps onto git status: `A` (new in this commit) is allowed, `M` (already committed) is not |
| `secret-scan` | the staged diff, via `gitleaks` when installed, else conservative built-in patterns |
| `default-branch` | whether HEAD is the repo's default branch |

`commit_severity` overrides `severity` on the commit surface only — use it where a rule should merely remind Claude but hard-stop a commit.

#### How `secret-scan` degrades

This is the only check that shells out to a third-party binary, and — paired with `commit_severity: block` — the only code path in Lodestar that can stop a stranger's commit. So it distinguishes a *finding* from a *tool failure*, and never reports the second as the first:

| gitleaks did | Result |
|---|---|
| exited 0 | clean scan, authoritative |
| exited 1 **and** wrote a JSON report with findings | findings, reported as `file:line: rule` — `block` stands |
| exited non-zero with no usable report | **tool failure** → built-in patterns, `block` degraded to `warn`, and the reason printed even when nothing was found |
| is not installed | built-in patterns, `block` degraded to `warn`, reported only when something matches |

The discriminator is the **report**, not the exit code: gitleaks exits 1 both for "leaks found" and for several fatal errors (unknown subcommand, malformed `.gitleaks.toml`, unsupported flag after an upgrade), so an exit code alone cannot tell a credential from a usage message. `gitleaks git --staged` is tried before the deprecated `gitleaks protect --staged`. Findings never include the matched secret — the output goes to a terminal and, on the CI path, into a build log.

The two degradations are reported differently on purpose. Having no scanner is a steady state, and announcing it on every commit is the warn fatigue that teaches people `--no-verify`. A scanner that is installed and failing is news: staying quiet would leave someone believing their commits are scanned when they are not.

A rule that reminds rather than forbids should silence itself. Without `requires_manifest_missing` you get one of two bad outcomes: a permanent nag (which trains people to ignore every warn the engine emits) or a one-time message (which is indistinguishable from no rule at all). `design-guidance-on-ui-edits` is the reference: it fires on UI edits while `designGuidance.installed` is false, and never again once it is true.

**Choosing a surface is a judgement about false positives, not about how much you care.** Three rules that look like obvious commit-surface candidates are deliberately `agent`-only:

- **`protect-generated-files`** matches `graph.json`, which the freshness hook *intentionally* rebuilds and stages into the same commit. Enforcing at commit time would break the lockstep map.
- **`no-hand-edit-lockfiles`** and **`protect-dbmate-schema`** guard files that legitimate tooling commits constantly; a pre-commit hook cannot tell a `yarn add` rewrite from a hand-edit.
- **`commit-message-style`** needs the `commit-msg` event, which reads the message file rather than the staged diff.

The commit surface must **never break an unrelated commit**: the checker exits 1 only on a `block` match, and a missing tool, unreadable manifest, invalid regex, or internal error all exit 0. `git commit --no-verify` stays the documented bypass — which is also why a commit hook is not a substitute for server-side branch protection against a determined committer.

#### Two roots, and which one resolves what

On the commit surface there are two directories that are the same in a monorepo and different in the separate-sub-repos layout (each repo its own git repo, `.claude/` in the parent — the layout `/lodestar-guardrails` §6b explicitly supports). Conflating them is how `stacks` scoping silently stopped working there:

| Root | Found by | Resolves |
|---|---|---|
| **git root** — the repo being committed | `git rev-parse --show-toplevel` | staged paths, which `git diff --cached` reports relative to *it* |
| **workspace** — where `.claude/` lives | walk up for `.claude/guardrails`, or `$LODESTAR_WORKSPACE` | manifest `repos[].path`, and the rule files themselves |

Resolving a staged path against the workspace names a file that exists under no onboarded repo. `stacks_for` then returns `None`, `in_scope` fails protective and returns `True`, and the rule fires **with no scoping at all** — a `python-django` rule matching `migrations/.*\.py$` could block a staged path in a Node repo, against `CATALOG.md`'s promise that a pack rule cannot fire in the wrong repo of a mixed workspace. Note the failure direction: the protective default is right for one unknown path and wrong as a steady state, because it turns a scoped rule into an unscoped one without any signal.

Frontmatter parsing is deliberately minimal: scalars and inline lists (`[a, b]`) only. A regex containing a comma cannot go in a list value — use a single scalar pattern instead.

The parser, `coerce`, `as_list`, and `surfaces_of` are **duplicated across every hook that reads a rule file, on purpose** — each must work when copied into `.claude/hooks/` alone, with no shared module to import. `test-hook-parity.py`'s `FILES` is the list of them. The cost of that is exactly the bug above: one rule file, two parsers, scoped differently by each. `test-hook-parity.py` is what keeps the cost bounded — it feeds one corpus through every hook's copy and fails when they disagree. When you change one, change them all and let that gate confirm it; do not extract a shared module.

`file` rules see the edited path; add `match: content` to test the edited text instead. The engine is registered for `Bash|Edit|Write|MultiEdit`, so a **hook** rule still cannot intercept a `Read` — a rule body promising "never read this" needs the `permission` surface above to be an enforced stop rather than a note to the model.

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

### Writing a trigger that fires

A skill fails differently from a guardrail. A rule that stops matching eventually gets noticed; a skill that never loads is indistinguishable from a task that needed no skill — no error, no log, no output. So the properties that decide whether it fires are checked rather than left to review. `validate.py` enforces all four:

- **The description starts `Use when`.** It is the whole routing decision: the model reads an index of triggers and pulls the body only when one matches the task in front of it. "Backend conventions for the API repo" is a summary — it describes the skill instead of naming the moment to load it. Name the task, and name what it excludes if that is what distinguishes it (`planning-workflow` ends "Not for implementation.").
- **Two skills sharing a stack may not read alike.** The model chooses *between* triggers, so two that a person cannot tell apart make the choice arbitrary. The check compares pairs sharing a literal `stacks` tag, plus every pair involving a `stacks: [all]` skill — same-stack is where the model has nothing but the wording to route on. It is narrower than "could co-load": a repo matches several tags at once and §5 copies every match into one `.claude/skills/`, so two skills with different tags do end up side by side without being compared. Nothing in the catalog is near the limit today (the highest pair is 0.69), so the narrowness costs nothing yet; what it protects is the per-stack conventions family, which is *correctly* similar by design and differentiated by a short decisive token rather than by sentence shape. `graphql-contract` and `drf-api-contract` show why the reader still matters more than the check: different stacks, so they are never compared, and each names its own surface anyway ("GraphQL schema", "REST API surface").
- **`stacks` values must be tags `/lodestar-onboard` §2 can detect.** The vocabulary is that table, read directly — not a second list kept in step by hand. A typo (`react-nativ`) yields an entry that installs cleanly and matches nothing, so add the detector *before* the tag (see [Add a stack detector](#add-a-stack-detector)).
- **The file stays under 2000 bytes.** A skill is a router, not a knowledge base. The shipped ten run 723–1593 bytes; past the budget it has become the always-on payload the router exists to avoid. Move the content into `docs/…` and point at it.

### The `REPO` substitution

`REPO` in a skill body is a placeholder, on purpose — `/lodestar-onboard` §5 replaces it with the repo's basename when it installs the skill, so the body points at that repo's own `docs/<repo>/conventions.md`. Six of the shipped skills rely on it.

`test-skill-install.py` asserts that installing resolves it — see [CI.md](CI.md) for what that gate does. Two consequences for you: leave the `REPO` token alone in a skill body (it is resolved at install time, not a typo), and if you point a skill at a new `docs/…` path, add the template that puts that file in a workspace, or the gate fails on a path no user has.

## Add a stack detector

To support a new stack:
1. Add a detection signal to `/lodestar-onboard` §2, as a table row — `` | `Cargo.toml` present | `rust` | ``. The row shape matters: `validate.py` parses that table to get the vocabulary every entry's `stacks` is checked against, so a signal written any other way leaves the tag unknown and fails your own new entry.
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
