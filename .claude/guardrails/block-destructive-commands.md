---
name: block-destructive-commands
enabled: true
event: bash
pattern: '(\brm\s+-[a-zA-Z]*[rf]|\bgit\s+reset\s+--hard|\bgit\s+clean\s+-[a-zA-Z]*f|\bgit\s+(checkout|restore)\s+(--\s+)?\.|\bdd\s+if=|\bmkfs\b|\bshred\b|\btruncate\s+-s|\bDROP\s+(DATABASE|TABLE|SCHEMA)|>\s*/dev/(sd|nvme|disk))'
severity: block
stacks: [all]
match: argv
allow_paths: ['^/tmp/', '^/var/tmp/', '^/var/folders/']
surface: agent
---

This command is irreversible and destroys work with no undo (`rm -rf`, `git reset --hard`, `git clean -fdx`, `git checkout/restore .`, `dd`, `mkfs`, `shred`, `truncate`, `DROP DATABASE/TABLE`, writing to a raw device). STOP and confirm intent with the user before running it, and prefer a recoverable alternative first:

- Discarding changes? `git stash` instead of `reset --hard` / `clean` — stashes are recoverable.
- Removing tracked files? `git rm` (staged, reversible) instead of `rm -rf`.
- Deleting a directory of real work? List it first and confirm the exact path — a wrong `rm -rf` target is unrecoverable.
- Dropping DB objects? Take a dump first, and never run it against a non-local database without explicit approval.

---

This guards against mistakes, not a determined adversary — an obfuscated command can slip the pattern. It is a stop-and-redirect, not a sandbox.

**Matching is shell-aware.** `match: argv` tests the command's *unquoted* words, so a destructive-looking string that runs nothing — `rm -rf` inside a JSON argument, an `echo`'d warning, a commit message — no longer trips the rule. Quoted payloads passed to a nested shell (`bash -c "…"`, `eval "…"`) are still matched, so quoting is not a bypass. `allow_paths` exempts deletes whose every operand resolves under a temp prefix (`/tmp`, `/var/tmp`, `/var/folders`), which is where scratch work lives; mix in one non-temp path and the rule fires again. Compound commands (`&&`, `;`, `|`, `$(…)`) skip the exemption entirely and always block.

**Surface: `agent` only.** It guards shell commands, not commit contents; there is nothing for a pre-commit hook to inspect.
