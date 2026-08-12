The drift checker landed in #69 with three states where a genuinely stale installed rule
still reported clean, each reproduced before being fixed. Closes #70.

Two of them are the same mistake: **failing to find the catalog source was treated as
"nothing to find."** The lookup keys on the installed rule's `name:`, and a miss filed the
rule as locally authored — excluded from `--check` by design, because a rule you wrote
yourself is not drift. But a miss has three other causes. The `name:` was edited while the
file remains the picker's copy of a catalog entry; the entry was retired or renamed while
the copy kept enforcing; or the entry is right there and unparseable, so there is nothing
to compare against. All three read as `local`, and a rule withdrawn *because it was wrong*
kept enforcing with the report saying the workspace was in sync.

The third is `validate.py`'s copied-field gate, which derives the field list by scanning
hook source for `.get(` and nothing else. Subscript is live local style — the engine reads
`rule["pattern"]` — so a new flag read that way was invisible to the scan, and `COPIED`,
`COMPARED`, and `/lodestar-guardrails` §5 could all omit it with no gate objecting. That is
the `requires_manifest_missing` failure (PR #64) arriving through a second door.

### Fixed
- `lodestar-rule-check.py` resolves the catalog source by `name:` and then by filename, and
  separates the outcomes that used to collapse into `local`: **`renamed`** (compared against
  the entry the filename names, since that is the copy it is), **`retired`** (no entry of
  that name, and the manifest records the id as adopted), and **`catalog-unreadable`** (the
  source is present and this parser cannot read it). All three fail `--check`; each says what
  happened and what to do about it. Renaming the file too is the documented way to keep a rule
  as your own.
- `validate.py`'s `hook_read_fields()` scans both access forms. `test-rule-check.sh` now
  mutates a *copy* of the tree to add a field read each way and asserts both fail, naming the
  same three sites — the `.get` case included, so the original door stays shut as well.

### Changed
- An adopted `emits: settings-hook` entry (the three autolint routers) is now **named in the
  report as not compared**, and counted apart from the installed rules. It installs into
  `.claude/settings.json` as shell logic rather than as a rule file, so there is nothing to
  compare field-by-field — but omitting it silently made a clean report look like it covered
  rules it had never examined. It does not fail `--check`: absence of evidence is not evidence
  of drift, and a report people learn to ignore protects nobody.
- `local` still passes, and still passes for exactly the same inputs as before whenever the
  manifest cannot say what was adopted. Telling "never adopted" from "adopted, and the entry
  is gone" is the only thing the manifest is read for, and with no manifest the benign reading
  is taken.
- `docs/EXTENDING.md` and `test-catalog.py` no longer say a settings-hook entry's pattern
  becomes the emitted hook's `matcher`. A hook matcher selects on tool name; the pattern lands
  inside the hook's shell logic, where nothing pins its shape — which is the reason the
  checker reports those entries instead of comparing them.
- `hook-engine-invariants` states the naming requirement the copied-field gate rests on: the
  frontmatter dict is `rule` or `fm`, because a read through any other name is invisible to
  the scan and re-opens the same hole.
