# Local Setup — run the whole system

> **How this gets filled:** `/lodestar-onboard` pre-fills the real prereqs and install/run/migrate commands it can read from each repo (scripts, `dbmate.yml`, requirements), and leaves `<!-- TODO: human -->` for version pins and gotchas. Confirm the filled commands; answer the TODOs.

<!-- TODO: This is the runbook to bring the ENTIRE system up locally, in order.
     It lives in `docs/_shared/` because it spans every repo. Replace command
     placeholders with the real ones for your workspace, and add/remove sections to
     match your repos. -->

Bring the system up in this order: **prerequisites → backend → consumers**. The clients are
useless without the backend, so start it first.

## 0. Prerequisites

<!-- TODO: Pin exact versions. List only what your stack needs. -->

- [ ] **Language runtime(s)** <!-- TODO: e.g. Node via `.nvmrc`, Python via pyenv, etc. -->
- [ ] **Database** <!-- TODO: engine + version; local install or Docker -->
- [ ] **Supporting services** <!-- TODO: cache/queue (e.g. Redis), if any -->
- [ ] **Migration tool** <!-- TODO: how migrations run, if applicable -->
- [ ] **Package manager(s)** <!-- TODO: be consistent across repos -->
- [ ] **Platform toolchain** <!-- TODO: only if needed, e.g. mobile SDKs -->

```bash
# TODO: quick start for supporting services, e.g.
# docker compose up -d db cache
```

## 1. Backend

```bash
# 1a. Install dependencies
cd <backend-repo>            # TODO
<install cmd>                # TODO: e.g. npm install / poetry install

# 1b. Configure env (see docs/_shared/env-matrix.md)
cp .env.example .env         # TODO: confirm filename; set the required variables

# 1c. Create the database, then run migrations
<createdb cmd>               # TODO
<migrate cmd>                # TODO: runs pending migrations

# 1d. (optional) Seed data
<seed cmd>                   # TODO

# 1e. Start
<start cmd>                  # TODO: note the port and API URL — the clients point here
```

<!-- TODO: Note the port and the API URL / any playground — the clients point here. -->

## 2. Consumers

<!-- TODO: Repeat per consumer repo (web, mobile, other services). Example: -->

```bash
cd <consumer-repo>           # TODO
<install cmd>                # TODO

# Point it at the local backend (see env-matrix.md)
cp .env.example .env         # TODO: set the API URL to the backend from step 1e

<start cmd>                  # TODO
```

<!-- TODO: For a mobile consumer, note how it reaches the local backend from a
     simulator/device (localhost vs 10.0.2.2 for Android emulator vs your LAN IP). -->

## Verify it's up

- [ ] Backend API responds <!-- TODO: URL / a sanity request -->
- [ ] Each consumer loads and can reach the API

## Troubleshooting

<!-- TODO: Common local failures and fixes — DB connection refused, port in use,
     stale migrations, wrong env file, CORS. -->
