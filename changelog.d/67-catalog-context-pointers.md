Five catalog entries told the model to acquire context the workspace never contains, or to
perform work its declared `tools` cannot perform. The instructions read correctly; they
pointed at the wrong artifact — which fails silently, because a prompt that names a
nonexistent file produces a confident answer built on nothing. Closes #67.

### Fixed
- `drf-endpoint-writer` read and wrote `docs/_shared/rest-api-contract.md`. That filename is
  a template seed only: `/lodestar-init` seeds the spine as `api-contract.md` and says
  explicitly not to copy the REST stub under its own name, so the agent was planning against
  a file that does not exist and writing a second, orphan contract beside the real one. Both
  occurrences now name `api-contract.md`, matching `resolver-writer` and
  `laravel-endpoint-writer`.
- `feature-orchestrator` was told to dispatch specialist roles in parallel and integrate
  their results, with a done-condition of "tasks dispatched, results integrated" — but its
  `tools` are `[Read, Grep, Glob, Bash]`, and no agent in the catalog has a delegation tool.
  An unsatisfiable done-condition marks a summary of work that never happened as success.
  It now produces an **execution order** (task, repo, role, parallel or waiting) and returns
  it for the main thread to run; the closing line states it has no delegation tool and must
  never report work as landed that it did not see land. `tools` unchanged — the job was
  wrong, not the profile.
- `architecture-overview` named only `graph.json`, though a repo's `architecture` mode may be
  `markdown` (producing `overview.md`) or `deferred` (producing no map). It now reads the mode
  from `.claude/lodestar.manifest.json` and branches on all three, and checks that repo's
  `mapping.coverage.filesMissing` before reading an empty graph answer as "no such code" —
  the coverage signal Lodestar has always computed and never delivered to a consumer.
  `feature-planner` now says "the repo's architecture map (`graph.json` or `overview.md`)"
  instead of naming the JSON alone.
- `reviewer` judged guardrail compliance from three remembered examples, missing every other
  installed rule including workspace-authored ones. It now enumerates `.claude/guardrails/*.md`
  for the rules actually installed and runs `lodestar-guardrails.py --explain --file <path>`
  (or `--bash '<cmd>'`) instead of recalling rules from memory. Same step count.

### Changed
- The three endpoint/resolver writers and the `planning-workflow` and `architecture-overview`
  skills now handle the state onboarding actually leaves the contract in: partly filled, with
  `<!-- TODO: human -->` markers. A stubbed section is unknown, not absent — say so and read
  the code; never infer the contract. The writers additionally fill the section from what they
  implement.
