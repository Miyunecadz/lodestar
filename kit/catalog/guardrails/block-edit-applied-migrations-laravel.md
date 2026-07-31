---
id: block-edit-applied-migrations-laravel
title: Block edits to migrations that have already run (Laravel)
category: database
severity: block
recommended: true
stacks: [laravel]
event: file
pattern: '(^|/)database/migrations/\d{4}_\d{2}_\d{2}_\d{6}_.*\.php$'
allow_if_untracked: true
surface: both
emits: rule
---

Laravel records which migrations have run in the `migrations` table; editing one that already ran desyncs migration state and breaks `php artisan migrate` on every other environment. Never edit an existing migration — create a NEW one for the change:

```
php artisan make:migration <describe_the_change>
```

Write both `up()` and `down()` there, then update the model (`$fillable`, `$casts`, relationships) to match.

Editing the migration `make:migration` just scaffolded is allowed: `allow_if_untracked: true` means this rule only fires for migrations git already tracks (tracked stands in for "has run", which cannot be detected offline). Once committed it is protected. **Surface: `both`** — also enforced for every committer, so staging a modification to a committed migration blocks the commit while adding a new one does not. Sibling of [[block-edit-applied-migrations-django]] and [[block-edit-applied-migrations]] (dbmate).
