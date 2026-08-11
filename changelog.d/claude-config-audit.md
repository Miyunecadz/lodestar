An audit of the dev Claude config for duplication, one release after #60 cut `CLAUDE.md`
down to what it owns. Nothing was removed as a component — the setup is already lean at two
agents, three skills, and no dev commands, and each was verified load-bearing. The waste was
prose: nine sites restating knowledge another file already owned, which is the same failure
`CLAUDE.md`'s ownership list exists to prevent, committed by the config that states the rule.

The worst offender was `CLAUDE.md`'s own paragraph naming the three skills and their
triggers. Skill descriptions are injected into every session automatically, so that
paragraph bought nothing and was paid for on every turn.

One behavioural bug came out of it. `dev-validate-catalog.py` watched `kit/templates`,
which `validate.py` never reads — every hook edit spent a subprocess re-proving an
untouched result — while `.github/fixtures/` and `changelog.d/`, which it does read, went
unwatched. The watch list now mirrors the validator's actual inputs.

### Fixed
- `.claude/hooks/dev-validate-catalog.py`: `WATCHED` drops `kit/templates` and gains
  `.github/fixtures` and `changelog.d`, so the hook fires when the validator's verdict can
  actually change, and only then.

### Changed
- `CLAUDE.md` drops the skills paragraph (duplicating the auto-loaded skill index) and the
  `Key Files` entries for `validate.py`, `docs/EXTENDING.md`, `CONTRIBUTING.md`, and
  `CATALOG.md` — each already answered by the sources-of-truth table above them or the
  ownership list below them. The three hook lines collapse to one.
- `.claude/skills/github-issue-necessity-analysis` is 39% smaller. Its "Prohibited
  behaviours" list, "Failure handling" table, and pre-return checklist between them
  restated the skill's own phases three times over; every behavioural rule survives, and
  the `gh issue view` step now records that an empty result needs a `--json` retry.
- `.claude/README.md` is 47% smaller: the kit-boundary explanation and the hook-drift story
  were its third copies, after `CONTRIBUTING.md` and `settings.json`'s `$comment`. It keeps
  what only it says — that `guardrails/` is re-derived, not hand-edited, and that the
  manifest is owned by `lodestar-permissions.py`.
- `catalog-entry-authoring` points at `hook-engine-invariants` for the fail-protective and
  never-raise rules instead of restating them; both skills drop "run every gate `ci.yml`
  names," which the always-loaded sources-of-truth table owns.
