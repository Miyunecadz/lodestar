# <WORKSPACE_NAME> — Workspace Router

This folder is a **Lodestar workspace**: several independent repositories coordinated from one root. This file is a *router*, not a knowledge base — it stays intentionally small. Real knowledge lives in skills and docs that load on demand.

## Repositories

<!-- One line per repo. Filled in by /lodestar-init and /lodestar-onboard. -->
<!-- e.g. - **backend** — GraphQL API (Node/Apollo/dbmate). See docs/backend/. -->

Full map and cross-repo relationships: **[docs/repo-map.md](docs/repo-map.md)**

## Loading policy (do not remove — this keeps the router thin)

- **Do not read docs eagerly.** Skills declare *when* they apply via their `description`. Trust those triggers; load a skill only when the current task matches.
- **Stay in the relevant repo.** For a task in one repo, do not load another repo's docs or skills.
- **Match the layer to the task.** Planning a feature → the planning skill (not coding standards). Writing code → the relevant stack skill (not the planning playbook).
- **Cross-repo truth lives in `docs/_shared/`.** The API contract there is the spine that links the repos; consult it for anything spanning repo boundaries.
- **Architecture graphs are queryable.** Prefer querying `docs/<repo>/architecture/graph.json` over re-reading source to understand structure.

## Enforcement

Guardrails (if enabled via `/lodestar-guardrails`) are **enforced**, not advisory — e.g. applied database migrations cannot be edited; secrets cannot be read. Follow the redirect a blocked action gives you.

## Onboarding a new repo

Run `/lodestar-onboard ./<new-repo>`. It detects the stack, generates the architecture graph, files docs, and installs matching skills. This router does not need editing — the repo registry above is updated for you.
