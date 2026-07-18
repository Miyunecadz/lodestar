---
name: planning-workflow
description: Use when scoping, spec'ing, or breaking down a feature — BEFORE any code is written. Not for implementation.
stacks: [all]
---

# Planning workflow

Turn a feature request into a cross-repo plan. You write no code here — the point is the map, not the hands (see `docs/CONCEPTS.md` §3).

**The loop:**

1. Read `docs/_shared/api-contract.md` — the API contract is the **spine**. Read `docs/repo-map.md` to see which repos the feature touches and how.
2. **Identify the contract change first.** If the feature moves data across a repo boundary, the shared API surface changes, and that change drives everything else. Plan it before anything else.
3. Produce a task breakdown: the smallest tasks that each have a crisp done-condition, **tagged by repo and by role** (`migration-writer`, `resolver-writer`, `implementer`, `test-writer`, …), ordered by dependency.

**Do NOT load coding-standards skills during planning** (`backend-standards`, `frontend-standards`, `mobile-standards`, etc.). Those are for execution. Loading them now is the wrong thing at the wrong time — planning is about the shape of the work across repos, not how any one repo writes code.
