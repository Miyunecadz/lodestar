# Report template

Reproduce this structure exactly: same headings, same order, all sections present. Bracketed text is guidance to replace, not text to emit. If a section has nothing to report, say so explicitly rather than deleting the section — a missing section is indistinguishable from an overlooked one.

For multiple issues, repeat the whole template per issue under a heading `# Issue #<number> — <title>`, preceded by a verdict index.

---

## Verdict

[Exactly one of: **IMPLEMENT** / **PARTIALLY REQUIRED** / **ALREADY IMPLEMENTED** / **DO NOT IMPLEMENT** / **NEEDS CLARIFICATION**]

## Confidence

**[HIGH / MEDIUM / LOW]**

[One or two sentences on what makes it this level — which evidence was verifiable and what was not.]

## Issue Summary

[What the issue is actually asking for, in your own words. Separate the claimed problem from the author's proposed solution. Two to five sentences.]

## Current Codebase Behaviour

[What the system does today in the area the issue touches, with `path:line` references. Describe observed code, not intended design.]

## Evidence

[The findings the verdict rests on. Each line: a reference, then what it shows. Include contradicting evidence, not only supporting evidence.]

- `path/to/file.ts:123` — [what this code does and why it matters here]
- `path/to/test.spec.ts:45` — [what this test asserts]
- [PR/issue reference] — [related or duplicate work, and its state]
- [Commit or `git log` finding] — [change since the issue was opened, if relevant]

## Necessity Analysis

### Is the reported problem real?

[Confirmed / partially confirmed / contradicted / could not be verified — and the evidence for that determination.]

### Is the requested functionality already available?

[What exists, what is missing, and whether an existing mechanism satisfies the same need in a different form.]

### Is this duplicated elsewhere?

[Related issues, PRs, or existing features. Write "No duplication found" if a search was run and returned nothing; write that no search was possible if it was not.]

### What is the actual impact?

[Only impact supported by evidence in the issue or the code. Where impact cannot be established, write "Unknown — cannot be determined from available evidence."]

### What are the risks of implementing it?

[Technical, architectural, data, performance, security, or UX risks — including duplication, migration, and regression risk. Write "No significant risks identified" if that is the finding.]

## Missing Information

[Anything that must be clarified before implementation, as a list. Write "None — the requirement is sufficiently specified." if nothing is missing.]

## Recommendation

[Why the issue should or should not be worked on. State the reasoning, not just the verdict again. Where the verdict is IMPLEMENT or PARTIALLY REQUIRED, define the remaining scope in one or two sentences — without designing the solution.]

## Suggested Next Action

[One concrete next step for the development team or another agent — e.g. "Close as resolved by #482", "Ask the reporter which client version reproduced this", "Proceed to implementation, scoped to the missing validation in `path/to/file.ts:88`".]