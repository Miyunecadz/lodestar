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
| any `*.sh` | `shellcheck` |
| `install.sh` | `shellcheck`, `test-install.sh` |
| `kit/catalog/**` | `validate.py` |
| `kit/catalog/guardrails/**`, `.github/fixtures/guardrails.tsv` | `validate.py`, `test-catalog.py` |
| `kit/templates/hooks/lodestar-guardrails.py` | `test-engine.sh`, `test-catalog.py`, `test-hook-parity.py`, **floor** |
| `kit/templates/hooks/lodestar-precommit-check.py` | `test-precommit.sh`, `test-hook-parity.py`, **floor** |
| `kit/templates/hooks/lodestar-permissions.py` | `test-permissions.sh`, `test-hook-parity.py` |
| `kit/templates/hooks/lodestar-graph-coverage.py` | `test-coverage.sh` |
| `kit/templates/hooks/lodestar-freshness-check.py` | `test-freshness.sh` |
| `kit/templates/hooks/lodestar-graph-refresh.sh` | `shellcheck`, `test-graph-refresh.sh` |
| `VERSION`, `CHANGELOG.md`, `changelog.d/**` | `validate.py`; `VERSION` also `test-install.sh` |
| adding/renaming/deleting anything under `kit/` | `test-install.sh` (it asserts the installed layout) |
| `.github/scripts/**` | the gate that script *is*, plus `shellcheck` if it is a `*.sh` |
| `.github/workflows/ci.yml` | the full suite — the gate list itself changed |

**floor** = also run the gate under the declared Python floor, because a floor break makes
every rule silently inert rather than failing:

```bash
LODESTAR_TEST_PYTHON="$(uv python find 3.8)" bash .github/scripts/test-engine.sh
```

`MIN_PYTHON` in the hooks is the source of truth for which version that is.

## Paths no gate covers

`docs/**`, `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `examples/**`, `.gitignore`,
`kit/templates/docs/**`, `kit/templates/CLAUDE.md`, `kit/commands/**` *content*, `LICENSE`,
`mise.toml`, and all of `.claude/**`. Nothing
executes them, so "gates pass" says nothing about whether they are right — validate these
by reading, and by `kit-boundary-reviewer` for the structural invariants.

Two of these bite in particular:

- `kit/commands/**` — a spec's paths are only wrong once installed. No gate catches it.
- `.claude/guardrails/**` — installed copies of catalog entries. Drift from
  `kit/catalog/guardrails/` means this repo dogfoods something it does not ship, and no
  gate compares them.

## Running them

Hand the derived list to the `gate-runner` agent rather than running gates inline: they
build temp workspaces, are slow, and produce long output that does not belong in the
caller's context. Pass the exact list — with no list it runs everything.
