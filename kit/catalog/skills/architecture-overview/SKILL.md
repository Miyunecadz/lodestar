---
name: architecture-overview
description: Use when you need the big picture of how the repos connect, or to trace a flow across a repo boundary.
stacks: [all]
---

# Architecture overview

Get the whole-system map, or follow one flow from repo to repo.

**Where to look:**

1. `docs/repo-map.md` — the registry of repos and how they relate.
2. `docs/_shared/api-contract.md` — the cross-repo spine. A section still marked `<!-- TODO: human -->` is unknown, not empty: say so and read the code rather than inferring the contract.
3. Per-repo structure: read the repo's `architecture` mode in `.claude/lodestar.manifest.json` first — `graphify` → prefer **querying** `docs/<repo>/architecture/graph.json` (built for querying without re-reading files) over re-reading source; `markdown` → read `docs/<repo>/architecture/overview.md`; `deferred` → no map exists, read source. Before treating an empty graph answer as "no such code", check that repo's `mapping.coverage.filesMissing` — a file the graph does not cover is unmapped, not absent.

**The one thing to remember:** cross-repo edges are **runtime** (repos talk over the API), not static imports. Graphify only draws static edges, so it will *not* show the connection between repos. The boundary between repos lives in `docs/_shared/api-contract.md` — that is where cross-repo flows are documented, not in any per-repo graph.
