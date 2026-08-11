# Lodestar

An AI-native workspace kit for Claude Code. Ships a **kit** that `install.sh` copies into
a user's multi-repo workspace. The product source is Markdown, not code.

## Architecture

```
kit/                  THE PRODUCT — everything install.sh distributes
  catalog/            guardrails/ agents/ skills/ — stack-tagged Markdown entries
  templates/          CLAUDE.md router, docs/_shared stubs, hooks/*.py, mcp/, git/
  commands/           lodestar-*.md slash-command specs
.claude/              THIS REPO'S dev tooling — never shipped
docs/ examples/       human docs
.github/              CI gates + release pipeline
changelog.d/          one fragment per PR; release.py folds them in
install.sh VERSION CHANGELOG.md
```

`install.sh` copies **only** from `kit/`. In a target workspace the kit lands at
`.lodestar/catalog|templates` and `.claude/commands` — a command spec must reference
those paths, never this repo's `kit/…`.

## Sources of truth — verify against these, not against prose

| Question | Authority |
|---|---|
| What gates must pass? | `.github/workflows/ci.yml` — run every gate it names; never a memorized list or count |
| What does a catalog entry require? | `.github/scripts/validate.py` |
| What Python floor do the hooks hold? | `MIN_PYTHON` in `kit/templates/hooks/lodestar-*.py` |
| What is enabled in this workspace? | `.claude/lodestar.manifest.json` |

Prefer running a gate over predicting its verdict. `gate-runner` (agent) reads `ci.yml`
and runs the lot; `kit-boundary-reviewer` (agent) checks the invariants CI cannot.

## Key Files

- `kit/templates/hooks/lodestar-{guardrails,precommit-check,permissions}.py` — the agent,
  commit, and permission surfaces, in that order.

Skills load on demand and their triggers are already in context. Do not restate skill
content here, or anything the ownership list below assigns to another file.

## Code Style

- Hooks and scripts: **Python 3 stdlib only**, and each hook stays a single
  self-contained file — a user copies it into `.claude/hooks/` alone. The frontmatter
  parser is duplicated across the three hooks on purpose.
- Shell must pass `shellcheck --severity=error`.
- Adding capability means adding a catalog entry, not changing code.
- Template placeholders (`REPO`, `<WORKSPACE_NAME>`) are intentional — do not "fix" them.
- No unit-test framework: every gate is a shell script that builds a temp workspace.

## Environment

- `.env` is gitignored and loaded into the shell by `mise` (`mise.toml`). Never read,
  echo, or commit it. `GH_TOKEN` there is what `gh` authenticates with.
- `.mcp.json` provides the `github` MCP server; it reads `GITHUB_PERSONAL_ACCESS_TOKEN`.

## Workflow

- Never commit to `main` (protected, trunk-based). Branch `feat/*` or `fix/*`, then PR.
- Commit subject: **one line, no body, no trailers — no `Co-Authored-By`.** This
  overrides the default trailer behavior and matches the `commit-message-style` guardrail
  the kit ships. Reference the issue as `(#N)`.
- **Never edit `VERSION` or `CHANGELOG.md` in a feature PR.** Add one
  `changelog.d/<issue>-<slug>.md` fragment instead; `.github/scripts/release.py <version>`
  folds the fragments in and bumps both at release time.
- This repo dogfoods its own guardrails: one rule set in `.claude/guardrails/`, three
  surfaces. A blocked action is the product working — follow the redirect, and treat a
  false positive as a bug in the catalog entry. The three surfaces are **not**
  interchangeable; the PreToolUse engine cannot see a `Read` at all.
- Knowledge has one owner — point at it, never copy it: `README.md` what/why + quickstart ·
  `docs/ARCHITECTURE.md` design + decision log · `docs/CONCEPTS.md` mental models ·
  `docs/EXTENDING.md` how to extend · `kit/catalog/CATALOG.md` the index ·
  `docs/CI.md` gates + release · `CONTRIBUTING.md` dev setup.
