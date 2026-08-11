Two `kit/commands/` specs had drifted from what the code they generate for actually reads —
the class of silent failure #25 exists to catch, found while analysing it rather than by any
gate. Neither closes #25: nothing yet verifies the specs, and the same two drifts could
reappear on the next edit.

`/lodestar-guardrails` §5 enumerates the frontmatter fields to copy from a catalog entry into
an installed rule, and `requires_manifest_missing` was not among them. The engine reads it
(`kit/templates/hooks/lodestar-guardrails.py:482`) and one shipped rule sets it
(`design-guidance-on-ui-edits`), so a rule installed per the spec as written lost its
*self-silencing*: `design-guidance-on-ui-edits` would keep flagging every UI edit even after
the workspace recorded `designGuidance.installed: true`, which is precisely the outcome
`/lodestar-agents` §5b warns about. `.github/scripts/test-catalog.py:95` already copied the
field — its comment claimed to list "exactly the fields §5 copies", so the gate exercised a
corrected picker and could not see the omission. That comment is now true.

`/lodestar-init` §6 hardcoded `"version": "0.4.0"` in the manifest it writes. `VERSION` is
`0.20.0`. Every workspace initialised since v0.5.0 recorded a version that corresponds to
nothing, defeating the one thing the field is for. This is issue #27's second acceptance
criterion; the rest of #27 — the JSON schema, the `validate.py` check that would have caught
the literal, the key-ownership table — is untouched and still open.

### Fixed
- `kit/commands/lodestar-guardrails.md` §5 copies `requires_manifest_missing` along with the
  other context and surface fields, and says what dropping it costs — a rule that nags
  forever rather than one that fires everywhere.
- `kit/commands/lodestar-init.md` §6 reads `.lodestar/VERSION` (what `install.sh` recorded)
  instead of a literal, falling back to `"unknown"` and saying so if the file is absent.
