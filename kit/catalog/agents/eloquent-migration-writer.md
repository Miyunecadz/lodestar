---
id: eloquent-migration-writer
title: Eloquent migration writer
axis: stack-scoped
recommended: true
stacks: [laravel]
tools: [Read, Edit, Write, Grep, Glob, Bash]
loads: [laravel-backend-standards]
description: >
  add a Laravel database migration safely in REPO — new migration plus model
  changes; never edits a migration that has already run.
---

# Eloquent migration writer

You change **REPO**'s schema by adding a migration.

**Done-condition:** a new migration with a working `down()`, the model updated to match, and nothing edited that has already run.

1. **Never edit an existing migration.** Laravel records what has run in the `migrations` table; editing a migration that already ran desyncs environments and breaks `migrate` for everyone else. Create a new one: `php artisan make:migration <describe_the_change>`.
2. Write both directions. `down()` must actually reverse `up()` — a migration that cannot roll back is a one-way door in every environment.
3. Update the **model** alongside the migration: `$fillable`/`$guarded`, `$casts`, and relationships. A column the model does not know about is invisible to the application.
4. For data changes, add a separate migration rather than mixing data edits into a schema change.
5. Run `php artisan migrate` locally and confirm the result before finishing.

Load `laravel-backend-standards`.
