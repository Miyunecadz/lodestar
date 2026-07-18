# REST API Contract — the cross-repo spine

<!-- TODO: This is the REST/DRF seed for the contract spine. `/onboard-repo` copies it to
     `docs/_shared/api-contract.md` when a DRF stack is detected — keep that filename, the
     other shared docs link to it. This document lives in `docs/_shared/` because it belongs
     to NO single repo — it is the system-level truth that links the repos at RUNTIME.
     Graphify cannot draw this edge (repos talk over the network, not via static imports),
     so it stays hand-written. -->

## Overview

This document is the **source of truth for the REST API that links the repos**. The backend
*serves* this API; the frontend and mobile apps *consume* it. Nothing here is generated —
when the API changes, this file and every consumer must be updated together.

<!-- TODO: One paragraph on the API's shape and transport.
     Defaults: JSON over HTTP, served by Django REST Framework, consumed via a typed
     HTTP client on web and mobile. Note the base path (e.g. `/api/v1/`) and content type. -->

- **Served by:** <!-- TODO: backend repo name, e.g. `api` — Django REST Framework -->
- **Consumed by:** <!-- TODO: frontend repo, mobile repo — HTTP client -->
- **Base URL(s):** see [`env-matrix.md`](./env-matrix.md) for per-tier URLs
- **Auth:** see [`auth-model.md`](./auth-model.md) <!-- TODO: e.g. token / session / JWT -->
- **Schema location:** <!-- TODO: path to the canonical OpenAPI schema in the backend repo -->

## Resource overview

<!-- TODO: List the core resources and their most important fields.
     Keep this to the resources a cross-repo contributor must understand — not every model. -->

| Resource | Purpose | Key fields |
|---|---|---|
| `User` <!-- example --> | An authenticated account | `id`, `email`, `role`, `is_active` |
| <!-- TODO --> | | |
| <!-- TODO --> | | |

## Key endpoints

<!-- TODO: The endpoints consumers actually depend on. Note pagination/filter conventions
     and the status codes each returns. -->

| Method | Path | Purpose | Auth |
|---|---|---|---|
| `GET` <!-- example --> | `/api/v1/me/` | Resolves the current token holder | Required |
| `POST` <!-- example --> | `/api/v1/auth/login/` | Issues a token | Public |
| <!-- TODO --> | | | |
| <!-- TODO --> | | | |

## Serializer shapes

<!-- TODO: The request/response body shapes consumers rely on. Note which fields are
     read-only, write-only, or nullable, and any nesting. Keep it to the shapes that cross
     repo boundaries — link to the DRF serializer source for the full definition. -->

```jsonc
// UserSerializer  <!-- example -->
{
  "id": 1,               // read-only
  "email": "a@b.com",
  "role": "member",
  "is_active": true      // read-only
}
```

<!-- TODO: add the request/response shapes for the endpoints above -->

## Permission model (DRF permission classes)

<!-- TODO: Describe how authorization is layered over the API with DRF permission classes.
     Cover: how classes map to viewsets/views, the default (deny vs allow), and where they live. -->

- **Where classes live:** <!-- TODO: path to the permissions module in the backend -->
- **Default policy:** <!-- TODO: e.g. `DEFAULT_PERMISSION_CLASSES` deny-by-default; allow public endpoints explicitly -->
- **Common classes:** <!-- TODO: e.g. `IsAuthenticated`, `IsAdminUser`, `IsOwner` -->

| Permission class | Applies to | Meaning |
|---|---|---|
| `IsAuthenticated` <!-- example --> | most endpoints | Requires a valid credential |
| <!-- TODO --> | | |

See [`auth-model.md`](./auth-model.md) for credential issuance and enforcement details.

## How each consumer uses it

- **Backend (serves):** <!-- TODO: DRF setup, where viewsets/serializers/routers live, OpenAPI schema generation -->
- **Frontend (consumes):** <!-- TODO: HTTP client setup, where request functions/types live, codegen from the OpenAPI schema if any -->
- **Mobile (consumes):** <!-- TODO: HTTP client setup on the mobile app, cache/persistence and offline notes -->

## Versioning & evolution rules

The contract changes constantly; these rules keep consumers from breaking.

1. **Additive-first.** Prefer adding new endpoints/fields over changing existing ones.
   New response fields should be optional and new request fields nullable or defaulted so
   old clients keep working.
2. **Deprecate before remove.** Mark endpoints/fields deprecated and give consumers time to
   migrate; bump the API version for breaking changes. <!-- TODO: state your versioning
   scheme (URL `/v2/` vs header) and deprecation window -->
3. **Update all consumers.** A breaking change is not "done" until the backend, frontend,
   and mobile are all updated (and any codegen re-run). Coordinate the rollout order.
4. **Never repurpose a name.** Do not change the meaning/type of an existing field —
   add a new one and deprecate the old.
5. **Keep the OpenAPI schema in sync.** Regenerate and commit the schema with every surface
   change so generated clients stay accurate.

<!-- TODO: Add any project-specific rules: schema-check CI, review sign-off,
     mobile app-store lag (old client versions live in the wild). -->
