A self-silencing rule's off switch lives in another directory. `design-guidance-on-ui-edits`
declares `requires_manifest_missing: designGuidance.installed`, and the key it names is written
by `/lodestar-agents` §5b — a different file, in a different half of the kit, with nothing
tying the two. Rename either side alone and the rule changes character without an error
anywhere: a reminder with no off switch, which is the warn fatigue `docs/EXTENDING.md` warns
about, or silence about a gap that is still open. This is the shape of the drift PR #64 already
had to fix by hand once, one level down — a partial step on #27 and #25, and neither is closed:
the manifest still has no schema and nothing yet verifies a command spec end to end.

### Added
- `validate.py`: `check_manifest_flags()` requires every segment of a
  `requires_manifest_missing` dotted path to appear as a quoted JSON key in some
  `kit/commands/lodestar-*.md`, and rejects a flag that names no key at all. Segments are
  matched as JSON keys rather than as the dotted string on purpose — the dotted form also
  appears in prose *about* the rule, and prose is not what writes the manifest, so matching it
  would let a renamed JSON block pass.
