---
name: github-issue-necessity-analysis
description: Investigate whether a GitHub issue actually needs to be implemented by verifying its claims against the current codebase, then return a structured verdict (IMPLEMENT / PARTIALLY REQUIRED / ALREADY IMPLEMENTED / DO NOT IMPLEMENT / NEEDS CLARIFICATION) backed by file/line evidence. Use this whenever someone asks whether an issue is valid, still relevant, worth doing, already done, obsolete, a duplicate, or should be closed, and whenever they paste an issue URL or number and ask for triage, backlog grooming, sprint planning input, or a second opinion before work starts. Do not use it when the user has already decided to implement and simply wants the code written.
---

# GitHub Issue Necessity Analysis

Determine whether a GitHub issue should be worked on, by verifying its claims against the current state of the codebase.

The governing stance: **an issue is a claim to investigate, not an instruction to implement.** Issues go stale, duplicate each other, describe problems that were already fixed, or propose a solution to a problem that does not exist. The value of this analysis comes entirely from checking the claim against real code — a report written from the issue text alone is worthless and worse than no report, because it looks authoritative while being unverified.

This skill investigates and reports. It never implements the issue.

## Scope boundaries

In scope: reading the issue and its context, locating and reading the relevant code, verifying the claim, and producing the report in `references/report-template.md`.

Out of scope — if the request is one of these, say so plainly and stop rather than partially complying:

| Request | Response |
| --- | --- |
| "Implement / fix this issue" | This skill only assesses necessity. Offer to run the analysis first, or to implement without it. |
| "Write the code once you've confirmed it's needed" | Two separate tasks. Deliver the report, then ask whether to proceed to implementation. |
| "Close / comment on / label the issue for me" | Report only. Do not mutate GitHub state. Offer to draft comment text the user can post. |
| "Estimate effort / write the spec / plan the sprint" | Out of scope unless it follows a completed necessity analysis the user asked to extend. |
| General code review, or an issue with no verifiable claim about a codebase (e.g. a design discussion) | Say the issue is not the kind of claim this analysis can verify, and explain why. |

## Step 0 — Preflight (do this before any analysis)

Two inputs are required. Establish both before reading code.

**1. Issue content.** Acquire in this order, stopping at the first that works. Verify availability rather than assuming — a `gh` command that fails silently produces a fabricated report.

1. `gh` CLI, if `gh auth status` succeeds: `gh issue view <number> --repo <owner/repo> --comments`. For linked context: `gh issue list --repo <owner/repo> --search "<key terms>" --state all` and `gh pr list --repo <owner/repo> --search "<key terms>" --state all`.
2. A connected GitHub tool (MCP server or connector), if one is present in the available tools.
3. `web_fetch` on the issue URL — public repositories only; private ones return a 404 page, which is not issue content.
4. Ask the user to paste the issue text.

**2. The codebase.** Confirm the repository is actually present and readable (list the directory; do not infer its existence from the issue). If the user gave no path, ask for one.

**Blocking conditions.** Stop and report the blocker instead of proceeding:

- Issue content unobtainable → state which acquisition methods were tried and what each returned, then ask for the issue text.
- Codebase unavailable → state that necessity cannot be verified without it, and offer the fallback below.
- The issue names a repository different from the one supplied → ask which is correct. Do not analyse a repository the issue is not about.

**Issue-text-only fallback.** Only if the user explicitly authorises analysis without codebase access: proceed, but the verdict is capped at **NEEDS CLARIFICATION**, confidence at **LOW**, and the report must open with a line stating no code was inspected. Never issue ALREADY IMPLEMENTED or DO NOT IMPLEMENT without having read the code.

## Investigation workflow

### Phase 1 — Extract the claim

From the issue title, body, comments, labels, dates, and linked PRs/issues, record separately:

- The **problem** claimed (what is broken or missing).
- The **expected behaviour** and any stated acceptance criteria.
- The **author's proposed solution**, kept distinct from the problem. The proposal is one option, not the requirement; a valid problem with a poor proposed fix is still worth doing, and this distinction changes the verdict.
- **Age and activity**: creation date, last activity, whether comments contradict the original report or narrow it.
- **Linked work**: referenced PRs, duplicate candidates, related issues, and whether any were merged.

If the issue's own comments have already resolved or redefined the problem, that is a primary finding — carry it forward.

### Phase 2 — Locate the relevant code

Search from the issue's domain terms outward: identifiers, error strings, endpoint paths, UI labels, config keys. Follow entrypoints to implementation. Read tests covering the area — tests are the fastest evidence that behaviour is intentional and already specified.

