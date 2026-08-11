# `.claude/` — this repo's own Claude Code config

Dev tooling for building Lodestar. Never shipped: `install.sh` copies only from
[`../kit/`](../kit/), so anything added here is safe. Layout and clone-time setup live in
[`../CONTRIBUTING.md`](../CONTRIBUTING.md).

| Path | What it does |
|---|---|
| `settings.json` | registers the guardrail engine (PreToolUse) and the two dev hooks (PostToolUse); holds the CI-gate allow-list and the `permissions.deny` block |
| `guardrails/` | four dogfooded rules — installed copies of the catalog entries of the same name, produced by the picker's transform (`id:` → `name:`, plus `enabled: true`). **Re-derive them from `kit/catalog/guardrails/` rather than hand-editing**, or they drift out of the product |
| `hooks/dev-*.py` | dev-only, no kit equivalent: run `validate.py` after a catalog edit and `shellcheck` after a shell edit, so a CI failure surfaces at the edit instead of at push |
| `agents/` | `gate-runner` (run every CI gate, report only failures), `kit-boundary-reviewer` (the invariants CI cannot check) |
| `skills/` | loaded on demand when a task matches |
| `lodestar.manifest.json` | records which deny entries `lodestar-permissions.py` owns; **do not hand-edit** |

`settings.json` runs the **shipped** hooks in place from `kit/templates/hooks/`. There is
deliberately no dev copy of them — see CONTRIBUTING.md for why.
