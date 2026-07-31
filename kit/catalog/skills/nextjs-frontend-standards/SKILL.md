---
name: nextjs-frontend-standards
description: Use when editing the Next.js repo (REPO) — pages or App Router routes, Server/Client Components, route handlers, server actions, data fetching, or metadata.
stacks: [nextjs]
---

# Next.js standards (REPO)

Conventions live in the docs, not here. Read **`docs/REPO/conventions.md`** and **`docs/REPO/architecture/`** before editing.

**Key reminders:**

- **Know which router this repo uses** — `app/` (App Router) or `pages/` (Pages Router). The file conventions and data-fetching APIs differ; mixing them produces code that silently never runs. Check before adding a route.
- **Server by default (App Router).** Components are Server Components unless the file declares `'use client'`. Add that directive at the **leaf** that needs state/effects/browser APIs, not at a layout — marking a high-level component client-side pulls its whole subtree into the bundle.
- **`NEXT_PUBLIC_` means public.** Those variables are inlined into the client bundle at build time and readable by anyone. Server-only secrets get no prefix and are read only in Server Components, route handlers, or server actions.
- **One data-fetching pattern per repo.** Read a neighbouring route and follow it (direct fetch in a Server Component / route handler / server action) rather than adding a third approach. Caching and revalidation behaviour is documented in `docs/REPO/`.
- **Mutations go through server actions or route handlers**, not client-side writes to a database client.

Details and the actual route/component layout are in `docs/REPO/` — go there.
