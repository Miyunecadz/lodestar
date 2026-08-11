---
description: Stage 3 — the only place a branch, commit, and pull request are created. Refuses to run unless the handoff file records an approved analysis, a completed implementation, an approved review, and passing gates.
argument-hint: <issue number or slug — the handoff file to open the PR from>
---

# Stage 3 — open the PR

Target: **$ARGUMENTS**

This is the **only** command that commits, pushes, or opens a PR. `/implement-ticket`,
`/review-ticket`, and `/pr-review` are all forbidden from doing any of it, so PR creation
has exactly one home.

Note what this means in practice: `.claude/settings.json` allows `git status|diff|log|
branch|switch` and `gh pr|issue`, but **not** `git add`, `git commit`, or `git push`. Those
three will prompt. That is the design — the human is in the loop at the mutation, not
before it.

## 1 — Gate

Read `.claude/handoff/<issue>.md`. All four must be recorded:

```
Issue Analysis  = APPROVED
Implementation  = Completed
Review          = APPROVED
Validation      = passed
```

Any one missing, absent, or contradicted → **stop** and name which. Do not infer approval
from a clean diff, a green gate run, or the user asking for a PR. An unrecorded stage is an
unrun stage.

`Review = CHANGES_REQUIRED` is a hard stop, not a warning to note in the PR body. Do not
open the PR "so the findings can be discussed there".

Confirm the working tree still matches what was reviewed: `git status --short` and
`git diff`. Uncommitted changes beyond the reviewed diff send it back to `/review-ticket` —
they were never reviewed.

## 2 — Branch, fragment, commit

**`CLAUDE.md`'s Workflow section owns all three rules and is already in your context** —
branch naming, the `changelog.d` fragment instead of `VERSION`/`CHANGELOG.md`, and the
commit-subject format. Follow it there. Do not look for a second copy, and do not let a
default trailer behaviour override it.

The dogfooded `commit-message-style` rule fires on every `git commit`, but it is
`severity: warn` on the `agent` surface — a reminder, not a gate. Nothing stops a
multi-line or trailered subject from landing. Getting it right is on you.

Two things only this stage knows:

- Adding a fragment changes `changelog.d/`, which `validation-scope` maps to `validate.py`.
  Re-run that one gate through `gate-runner` before committing.
- `git log --oneline -10` is the house style for a subject line worth copying.

## 3 — Push and open

Push the branch. Never force-push, never push to `main`.

Open a **draft** PR unless the user asked otherwise, with `gh pr create`. The body:

- what changed and why, in a few lines;
- the analysis verdict and its one-line reasoning;
- the acceptance criteria, each marked met, with its evidence;
- the gates run and their results;
- anything the review flagged as MEDIUM or LOW and deliberately left.

All of that is already in the handoff file. Copy it across; do not re-derive it.

CI is the required check. Report the PR URL and the check status; **do not merge.**

## 4 — Record

Append the PR number and URL to the handoff file. `/pr-review` needs the number, and it is
the last thing this stage knows that the next one cannot cheaply find.
