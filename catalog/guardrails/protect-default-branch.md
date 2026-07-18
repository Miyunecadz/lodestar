---
id: protect-default-branch
title: Protect the default branch from force-push
category: safety
severity: block
recommended: true
stacks: [all]
event: bash
pattern: '\bgit\s+push\b[^|;&]*(\s-f\b|--force(?!-with-lease))'
emits: hookify
---

A plain `git push --force` (or `-f`) to a shared branch overwrites remote history and can erase teammates' commits. Never force-push to `main`/`master` or any shared branch. If you genuinely need to overwrite your OWN feature branch after a rebase, use `git push --force-with-lease` (which refuses if someone else pushed in the meantime) — never bare `--force`.

Related discipline this rule does not enforce on its own: before committing, confirm you are on a feature branch, not directly on `main`/`master` (`git branch --show-current`). If you are on the default branch, create one first: `git switch -c feat/<name>`.
