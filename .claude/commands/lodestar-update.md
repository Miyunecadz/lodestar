---
description: Update the installed Lodestar kit in this workspace — pull the latest source and re-sync catalog, templates, commands, and the guardrail engine, without touching anything you generated.
argument-hint: (run from the workspace root)
allowed-tools: Bash, Read, AskUserQuestion
effort: low   # mechanical: git pull the source, re-run install.sh, diff versions, report
---

You update the Lodestar **kit** installed in this workspace to the latest version. This refreshes the reusable catalog/templates/commands/engine only — it must **never** touch what the user generated (their manifest, `.claude/guardrails/*`, `.claude/agents/*`, `.claude/settings.json`, `CLAUDE.md`, or `docs/`). Narrate each step.

## 1. Locate the install
- Confirm `.lodestar/` exists here. If not, this workspace has no Lodestar install — tell the user to run `install.sh <workspace>` first and stop.
- Read `.lodestar/SOURCE` (the path to the source clone) and `.lodestar/VERSION` (the currently-installed version). If `SOURCE` is missing (installed before updater support), ask the user for the path to their Lodestar clone (AskUserQuestion / free text) and proceed with that.

## 2. Pull the latest source
- Check the source is a git clone: `git -C "<SOURCE>" rev-parse --git-dir`. If it is, run `git -C "<SOURCE>" pull --ff-only` and report what came in. If the pull fails (local changes, detached, network), report the error and ask whether to continue with the source as-is or abort. If `<SOURCE>` is not a git repo (e.g. a copied folder), skip the pull and just re-sync from it.
- Read `<SOURCE>/VERSION` — the new version. If it equals `.lodestar/VERSION`, tell the user they're already current and ask whether to re-sync anyway (to repair files); otherwise continue.

## 3. Re-sync the kit (non-destructive)
- Run the source installer against this workspace: `"<SOURCE>/install.sh" "$PWD"`. It detects the existing install and updates in place — refreshing `.lodestar/catalog`, `.lodestar/templates`, `.claude/commands/lodestar-*.md`, and (only if already present) `.claude/hooks/lodestar-guardrails.py`, plus `.lodestar/VERSION` and `.lodestar/SOURCE`. It does not remove or overwrite any generated content.
- Do **not** hand-copy files yourself — let `install.sh` do it so the behavior stays in one place.

## 4. Report what changed and what to do next
- Show old → new version. Summarize notable changes from `<SOURCE>/CHANGELOG.md` for the new version.
- Compare the refreshed catalog against the manifest's enabled ids: list any **new catalog entries** (guardrails / agents / skills) now available that the workspace hasn't adopted. This is the key value — the user won't see new rules/agents until they opt in.
- Recommend the follow-ups only where relevant:
  - New or changed **guardrails** → re-run `/lodestar-guardrails` and tick them.
  - New or changed **agents** → re-run `/lodestar-agents`.
  - New **stack skills** → re-run `/lodestar-onboard ./<repo>` for the affected repo.
- Remind the user their existing rules/agents/docs were left exactly as they were; updating the catalog never regenerates them silently — adoption is always an explicit re-run.
