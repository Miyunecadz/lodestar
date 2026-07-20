---
name: architecture-overview
description: Use when you need the big picture of how the repos connect, or to trace a flow across a repo boundary.
stacks: [all]
---

# Architecture overview

Get the whole-system map, or follow one flow from repo to repo.

**Where to look:**

1. `docs/repo-map.md` — the registry of repos and how they relate.
2. `docs/_shared/api-contract.md` — the cross-repo spine.
3. Per-repo structure: prefer **querying** each repo's `docs/<repo>/architecture/graph.json` (Graphify output — built for querying without re-reading files) over re-reading source. Re-read source only when the graph can't answer.

**The one thing to remember:** cross-repo edges are **runtime** (repos talk over the API), not static imports. Graphify only draws static edges, so it will *not* show the connection between repos. The boundary between repos lives in `docs/_shared/api-contract.md` — that is where cross-repo flows are documented, not in any per-repo graph.
