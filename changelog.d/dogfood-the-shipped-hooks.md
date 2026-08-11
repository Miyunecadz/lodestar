The repo claimed to dogfood its own guardrail engine, and had stopped. `.claude/hooks/`
held copies of the three shipped surface hooks, no gate compared them to the originals,
and they had fallen two releases behind: the dev copy of the engine had neither
`redirect_of` (0.20.0) nor `MIN_PYTHON` (0.19.0). Every rule change since was being
exercised against a version the project does not ship.

The fix is to delete the copies rather than re-sync them. `.claude/settings.json` now runs
`kit/templates/hooks/lodestar-guardrails.py` in place, and the clone-time pre-commit wiring
copies from the same folder — the hooks resolve their rule set from `CLAUDE_PROJECT_DIR`,
so nothing about their behaviour depends on sitting in `.claude/hooks/`. Drift becomes
impossible instead of merely detected.

The dogfooded rules had drifted too, in the same silent direction: `.claude/guardrails/`
predated the `---` redirect separator, so this repo's own block messages still shipped the
entire rule body — the behaviour 0.20.0 changed. Re-deriving them from the catalog through
the picker's transform surfaced a second gap: `test-catalog.py`'s `COPIED` list, documented
as "exactly the fields the picker copies," was missing `permission_rules`. Nothing caught
it because that harness never exercises the permission surface — but the list is the
harness's claim about the product, and it was wrong.

`CLAUDE.md` had drifted the same way, in the direction that matters more: it still told
contributors to bump `VERSION` and `CHANGELOG.md` together, which 0.20.0 replaced with
`changelog.d/` fragments. It also carried a hand-maintained gate list whose shellcheck line
was the exact stale invocation CI abandoned for `find`, and restated, at session-global
cost, most of what the two on-demand skills already own.

### Fixed
- `.claude/settings.json`, `CONTRIBUTING.md`, `.claude/README.md` point at
  `kit/templates/hooks/`; the three drifted copies under `.claude/hooks/` are removed.
- `CLAUDE.md`: the `VERSION`/`CHANGELOG` instruction now says to add a `changelog.d/`
  fragment, matching `CONTRIBUTING.md` and `docs/CI.md`.
- `docs/CI.md`: the "Helper scripts live in `.github/scripts/`" paragraph appeared twice,
  each copy describing a different subset of the gates; merged into one.
- `.claude/guardrails/*.md` re-derived from `kit/catalog/guardrails/` through the picker's
  transform, so the dogfooded rules carry the redirect separator the product ships.
- `test-catalog.py`: `permission_rules` added to `COPIED`.

### Changed
- `CLAUDE.md` drops the per-gate command table and the guardrail/hook detail owned by
  `catalog-entry-authoring` and `hook-engine-invariants`, and gains a sources-of-truth
  table naming the file that answers each question. Roughly 45% smaller, and no longer
  restates what loads on demand.
- `.claude/settings.json` allow-lists the gates added since it was written
  (`test-hook-parity.py`, `test-catalog.py`, `test-graph-refresh.sh`) so a full local gate
  run no longer prompts partway through.
- `CONTRIBUTING.md` no longer hardcodes a gate count.

### Added
- `.claude/skills/github-issue-necessity-analysis` — a dev-only skill that treats an issue
  as a claim to verify against the code rather than an instruction to implement, and
  returns a verdict with `path:line` evidence. Dev tooling, not catalog: `install.sh`
  copies only from `kit/`, so it ships to nobody.
