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
  to be a path the engine could actually walk to in the manifest — one written by a
  `kit/commands/lodestar-*.md` manifest fence, or by a `kit/templates/hooks/*.py` assignment
  into the manifest dict. Both sides are read structurally, so a key under an array and two
  unrelated sibling keys are both rejected, and prose *about* a rule never stands in for the
  JSON that writes it. A flag naming no key at all is rejected.

### Changed
- Command specs mark the JSON blocks that write `.claude/lodestar.manifest.json` by opening
  the fence ` ```json manifest `. Their other blocks describe `settings.json`, `source.json`,
  or a repo entry inside `repos[]` — real keys, but not manifest paths, and a rule keyed on
  one would nag forever. Nothing in the JSON itself distinguishes them.
