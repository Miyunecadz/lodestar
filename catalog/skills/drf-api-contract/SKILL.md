---
name: drf-api-contract
description: Use when changing the shared REST API surface — endpoints, serializers, status codes, or permissions — that other repos depend on.
stacks: [drf]
---

# DRF API contract

The shared REST API surface is the spine every repo depends on. Its single source of truth is **`docs/_shared/rest-api-contract.md`** — read it first and plan the change against it.

**Rules for evolving the contract without breaking consumers:**

- **Additive first.** Add new endpoints/fields rather than changing existing ones. Additions don't break anyone.
- **Deprecate before removing.** Mark the old surface deprecated (or version it), migrate consumers off it, then remove — never remove in one step.
- **Keep serializers backward-compatible.** New serializer fields should be optional or safely defaulted so old clients keep working; never repurpose an existing field's name or meaning.
- **Update every consumer.** A contract change is only done when all repos that depend on it are updated. Trace them via `docs/repo-map.md`.
- **Keep the schema in sync.** Any change to the surface updates `docs/_shared/rest-api-contract.md` and the OpenAPI schema in the same change. A drifted contract is worse than no contract.

Point to the contract doc for the actual schema — do not restate it here.
