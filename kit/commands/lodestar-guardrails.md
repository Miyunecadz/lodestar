---
description: Pick which guardrails to enforce in this workspace from a stack-aware catalog — safety rules hard-block, quality rules warn.
argument-hint: (run after onboarding at least one repo)
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion
effort: low   # mechanical: intersect stacks, then copy catalog rule bodies verbatim
---

You are the Lodestar guardrails installer. Guardrails are **enforced** (deterministic hooks/permissions), unlike advisory docs. Present a menu, then write only what the user selects. Narrate each step.

## 1. Load context
- Read `.claude/lodestar.manifest.json`. Collect the union of all `stacks` across onboarded repos.
- If there are no repos yet, tell the user to run `/lodestar-onboard` first and stop.

## 2. Build the candidate list
- Read every entry in `.lodestar/catalog/guardrails/*.md`.
- Keep an entry if its `stacks` is `[all]` or intersects the workspace stacks.
- Group by `category` (safety, secrets, database, dependencies, quality, generated). Note each entry's `severity` (block/warn).

## 2b. Adaptive recommendation pass
Decide which candidates to **pre-check** by reading repo signals, not just the static `recommended` flag. A rule is recommended for this workspace if ANY of these hold:
- its frontmatter has `recommended: true`, OR
- it is tagged to a **capability** stack the workspace actually has (`has-eslint` → `autolint-on-edit`; `has-python-lint` → `python-autolint-on-edit`; `has-gitleaks` → `scan-secrets-before-commit`; etc.), OR
- a quick scan of the onboarded repos surfaces its trigger even though no tag captured it — e.g. a `.pre-commit-config.yaml` or CI step already running gitleaks/eslint means the matching autolint/secret-scan rule is worth enabling for parity.

This is how "does this codebase need this?" is answered: detection feeds the picker, the catalog stays authoritative, and the human still confirms every rule. Never invent a rule that isn't in the catalog — if a repo needs something new, author a catalog entry (see `docs/EXTENDING.md`) rather than emitting an ad-hoc hook.

## 3. Present the picker
Use AskUserQuestion with **multiSelect: true**. One question per category (or a single grouped question if few). For each option:
- Label = the rule `title` + a `[block]` or `[warn]` tag.
- Description = the one-line effect. For a rule pre-checked by §2b for a reason other than `recommended: true`, append why (e.g. "— your repo already runs gitleaks").
- Pre-check (put first / recommend) every entry the §2b pass marked recommended.

Make clear: **block** rules stop the action and redirect; **warn** rules inform without stopping.

## 4. Install the guardrail engine (once)
Lodestar enforces `emits: rule` guardrails with its own **self-contained engine** — no external plugin. Ensure these exist:
- Copy `.lodestar/templates/hooks/lodestar-guardrails.py` to `.claude/hooks/lodestar-guardrails.py` (create `.claude/hooks/` if absent). Make it executable (`chmod +x`).
- Register it in `.claude/settings.json` as a **PreToolUse** hook (create the file / `hooks` key if absent; do not duplicate if already present):
  ```json
  {
    "hooks": {
      "PreToolUse": [
        {
          "matcher": "Bash|Edit|Write|MultiEdit",
          "hooks": [
            { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/lodestar-guardrails.py\"" }
          ]
        }
      ]
    }
  }
  ```
The engine reads every rule in `.claude/guardrails/*.md` on each matching tool call: `block` rules deny the action (with the redirect message); `warn` rules surface the message without stopping. `file` rules match the edited **path**; `bash` rules match the **command**.

