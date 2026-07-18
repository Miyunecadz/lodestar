---
name: graphql-contract
description: Use when changing anything on the shared API surface — queries, mutations, subscriptions, or permissions — that the repos depend on.
stacks: [graphql-apollo-server, graphql-apollo-client]
---

# GraphQL contract

The shared API surface is the spine every repo depends on. Its single source of truth is **`docs/_shared/<api>-contract.md`** — read it first and plan the change against it.

**Rules for evolving the contract without breaking consumers:**

- **Additive first.** Add new fields/types/args rather than changing existing ones. Additions don't break anyone.
- **Deprecate before removing.** Mark the old surface deprecated, migrate consumers off it, then remove — never remove in one step.
- **Update every consumer.** A contract change is only done when all repos that depend on it are updated. Trace them via `docs/repo-map.md`.
- **Keep the doc in sync.** Any change to the surface updates `docs/_shared/<api>-contract.md` in the same change. A drifted contract is worse than no contract.

Point to the contract doc for the actual schema — do not restate it here.
