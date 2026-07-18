# GraphQL Contract — the cross-repo spine

<!-- TODO: Rename this file to match your API (e.g. `graphql-contract.md`, `rest-contract.md`).
     This document lives in `docs/_shared/` because it belongs to NO single repo — it is the
     system-level truth that links the repos at RUNTIME. Graphify cannot draw this edge
     (repos talk over the network, not via static imports), so it stays hand-written. -->

## Overview

This document is the **source of truth for the API that links the repos**. The backend
*serves* this schema; the frontend and mobile apps *consume* it. Nothing here is generated —
when the schema changes, this file and every consumer must be updated together.

<!-- TODO: One paragraph on the API's shape and transport.
     Defaults: GraphQL over HTTP (queries/mutations) + WebSocket (subscriptions),
     served by apollo-server, consumed via @apollo/client on web and mobile. -->

- **Served by:** <!-- TODO: backend repo name, e.g. `api` — apollo-server -->
- **Consumed by:** <!-- TODO: frontend repo, mobile repo — @apollo/client -->
- **Endpoint(s):** see [`env-matrix.md`](./env-matrix.md) for per-tier URLs
- **Auth:** see [`auth-model.md`](./auth-model.md) (JWT + graphql-shield)
- **Schema location:** <!-- TODO: path to canonical SDL / schema file in the backend repo -->

## Schema overview (key types)

<!-- TODO: List the core domain types and their most important fields.
     Keep this to the types a cross-repo contributor must understand — not every type. -->

| Type | Purpose | Key fields |
|---|---|---|
| `User` <!-- example --> | An authenticated account | `id`, `email`, `role`, `twoFactorEnabled` |
| <!-- TODO --> | | |
| <!-- TODO --> | | |

## Key queries

<!-- TODO: The queries consumers actually depend on. Note pagination/filter conventions. -->

| Query | Args | Returns | Notes |
|---|---|---|---|
| `me` <!-- example --> | — | `User` | Resolves the current token holder |
| <!-- TODO --> | | | |

## Key mutations

<!-- TODO: Mutations that change state. Note idempotency and validation expectations. -->

| Mutation | Args | Returns | Notes |
|---|---|---|---|
| `login` <!-- example --> | `email`, `password` | `AuthPayload` | Issues a JWT; may require 2FA step |
| <!-- TODO --> | | | |

## Key subscriptions

<!-- TODO: Real-time channels. Note the transport (e.g. graphql-ws) and auth handshake. -->

| Subscription | Args | Emits | Notes |
|---|---|---|---|
| <!-- TODO --> | | | |

## Permission model (graphql-shield)

<!-- TODO: Describe how authorization is layered over the schema with graphql-shield.
     Cover: how rules map to types/fields, the default (deny vs allow), and where rules live. -->

- **Where rules live:** <!-- TODO: path to the shield permissions file in the backend -->
- **Default policy:** <!-- TODO: e.g. deny-by-default; explicitly allow public fields -->
- **Common rules:** <!-- TODO: e.g. `isAuthenticated`, `isAdmin`, `isOwner` -->

| Rule | Applies to | Meaning |
|---|---|---|
| `isAuthenticated` <!-- example --> | most queries/mutations | Requires a valid JWT |
| <!-- TODO --> | | |

See [`auth-model.md`](./auth-model.md) for token issuance and enforcement details.

## How each consumer uses it

- **Backend (serves):** <!-- TODO: apollo-server setup, resolver location, schema stitching/codegen if any -->
- **Frontend (consumes):** <!-- TODO: @apollo/client setup, where queries/fragments live, codegen typing -->
- **Mobile (consumes):** <!-- TODO: @apollo/client setup on React Native, cache/persistence notes -->

## Evolution rules

The contract changes constantly; these rules keep consumers from breaking.

1. **Additive-first.** Prefer adding new types/fields/args over changing existing ones.
   New fields should be nullable or have safe defaults so old clients keep working.
2. **Deprecate before remove.** Mark fields `@deprecated(reason: "…")` and give consumers
   time to migrate. <!-- TODO: state your deprecation window / policy -->
3. **Update all consumers.** A breaking change is not "done" until the backend, frontend,
   and mobile are all updated (and any codegen re-run). Coordinate the rollout order.
4. **Never repurpose a name.** Do not change the meaning/type of an existing field —
   add a new one and deprecate the old.

<!-- TODO: Add any project-specific rules: versioning strategy, review sign-off,
     schema-check CI, mobile app-store lag (old client versions live in the wild). -->
