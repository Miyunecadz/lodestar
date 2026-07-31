---
id: block-edit-applied-migrations
title: Block edits to applied DB migrations
category: database
severity: block
recommended: true
stacks: [node-dbmate]
event: file
pattern: 'db/migrations/.*\.sql$'
allow_if_untracked: true
surface: both
emits: rule
---

dbmate tracks applied migrations in `schema_migrations` and regenerates `db/schema.sql` from them; editing an already-applied migration desyncs the tracked schema and corrupts history. Never edit an existing migration — create a NEW one with `yarn db:new <name>` (or `dbmate new <name>`) and write your forward/rollback SQL there.

Writing the migration you just created is allowed: `allow_if_untracked: true` means this rule only fires for migrations git already tracks. A file `dbmate new` just scaffolded is untracked, so you can fill in its SQL; once it is committed it becomes protected. Git-tracked status stands in for "applied" — it cannot be detected offline, but anything committed is assumed to have run somewhere. If git is unavailable the rule blocks anyway, erring toward protection.

**Surface: `both`.** Also enforced for every committer: staging a *modification* to a migration git already tracks blocks the commit, while adding a brand-new migration is allowed — at commit time `allow_if_untracked` maps exactly onto the file's status (`A` = new here, `M` = already committed).
