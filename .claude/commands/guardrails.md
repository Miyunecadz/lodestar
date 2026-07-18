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
- Group by `category` (database, secrets, dependencies, quality, generated). Note each entry's `severity` (block/warn).

## 3. Present the picker
Use AskUserQuestion with **multiSelect: true**. One question per category (or a single grouped question if few). For each option:
- Label = the rule `title` + a `[block]` or `[warn]` tag.
- Description = the one-line effect.
- Pre-check (put first / recommend) every entry with `recommended: true`.

Make clear: **block** rules stop the action and redirect; **warn** rules inform without stopping.

## 4. Write the selected rules
For each chosen entry:
- If `emits: hookify`: write `.claude/hookify.<id>.local.md` with frontmatter `name`, `enabled: true`, `event`, `pattern`, and the message body from the catalog entry. Preserve `severity` semantics (a `block` rule must instruct hard refusal + the correct alternative; a `warn` rule advises).
- If `emits: settings-hook`: add the corresponding hook to `.claude/settings.json` (create the file/`hooks` key if absent). Use this only for rules needing custom logic (e.g. a per-repo lint router that maps an edited path to that repo's linter).

Never write secrets. These files are meant to be safe to share (the actual `.local.md` suffix keeps them out of version control by default).

## 5. Update the manifest & report
- Set `.claude/lodestar.manifest.json` `guardrails` to the enabled ids.
- Report what was enabled, grouped by block vs warn. Explain how to disable one (set `enabled: false` in its `.local.md`, or re-run this command and untick it).
