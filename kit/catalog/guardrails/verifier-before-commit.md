---
id: verifier-before-commit
title: Review staged diff before committing
category: quality
severity: warn
recommended: false
stacks: [all]
event: bash
pattern: '(^|[;&|]\s*)git(\s+-\S+)*\s+commit\b'
match: argv
emits: rule
---

Before committing a non-trivial change, dispatch the `reviewer` agent on the staged diff (`git diff --cached`) to catch issues a regex can't — logic errors, missing cases, leaked debug code. This is advisory: it reminds you, it does not block the commit.

**Advisory only, and it fires on every commit.** A `PreToolUse` hook sees the command about to run, not whether you already did the step it asks for — it cannot confirm a scan or review happened, so treat it as a checklist prompt rather than a gate. A real gate needs state written by the prior step or a `commit`-surface git hook (see [[scan-secrets-before-commit]] / issue #3).

Matching is anchored to a real invocation (`match: argv` on `git … commit` at a command boundary), so `git commit` inside a quoted string or an echoed message no longer triggers it. `git commit --amend` does still count — amending is committing.
