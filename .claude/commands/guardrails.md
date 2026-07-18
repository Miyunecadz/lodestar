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

## 4. Write the selected rules
For each chosen entry:
- If `emits: hookify`: write `.claude/hookify.<id>.local.md` with frontmatter `name`, `enabled: true`, `event`, `pattern`, and the message body from the catalog entry. Preserve `severity` semantics (a `block` rule must instruct hard refusal + the correct alternative; a `warn` rule advises).
- If `emits: settings-hook`: add the corresponding hook to `.claude/settings.json` (create the file/`hooks` key if absent). Use this only for rules needing custom logic (e.g. a per-repo lint router that maps an edited path to that repo's linter).

Never write secrets. These files are meant to be safe to share (the actual `.local.md` suffix keeps them out of version control by default).

## 5. Update the manifest & report
- Set `.claude/lodestar.manifest.json` `guardrails` to the enabled ids.
- Report what was enabled, grouped by block vs warn. Explain how to disable one (set `enabled: false` in its `.local.md`, or re-run this command and untick it).
