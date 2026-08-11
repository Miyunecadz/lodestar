---
name: validation-scope
description: Derive the minimum set of CI gates a change can actually break, from the paths it touched. Apply before running gates locally, before handing work to review or opening a PR, and whenever the alternative is running the whole suite for a one-file edit.
user-invocable: false
---

# Validation scope

`.github/workflows/ci.yml` is the authoritative gate list. This skill does not restate it —
it decides **which of its gates a given diff can break**, so a docs edit does not pay for
the whole suite of temp-workspace smoke tests.

The table is derived from each script's own path constants, not from prose. If it looks
stale, re-derive it from the scripts and fix the table; never trust it over the files.

## Procedure

1. Get the changed paths — `git diff --name-only main...HEAD`, `--cached`, or
   `git status --short`. Paths, not recollection.
2. Union the gates every changed path triggers.
3. Run them from the repo root, in the order `ci.yml` declares. Keep going after a failure.
4. **Any changed path matching no row → run the full suite**, and say why. An unmapped path
   means this table is behind the repo, and the safe reading of unknown is "everything".

## Path → gate

| Changed path | Gates it can break |
|---|---|
| any `*.sh`, anywhere in the repo | `shellcheck` |
| `install.sh` | `shellcheck`, `test-install.sh` |
| `kit/catalog/**` | `validate.py` |
| `kit/catalog/guardrails/**`, `.github/fixtures/guardrails.tsv` | `validate.py`, `test-catalog.py` |
| any `kit/templates/hooks/*.py` | `test-engine.sh` — see **hook-wide** below |
| `kit/templates/hooks/lodestar-guardrails.py` | `test-engine.sh`, `test-catalog.py`, `test-hook-parity.py`, **floor** |
| `kit/templates/hooks/lodestar-precommit-check.py` | `test-precommit.sh`, `test-hook-parity.py`, `test-engine.sh`, **floor** |
| `kit/templates/hooks/lodestar-permissions.py` | `test-permissions.sh`, `test-hook-parity.py`, `test-engine.sh` |
| `kit/templates/hooks/lodestar-rule-check.py` | `test-rule-check.sh`, `test-hook-parity.py`, `test-engine.sh`, `validate.py` — it gates the checker's `COMPARED` list |
| `kit/templates/hooks/lodestar-graph-coverage.py` | `test-coverage.sh`, `test-engine.sh` |
| `kit/templates/hooks/lodestar-freshness-check.py` | `test-freshness.sh`, `test-engine.sh` |
| `kit/templates/hooks/lodestar-graph-refresh.sh` | `shellcheck`, `test-graph-refresh.sh` |
| `VERSION`, `CHANGELOG.md`, `changelog.d/**` | `validate.py`; `VERSION` also `test-install.sh` |
| adding/renaming/deleting anything under `kit/` | `test-install.sh` (it asserts the installed layout) |
| `.github/scripts/test-*.sh`, `.github/scripts/test-*.py`, `validate.py` | the gate that script *is*, plus `shellcheck` if it is a `*.sh` |
| `.github/scripts/test-catalog.py` | `test-catalog.py`, plus `test-rule-check.sh` (it installs rules through this file's transform) and `validate.py` (it gates this file's `COPIED` list) |
| `kit/commands/lodestar-guardrails.md` | `validate.py` — it checks §5 names every field the hooks read |
| `.github/scripts/release.py` | **no gate runs it** — see below |
| `.github/workflows/ci.yml` | the full suite — the gate list itself changed |

**hook-wide** = `test-engine.sh` is not only the engine's own suite. It globs
`kit/templates/hooks/*.py` and `ast.parse`s every one at the `MIN_PYTHON` floor, so a syntax
error, or syntax above the floor, in *any* shipped hook fails it. That is why every hook row
above carries it, not just the engine's. It also `py_compile`s `lodestar-guardrails.py`
specifically.

**floor** = also run the gate under the declared Python floor, because a floor break makes
every rule silently inert rather than failing:

```bash
LODESTAR_TEST_PYTHON="$(uv python find 3.8)" bash .github/scripts/test-engine.sh
LODESTAR_TEST_PYTHON="$(uv python find 3.8)" bash .github/scripts/test-precommit.sh
```

`MIN_PYTHON` in the hooks is the source of truth for which version that is, and `ci.yml`'s
`python-floor` job is the source of truth for which suites run there: those two only.

Know what that leaves uncovered rather than assuming the floor is fully guarded.
`test-engine.sh`'s glob catches floor-breaking **syntax** in every hook, but a construct that
*parses* at the floor and fails at runtime — the dict-union operator is the known case — is
only caught by executing the hook under the floor interpreter. CI does that for the engine and
the pre-commit checker. It does not for `lodestar-permissions.py`,
`lodestar-graph-coverage.py`, or `lodestar-freshness-check.py`. A version-sensitive change in
those three is a reading job, and saying so is more useful than pretending a gate covers it.

**`release.py`** is not a gate and no CI step executes it. `validate.py` checks the
`VERSION` / `CHANGELOG.md` / `changelog.d` *state* that `release.py` is supposed to produce —
which means a bug in `release.py` surfaces when a release is cut, not on the PR that
introduced it. Validate a change to it by reading, and by running it against a throwaway copy
of the repo; do not record `validate.py` as covering it.

## Paths no gate covers

`docs/**`, `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `examples/**`, `.gitignore`,
`kit/templates/docs/**`, `kit/templates/CLAUDE.md`, `kit/commands/**` *content*, `LICENSE`,
`mise.toml`, `.github/rulesets/*.json`, `.github/scripts/release.py`, and all of
`.claude/**`. Nothing
executes them, so "gates pass" says nothing about whether they are right — validate these
by reading, and by `kit-boundary-reviewer` for the structural invariants.

**The `*.sh` row wins over this list.** CI shellchecks
`find . -name '*.sh' -not -path './.git/*'` — every shell script in the repo, including one
living inside a tree named above (`.github/rulesets/apply.sh` is the standing example). This
list means *no gate exercises the file's behaviour*; it never means a `*.sh` here escapes
`shellcheck`. Read a row as: the union of every row a path matches, and only then check
whether what remains is ungated.

Two exceptions carved out of that list, both narrow:

- `kit/commands/lodestar-guardrails.md` §5 — `validate.py` now checks that the section names
  every frontmatter field the hooks read, because a field it omits is a field the picker
  drops. The rest of that spec, and every other command spec, is still ungated.
- `.claude/guardrails/**` — `test-rule-check.sh` compares this repo's installed rules
  against `kit/catalog/guardrails/`, so dogfooding a rule the repo does not ship now fails
  CI. Nothing else in `.claude/**` is gated.

One that still bites:

- `kit/commands/**` — a spec's paths are only wrong once installed. No gate catches it, and
  the §5 field check above is one line of one spec, not coverage of the specs.

## Running them

Hand the derived list to the `gate-runner` agent rather than running gates inline: they
build temp workspaces, are slow, and produce long output that does not belong in the
caller's context. Pass the exact list — with no list it runs everything.
