---
name: github-issue-necessity-analysis
description: Investigate whether a GitHub issue actually needs to be implemented by verifying its claims against the current codebase, then return a structured verdict (IMPLEMENT / PARTIALLY REQUIRED / ALREADY IMPLEMENTED / DO NOT IMPLEMENT / NEEDS CLARIFICATION) backed by file/line evidence. Use this whenever someone asks whether an issue is valid, still relevant, worth doing, already done, obsolete, a duplicate, or should be closed, and whenever they paste an issue URL or number and ask for triage, backlog grooming, sprint planning input, or a second opinion before work starts. Do not use it when the user has already decided to implement and simply wants the code written.
---

# GitHub issue necessity analysis

**An issue is a claim to investigate, not an instruction to implement.** Issues go stale,
duplicate each other, describe fixed problems, or solve problems that do not exist. A
report written from the issue text alone is worse than none — it looks authoritative
while being unverified.

This skill investigates and reports. It never implements, and never mutates GitHub state
(no closing, labelling, assigning, commenting). If asked to do either, say so in one
sentence and offer the alternative — run the analysis first, or draft comment text the
user posts themselves. If the issue makes no verifiable claim about a codebase (a design
discussion), say that instead of forcing a verdict.

## Step 0 — Preflight

Both inputs are required before reading code.

**Issue content.** First method that works, verified rather than assumed — a command that
fails silently produces a fabricated report:

1. `gh issue view <number> --repo <owner/repo> --comments` (check `gh auth status` first).
   If it returns empty, retry with `--json number,title,state,body,createdAt,labels,comments`.
2. A connected GitHub MCP tool, if present.
3. `web_fetch` on the URL — public repos only; a private one returns a 404 page, which is
   not issue content.
4. Ask the user to paste it.

**The codebase.** List the directory to confirm it is present and readable. Ask for a path
if none was given.

**Stop and report the blocker** if: issue content is unobtainable (say which methods were
tried and what each returned); the codebase is unavailable; or the issue names a different
repository than the one supplied (ask which is correct).

**Issue-text-only fallback**, only if the user explicitly authorises it: the verdict is
capped at NEEDS CLARIFICATION, confidence at LOW, and the report opens by stating no code
was inspected. Never issue ALREADY IMPLEMENTED or DO NOT IMPLEMENT without reading code.

## 1 — Extract the claim

Record separately: the **problem** claimed; the **expected behaviour** and acceptance
criteria; the **author's proposed solution**, kept distinct — a valid problem with a poor
proposed fix is still worth doing, and conflating them changes the verdict; **age and
activity**; **linked work** (PRs, duplicates, related issues, and whether any merged).

If the issue's own comments already resolved or redefined the problem, that is a primary
finding.

## 2 — Locate the relevant code

Search outward from the issue's domain terms: identifiers, error strings, endpoint paths,
UI labels, config keys. Read the tests covering the area — they are the fastest evidence
that behaviour is intentional. Record `path:line` for everything you rely on.

Keep it targeted; do not survey the repository. Stop expanding once the relevant module
confirms or contradicts the claim. If the code genuinely cannot be found after a focused
search, report that as Unknown — it is not licence to guess at file names.

## 3 — Verify against the code, not the issue's assertions

- Does the reported problem exist today? (confirmed / partial / contradicted / unverifiable)
- Does the requested functionality already exist — fully, partially, or in a different form
  that satisfies the same need?
- Has the code changed since the issue was opened in a way that resolves it? Use
  `git log`/`git blame` scoped to the relevant paths and the issue's creation date.
- Is it duplicated by another issue, an open or merged PR, or an existing feature?
- Would implementing it cause duplication, regression risk, migrations, or architectural
  conflict?

Claims that depend on runtime, production, or environment-specific behaviour are Unknown —
source code cannot settle them.

## 4 — Label every statement

**Fact** (verified in the issue or the code, with a reference) · **Inference** (drawn from
verified evidence, presented as such) · **Unknown** (not establishable). Never state
impact, user counts, business value, or severity as fact without evidence for it, and never
resolve an Unknown by assumption. Issue age, label, and author are not evidence of validity.

## 5 — Select the verdict

First matching rule wins:

1. Material ambiguity — the required change cannot be determined, or requirements
   contradict each other → **NEEDS CLARIFICATION**. Outranks the rest: an unclear
   requirement is not a clear IMPLEMENT.
2. Cited code fully satisfies the requirement → **ALREADY IMPLEMENTED**.
3. Cited code satisfies part, with a specific remainder missing → **PARTIALLY REQUIRED**.
4. Contradicted by the code, obsoleted by later changes, or duplicated by a merged PR or
   another issue → **DO NOT IMPLEMENT**.
5. Problem confirmed, functionality absent, requirement unambiguous → **IMPLEMENT**.

Confidence follows the evidence, not the strength of the conclusion:

- **HIGH** — issue and code both inspected; ≥2 `path:line` references support the verdict;
  no Unknown affects it.
- **MEDIUM** — primary claim verified, but a supporting question is Unknown, or source
  cannot settle runtime behaviour.
- **LOW** — no code inspected, code not located, or the verdict rests mainly on inference.

## 6 — Write the report

Read `references/report-template.md` and reproduce it exactly — same sections, same order,
all present (write "None" rather than dropping one). Every `path:line` must be a file you
actually opened; never invent files, APIs, schemas, dependencies, or requirements.

For multiple issues: analyse each independently, one complete report per issue in ascending
number order, preceded by a one-line verdict index (`#123 — DO NOT IMPLEMENT (HIGH)`). Do
not merge them; note a shared root cause inside each affected report.

If a tool fails mid-analysis, report the partial analysis and state exactly which
verification steps did not run, with confidence lowered accordingly. Never present a
partial investigation as complete.
