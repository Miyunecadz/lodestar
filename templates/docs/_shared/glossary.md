# Glossary

> **How this gets filled:** `/lodestar-onboard` proposes candidate terms from model/type names, but leaves their *meanings* as `<!-- TODO: human -->` — business semantics are not in the code and must not be guessed. Fill in the meanings.

<!-- TODO: Domain vocabulary shared across all repos. Keep terms here when the same word
     must mean the same thing in the backend, frontend, and mobile. This lives in
     `docs/_shared/` because the language belongs to the system, not one repo.

     Replace the example rows below with your real domain terms and remove the
     "(example)" markers. Aim for terms a new contributor would otherwise guess at. -->

| Term | Meaning |
|---|---|
| Tenant _(example)_ | An isolated customer account; most data is scoped to one tenant. <!-- TODO: replace --> |
| Workspace _(example)_ | A container within a tenant that groups users and resources. <!-- TODO: replace --> |
| Actor _(example)_ | The authenticated user performing a request; drives permission checks. <!-- TODO: replace --> |
| Soft delete _(example)_ | Marking a record inactive (e.g. `deletedAt`) instead of removing the row. <!-- TODO: replace --> |
| <!-- TODO: term --> | <!-- TODO: meaning --> |
| <!-- TODO: term --> | <!-- TODO: meaning --> |

<!-- TODO: If a term maps to a specific API type/resource or DB table, link it to
     api-contract.md so the vocabulary and the schema stay in sync. -->
