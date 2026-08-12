A self-silencing rule's off switch lives in another directory. `design-guidance-on-ui-edits`
declares `requires_manifest_missing: designGuidance.installed`, and the key it names is written
by `/lodestar-agents` §5b — a different file, in a different half of the kit, with nothing
tying the two. Rename either side alone and the rule changes character without an error
anywhere: a reminder with no off switch, which is the warn fatigue `docs/EXTENDING.md` warns
about, or silence about a gap that is still open. This is the shape of the drift PR #64 already
had to fix by hand once, one level down — a partial step on #27 and #25, and neither is closed:
the manifest still has no schema and nothing yet verifies a command spec end to end.

### Added
- `validate.py`: `check_manifest_flags()` requires a rule's `requires_manifest_missing` value
  to exist as a *path* among the things that write the manifest — the same nesting, in a
  fenced JSON block of some `kit/commands/lodestar-*.md`, or in a `kit/templates/hooks/*.py`
  assignment into the manifest dict. Both sides are read structurally, so two unrelated
  sibling keys never satisfy a two-segment flag, and prose *about* a rule never stands in for
  the JSON block that writes it. A flag naming no key at all is rejected.
