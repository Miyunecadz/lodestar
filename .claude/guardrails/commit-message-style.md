---
name: commit-message-style
enabled: true
event: bash
pattern: '(^|[;&|]\s*)git(\s+-\S+)*\s+commit\b'
severity: warn
stacks: [all]
match: argv
surface: agent
---

Keep commit messages to a **single line** — a concise subject, no body — and do **not** append a `Co-Authored-By:` trailer (or other trailers). If a `-m` message spans multiple lines or adds a co-author, rewrite it as one line before committing.

---

This encodes an opinionated style; adjust to taste. Set `severity: block` to hard-reject instead of remind. Note a `bash` rule only sees `git commit -m "…"` — for enforcement across *all* commits (including editor/manual ones), pair it with a native `commit-msg` git hook that reads the message file.

**Advisory only, and it fires on every commit.** A `PreToolUse` hook sees the command about to run, not whether you already did the step it asks for — it cannot confirm a scan or review happened, so treat it as a checklist prompt rather than a gate. A real gate needs state written by the prior step or a `commit`-surface git hook (see [[scan-secrets-before-commit]] / issue #3).

Matching is anchored to a real invocation (`match: argv` on `git … commit` at a command boundary), so `git commit` inside a quoted string or an echoed message no longer triggers it. `git commit --amend` does still count — amending is committing.

**Surface: `agent` only.** The commit-time twin is a `commit-msg` hook — a different git event from the `pre-commit` surface Lodestar installs, and it reads the message file rather than the staged diff. Until that event is generated, this rule holds for Claude only.
