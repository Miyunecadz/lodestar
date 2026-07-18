---
id: block-destructive-commands
title: Block irreversible destructive shell commands
category: safety
severity: block
recommended: true
stacks: [all]
event: bash
pattern: '(\brm\s+-[a-zA-Z]*[rf]|\bgit\s+reset\s+--hard|\bgit\s+clean\s+-[a-zA-Z]*f|\bgit\s+(checkout|restore)\s+(--\s+)?\.|\bdd\s+if=|\bmkfs\b|\bshred\b|\btruncate\s+-s|\bDROP\s+(DATABASE|TABLE|SCHEMA)|>\s*/dev/(sd|nvme|disk))'
emits: hookify
---

This command is irreversible and destroys work with no undo (`rm -rf`, `git reset --hard`, `git clean -fdx`, `git checkout/restore .`, `dd`, `mkfs`, `shred`, `truncate`, `DROP DATABASE/TABLE`, writing to a raw device). STOP and confirm intent with the user before running it, and prefer a recoverable alternative first:

- Discarding changes? `git stash` instead of `reset --hard` / `clean` — stashes are recoverable.
- Removing tracked files? `git rm` (staged, reversible) instead of `rm -rf`.
- Deleting a directory of real work? List it first and confirm the exact path — a wrong `rm -rf` target is unrecoverable.
- Dropping DB objects? Take a dump first, and never run it against a non-local database without explicit approval.

This guards against mistakes, not a determined adversary — an obfuscated command can slip the pattern. It is a stop-and-redirect, not a sandbox.
