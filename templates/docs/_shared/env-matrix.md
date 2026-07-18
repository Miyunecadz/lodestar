# Environment Matrix

> **How this gets filled:** `/onboard-repo` pre-fills what it can ground in the repo (config mechanism, variable *names* from `.env.example`, the dev endpoint) with a cited basis, and leaves `<!-- TODO: human -->` for staging/prod URLs and the secret store. Never put secret *values* here.

<!-- TODO: This maps each environment tier to its config across all repos. It lives in
     `docs/_shared/` because environments span the whole system, not one repo. Replace the
     example mechanisms below with the ones your repos actually use. -->

How configuration differs across tiers, and which file supplies it in each repo. Each repo
may load config differently — document the mechanism per repo below.

<!-- TODO: e.g. a backend keyed off an env var + git-ignored override files; a web client
     using build-time `.env` files; a mobile app selecting a config at build time. -->

## Tiers

<!-- TODO: Fill in real endpoints and per-tier differences. Add/remove tiers as needed.
     Do NOT put secrets in this file — reference the secret store instead. -->

| Tier | Purpose | API endpoint | Notable differences |
|---|---|---|---|
| **development** | Local dev on your machine | `http://localhost:<port>` <!-- TODO --> | Debug logging on; seed/mock data; mail/payments stubbed |
| **staging** | Shared pre-prod for QA | <!-- TODO --> | Prod-like config; test integrations; safe to reset |
| **sandbox** | Isolated demo / external testing | <!-- TODO --> | Isolated data; third-party sandbox keys |
| **production** | Live | <!-- TODO --> | Real secrets; no debug; strict rate limits |

## Per-repo env files

<!-- TODO: Confirm the exact mechanism and filenames each repo reads for each tier.
     The rows below are examples — replace with yours. -->

| Repo | Mechanism | development | staging | sandbox | production |
|---|---|---|---|---|---|
| Backend _(example)_ | env var + override files | `.env` / `.env.local` <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |
| Web client _(example)_ | build-time `.env` | `.env.development` <!-- TODO --> | `.env.staging` <!-- TODO --> | `.env.sandbox` <!-- TODO --> | `.env.production` <!-- TODO --> |
| Mobile/other _(example)_ | build-time config select | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |

## Key variables

<!-- TODO: List the variables a contributor must set to run each repo. Names, not values. -->

| Variable | Repo(s) | Meaning |
|---|---|---|
| `ENV` / `NODE_ENV` / `DJANGO_SETTINGS_MODULE` <!-- example --> | Backend | Selects the tier's config profile |
| `API_URL` <!-- example --> | Clients | Where the client points |
| <!-- TODO --> | | |

## Notes

- **Secrets never live here** or in committed `.env` files. <!-- TODO: name your secret manager / vault. -->
- **Build-time config is baked in** — if a client selects its tier at build time, switching
  tiers means a rebuild, not a runtime toggle. <!-- TODO: confirm whether this applies. -->
- <!-- TODO: Any gotchas — CORS origins per tier, cookie domains, feature flags, etc. -->
