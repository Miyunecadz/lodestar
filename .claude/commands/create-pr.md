---
description: Stage 3 — the only place a branch, commit, and pull request are created. Refuses to run unless the handoff file records an approved analysis, a completed implementation, an approved review, and passing gates.
argument-hint: <issue number — the handoff file to open the PR from>
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

Read `.claude/handoff/<issue>.md`, whose schema is [`.claude/HANDOFF.md`](../HANDOFF.md).
All four fields must be present with exactly these values:

```
Analysis.verdict       == APPROVED
Implementation.status  == COMPLETED
Validation.status      == PASSED
Review.verdict         == APPROVED
```

Match the literal field names and the literal values. A field that is absent, empty, spelled
differently, or holds any other value — `BLOCKED`, `NOT_STARTED`, `UNVERIFIED`, `FAILED`,
`NOT_RUN`, `CHANGES_REQUIRED` — is a **stop**, and say which field and what it held.

**Do not interpret.** Not from prose elsewhere in the file, not from a clean diff, not from a
green gate run you do yourself, not from the user asking for a PR. If an earlier stage meant
to record approval and did not, the fix is to re-run that stage, not to read its intent. An
unrecorded stage is an unrun stage — that is the entire purpose of the handoff.

`Review.verdict: CHANGES_REQUIRED` is a hard stop, not a warning to note in the PR body. Do
not open the PR "so the findings can be discussed there".

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
- `Analysis.verdict` and its one-line reasoning;
- `Analysis.criteria` with `Review.criteria_results` — each criterion, met, with its evidence;
- `Validation.gates` and `Review.gates` — the gates run and their results;
- anything in `Review.findings` at MEDIUM or LOW that was deliberately left.

All of that is already in the handoff file. Copy it across; do not re-derive it.

Reference the issue as `(#N)` in the commit subject and name it in the body, so `/pr-review`
can resolve this PR back to `handoff/<issue>.md`.

CI is the required check. Report the PR URL and the check status; **do not merge.**

## 4 — Record

Append the `PR` block — `number`, `url`, and `head_sha` (the SHA you actually pushed,
`git rev-parse HEAD` after the last commit) — per
[`.claude/HANDOFF.md`](../HANDOFF.md). `/pr-review` reads all three, and they are the last
things this stage knows that the next one cannot cheaply find.

If the pushed head is a **new commit** of content stage 2 reviewed as staged or dirty, that
does not retroactively validate `Review.reviewed_sha`. Leave stage 2's block exactly as it
is, `UNAVAILABLE` included. `/pr-review` will re-review the diff in full, which is correct:
no one has reviewed these commits.
