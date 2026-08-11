---
description: Stage 1 — decide whether an issue should be implemented, implement it only if the analysis approves, validate proportionally, and report. Never opens a PR.
argument-hint: <issue number, URL, or a description of the work>
---

# Stage 1 — analyse, then implement

Target: **$ARGUMENTS**

You may not skip stage 2 or stage 4. Producing a correct `BLOCKED` beats producing a
change nobody asked for.

## 1 — Set up the handoff file

`.claude/handoff/<issue-or-slug>.md` carries state to `/dev-review` and `/dev-pr`, which
run in later sessions with none of this context. It is gitignored.

If it already exists with a recorded verdict, this issue has been analysed — read it and
resume from where it stopped rather than re-analysing.

## 2 — Analyse necessity

Invoke the `github-issue-necessity-analysis` skill and follow it. Do not paraphrase it,
re-derive it, or shortcut it because the issue looks obvious.

Write its full report into the handoff file, then map its verdict to a gate:

| Skill verdict | Gate | Then |
|---|---|---|
| IMPLEMENT | `APPROVED` | continue to step 3 |
| PARTIALLY REQUIRED | `APPROVED` | continue, scoped to the stated remainder only |
| ALREADY IMPLEMENTED | `NOT_APPROVED` | stop |
| DO NOT IMPLEMENT | `NOT_APPROVED` | stop |
| NEEDS CLARIFICATION | `NOT_APPROVED` | stop |

On `NOT_APPROVED`: record the gate in the handoff file, report the verdict, the reasoning,
and the suggested next action. **Change no files.** A request to implement anyway is a new
instruction from the user, not something you decide.

Carry forward from the report: the acceptance criteria, the scope, and the flagged risks.
Stage 2 checks the implementation against exactly those.

**No acceptance criteria you can actually verify → `NOT_APPROVED`, reason
`NEEDS CLARIFICATION`.** An unverifiable requirement cannot be reviewed or closed.

## 3 — Implement

The analysis already located the affected code. Re-read those files before editing them;
do not re-survey the repository.

**Repo conventions, code style, and the sources-of-truth table are `CLAUDE.md`'s, already
in your context — follow them there rather than looking for a copy here.** Where it names
an authority for a question, read the authority instead of inferring the answer. The two
skills it points at carry the detail: `catalog-entry-authoring` for anything under
`kit/catalog/`, `hook-engine-invariants` for anything under `kit/templates/hooks/`.

What this stage adds on top, because it comes from the analysis rather than the repo:

- smallest change that satisfies the **scope the analysis stated** — nothing wider;
- no unrelated refactoring, however tempting the surrounding code is;
- no invented path, flag, command, or field — verify it exists before relying on it;
- a risk the analysis flagged is a thing to handle, not to rediscover.

If implementation needs an architectural decision the analysis did not scope: stop, record
`BLOCKED` with the specific decision needed, and report. Do not choose for the user.

## 4 — Validate, proportionally

Load the `validation-scope` skill, derive the gate list from the paths you actually
changed, and pass **that list** to the `gate-runner` agent.

Run nothing else. Run nothing less. Mind the skill's two different "no gate" cases: a path
it lists as ungated (docs, `.claude/**`) is genuinely validated by reading, while a path it
does not list at all means the table is stale — run the full suite and say so.

An ungated change is not an unvalidated one. Say how you verified it instead.

Gate failures caused by your change get fixed here, then the same list is re-run. A failure
you cannot fix is `BLOCKED`, reported with the decisive output line.

## 5 — Report

Append to the handoff file and return, verbatim structure:

```
Implementation Status
- Completed | Blocked

Issue Analysis
- Decision: APPROVED | NOT_APPROVED (skill verdict, confidence)
- Reasoning: two lines
- Acceptance criteria: the list, carried forward

Changes
- What changed, and the files touched

Validation
- Gates run (and why that set), with results

Notes
- Assumptions, limitations, anything the reviewer must look at
```

**Do not commit, push, or open a PR.** `/dev-review` runs next; `/dev-pr` after that.
