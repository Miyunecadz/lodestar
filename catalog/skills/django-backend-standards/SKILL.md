---
name: django-backend-standards
description: Use when editing the Django backend repo (REPO) — models, migrations, DRF views/serializers, settings, or Celery tasks.
stacks: [python-django]
---

# Django backend standards (REPO)

Conventions live in the docs, not here. Read **`docs/REPO/conventions.md`** and **`docs/REPO/architecture/`** before editing.

**Key reminders:**

- **Models drive migrations:** change the model, then `python manage.py makemigrations` — never edit an already-applied migration.
- **API surface:** the API is served through **DRF** (serializers, viewsets/views, permissions). Changes to the surface also mean updating the contract — load `drf-api-contract`.
- **Settings:** configuration is **split per environment** — put values in the right settings module, never hard-code per-tier values.
- **ORM hygiene:** watch for N+1 queries — use `select_related` / `prefetch_related` and keep querysets lean.

Details, patterns, and the actual code layout are in `docs/REPO/` — go there.
