---
id: nextjs-no-public-secrets
title: Warn on secret-looking NEXT_PUBLIC_ variables
category: secrets
severity: warn
recommended: true
stacks: [nextjs]
event: file
match: content
pattern: 'NEXT_PUBLIC_[A-Z0-9_]*(SECRET|PRIVATE|PASSWORD|CREDENTIAL|_TOKEN|API_KEY|ACCESS_KEY)'
surface: agent
emits: rule
---

In Next.js, **every** `NEXT_PUBLIC_`-prefixed variable is inlined into the client bundle at build time and is readable by anyone who opens the page. Prefixing a secret makes it public — there is no "public but hidden" tier.

If this value is genuinely secret, drop the prefix and read it **server-side only** (a Server Component, a route handler under `app/api/`, or a server action). If the browser needs the result, expose an endpoint that uses the secret server-side and returns only what the client may see.

Some `NEXT_PUBLIC_` keys are legitimately public — a Stripe *publishable* key, a Mapbox public token, a public analytics id — which is why this **warns** rather than blocks: the name pattern cannot tell a publishable key from a secret one. Confirm which you have; if it is publishable, say so and continue.

**Surface: `agent`** — it matches edited *content*, and the commit-surface checker inspects staged paths and diffs rather than re-running content rules. [[block-env-files]] and [[scan-secrets-before-commit]] cover the commit path for real credentials.
