Guardrails get eight frontmatter checks, a regex compile, and — since #26 — behaviour
fixtures executed against the real engine. Skills got two presence checks: `name` and
`description`, both merely present. That was the entire verification of half the catalog,
and it is the half whose failure is silent. A guardrail that stops matching eventually gets
noticed; a skill that never loads is indistinguishable from a task that needed no skill —
no error, no log, no output. Closes #59.

Three properties were unchecked and load-bearing. The `description` **is** the routing
decision (`docs/CONCEPTS.md` §1: the model reads an index of triggers and pulls the body
only when one matches), so a description written as a summary is a skill that never fires.
`stacks` values were required to be *present* on guardrails and agents and never checked for
*existence* — a typo like `react-nativ` installs cleanly and matches nothing. And six of the
ten shipped skills carry a `REPO` placeholder five or six times each, substituted by
`/lodestar-onboard` §5 with the repo basename; nothing exercised that substitution, so an
install that skipped it would send the model to `docs/REPO/conventions.md` and the model
would read nothing and proceed on general knowledge.

That last one was not hypothetical. Installing the real skills into a throwaway workspace
built from `kit/templates/` immediately failed on `planning-workflow`, which pointed the
model at `docs/CONCEPTS.md` §3 — a Lodestar repo doc that `install.sh` never copies, so no
workspace has ever had it.

The stack vocabulary is *derived* from `/lodestar-onboard` §2's detection table rather than
declared a second time. `docs/EXTENDING.md` already makes adding the detector step one and
tagging entries step two, so that table is the vocabulary; a hand-maintained list beside it
would be a rival source of truth with nothing keeping the two in step. Verifying the
command's own behaviour remains #25's scope — this only reads the table.

### Added
- `.github/scripts/test-skill-install.py` — installs every real `kit/catalog/skills/*/SKILL.md`
  into a throwaway workspace, applies the `/lodestar-onboard` §5 `REPO` substitution, and
  asserts no placeholder survives and every `docs/…` path an installed skill names exists in
  a workspace built from the shipped templates. Wired into `ci.yml`. It also asserts the
  substitution is not vacuous, so the check cannot pass by having nothing to replace, and
  carries a literal unsubstituted fixture the detector must fire on — picking a real skill
  *because* the detector matched it cannot then witness that the detector works.
- `validate.py`: `check_skill_triggers()` reports two skills whose descriptions are ≥80%
  alike and that share a `stacks` tag (or where one is `stacks: [all]`). That is knowingly
  narrower than "could co-load", since a repo matches several tags at once and §5 copies
  every match into one `.claude/skills/`; widening it would flag the per-stack conventions
  family, which is correctly similar by design. The docstring says so rather than implying
  the check is exhaustive.
- `validate.py`: `check_stack_vocabulary()` checks `stacks` values for guardrails, agents,
  and skills alike against the tags `/lodestar-onboard` §2 can actually detect. A stale
  parser reports itself rather than failing all 50 entries against an empty vocabulary.
- `docs/EXTENDING.md` gains "Writing a trigger that fires" and "The `REPO` substitution"
  under "Add a skill" — the four mechanical properties, why each is checked rather than
  reviewed, and what the trigger-similarity check deliberately does not cover. "Add a stack
  detector" now shows the §2 signal as a literal table row, because that row shape is what
  the vocabulary is parsed from.
- `docs/CI.md` names `test-skill-install.py` alongside `test-catalog.py`, the gate it
  parallels. That paragraph enumerates every gate individually, so a new step missing from it
  leaves CI's documented owner stale the moment it merges. `docs/EXTENDING.md` points at it
  rather than describing it twice.

### Fixed
- `kit/catalog/skills/planning-workflow/SKILL.md` no longer points at `docs/CONCEPTS.md`,
  which does not exist in an installed workspace.

### Changed
- `validate.py`: `check_skills()` now requires `stacks`, requires the `description` to be a
  non-empty when-to-load trigger starting `Use when`, and holds the file to a 2000-byte
  budget — a skill is a router, not a knowledge base, and the shipped ten run 723–1593 bytes.
- `kit/catalog/skills/graphql-contract/SKILL.md`'s description names the GraphQL schema and
  the repos that query it, instead of "the shared API surface … that the repos depend on" —
  near-verbatim with `drf-api-contract`'s trigger. The two are scoped to different stacks so
  they rarely co-occur, but a trigger a reader cannot route between is the failure the new
  check exists to catch, and the catalog should not ship an example of it.
