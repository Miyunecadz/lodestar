---
name: laravel-backend-standards
description: Use when editing the Laravel backend repo (REPO) — Eloquent models, migrations, controllers, FormRequests, API Resources, policies, queues, or artisan commands.
stacks: [laravel]
---

# Laravel backend standards (REPO)

Conventions live in the docs, not here. Read **`docs/REPO/conventions.md`** and **`docs/REPO/architecture/`** before editing.

**Key reminders:**

- **Migrations are append-only:** `php artisan make:migration` for every schema change, with a real `down()`. Never edit a migration that has already run — update the model to match instead.
- **Validation belongs in a FormRequest**, not the controller body; **response shape belongs in an API Resource**, not a hand-built array. Both are what keep `docs/_shared/api-contract.md` true.
- **Authorization is per-action:** a Policy method or an explicit gate check. An endpoint with no authorization is a gap, not a default.
- **`env()` only inside `config/`.** Once config is cached (`php artisan config:cache`) an `env()` call elsewhere returns null in production. Read `config('x.y')` everywhere else.
- **ORM hygiene:** watch for N+1 — `with()` / `load()` for eager loading, and keep queries out of Blade loops.
- **Queues for slow work**, not the request cycle; remember jobs are serialized, so pass ids rather than whole models where the payload matters.

Details, patterns, and the actual code layout are in `docs/REPO/` — go there.
