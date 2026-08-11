---
description: Stage 2 — independently review an implemented change against its ticket and necessity analysis, run the gates its paths need, and return APPROVED or CHANGES_REQUIRED. Never opens a PR.
argument-hint: <issue number — the handoff file to review against>
---

# Stage 2 — review the implementation

Target: **$ARGUMENTS**

Answers one question: **did the implementation correctly solve the approved ticket?** Whether
the final PR is safe to merge is `/pr-review`'s question, not this one.

`/implement-ticket` completing is not evidence the change is right. Review it independently.

## 1 — Load the record, or stop

Read `.claude/handoff/<issue>.md`, whose schema is [`.claude/HANDOFF.md`](../HANDOFF.md).
You need `Issue`, `Analysis.verdict`, `Analysis.scope`, `Analysis.criteria`, and
`Implementation.status`.

Missing file, or no `Analysis.criteria` → **stop**. Report which field is missing and send it
back to `/implement-ticket`. Do not reconstruct a ticket from the diff: that reviews the
change against itself and approves anything self-consistent.

`Analysis.verdict: NOT_APPROVED` but a change exists → report that as a BLOCKER and stop.

## 1b — Establish the range, then decide whether a SHA may be recorded

Establish the diff range — `git diff main...HEAD` for branch work, `--cached` for staged
work — and record it literally as `Review.reviewed_range`.

`Review.reviewed_sha` is not "the current HEAD". It is a claim that this SHA *contains the
content you reviewed*, and `/pr-review` skips the whole implementation diff review on the
strength of it. Record one only when all three hold:

- the range you reviewed ends at a commit, and that commit is `HEAD`;
- `git status --porcelain` is **empty** — nothing staged, nothing unstaged, nothing untracked
  that the review depended on;
- you reviewed that range, not a set of working-tree files.

Then `Review.reviewed_sha: <git rev-parse HEAD>`.

Otherwise — `--cached`, any dirty tree, a range not ending at `HEAD` — record
`Review.reviewed_sha: UNAVAILABLE`. `HEAD` does not represent staged or unstaged content, so
writing it there would let `/pr-review` skip reviewing code no one reviewed. `UNAVAILABLE`
is a correct answer that costs one full re-review at stage 4; a wrong SHA costs the review
itself.

## 2 — Review, in parallel

Dispatch both, in one message, so neither waits:

- **`change-reviewer`** — ticket correctness: requirement compliance, the acceptance
  criteria, approved scope versus actual diff, implementation correctness, and regression
  risk. Pass it the handoff path and the diff range.
- **`kit-boundary-reviewer`** — the repository's structural invariants, which CI cannot
  check: the kit/dev boundary, repo-local paths inside command specs, clobbered template
  placeholders, surface honesty, hook engine invariants, and single source of truth across
  docs.

The split is by *kind of defect*, not by file: `change-reviewer` asks "does this correctly do
what the ticket approved", `kit-boundary-reviewer` asks "does this hold Lodestar's structural
invariants". Both may read the same file and reach different questions about it —
`change-reviewer` judges whether a hook's new probe computes the right answer, while
`kit-boundary-reviewer` judges whether it can raise, fail permissive, or import outside the
stdlib. Neither performs the other's checks; `change-reviewer` is instructed to defer the
boundary and invariant list by name.

Because both read one diff, the same underlying mistake can surface in both reports from
different angles. Merge those in step 4 rather than counting them twice. Do not run a third
review, and do not re-review inline what you already delegated.

## 3 — Validate

Load `validation-scope`, derive the gate list from the diff's paths, and pass it to
`gate-runner`.

Run this even if stage 1 reported green — stage 1 validated what it *thought* it changed.
Skip only if the diff is byte-identical to what stage 1 reported and `Validation.gates`
records the same list; record those lines as `skipped (identical to stage 1)` in
`Review.gates` and say so in the report.

Gates that cannot run at all (a missing tool, for example) are `unverified`, never `passed`.
If an unverified gate covers a path the diff touched, that is `CHANGES_REQUIRED`.

## 4 — Decide

`CHANGES_REQUIRED` if any of these hold:

- a BLOCKER or HIGH finding from either reviewer,
- an acceptance criterion unmet or unverifiable,
- a gate failing, or unverified over a touched path,
- the diff does something the analysis did not scope.

Otherwise `APPROVED`.

Report every finding in the reviewers' own form — `Severity · Location · Problem · Why it
matters · Recommended correction` — ranked by impact. Merge duplicates that both reviewers
raised into one.

**Do not fix what you found.** Return the findings; the fix is a new `/implement-ticket`
pass or a direct instruction from the user. A reviewer that patches its own findings has
stopped being a second opinion.

## 5 — Record

Append one `Review` block to the handoff file in the exact form
[`.claude/HANDOFF.md`](../HANDOFF.md) defines: `verdict`, `reviewed_range`, `reviewed_sha`
(a SHA only under the step-1b conditions, else `UNAVAILABLE`), `gates`, `findings`, and
`criteria_results`. Do not edit stage 1's blocks. Return the same content to the user.

`/create-pr` reads `Review.verdict` literally and refuses to run without `APPROVED`.

**Do not commit, push, or open a PR.** On `CHANGES_REQUIRED` the next step is a fix, not a
PR — and `/create-pr` will refuse anyway.
