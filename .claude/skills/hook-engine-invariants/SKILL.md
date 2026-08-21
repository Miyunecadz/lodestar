---
name: hook-engine-invariants
description: The safety invariants for Lodestar's hook scripts — the guardrail engine, the pre-commit checker, the permission applier, and the rule-drift checker. Apply when editing anything in kit/templates/hooks/, when adding a context probe or frontmatter flag to a hook, or when reasoning about hook exit codes and failure modes.
user-invocable: false
---

# Hook invariants

These scripts run inside other people's workspaces. Most of what they do is **intercept** —
they fire on an action someone else took, and a bug there is not a failed test, it is a
workspace where nothing can be done.

| Script | Surface | Trigger |
|---|---|---|
| `lodestar-guardrails.py` | agent | PreToolUse, matcher `Bash\|Edit\|Write\|MultiEdit` |
| `lodestar-precommit-check.py` | commit | git `pre-commit` |
| `lodestar-permissions.py` | permission | run once by the picker; merges `permissions.deny` |
| `lodestar-rule-check.py` | none — it reports drift | on demand, by `/lodestar-update` or by hand |

The axis for exit codes below is not which surface a script serves, but **who asked**.
Interception must never punish someone who did not ask: it allows, and it reports. A mode
someone invoked deliberately to be told something — `--check` — owes them an honest exit
status instead. Two files have such a mode, and both use exit 1 for it.

## Non-negotiable

1. **Never raise, and never break an action you intercepted.** Every entry point wraps
   `main()` and exits 0 in a `finally`. An uncaught exception in a PreToolUse hook blocks
   every tool call in the workspace.

   The exception is a `--check` mode, which exists to answer a question and so must answer
   honestly: `lodestar-permissions.py --check` exits 1 on settings drift, and
   `lodestar-rule-check.py --check` exits 1 on rule drift **or on an internal error** — the
   two differ deliberately, because the second is the one whose silence would read as "no
   drift" about a scan that never ran, which is permissive failure by another name (see
   invariant 2). Neither file's interception path is affected: both still exit 0 there.
2. **Fail protective, not permissive.** Every context probe is best-effort. No git, no
   manifest, a detached HEAD, an unparseable command → fall back to behaving as a plain
   pattern match, or stay silent for a probe that *adds* blocking. Never let an
   unavailable probe silently drop a safety rule. `is_tracked()` returning `True` when git
   is absent is the model: unknown means "assume the protected case."
3. **Stdlib only.** No third-party imports, ever. The kit's promise is Python 3 and
   nothing else.
4. **Single self-contained file.** Each hook must work when copied into `.claude/hooks/`
   alone. The frontmatter parser is duplicated across every hook that reads a rule file
   **on purpose** — do not factor it into a shared module. `test-hook-parity.py`'s `FILES`
   is the list of those hooks; adding one there is what keeps a new copy honest.
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
(commit), `test-permissions.sh` (permission), `test-rule-check.sh` (rule drift). A **new
frontmatter flag** is not done when the hook reads it: the picker has to copy it into the
installed rule, so it also belongs in `/lodestar-guardrails` §5, in `test-catalog.py`'s
`COPIED`, and in `lodestar-rule-check.py`'s `COMPARED`. `validate.py` fails if you miss one
— that check exists because this was missed once (`requires_manifest_missing`, PR #64). A
new flag also needs a row in the
`docs/EXTENDING.md` table.

**Name the frontmatter dict `rule` or `fm`.** That check derives the field list by scanning
hook source for `rule`/`fm` reads — `.get("x")` and `["x"]` both — so a field read through
any other name (`cfg = rule; cfg.get("x")`) is invisible to it, and every site above can
then omit the field with no gate objecting. This is a real constraint the gate rests on, not
a style preference.
