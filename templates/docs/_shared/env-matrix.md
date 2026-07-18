# Environment Matrix

<!-- TODO: This maps each environment tier to its config across all repos. It lives in
     `docs/_shared/` because environments span the whole system, not one repo. -->

How configuration differs across tiers, and which file supplies it in each repo. Each repo
loads config differently:

- **Backend** — keyed off `NODE_ENV`; secrets/overrides in `*.local` files (git-ignored).
- **Frontend** — Create React App / craco style `.env` files.
- **Mobile** — `react-native-config`, selected at build time via the `ENVFILE` variable.

## Tiers

<!-- TODO: Fill in real endpoints and per-tier differences. Add/remove tiers as needed.
     Do NOT put secrets in this file — reference the secret store instead. -->

| Tier | Purpose | API endpoint | Notable differences |
|---|---|---|---|
| **development** | Local dev on your machine | `http://localhost:<port>/graphql` <!-- TODO --> | Debug logging on; seed/mock data; mail/payments stubbed |
| **staging** | Shared pre-prod for QA | <!-- TODO --> | Prod-like config; test integrations; safe to reset |
| **sandbox** | Isolated demo / external testing | <!-- TODO --> | Isolated data; third-party sandbox keys |
| **production** | Live | <!-- TODO --> | Real secrets; no debug; strict rate limits |

## Per-repo env files

<!-- TODO: Confirm the exact filenames each repo reads for each tier. -->

| Repo | Mechanism | development | staging | sandbox | production |
|---|---|---|---|---|---|
| Backend | `NODE_ENV` + `*.local` | `.env` / `.env.local` <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |
| Frontend | `.env` | `.env.development` <!-- TODO --> | `.env.staging` <!-- TODO --> | `.env.sandbox` <!-- TODO --> | `.env.production` <!-- TODO --> |
| Mobile | `react-native-config` (`ENVFILE`) | `ENVFILE=.env.development` <!-- TODO --> | `ENVFILE=.env.staging` <!-- TODO --> | `ENVFILE=.env.sandbox` <!-- TODO --> | `ENVFILE=.env.production` <!-- TODO --> |

## Key variables

<!-- TODO: List the variables a contributor must set to run each repo. Names, not values. -->

| Variable | Repo(s) | Meaning |
|---|---|---|
| `NODE_ENV` <!-- example --> | Backend | Selects the tier's config profile |
| `API_URL` / `REACT_APP_API_URL` <!-- example --> | Frontend / Mobile | Where the client points |
| <!-- TODO --> | | |

## Notes

- **Secrets never live here** or in committed `.env` files. <!-- TODO: name your secret manager / vault. -->
- **Mobile builds bake env in at build time** — switching tiers means a rebuild with a
  different `ENVFILE`, not a runtime toggle.
- <!-- TODO: Any gotchas — CORS origins per tier, cookie domains, feature flags, etc. -->
