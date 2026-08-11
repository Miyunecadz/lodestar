# The handoff contract

`.claude/handoff/<issue>.md` is the only channel between the four stages of the
ticket-to-PR workflow. Each stage runs in its own session with none of the previous
stage's context, so a field a later stage reads must have been **written literally** by
an earlier one.

This file owns the schema. The commands point at it; they do not restate it.

## Rules

1. **Literal field names.** A consumer matches the names below exactly. `Review = ok`,
   `Implementation: done`, or a prose paragraph saying the review passed are all *absent
   fields*, not equivalents.
2. **Absent means unrun.** A consumer never infers a value from the diff, a green gate
   run, a PR body, or the user asking. Missing required field → stop and name it.
3. **Append, never rewrite.** A stage writes its own block. It does not edit another
   stage's block. Re-running a stage replaces only that stage's block, and states that it
   did.
4. **Only recorded facts.** A gate that could not execute is `unverified`, never
   `passed`. A SHA is recorded only when it actually identifies the reviewed content
   (see `Review.reviewed_sha`).
5. The file is gitignored and cheap to delete. It carries verdicts, criteria, scope,
   risks, files touched, and gate results — **not** a copy of the repo or of the diff.
   Later stages read those from git.

## Schema

```
Issue: <number>
Ticket: <issue URL>

Analysis:                       # written by /implement-ticket
  verdict: APPROVED | NOT_APPROVED
  skill_verdict: IMPLEMENT | PARTIALLY REQUIRED | ALREADY IMPLEMENTED | DO NOT IMPLEMENT | NEEDS CLARIFICATION
  confidence: HIGH | MEDIUM | LOW
  scope: <one line — what is in scope, and for PARTIALLY REQUIRED what is excluded>
  criteria:
    - <acceptance criterion> — <how it can be verified>
  risks:
    - <risk the analysis flagged>

Implementation:                 # written by /implement-ticket
  status: COMPLETED | NOT_STARTED | BLOCKED
  files:
    - <path touched>
  notes: <what changed in a line; for BLOCKED, the decision needed>

Validation:                     # written by /implement-ticket
  status: PASSED | FAILED | UNVERIFIED | NOT_RUN
  scope_reason: <why this gate set, per validation-scope>
  gates:
    - <gate> — passed | failed | unverified

Review:                         # written by /review-ticket
  verdict: APPROVED | CHANGES_REQUIRED
  reviewed_range: <the literal range reviewed, e.g. main...HEAD or --cached>
  reviewed_sha: <40-hex sha> | UNAVAILABLE
  gates:
    - <gate> — passed | failed | unverified | skipped (identical to stage 1)
  findings:
    - <BLOCKER|HIGH|MEDIUM|LOW> <path:line> — <problem>
  criteria_results:
    - <criterion> — met | unmet | unverifiable — <evidence>

PR:                             # written by /create-pr
  number: <n>
  url: <url>
  head_sha: <40-hex sha of the pushed head>

PRReview:                       # written by /pr-review
  verdict: APPROVED | CHANGES_REQUIRED
  mode: FULL | REDUCED
  reviewed_head_sha: <the PR headRefOid actually reviewed>
  diff_review: performed | skipped-on-sha-match
  findings:
    - <BLOCKER|HIGH|MEDIUM|LOW> <anchor> — <problem>
```

Omit an inner list when it is empty; never omit a `verdict` or `status` line.

## Producer → consumer

| Field | Written by | Read by |
|---|---|---|
| `Issue`, `Ticket` | stage 1 | 2, 3, 4 |
| `Analysis.verdict` | stage 1 | 2 (stop if `NOT_APPROVED` and a change exists), 3 (require `APPROVED`) |
| `Analysis.scope`, `Analysis.risks` | stage 1 | 2, 4 (scope creep) |
| `Analysis.criteria` | stage 1 | 2 (checks them), 3 (PR body), 4 |
| `Implementation.status` | stage 1 | 3 (require `COMPLETED`) |
| `Validation.status`, `Validation.gates` | stage 1 | 2 (may skip an identical run), 3 (require `PASSED`), 4 (PR body claims) |
| `Review.verdict` | stage 2 | 3 (require `APPROVED`), 4 |
| `Review.reviewed_sha` | stage 2 | 4 (drift comparison) |
| `Review.gates` | stage 2 | 3 (PR body), 4 |
| `Review.findings`, `Review.criteria_results` | stage 2 | 3 (PR body), 4 (unfixed findings) |
| `PR.number`, `PR.head_sha` | stage 3 | 4 |
| `PRReview.*` | stage 4 | the human |

## `Review.reviewed_sha` — provenance, not convenience

Stage 4 may skip the implementation diff review when the recorded SHA equals the PR head.
That optimisation is only sound if the SHA **is** the reviewed content. So stage 2 records
a SHA under exactly one condition:

> The reviewed range ended at a commit, that commit is `HEAD`, and `git status --porcelain`
> is empty — nothing staged, nothing unstaged, nothing that the SHA does not contain.

Anything else — `--cached`, a dirty tree, a range not ending at `HEAD`, a review of files
rather than a range — records `reviewed_sha: UNAVAILABLE`. `UNAVAILABLE` is a normal,
correct value; it costs stage 4 one full diff review, which is the honest price.

Stage 4 treats a recorded SHA as usable only if it is 40 hex characters and equals the
PR's `headRefOid`. `UNAVAILABLE`, absent, malformed, or unequal → full implementation
review.
