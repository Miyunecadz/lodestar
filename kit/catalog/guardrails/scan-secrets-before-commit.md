---
id: scan-secrets-before-commit
title: Scan the staged diff for secrets before committing
category: secrets
severity: warn
recommended: true
stacks: [all]
event: bash
pattern: 'git commit'
emits: rule
---

Before committing, check the staged diff for hardcoded credentials — a leaked secret in git history is expensive to purge and must be rotated even after removal. Run `git diff --cached` and scan for obvious credential shapes: AWS keys (`AKIA[0-9A-Z]{16}`), private-key headers (`-----BEGIN [A-Z ]*PRIVATE KEY-----`), bearer/API tokens, and `password`/`secret`/`token =` assignments with real-looking values.

If the repo has a scanner configured, prefer it: `gitleaks protect --staged` or `detect-secrets-hook`. This is advisory — it reminds, it does not block. If you find a secret, unstage it, move the value to `.env` / a secrets manager, and reference it via config. Complements [[block-env-files]], which only stops `.env` files from being read/written, not secrets pasted inline.
