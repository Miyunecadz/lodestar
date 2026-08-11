---
name: hook-engine-invariants
description: The safety invariants for Lodestar's hook scripts — the guardrail engine, the pre-commit checker, and the permission applier. Apply when editing anything in kit/templates/hooks/, when adding a context probe or frontmatter flag to a hook, or when reasoning about hook exit codes and failure modes.
user-invocable: false
---

# Hook invariants

These three scripts run inside other people's workspaces on every matching action. A bug
here is not a failed test — it is a workspace where nothing can be done.

| Script | Surface | Trigger |
|---|---|---|
| `lodestar-guardrails.py` | agent | PreToolUse, matcher `Bash\|Edit\|Write\|MultiEdit` |
| `lodestar-precommit-check.py` | commit | git `pre-commit` |
| `lodestar-permissions.py` | permission | run once by the picker; merges `permissions.deny` |

## Non-negotiable

1. **Never raise.** Every entry point wraps `main()` and exits 0 in a `finally`. An
   uncaught exception in a PreToolUse hook blocks every tool call in the workspace.
2. **Fail protective, not permissive.** Every context probe is best-effort. No git, no
   manifest, a detached HEAD, an unparseable command → fall back to behaving as a plain
   pattern match, or stay silent for a probe that *adds* blocking. Never let an
   unavailable probe silently drop a safety rule. `is_tracked()` returning `True` when git
   is absent is the model: unknown means "assume the protected case."
3. **Stdlib only.** No third-party imports, ever. The kit's promise is Python 3 and
   nothing else.
4. **Single self-contained file.** Each hook must work when copied into `.claude/hooks/`
   alone. The frontmatter parser is duplicated across all three **on purpose** — do not
   factor it into a shared module.
5. **Never hang.** Subprocess calls take a timeout (`GIT_TIMEOUT = 2` in the engine). A
   hook that hangs is worse than one that fails.
6. **The commit hook exits 1 only on a `block` match.** Missing tool, unreadable
   manifest, invalid regex, internal error → exit 0. It must never break an unrelated
   commit. `git commit --no-verify` stays the documented bypass, which is also why it is
   not a substitute for server-side branch protection.
7. **The permission applier stays idempotent and reversible.** Re-running never
   duplicates, never disturbs hand-written entries, and unticking a rule removes exactly
   the entries that rule contributed. Ownership lives in the manifest under
   `guardrailSurfaces.permission.entries` — that record is what makes removal safe.

## Output protocol

The engine writes one JSON object to stdout and exits 0:

- block → `hookSpecificOutput` with `permissionDecision: "deny"` and a
  `permissionDecisionReason`, plus `systemMessage`.
- warn → `systemMessage` only.
- nothing matched → `{}`.

Block wins over warn; all matching messages are combined. Keep this shape — a bare string
on stdout is not a decision.

## Shell-awareness, when touching command matching

`shell_words()` is hand-rolled rather than `shlex`-based because quoting matters *within*
a word: `-f body="rm -rf x"` is one word whose payload is inert text, and shlex's
`whitespace_split` cannot report that distinction. `command_targets()` uses it so
`match: argv` tests unquoted words, while nested shell payloads (`bash -c "…"`, `eval "…"`)
stay matched — quoting must not become a bypass. `command_operands()` returns `None` for
any compound command (`&&`, `;`, `|`, `$(…)`), because operand analysis is only sound for a
single command; callers must stay protective on `None`.

## Before you finish

Add a case for each surface touched — `test-engine.sh` (agent), `test-precommit.sh`
(commit), `test-permissions.sh` (permission). A new flag also needs a row in the
`docs/EXTENDING.md` table.
