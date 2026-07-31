# Extending this workspace's Lodestar catalog

Onboarding detected one or more stacks that **no catalog entry covers**. The affected repos work fine — they got Lodestar's universal core (the stack-neutral guardrails, agents, and skills) — but they did **not** get stack-aware help: no conventions skill for the framework, no framework-specific guardrails, no specialist agents.

This file exists so that gap is visible and actionable instead of buried in `.claude/lodestar.manifest.json`.

## Gaps detected

<!-- One section per repo. /lodestar-onboard appends here; keep older sections. -->

### REPO — unmatched stacks: `STACKS`

Detected on DATE.

**What this repo has:** the universal core only — `block-destructive-commands`, `block-env-files`, `block-secret-files`, the lockfile and generated-file guards, plus the universal agents (`implementer`, `reviewer`, `feature-planner`, …) and workspace skills.

**What it's missing:** anything that knows `STACKS` specifically — where routes live, how migrations work, which files are generated, what the test runner is.

## How to close a gap

Everything in Lodestar is a plain Markdown file, so adding a pack means adding files to the catalog — no code.

**Option A — contribute it upstream (preferred).** The pack then arrives for everyone on the next `/lodestar-update`, and stays maintained:

1. Clone the Lodestar repo and read [`docs/EXTENDING.md`](https://github.com/Miyunecadz/lodestar/blob/main/docs/EXTENDING.md) — it documents the frontmatter for each entry kind, the guardrail engine's context flags, and the enforcement surfaces.
2. Add a **stack detector** signal to `kit/commands/lodestar-onboard.md` §2 so the tag is produced at all.
3. Add entries under `kit/catalog/`:
   - `skills/<stack>-standards/SKILL.md` — the conventions skill. Keep it thin: point at `docs/REPO/`, don't restate the docs.
   - `guardrails/*.md` — what must not happen. Framework-generated paths, migrations that have already run, secrets that would ship to a client.
   - `agents/*.md` — narrow roles with a crisp done-condition (endpoint writer, migration writer, test writer).
4. Tag every entry with `stacks: [<your-tag>]` so it only activates where it applies.
5. Open a PR. The CI validator checks the frontmatter for you.

**Option B — keep it local.** Add the same files to this workspace's `.lodestar/catalog/`, then re-run `/lodestar-guardrails`, `/lodestar-agents`, and `/lodestar-onboard ./REPO`. Note the trade-off: `/lodestar-update` refreshes `.lodestar/catalog/` from the kit, so local-only entries there can be overwritten. Keep a copy outside the workspace, or upstream them.

## What not to do

Do not hand-write agents or guardrails straight into `.claude/`. They work, but they are unversioned, unshared, and invisible to `/lodestar-update` — the next person onboarding the same stack starts from scratch. The catalog is the shareable asset; that is the whole point of it.
