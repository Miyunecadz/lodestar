---
name: backend-standards
description: Use when editing the backend repo (REPO) — resolvers, dbmate migrations, redis/bull jobs, or cron.
stacks: [graphql-apollo-server, node-dbmate]
---

# Backend standards (REPO)

Conventions live in the docs, not here. Read **`docs/REPO/conventions.md`** and **`docs/REPO/architecture/`** before editing.

**Key reminders:**

- **Migrations:** create a **NEW** migration — never edit one that has already been applied.
- **Resolvers:** every resolver goes through `graphql-shield` (a resolver without a permission rule is a gap). Changes to the API surface also mean updating the contract — load `graphql-contract`.
- **Background work:** use **Bull** for jobs/queues and cron for scheduled work.

Details, patterns, and the actual code layout are in `docs/REPO/` — go there.
