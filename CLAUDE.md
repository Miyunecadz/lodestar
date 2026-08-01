# Lodestar

An AI-native workspace kit for Claude Code. Ships a **kit** that `install.sh` copies into
a user's multi-repo workspace. The product source is Markdown, not code.

## Commands

| Command | Description |
|---|---|
| `shellcheck --severity=error install.sh .github/scripts/test-*.sh` | shell lint |
| `python3 .github/scripts/validate.py` | catalog frontmatter, CATALOG.md index/totals, VERSION↔CHANGELOG |
| `bash .github/scripts/test-engine.sh` | guardrail engine, agent surface |
| `bash .github/scripts/test-install.sh` | installer: clone, bootstrap, pinning, refusals |
| `bash .github/scripts/test-precommit.sh` | commit surface, staged-diff enforcement |
| `bash .github/scripts/test-coverage.sh` | graph completeness: on-disk code vs graph nodes |
| `bash .github/scripts/test-freshness.sh` | map drift, in both workspace layouts |
| `bash .github/scripts/test-permissions.sh` | permission surface: idempotent, reversible deny merge |
| `./install.sh /tmp/lodestar-scratch` | install into a scratch workspace to exercise the commands |

**`.github/workflows/ci.yml` is the authoritative gate list** — run every gate it names
rather than a memorized count (the count has grown twice). Run them all before pushing.

## Architecture

```
kit/                  THE PRODUCT — everything install.sh distributes
  catalog/            guardrails/ agents/ skills/ — stack-tagged Markdown entries
  templates/          CLAUDE.md router, docs/_shared stubs, hooks/*.py, mcp/, git/
  commands/           lodestar-*.md slash-command specs
.claude/              THIS REPO'S dev tooling — never shipped
docs/ examples/       human docs
.github/              CI gates + release pipeline
install.sh VERSION CHANGELOG.md
```

`install.sh` copies **only** from `kit/`. In a target workspace the kit lands at
`.lodestar/catalog|templates` and `.claude/commands` — a command spec must reference
those paths, never this repo's `kit/…`.

## Key Files

- `.github/scripts/validate.py` — the catalog contract in executable form. Read it before
  adding or renaming a frontmatter field.
- `kit/templates/hooks/lodestar-guardrails.py` — agent surface (PreToolUse).
- `kit/templates/hooks/lodestar-precommit-check.py` — commit surface (pre-commit).
- `kit/templates/hooks/lodestar-permissions.py` — permission surface (merges
  `permissions.deny` into `settings.json`; idempotent and reversible).
- `docs/EXTENDING.md` — context flags, surface semantics, engine invariants.
- `kit/catalog/CATALOG.md` — the index; every entry must appear here.

## Code Style

- Hooks and scripts: **Python 3 stdlib only** — no packages, no plugin dependency.
- Each hook stays a **single self-contained file** a user can copy into `.claude/hooks/`
  alone. The frontmatter parser is duplicated across the three hooks on purpose.
- Shell must pass `shellcheck --severity=error`.
- Adding capability means adding a catalog entry, not changing code.
- Template placeholders (`REPO`, `<WORKSPACE_NAME>`) are intentional — do not "fix" them.

## Environment

- `.env` is gitignored and loaded into the shell by `mise` (`mise.toml`). Never read,
  echo, or commit it. `GH_TOKEN` there is what `gh` authenticates with.
- `.mcp.json` provides the `github` MCP server; it reads `GITHUB_PERSONAL_ACCESS_TOKEN`.

## Testing

- No unit-test framework. Every gate is a shell script that builds a temp workspace and
  asserts on the result.
- A new guardrail or engine flag needs a case in the script for each surface it touches:
  `test-engine.sh` (agent), `test-precommit.sh` (commit), `test-permissions.sh` (permission).
- The `lodestar-*` commands are **not live** in this repo — the specs live in
  `kit/commands/`, not `.claude/commands/`. Test them end to end:
  `./install.sh /tmp/lodestar-scratch && cd /tmp/lodestar-scratch && claude`

## Gotchas

- **Adding a catalog entry has four obligations**, all enforced by `validate.py`: the
  entry file with required frontmatter; the id listed in `CATALOG.md` **in backticks**;
  the `Totals: **N entries**` line updated; and `docs/EXTENDING.md` updated for any new
  flag, surface, or stack detector.
- Guardrail frontmatter enums: `severity: block|warn`, `event: file|bash|all`,
  `emits: rule|settings-hook`, `surface: agent|commit|both`; `pattern` must compile.
  `surface: commit|both` also needs `commit_check: staged-paths|secret-scan|default-branch`
  or `event: file`.
- **One rule set, three enforcement surfaces**, and they are not interchangeable. The
  PreToolUse engine is registered for `Bash|Edit|Write|MultiEdit`, so it cannot see a
  `Read` at all — "never read this" is only true on the `permission` surface. A rule body
  promising more than its surfaces deliver is documenting intent, not enforcing it.
- **Engine invariants — violating these breaks every tool call in a user's workspace:**
  never raise, and fail protective (no git, no manifest, unparseable command → behave as
  a plain pattern match; never silently drop a safety rule).
- The pre-commit checker exits 1 **only** on a `block` match. Missing tool, bad regex,
  unreadable manifest, internal error → exit 0. It must never break an unrelated commit.
- `lodestar-permissions.py` must stay idempotent and reversible: re-running never
  duplicates, never disturbs hand-written entries, and unticking a rule removes exactly
  the entries that rule contributed. Ownership lives in the manifest under
  `guardrailSurfaces.permission.entries`.
- `VERSION` and the top `## [x.y.z]` entry in `CHANGELOG.md` must be bumped together; a
  bump landing on `main` cuts a release.
- Frontmatter parsing is scalars and inline lists only — a regex containing a comma
  cannot go in a list value.
- Choosing a surface is a judgement about **false positives**, not about how much the
  rule matters. `protect-generated-files`, `no-hand-edit-lockfiles`,
  `protect-dbmate-schema`, and `commit-message-style` are deliberately `agent`-only —
  the reasons are in `docs/EXTENDING.md`.

## Workflow

- Never commit to `main` (protected, trunk-based). Branch `feat/*` or `fix/*`, then PR.
- Commit subject: **one line, no body, no trailers — no `Co-Authored-By`.** This
  overrides the default trailer behavior and matches the `commit-message-style` guardrail
  the kit ships. Reference the issue as `(#N)`.
- This repo dogfoods its own guardrails. One rule set in `.claude/guardrails/`, three
  surfaces live: the PreToolUse engine (`lodestar-guardrails.py`), the pre-commit checker
  (`lodestar-precommit-check.py`, wired at `.git/hooks/pre-commit`), and `permissions.deny`
  (merged by `lodestar-permissions.py`). A blocked action is the product working — follow
  the redirect, and treat a false positive as a bug in the catalog entry.
- **`.git/hooks` is not tracked**, so a fresh clone has no commit surface until someone
  copies `.claude/hooks/lodestar-precommit-check.py` into `.git/hooks/pre-commit`.
  `git commit --no-verify` bypasses it deliberately; server-side branch protection
  (`docs/CI.md`) is the only trunk guard nobody can skip.
- Knowledge has one owner — point at it, never copy it: `README.md` what/why + quickstart ·
  `docs/ARCHITECTURE.md` design + decision log · `docs/CONCEPTS.md` mental models ·
  `docs/EXTENDING.md` how to extend · `kit/catalog/CATALOG.md` the index ·
  `docs/CI.md` gates + release.
