---
description: Stage 1 — decide whether a GitHub issue should be implemented, implement it only if the analysis approves, validate proportionally, and report. Never opens a PR.
argument-hint: <issue number or issue URL>
---

# Stage 1 — analyse, then implement

Target: **$ARGUMENTS**

Stage 1 of four: `/implement-ticket` → `/review-ticket` → `/create-pr` → `/pr-review`. You
may not skip a stage. Producing a correct `BLOCKED` beats producing a change nobody asked
for.

## 0 — Input contract: a GitHub issue, nothing else

This stage takes **an issue number or an issue URL**. Necessity analysis verifies the
issue's claims against the code and the whole pipeline is keyed by issue number, so there
is nothing for a free-form description to be analysed against or filed under.

Given a description of work rather than an issue → **stop**. Say that this command needs an
issue, and offer the two real paths: open the issue first (then re-run this), or ask for the
change directly outside this workflow, where no handoff record and no `/create-pr` gate
exist. Do not invent an issue number, and do not analyse a paraphrase of the request as if
it were a ticket.

## 1 — Set up the handoff file

`.claude/handoff/<issue>.md` carries state to `/review-ticket`, `/create-pr`, and
`/pr-review`, which run in later sessions with none of this context. It is gitignored.

**[`.claude/HANDOFF.md`](../HANDOFF.md) owns the schema — read it and write the literal
field names it defines.** Later stages match those names exactly; a field written in prose
is a field they will treat as absent. This stage writes the `Issue`, `Ticket`, `Analysis`,
`Implementation`, and `Validation` blocks.

If it already exists with a recorded `Analysis.verdict`, this issue has been analysed — read
it and resume from where it stopped rather than re-analysing.

## 2 — Analyse necessity

Invoke the `github-issue-necessity-analysis` skill and follow it. Do not paraphrase it,
re-derive it, or shortcut it because the issue looks obvious.

Write its full report into the handoff file, then map its verdict to `Analysis.verdict`:

| Skill verdict | `Analysis.verdict` | Then |
|---|---|---|
| IMPLEMENT | `APPROVED` | continue to step 3 |
| PARTIALLY REQUIRED | `APPROVED` | continue, scoped to the stated remainder only |
| ALREADY IMPLEMENTED | `NOT_APPROVED` | stop |
| DO NOT IMPLEMENT | `NOT_APPROVED` | stop |
| NEEDS CLARIFICATION | `NOT_APPROVED` | stop |

Record the skill's own verdict verbatim as `Analysis.skill_verdict` alongside it, so a later
stage can see which of the five produced the gate.

Verify this mapping against the skill's own verdict list before relying on it — if the skill
has gained or renamed a verdict, an unmapped verdict is `NOT_APPROVED`, not a guess.

### On NOT_APPROVED — stop, then say so on the issue

**Change no files.** No branch, no commit, no PR. A request to implement anyway is a new
instruction from the user, not something you infer from the issue being open.

1. Record it in the handoff file, explicitly and without ambiguity — `Analysis.verdict:
   NOT_APPROVED` with its `skill_verdict`, `Implementation.status: NOT_STARTED`, and
   `Validation.status: NOT_RUN`. A stage that stopped still writes its three status lines;
   the next stage must be able to tell "stopped deliberately" from "never ran".
2. Draft the issue comment: the verdict, the confidence, the two or three `path:line`
   findings it rests on, and the suggested next action. No speculation about impact.
3. **Show the drafted comment and ask before posting.** `gh issue comment` is permitted by
   `.claude/settings.json`, so posting will succeed — which is the reason to confirm first.
   A comment on someone else's issue is public and outward-facing.
4. Post on confirmation: `gh issue comment <number> --body-file <path>`. Declined, or no
   answer: report the exact text that should be posted and stop.

The `github-issue-necessity-analysis` skill never mutates GitHub state — that rule is
intact. The mutation is this command's, taken on the user's explicit go-ahead.

`NEEDS CLARIFICATION` is a full stop. Do not resolve the ambiguity yourself and proceed.

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
`Implementation.status: BLOCKED` with the specific decision needed in `Implementation.notes`,
and report. Do not choose for the user. `BLOCKED` is not `COMPLETED`, and `/create-pr` reads
that field literally.

On a finished change, record `Implementation.status: COMPLETED` and list every file touched
under `Implementation.files`.

## 4 — Validate, proportionally

Load the `validation-scope` skill, derive the gate list from the paths you actually
changed, and pass **that list** to the `gate-runner` agent.

Run nothing else. Run nothing less. Mind the skill's two different "no gate" cases: a path
it lists as ungated (docs, `.claude/**`) is genuinely validated by reading, while a path it
does not list at all means the table is stale — run the full suite and say so.

An ungated change is not an unvalidated one. Say how you verified it instead.

Gate failures caused by your change get fixed here, then the same list is re-run. A failure
you cannot fix is `BLOCKED`, reported with the decisive output line.

**Report only what actually ran.** A gate that could not execute — missing tool, missing
interpreter — is `unverified`, never `passed`. Saying a check passed when it did not run is
the one failure this stage cannot recover from, because every later stage trusts it.

`Validation.status` follows from the gate lines, with no rounding up:

| Gate results | `Validation.status` |
|---|---|
| every derived gate ran and passed | `PASSED` |
| any gate failed | `FAILED` |
| all that ran passed, but one could not execute | `UNVERIFIED` |
| no gate ran — nothing was implemented, or none was derived | `NOT_RUN` |

An ungated change — every path is in `validation-scope`'s ungated list — is `PASSED` with
`gates:` naming the reading you did in place of a gate, not `NOT_RUN`.

## 5 — Record and report

Write the `Issue`, `Ticket`, `Analysis`, `Implementation`, and `Validation` blocks to the
handoff file in the exact form [`.claude/HANDOFF.md`](../HANDOFF.md) defines — those field
names are the contract `/review-ticket` and `/create-pr` read.

Then return, to the user, the same state in readable form: the analysis verdict with its
confidence and two lines of reasoning, what changed and where, the gates that actually ran
and why that set, the acceptance criteria · scope · flagged risks, the handoff file path, and
any verified known issue. Nothing that is not also in the file — the file is what survives.

**Do not commit, push, or open a PR.** `/review-ticket` runs next.
