Rule authoring was blind. To find out what a rule would do to an input, an author had to
hand-build the PreToolUse payload and pipe it into the engine — the shape CI itself resorted to
(`.github/scripts/test-catalog.py:153`) — or install the rule and try to trigger it live, which is
impossible to do safely for a rule whose job is to block something destructive. So authors shipped
patterns they had not actually run, and `docs/CONCEPTS.md` §4 calls writing your own rules the
primary way to use the product.

The harder half of the problem is that **why a rule did *not* fire is invisible**. A pattern that
never matched and a match silenced by a context flag look identical from outside, and they need
opposite fixes. Nothing reported which flag went quiet.

### Added
- `lodestar-guardrails.py --explain` — a read-only mode answering "what would the installed rules
  do to this input", with no live session and nothing to trigger. `--bash '<command>'` or
  `--file <path>` (plus `--content` for a `match: content` rule), `--rule <name>` to narrow, `--json`
  for machine use. Per rule it prints the field tested, whether the pattern matched, every context
  probe consulted and what it answered, and the name of the flag that suppressed a match.
- `docs/EXTENDING.md` documents it as the recommended authoring loop, ahead of the fixtures step.

### Changed
- The decision loop moved into one `evaluate()` used by both the hook path and `--explain`, so the
  explanation cannot drift from the decision. `test-engine.sh` asserts the two agree on the same
  input, five ways, and that a no-argument invocation still decides exactly as before — the hook
  path is the only way Claude Code calls this file and had to stay untouched.
- `suppressed()` became `suppression_of()`, returning the *name* of the flag that silenced a match
  instead of a bare `True`. Truthiness is unchanged, so the enforcing path reads it as it did.
