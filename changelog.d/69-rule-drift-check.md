`/lodestar-guardrails` copies a catalog entry into `.claude/guardrails/<id>.md` once. From
then on the two are unconnected: `install.sh` refreshes `.lodestar/catalog/` wholesale on
every update and never touches what you generated — the right default, and also the reason a
**corrected rule never reaches the file that enforces it**. `block-env-files`' pattern has
been fixed twice since it first shipped, once because `.env.local.example` was wrongly
treated as a live secret; a workspace that adopted the rule before those fixes is still
enforcing the old regex, and nothing said so. That release's own upgrading note told adopters
to re-run the picker "to tick the **new** entries" and never mentioned the installed copy.
Closes #69.

The second half is quieter. An installed rule is written by a model following
`/lodestar-guardrails` §5, so a field §5 forgets to name is a field the picker silently
drops — the rule then enforces without its scoping, or nags forever without its
self-silencing. That is not hypothetical: `requires_manifest_missing` was read by the engine
and set by a shipped rule while §5 did not name it (#27), and it was found by reading rather
than by any gate. `test-catalog.py` could not see it, because it copies the fields through
its own list and so only ever exercises a *corrected* picker.

Nothing here rewrites anything. A difference is not automatically a defect — installed rules
are meant to be edited, and `block-env-files` tells you to add your own env tiers to
`permission_rules` right in its body. Without provenance nothing can tell your edit from a
stale copy, so the checker names the difference and leaves the judgement to you. Adopting the
catalog version is re-running `/lodestar-guardrails` and re-ticking the rule.

### Added
- `kit/templates/hooks/lodestar-rule-check.py` — compares each installed rule against its
  catalog source and reports the fields that differ, with `--check`, `--json`, `--rule`,
  `--workspace`, `--catalog`, and `--verbose`. Statuses are `ok` / `drifted` / `local` /
  `unreadable`; an installed rule the parser cannot read is reported rather than skipped,
  because the *engine* cannot read it either, so it is silently enforcing nothing. List-valued
  fields are compared order-insensitively — each is a membership test wherever a hook reads
  it — and `surface: both` is expanded before comparison, so a rule rewritten from the legacy
  spelling to `[agent, commit]` is not reported as a behaviour change. Unlike the three
  registered hooks it exits **1** under `--check` on an internal error: it is a CLI someone
  ran deliberately, and exiting 0 after a crash would report "nothing wrong" about a check
  that never ran.
- `validate.py`: `check_copied_fields()` derives the set of frontmatter fields the shipped
  hooks actually read from their own source, then requires equality against
  `test-catalog.py`'s `COPIED` and the new checker's `COMPARED`, and membership in
  `/lodestar-guardrails` §5. Both directions — a field a hook reads but a list omits, and a
  field a list carries that no hook reads. Deriving rather than declaring is the point: a
  hand-kept list here would be a fourth rival copy of the thing the check exists to keep in
  step. A scan that finds implausibly few fields reports itself stale instead of validating
  every site against an empty set and passing.
- `.github/scripts/test-rule-check.sh`, wired into `ci.yml`. It builds its workspace from the
  real catalog with rules installed through `test-catalog.py`'s own `install_rule` — imported,
  not re-implemented, so the gate cannot agree with a private copy of the field list. It
  reverts `block-env-files`' pattern to a superseded version and asserts the field and both
  values are named, that `--check` exits 1, and that the file is left byte-identical. It also
  runs the checker against **this repo's** `.claude/guardrails`, closing a dogfooding hole
  `validation-scope` had documented as uncovered: the repo could ship one rule and enforce
  another on itself.

### Changed
- `/lodestar-update` reports the rules the workspace already adopted whose catalog source has
  since changed, not only the entries it has never adopted. It runs the shipped checker and
  relays the output verbatim — which field moved is the whole content of the report — and is
  explicitly forbidden from editing an installed rule to "fix" the drift.
- `test-hook-parity.py`'s `FILES` gains the new hook, so its duplicated frontmatter helpers
  are compared against the other three. Five documentation sites that stated a hook *count*
  now point at that list instead, which is what stops the next copy drifting unwatched.
- `docs/CI.md`, `CONTRIBUTING.md`, and `.claude/skills/validation-scope` describe the new
  gate and no longer claim `.claude/guardrails/**` is ungated. `hook-engine-invariants` gains
  the unregistered-hook carve-out for invariant 1, and a clause naming the three sites a new
  frontmatter flag has to reach before it is done.
