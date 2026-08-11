---
description: Stage 4 — review the actual pull request before merge, covering the final diff, the commits, the description, CI status, and any drift from what was reviewed at stage 2. Returns APPROVED or CHANGES_REQUIRED. Never creates a PR and never merges.
argument-hint: <pr number>
---

# Stage 4 — review the pull request

Target PR: **$ARGUMENTS**

`/review-ticket` asked *is the implementation correct for the ticket?* This asks a different
question: **is this pull request, as it stands right now, safe and appropriate to merge?**

A stage-2 approval is evidence about a diff that existed then. The PR may have gained
commits, been rebased, or had its description written to describe something it does not do.
Do not treat the earlier verdict as the answer.

## 1 — Read the PR from GitHub, not from memory

```bash
gh pr view <n> --json number,title,body,state,isDraft,headRefName,baseRefName,headRefOid,commits,files,additions,deletions
gh pr diff <n>
gh pr checks <n>
```

`gh` unavailable or the PR unreadable → **stop** and say so. There is no fallback: reviewing
a PR you cannot fetch means reviewing a local branch and calling it a PR.

Then read `.claude/handoff/<issue>.md` for the ticket, the analysis, the acceptance criteria,
and the stage-2 verdict. No handoff file → say so and continue in **reduced mode**: report
what the PR does and whether it is internally sound, cap the verdict at
`CHANGES_REQUIRED`, and name the missing record as the reason. Never `APPROVED` without a
ticket to approve it against.

## 2 — Measure drift, then decide how much to re-review

Compare the PR's `headRefOid` against the SHA stage 2 recorded.

| Drift | Do |
|---|---|
| Identical, and stage 2 was `APPROVED` | Skip re-delegating the diff review. Say you skipped it and why. Run step 3 onward. |
| Identical, and stage 2 was `CHANGES_REQUIRED` | **BLOCKER.** Unfixed findings; stop. |
| Changed, or stage 2 recorded no SHA | Re-review the diff — dispatch `change-reviewer` and `kit-boundary-reviewer` in one message, passing the handoff path and `<baseRefName>...<headRefOid>`. |

That comparison is the whole point of recording a SHA: it turns "trust the earlier review"
into a verifiable fact, so the expensive path runs only when the diff actually moved.

## 3 — The PR layer — what stage 2 could not see

Stage 2 reviewed a diff. These exist only once there is a PR:

- **Description honesty.** Does the body describe what the diff does? A body claiming a
  behaviour the diff does not contain is a BLOCKER — it is what a human reviewer will
  approve against.
- **Unrelated changes.** Any file outside the analysis's scope. A stray formatting sweep, a
  committed artifact, a `__pycache__` directory, a debugging leftover.
- **Commits.** Subject style per `CLAUDE.md`. Confirm no commit touches `VERSION` or
  `CHANGELOG.md` — a feature PR must carry a `changelog.d/` fragment instead, and the
  fragment should be present if the change is user-visible.
- **Base branch.** `baseRefName` is the default branch and `headRefName` is not.
- **CI.** `gh pr checks` is authoritative for merge-readiness — it ran the full suite on the
  real head. A failing or pending required check is `CHANGES_REQUIRED`; pending is not
  passing.
- **Secrets.** Nothing in the diff that should not be public.

## 4 — Local gates, only where CI cannot answer

If `gh pr checks` is green on this exact head, that is stronger evidence than any local run
— do not repeat it.

Run local gates only when CI is pending, failing in a way you need to localise, or the
change touches a path no gate covers (`validation-scope` lists those). Then load
`validation-scope`, derive the set, and pass it to `gate-runner`.

## 5 — Decide

`CHANGES_REQUIRED` if any holds:

- a BLOCKER or HIGH finding, from this stage or an unfixed one from stage 2;
- a required CI check failing or pending;
- the description does not match the diff;
- changes outside the analysis's scope;
- `VERSION` or `CHANGELOG.md` edited in a feature PR;
- an acceptance criterion unmet or unverifiable;
- no handoff record (reduced mode).

Otherwise `APPROVED`.

Per finding: `Severity · Location · Problem · Why it matters · Recommended correction`,
ranked by impact. Anchor every one to the PR diff, a commit, the body, the ticket, the
analysis, or a stated repo convention. Anything else is speculation — drop it.

## 6 — Report

Append the verdict to the handoff file and return it, stating explicitly which parts you
re-reviewed and which you skipped on the SHA match.

**Do not merge. Do not push. Do not open another PR.** Posting the findings as a PR review
comment is allowed only on the user's explicit go-ahead — it is public and outward-facing —
and `gh pr review` never carries `--approve` from here. Approval of a human's PR is a
human's to give.
