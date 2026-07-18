---
description: Pick which guardrails to enforce in this workspace from a stack-aware catalog — safety rules hard-block, quality rules warn.
argument-hint: (run after onboarding at least one repo)
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion
---

You are the Lodestar guardrails installer. Guardrails are **enforced** (deterministic hooks/permissions), unlike advisory docs. Present a menu, then write only what the user selects. Narrate each step.

## 1. Load context
- Read `.claude/lodestar.manifest.json`. Collect the union of all `stacks` across onboarded repos.
- If there are no repos yet, tell the user to run `/onboard-repo` first and stop.

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

## 5. Write the selected rules — into the `.claude/guardrails/` folder
For each chosen entry:
- If `emits: rule`: write `.claude/guardrails/<id>.md` with frontmatter `name: <id>`, `enabled: true`, `event`, `pattern`, `severity` (`block`/`warn`), and the message body from the catalog entry — copied verbatim (a `block` message must redirect to the correct alternative, not just deny). Keeping one rule per file in this folder is the whole point: `.claude/` root stays clean.
- If `emits: settings-hook`: add the corresponding hook to `.claude/settings.json` directly (e.g. a per-repo lint **router** that must run a linter after an edit — that needs shell logic the declarative engine doesn't do). This is the only case that still writes into `settings.json` beyond the engine registration above.

Never write secrets into any rule file — they hold patterns and guidance only, and are safe to commit and share.

## 6. Update the manifest & report
- Set `.claude/lodestar.manifest.json` `guardrails` to the enabled ids.
- Report what was enabled, grouped by block vs warn, and note that rules live in `.claude/guardrails/` enforced by `.claude/hooks/lodestar-guardrails.py`. Explain how to disable one: set `enabled: false` in its `.claude/guardrails/<id>.md` (or delete the file), or re-run this command and untick it. Changes take effect on the next tool call — no restart.