Record `path:line` for everything you rely on. Keep the search targeted; do not survey the whole repository. Stop expanding when the relevant module is understood well enough to confirm or contradict the claim.

If the relevant code genuinely cannot be located after a focused search, that is a finding to report as **Unknown** — not a licence to guess at file names.

### Phase 3 — Verify

Answer each of these against the code, not against the issue's assertions:

- Does the reported problem exist in the current code? (Confirmed / partially confirmed / contradicted / unverifiable.)
- Does the requested functionality already exist — fully, partially, or in a different form that satisfies the same need?
- Has the code changed since the issue was opened in a way that resolves it? Use `git log`/`git blame` scoped to the relevant paths and the issue's creation date.
- Is this duplicated by another issue, an open or merged PR, or an existing feature?
- Would implementing it introduce duplication, regression risk, migrations, or architectural conflict with what is already there?

Where a claim depends on runtime, production, or environment-specific behaviour that source code cannot settle, mark it Unknown rather than inferring.

### Phase 4 — Classify every statement

Before writing, label each statement you intend to make:

- **Fact** — directly verified in the issue or the code, with a reference.
- **Inference** — a reasonable conclusion drawn from verified evidence, presented as such.
- **Unknown** — could not be established from available evidence.

Never state impact, user counts, business value, or severity as fact unless the issue or code supplies evidence for it. "Unknown" is an acceptable and expected answer.

### Phase 5 — Select the verdict

Apply in order; the first matching rule wins:

1. Material ambiguity remains — the required change cannot be determined, or the issue contains contradictory requirements → **NEEDS CLARIFICATION**. This rule outranks the others: an unclear requirement is not a clear IMPLEMENT.
2. Cited code fully satisfies the stated requirement → **ALREADY IMPLEMENTED**.
3. Cited code satisfies part of it, with a specific remainder missing → **PARTIALLY REQUIRED**.
4. The problem is contradicted by the code, obsoleted by later changes, or duplicated by a merged PR or another issue → **DO NOT IMPLEMENT**.
5. The problem is confirmed real, the functionality is absent, and the requirement is unambiguous → **IMPLEMENT**.

Confidence follows the evidence, not the strength of the conclusion:

- **HIGH** — issue and code both directly inspected; at least two `path:line` references support the verdict; no Unknown affects it.
- **MEDIUM** — the primary claim was verified, but a supporting question is Unknown, or source code cannot settle runtime behaviour.
- **LOW** — no code inspected, the relevant code was not located, or the verdict rests mainly on inference.

### Phase 6 — Write the report

Use `references/report-template.md` exactly: same sections, same order, same headings. Read it before writing.

If more than one issue was supplied, analyse each independently and emit one complete report per issue in ascending issue-number order, preceded by a one-line verdict index (`#123 — DO NOT IMPLEMENT (HIGH)`). Do not merge reports; a shared root cause is noted inside each affected report.

## Prohibited behaviours

These exist because each one silently converts an investigation into an unfounded assertion:

- Do not implement, edit, or refactor anything, and do not create branches, commits, or PRs.
- Do not modify GitHub state — no closing, labelling, assigning, or commenting.
- Do not invent file paths, line numbers, APIs, schemas, tests, metrics, or business impact. Every reference must be one you actually opened.
- Do not treat the author's proposed solution as the requirement.
- Do not treat issue age, label, or author seniority as evidence of validity.
- Do not pad the report with repository-wide observations unrelated to the issue.
- Do not resolve an Unknown by assumption.

## Failure handling

| Situation | Required behaviour |
| --- | --- |
| `gh` unavailable or unauthenticated | Fall through the acquisition order; report which methods failed. |
| Issue is private/inaccessible | Stop; ask for pasted content. |
| Repository path missing or unreadable | Stop; ask for the correct path. |
| Relevant code not found after focused search | Continue; record it as Unknown and cap confidence at LOW. |
| Issue conflicts with itself or with a linked issue | Verdict NEEDS CLARIFICATION; list the specific conflict under Missing Information. |
| Tooling fails mid-analysis (search, git, fetch) | Report the partial analysis, state exactly which verification steps were not completed, and lower confidence accordingly. Never present a partial investigation as complete. |

## Before returning the report, confirm

1. Every `path:line` reference points to a file actually read in this session.
2. Every claim is labelled Fact, Inference, or Unknown, and no Inference is written as Fact.
3. The verdict follows from Phase 5's rules given the evidence presented.
4. The confidence level matches the Phase 5 definition.
5. All template sections are present, in order, including "Missing Information" (write "None" if genuinely nothing is missing).
6. No implementation, code change, or GitHub mutation was performed.