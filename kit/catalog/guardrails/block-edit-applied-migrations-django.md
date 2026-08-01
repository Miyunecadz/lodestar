---
id: block-edit-applied-migrations-django
title: Block edits to applied Django migrations
category: database
severity: block
recommended: true
stacks: [python-django]
event: file
pattern: '(^|/)migrations/\d{4}_.*\.py$'
allow_if_untracked: true
surface: both
emits: rule
---

Django records applied migrations in the `django_migrations` table; editing an already-applied migration desyncs migration state and breaks `migrate` on other environments. Never edit an existing migration — change your models and run `python manage.py makemigrations` to generate a NEW one, then `migrate`. For data changes, add a new data migration.

---

Editing a migration `makemigrations` just generated is allowed: `allow_if_untracked: true` means this rule only fires for migrations git already tracks (git-tracked stands in for "applied", which cannot be detected offline). Hand-editing a fresh, uncommitted migration — adding a `RunPython` data step, fixing a field name — stays possible; once committed it is protected. If git is unavailable the rule blocks anyway, erring toward protection.

**Surface: `both`.** Also enforced for every committer, with the same status mapping: a new migration is an addition (allowed), editing a committed one is a modification (blocked).
