---
name: block-env-files
enabled: true
severity: block
stacks: [all]
event: file
pattern: '(^|/)\.env(?!.*\.(example|sample|template|dist|defaults)$)(\.[^/]+)?$'
surface: [agent, commit, permission]
permission_rules: [Read(./.env), Read(./**/.env), Read(./.env.local), Read(./**/.env.local), Read(./.env.development), Read(./**/.env.development), Read(./.env.production), Read(./**/.env.production)]
---

Real `.env` files hold live credentials and must never be read or written by the assistant. Use a committed template (`.env.example`, `.env.sample`, `.env.template`, `.env.dist`, `.env.defaults`) to learn the expected variable shape instead — those template suffixes are excluded by the negative lookahead, while `.env` and real per-tier files like `.env.local` / `.env.production` are blocked. The lookahead checks the **end** of the name, so a per-tier template (`.env.local.example`, `.env.staging.sample`) is allowed too — the earlier pattern only excused a bare `.env.example` and blocked those.

**Surfaces: `agent`, `commit`, `permission` — three mechanisms, because no one of them covers the whole rule.**

- **`permission`** — `permissions.deny` entries stop a **`Read`**, which the PreToolUse engine cannot see at all (it is registered for `Bash|Edit|Write|MultiEdit`). This is the half that makes "never read" true rather than advisory.
- **`agent`** — the hook keeps the write side, because its regex is *precise* and a deny glob is not. `permissions.deny` has no way to express "block `.env.*` **except** `*.example`", and blocking `.env.local.example` would break the very workflow this rule tells you to use. So the permission entries name only files that can never be a template — bare `.env` plus the common real tiers — and the regex above handles everything else.
- **`commit`** — a staged real `.env` blocks the commit for every committer via `.claude/hooks/lodestar-precommit-check.py`.

Using a tier this list does not name (`.env.staging`, `.env.qa`)? Add it to `permission_rules` in `.claude/guardrails/block-env-files.md` and re-run `/lodestar-guardrails`; the write and commit surfaces already cover it through the regex.
