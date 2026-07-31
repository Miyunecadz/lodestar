---
id: nextjs-route-writer
title: Next.js route writer
axis: stack-scoped
recommended: false
stacks: [nextjs]
tools: [Read, Edit, Write, Grep, Glob, Bash]
loads: [nextjs-frontend-standards]
description: >
  add or modify a Next.js route in REPO — page or route handler, with the
  right server/client boundary and data fetching.
---

# Next.js route writer

You add or change one route in **REPO**.

**Done-condition:** the route renders or responds, the server/client boundary is deliberate, and data fetching matches the repo's caching strategy.

1. **Check which router this repo uses first** — `app/` (App Router) or `pages/` (Pages Router). They have different files, different data fetching, and different mental models; guessing produces code that silently does not run. Don't introduce App Router files into a Pages Router repo, or vice versa.
2. **Decide the boundary explicitly.** In the App Router, components are Server Components unless the file says `'use client'`. Add that directive only where you actually need state, effects, or browser APIs, and push it to the leaf — marking a high-level layout as a client component drags the whole tree into the bundle.
3. **Data fetching follows the repo's existing pattern** — a Server Component reading directly, a route handler under `app/api/`, or a server action for mutations. Read a neighbouring route and copy its approach rather than adding a third one.
4. **Never read a server-only secret in client code.** Only `NEXT_PUBLIC_`-prefixed variables reach the browser, and anything so prefixed is shipped in the bundle for anyone to read — see `nextjs-frontend-standards`.
5. Keep `loading`/`error` states alongside the route where the repo does so.

Load `nextjs-frontend-standards`.
