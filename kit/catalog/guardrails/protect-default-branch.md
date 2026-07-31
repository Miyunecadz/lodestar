---
id: protect-default-branch
title: Block bare force-push to any branch
category: safety
severity: block
recommended: true
stacks: [all]
event: bash
pattern: '\bgit\s+push\b[^|;&]*(\s-f\b|--force(?!-with-lease))'
surface: agent
emits: rule
---

A plain `git push --force` (or `-f`) to a shared branch overwrites remote history and can erase teammates' commits. Never force-push to `main`/`master` or any shared branch. If you genuinely need to overwrite your OWN feature branch after a rebase, use `git push --force-with-lease` (which refuses if someone else pushed in the meantime) — never bare `--force`.

Scope note: this rule is **force-push-only** — its name once promised more than a regex can deliver. It fires on any branch, since a bare `--force` is wrong on a shared feature branch too, and it deliberately does not try to infer the push destination (a refspec can name any branch; a pattern cannot resolve one). Blocking *ordinary* commits and pushes while you are standing on the default branch is a separate, branch-aware rule: [[block-commit-to-default-branch]]. Enable both for full coverage.

**Surface: `agent` only.** Force-push happens at push time, not commit time, so the git-layer twin of this rule is a `pre-push` hook rather than the `pre-commit` surface Lodestar installs today. Server-side branch protection (a ruleset that forbids force-push) is the real enforcement for everyone; see `docs/CI.md`.
