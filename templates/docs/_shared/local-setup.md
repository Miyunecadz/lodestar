# Local Setup — run the whole system

<!-- TODO: This is the runbook to bring the ENTIRE system up locally, in order.
     It lives in `docs/_shared/` because it spans every repo. Replace command
     placeholders with the real ones for your workspace. -->

Bring the system up in this order: **prerequisites → backend → frontend → mobile**.
The clients are useless without the backend, so start it first.

## 0. Prerequisites

<!-- TODO: Pin exact versions. -->

- [ ] **Node** <!-- TODO: version, e.g. via `nvm use` / `.nvmrc` -->
- [ ] **Database** — e.g. **MariaDB** <!-- TODO: version; local install or Docker -->
- [ ] **Redis** <!-- TODO: version; used for queues/cache -->
- [ ] **dbmate** <!-- TODO: install for running migrations -->
- [ ] **Package manager** <!-- TODO: npm / yarn / pnpm — be consistent across repos -->
- [ ] **Mobile toolchain** (only if running mobile): Xcode + CocoaPods (iOS), Android Studio + SDK

```bash
# TODO: quick start for supporting services, e.g.
# docker compose up -d mariadb redis
```

## 1. Backend

```bash
# 1a. Install dependencies
cd <backend-repo>            # TODO
<install cmd>                # TODO: e.g. npm install

# 1b. Configure env (see docs/_shared/env-matrix.md)
cp .env.example .env.local   # TODO: confirm filename; set NODE_ENV, DB, REDIS, JWT secret

# 1c. Create the database, then run migrations (dbmate)
<createdb cmd>               # TODO: e.g. dbmate create
dbmate up                    # TODO: confirm; runs pending migrations

# 1d. (optional) Seed data
<seed cmd>                   # TODO

# 1e. Start
<start cmd>                  # TODO: e.g. npm run dev  → serves GraphQL at http://localhost:<port>/graphql
```

<!-- TODO: Note the port and the GraphQL playground/URL — the clients point here. -->

## 2. Frontend

```bash
cd <frontend-repo>           # TODO
<install cmd>                # TODO: e.g. npm install

# Point it at the local backend (see env-matrix.md)
cp .env.example .env         # TODO: set API_URL / REACT_APP_API_URL to the backend from step 1e

<start cmd>                  # TODO: e.g. npm start  → opens http://localhost:<port>
```

## 3. Mobile

```bash
cd <mobile-repo>             # TODO
<install cmd>                # TODO: e.g. npm install

# iOS only: install native pods
cd ios && pod install && cd ..   # TODO

# Select env (react-native-config) and run
ENVFILE=.env.development <run cmd>   # TODO: e.g. npx react-native run-ios / run-android
```

<!-- TODO: Note how the mobile app reaches the local backend from a simulator/device
     (e.g. localhost vs 10.0.2.2 for Android emulator vs your LAN IP for a physical device). -->

## Verify it's up

- [ ] Backend GraphQL endpoint responds <!-- TODO: URL / a sanity query like `{ __typename }` -->
- [ ] Frontend loads and can log in
- [ ] Mobile app builds and reaches the API

## Troubleshooting

<!-- TODO: Common local failures and fixes — DB connection refused, port in use,
     stale migrations, pod install errors, wrong ENVFILE, CORS. -->