Rules can also opt into a **context layer** the engine computes per invocation (git tracked-status and branch, the target repo's stacks from the manifest, shell-word tokenization) — that is what makes `stacks:` actually scope a rule and lets a migration guard allow the file you just created. Every probe fails protective: no git, no manifest, or an unparseable command means the rule behaves as a plain pattern match. See `docs/EXTENDING.md` for the flags.

## 5. Write the selected rules — into the `.claude/guardrails/` folder
For each chosen entry:
- If `emits: rule`: write `.claude/guardrails/<id>.md` with frontmatter `name: <id>`, `enabled: true`, `event`, `pattern`, `severity` (`block`/`warn`), and the message body from the catalog entry — copied verbatim (a `block` message must redirect to the correct alternative, not just deny). Keeping one rule per file in this folder is the whole point: `.claude/` root stays clean.
  - **Copy the catalog entry's `stacks`, context flags, and surface fields too** — `stacks`, `allow_if_untracked`, `only_on_default_branch`, `match`, `allow_paths`, `ignore_case`, `surface`, `permission_rules`, `commit_check`, `commit_severity`. These are what the engine's context layer reads; a rule installed without them silently loses its scoping and fires everywhere. Copy the values verbatim, including list syntax (`stacks: [react-native]`, `surface: [agent, commit, permission]`).
- If `emits: settings-hook`: add the corresponding hook to `.claude/settings.json` directly (e.g. a per-repo lint **router** that must run a linter after an edit — that needs shell logic the declarative engine doesn't do). This is the only case that still writes into `settings.json` beyond the engine registration above.

Never write secrets into any rule file — they hold patterns and guidance only, and are safe to commit and share.

## 5b. Apply the permission surface (automatic — no prompt needed)

A rule may declare `surface: permission`, meaning some of what it forbids is enforced by Claude Code's own `permissions.deny` in `.claude/settings.json` rather than by a hook. That mechanism is stronger where it applies: it covers **every tool including `Read`** (which the PreToolUse engine cannot intercept), deny rules merge across settings scopes so a local file cannot loosen a project one, and there is no interpreter that could fail open.

Do not hand-edit `settings.json` for this. Run the shipped applier, which is idempotent and reversible:

```bash
cp .lodestar/templates/hooks/lodestar-permissions.py .claude/hooks/lodestar-permissions.py
python3 .claude/hooks/lodestar-permissions.py --dry-run    # show the plan
python3 .claude/hooks/lodestar-permissions.py              # apply
```

It reads the same `.claude/guardrails/*.md` files, collects `permission_rules` from every enabled rule on the permission surface, and merges them into `permissions.deny` — preserving entries the user wrote by hand, never duplicating on a re-run, and removing exactly the entries a now-unticked rule had contributed. Ownership is tracked in the manifest under `guardrailSurfaces.permission.entries`, which is what makes the removal safe.

Report the entry count and say plainly what it bought: reads of those paths are now blocked outright, not merely discouraged.

## 6. Install the commit surface (opt-in — this is what covers non-Claude commits)

The engine from §4 is a **PreToolUse** hook: it only fires when *Claude* is about to act. A teammate editing in their IDE, or CI, never touches that path — so a rule labelled "safety" is, by itself, enforced against one committer out of many. Rules that must hold for **any** committer declare it in frontmatter:

| `surface` | Where it holds | Enforced by |
|---|---|---|
| `agent` | Claude tool-use (Bash/Edit/Write/MultiEdit) | the PreToolUse engine |
| `commit` | any committer | the pre-commit checker |
| `permission` | Claude tool-use, **every tool including `Read`** | Claude Code core, via `permissions.deny` |
| `both` | the legacy spelling of `[agent, commit]` | both of those |

`surface` accepts a list, so a rule can name several (`surface: [agent, commit, permission]`) — which is what the secrets rules do, because no single mechanism covers all of what they forbid.

If any selected rule has `surface: commit` or `both`, offer to install the commit surface (AskUserQuestion, recommended). Be honest about the trade: it holds for everyone, and `git commit --no-verify` remains a deliberate bypass. If the user declines, say plainly which rules therefore hold **for Claude only** — that is the false-sense-of-security this step exists to remove.

**a. Copy the checker.** `.lodestar/templates/hooks/lodestar-precommit-check.py` → `.claude/hooks/lodestar-precommit-check.py`. It reads the same `.claude/guardrails/*.md` files, keeps the ones with a `commit`/`both` surface, and applies them to the **staged** change: `staged-paths` matches the rule pattern against staged paths (honoring `allow_if_untracked` — at commit time `A` is a new file, `M` an already-committed one), `secret-scan` inspects the staged diff, `default-branch` refuses a direct trunk commit. It exits 1 only on a `block` match; anything else — a warn, no rules, a missing tool, an internal error — exits 0.

**b. Detect the git-hook manager and integrate without clobbering.** Same detection as `/lodestar-freshness`, and the two must **coexist** — each adds its own distinct entry, never replacing the other's:
- **lefthook** (`lefthook.yml`) → add under `pre-commit.commands`:
  ```yaml
  pre-commit:
    commands:
      lodestar-guardrails:
        run: python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/lodestar-precommit-check.py"
  ```
- **husky** (`.husky/`) → append the `python3 …` line to `.husky/pre-commit`.
- **`core.hooksPath` set** → write into that directory, chaining any existing hook.
- **none** → write `.git/hooks/pre-commit` and `chmod +x`, chaining an existing hook rather than overwriting it.

Confirm the detected manager with the user before writing. In a **separate sub-repos** layout install into each repo you want covered; the checker walks up from the git root to find the workspace's `.claude/guardrails/` (or honors `LODESTAR_WORKSPACE`).

**c. Note the gap that remains.** Tell the user which selected rules are `agent`-only and why they cannot move to the commit surface — e.g. lockfiles and `db/schema.sql` are *supposed* to be committed by tooling, so a commit-time check cannot tell a legitimate regeneration from a hand-edit; force-push is a `pre-push` concern; commit-message style needs a `commit-msg` hook. For trunk protection that nobody can bypass, point at a server-side branch ruleset (`docs/CI.md`).

**d. Recommend `gitleaks` if `scan-secrets-before-commit` was selected.** With it installed the secret scan **blocks**; without it the built-in patterns only **warn**, because heuristics precise enough to nag are not precise enough to stop a teammate's commit.

## 7. Update the manifest & report
- Set `.claude/lodestar.manifest.json` `guardrails` to the enabled ids.
- If the commit surface was installed, record it: `"guardrailSurfaces": { "commit": { "hookManager": "lefthook|husky|hooksPath|git-hooks", "rules": [ ...ids... ] } }`. The permission applier writes its own `guardrailSurfaces.permission` record — do not edit that key by hand, or the next run will lose track of which deny entries are Lodestar's.
- Report what was enabled, grouped by block vs warn, **and by surface** — make explicit which rules hold for every committer and which are Claude-only. Note that rules live in `.claude/guardrails/` enforced by `.claude/hooks/lodestar-guardrails.py` (agent) and `.claude/hooks/lodestar-precommit-check.py` (commit). Explain how to disable one: set `enabled: false` in its `.claude/guardrails/<id>.md` (or delete the file), or re-run this command and untick it. Changes take effect on the next tool call — no restart.
