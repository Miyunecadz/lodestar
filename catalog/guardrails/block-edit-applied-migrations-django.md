---
id: block-edit-applied-migrations-django
title: Block edits to applied Django migrations
category: database
severity: block
recommended: true
stacks: [python-django]
event: file
pattern: '(^|/)migrations/\d{4}_.*\.py$'
emits: hookify
---

Django records applied migrations in the `django_migrations` table; editing an already-applied migration desyncs migration state and breaks `migrate` on other environments. Never edit an existing migration — change your models and run `python manage.py makemigrations` to generate a NEW one, then `migrate`. For data changes, add a new data migration.
