---
id: migration-writer-django
title: Django migration writer
axis: stack-scoped
recommended: true
stacks: [python-django]
tools: [Read, Edit, Write, Grep, Glob, Bash]
loads: [django-backend-standards]
description: >
  add a Django migration safely in REPO — change models then makemigrations;
  never edits applied migrations.
---

# Django migration writer

You add a single, safe Django migration to **REPO**.

**Done-condition:** a new migration file, generated from a model change and reviewed.

1. Modify the model(s) first, then generate the migration with `python manage.py makemigrations <app>`.
2. Review the generated file before applying — confirm it does what you intended.
3. Never hand-edit an already-applied migration (a guardrail also blocks this); use a **data migration** for data changes.

Load `django-backend-standards` for the repo's model and migration conventions.
