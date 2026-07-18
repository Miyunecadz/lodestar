# API Contract — the cross-repo spine

<!-- TODO: This is the generic, stack-neutral contract stub. `/lodestar-init` copies the
     stub matching your workspace here as `api-contract.md`:
       • GraphQL workspace  → seeded from graphql-contract.md
       • REST/DRF workspace → seeded from rest-api-contract.md
       • anything else      → this generic stub
     This document lives in `docs/_shared/` because it belongs to NO single repo — it is the
     system-level truth that links the repos at RUNTIME. A code-graph tool cannot draw this
     edge (repos talk over the network, not via static imports), so it stays hand-written. -->

## Overview

This document is the **source of truth for the API that links the repos**. The backend
*serves* it; the other repos *consume* it. Nothing here is generated — when the API changes,
this file and every consumer must be updated together.

<!-- TODO: One paragraph on the API's shape and transport — e.g. JSON over HTTP, gRPC,
     GraphQL, a message queue, etc. Note the base path/URL and content type. -->

- **Style / transport:** <!-- TODO: e.g. REST+JSON / GraphQL / gRPC / events -->
- **Served by:** <!-- TODO: backend repo name -->
- **Consumed by:** <!-- TODO: which repos, and via what client -->
- **Base URL(s):** see [`env-matrix.md`](./env-matrix.md) for per-tier URLs
- **Auth:** see [`auth-model.md`](./auth-model.md) <!-- TODO: e.g. token / session / JWT -->
- **Schema location:** <!-- TODO: path to the canonical schema/IDL in the backend, if any -->

## Surface overview

<!-- TODO: List the core operations/resources a cross-repo contributor must understand —
     not every model. Adapt the columns to your style (endpoints, queries/mutations, RPCs,
     event topics). -->

| Operation / Resource | Purpose | Key fields | Auth |
|---|---|---|---|
| `getCurrentUser` <!-- example --> | Resolves the current credential holder | `id`, `email`, `role` | Required |
| <!-- TODO --> | | | |
| <!-- TODO --> | | | |

## Payload shapes

<!-- TODO: The request/response shapes consumers rely on. Note read-only/write-only/nullable
     fields and nesting. Keep it to shapes that cross repo boundaries — link to the source
     definition for the full detail. -->

```jsonc
// current user  <!-- example -->
{
  "id": 1,              // read-only
  "email": "a@b.com",
  "role": "member"
}
```

## Permission model

<!-- TODO: Describe how authorization is layered over the API. Cover where the rules live,
     the default policy (deny vs allow), and how rules map onto operations. -->

- **Where enforced:** <!-- TODO: path to the authorization layer in the backend -->
- **Default policy:** <!-- TODO: deny-by-default recommended; list public exceptions -->
- **Roles/rules:** <!-- TODO: the roles that exist and what each can do -->

See [`auth-model.md`](./auth-model.md) for credential issuance and enforcement details.

## Versioning & evolution rules

The contract changes constantly; these rules keep consumers from breaking.

1. **Additive-first.** Prefer adding new operations/fields over changing existing ones. New
   response fields should be optional and new request fields nullable or defaulted so old
   clients keep working.
2. **Deprecate before remove.** Mark surface deprecated and give consumers time to migrate;
   version the API for breaking changes. <!-- TODO: state your versioning scheme -->
3. **Update all consumers.** A breaking change is not "done" until the backend and every
   consumer are updated (and any codegen re-run). Coordinate the rollout order.
4. **Never repurpose a name.** Do not change the meaning/type of an existing field — add a
   new one and deprecate the old.
5. **Keep the schema in sync.** Regenerate and commit any schema/IDL with every surface
   change so generated clients stay accurate.
