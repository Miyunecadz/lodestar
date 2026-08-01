---
id: scan-secrets-before-commit
title: Scan the staged diff for secrets before committing
category: secrets
severity: warn
recommended: true
stacks: [all]
event: bash
pattern: '(^|[;&|]\s*)git(\s+-\S+)*\s+commit\b'
match: argv
surface: both
commit_check: secret-scan
commit_severity: block
emits: rule
---

Before committing, check the staged diff for hardcoded credentials — a leaked secret in git history is expensive to purge and must be rotated even after removal. Run `git diff --cached` and scan for obvious credential shapes: AWS keys (`AKIA[0-9A-Z]{16}`), private-key headers (`-----BEGIN [A-Z ]*PRIVATE KEY-----`), bearer/API tokens, and `password`/`secret`/`token =` assignments with real-looking values.

If the repo has a scanner configured, prefer it: `gitleaks git --staged` (`gitleaks protect --staged` on older releases) or `detect-secrets-hook`. This is advisory — it reminds, it does not block. If you find a secret, unstage it, move the value to `.env` / a secrets manager, and reference it via config. Complements [[block-env-files]], which only stops `.env` files from being read/written, not secrets pasted inline.

**Advisory only, and it fires on every commit.** A `PreToolUse` hook sees the command about to run, not whether you already did the step it asks for — it cannot confirm a scan or review happened, so treat it as a checklist prompt rather than a gate. A real gate needs state written by the prior step or a `commit`-surface git hook that runs for every committer, Claude or not (issue #3).

Matching is anchored to a real invocation (`match: argv` on `git … commit` at a command boundary), so `git commit` inside a quoted string or an echoed message no longer triggers it. `git commit --amend` does still count — amending is committing.

**Surface: `both`, and this is where it stops being advisory.** The commit-time check (`commit_check: secret-scan`) actually inspects the staged diff for every committer. With `gitleaks` installed it blocks on findings (`commit_severity: block`). Without it, the built-in patterns are deliberately conservative and only **warn** — heuristics precise enough to nag are not precise enough to stop a teammate's commit. Install `gitleaks` to get enforcement.

**A broken scanner is not a finding.** This is the one rule that can stop a stranger's commit, so the checker only treats gitleaks as authoritative when it produced a findings report. An invocation that fails — removed subcommand, malformed `.gitleaks.toml`, unsupported flag after an upgrade — degrades to the built-in patterns and **warns**, naming the failure and the gitleaks version, rather than reporting usage text as leaked credentials. See `docs/EXTENDING.md` for the full table.
