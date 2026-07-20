---
id: block-edit-applied-migrations
title: Block edits to applied DB migrations
category: database
severity: block
recommended: true
stacks: [node-dbmate]
event: file
pattern: 'db/migrations/.*\.sql$'
emits: rule
---

dbmate tracks applied migrations in `schema_migrations` and regenerates `db/schema.sql` from them; editing an already-applied migration desyncs the tracked schema and corrupts history. Never edit an existing migration — create a NEW one with `yarn db:new <name>` (or `dbmate new <name>`) and write your forward/rollback SQL there.
