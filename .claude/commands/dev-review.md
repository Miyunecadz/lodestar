---
description: Stage 2 — independently review an implemented change against its ticket and necessity analysis, run the gates its paths need, and return APPROVED or CHANGES_REQUIRED. Never opens a PR.
argument-hint: <issue number or slug — the handoff file to review against>
---

# Stage 2 — review

Target: **$ARGUMENTS**

Stage 1 completing is not evidence the change is right. Review it independently.

## 1 — Load the record, or stop

Read `.claude/handoff/<issue-or-slug>.md` for the ticket, the analysis verdict, the
acceptance criteria, and the implementation report.

Missing file, or no recorded acceptance criteria → **stop**. Report what is missing and
send it back to `/dev-analyze-implement`. Do not reconstruct a ticket from the diff: that
reviews the change against itself and approves anything self-consistent.

Analysis gate is `NOT_APPROVED` but a change exists → report that as a BLOCKER and stop.

Establish the diff range — `git diff main...HEAD` for branch work, `--cached` for staged.
State which you used.

## 2 — Review, in parallel

Dispatch both, in one message, so neither waits:

- **`change-reviewer`** — correctness against the ticket, the analysis, and the acceptance
  criteria. It routes each file to a code review or a behaviour review itself. Pass it the
  handoff path and the diff range.
- **`kit-boundary-reviewer`** — the structural invariants CI cannot check: kit/dev leakage,
  repo-local paths inside command specs, clobbered placeholders, surface honesty, knowledge
  duplicated across docs.

They do not overlap: one asks "is it correct and complete", the other "is it in the right
place and honest about itself". Do not run a third review, and do not re-review inline what
you already delegated.

## 3 — Validate

Load `validation-scope`, derive the gate list from the diff's paths, and pass it to
`gate-runner`.

Run this even if stage 1 reported green — stage 1 validated what it *thought* it changed.
Skip only if the diff is byte-identical to what stage 1 reported and it recorded the same
gate list; say so if you skip.

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

**Do not fix what you found.** Return the findings; the fix is a new `/dev-analyze-implement`
pass or a direct instruction from the user. A reviewer that patches its own findings has
stopped being a second opinion.

## 5 — Record

Append verdict, findings, and the criteria checklist to the handoff file, then return the
same. `/dev-pr` reads it and refuses to run without `APPROVED`.

**Do not commit, push, or open a PR.**
