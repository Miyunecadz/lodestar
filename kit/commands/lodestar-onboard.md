---
description: Absorb a repository into the workspace — detect its stack, map its architecture (Graphify or Markdown), file its docs, and install the matching skills.
argument-hint: <path-to-repo> (e.g. ./backend)
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
effort: medium   # mostly mechanical, but the Markdown architecture fallback needs real synthesis
---

You are onboarding the repository at `$ARGUMENTS` into the Lodestar workspace. This command is **informational and non-destructive** — it adds knowledge, it does not enforce anything. Narrate each step.

## 1. Locate and identify the repo
- Resolve `$ARGUMENTS` to a directory; confirm it exists and contains `.git`. If not, stop and explain.
- Let `REPO` be its basename. Read `package.json`, `dbmate.yml`, and any obvious config.

## 2. Detect stacks
Classify the repo using these signals (collect ALL that match):

| Signal | Stack tag |
|---|---|
| `dbmate.yml` present | `node-dbmate` |
| `apollo-server-*` in deps | `graphql-apollo-server` |
| `@apollo/client` in deps | `graphql-apollo-client` |
| `@craco/craco` in deps | `react-craco` |
| `react-native` in deps | `react-native` |
| `.husky/` present | `has-husky` |
| eslint config or dep | `has-eslint` |
| `bull` / `ioredis` in deps | `redis-queue` |
| `artisan` present, or `laravel/framework` in `composer.json` | `laravel` |
| `composer.json` present | `php` |
| `laravel/pint` in deps or `pint.json` present | `has-pint` |
| `pest` / `pestphp/pest` in deps or `Pest.php` in `tests/` | `has-pest` |
| `next` in deps or a `next.config.*` file | `nextjs` |
| `manage.py` present | `python-django` |
| `requirements.txt` / `pyproject.toml` / `Pipfile` | `python` |
| `djangorestframework` in deps | `drf` |
| `pytest` dep or `pytest.ini` / `conftest.py` | `has-pytest` |
| `ruff` / `black` / `flake8` config or dep | `has-python-lint` |
| `.gitleaks.toml` / gitleaks or detect-secrets in pre-commit/deps | `has-gitleaks` |
| `.pre-commit-config.yaml` present | `has-precommit` |
| prettier config or dep | `has-prettier` |
| a UI framework present (`react`, `react-native`, `vue`, `svelte`, `@angular/core`) or a components/`.jsx`/`.tsx`/`.vue` tree | `has-frontend` |
| an auth library present (`jsonwebtoken`, `passport`, `next-auth`, `bcrypt`, `django.contrib.auth`, `djangorestframework-simplejwt`, `devise`, `omniauth`) | `has-auth` |

For a `nextjs` repo also note **which router** it uses — an `app/` directory (App Router) or `pages/` (Pages Router), or both mid-migration. Record it in the repo's `conventions.md`: the file conventions and data-fetching APIs differ, and an agent that guesses writes code that silently never runs.

Report the detected tags. Tags fall into two kinds: **stack tags** (the ecosystem — `python-django`, `react-native`) and **capability tags** (a tool is configured — `has-eslint`, `has-gitleaks`). Both feed the pickers identically; capability tags are how a rule adapts to "this repo already uses X." (Extend this table for new stacks/capabilities as needed — see `docs/EXTENDING.md`.)

## 3. Map the architecture (Graphify if installed, else Markdown)
The "Structure" layer gives the assistant a map to query instead of re-reading source. Produce it one of two ways — never fail this step, and never silently skip it.

- **If the `graphify` CLI is available:** run a **full** build, not an incremental one, so the baseline map is complete on day one:
  ```bash
  graphify extract <repo> --force              # full re-scan; add --code-only if no LLM backend is configured
  ```
  `--force` skips the incremental manifest gate and semantic cache, so nothing carries over from an earlier partial run. `graphify update` is the *incremental* path — right for the per-commit freshness hook (`/lodestar-freshness`), wrong for the initial baseline, which should not inherit state. Then move/copy the outputs (`graph.html`, `GRAPH_REPORT.md`, `graph.json`) into `docs/REPO/architecture/`.
- **Assert the graph is complete before trusting it** (see §3b). A map that silently omits real files misleads an agent exactly like a stale one, because `CLAUDE.md` tells agents to prefer the graph over re-reading source.
- **If Graphify is NOT installed:** do not assume. Ask the user (AskUserQuestion) how to proceed, with two options:
  1. **Install Graphify first, then re-run** *(richest, deterministic)* — Graphify installs entirely at **user level, no sudo**. Show the commands: `uv tool install graphifyy` (or `pipx install graphifyy`), then `graphify install`. Then **pause onboarding** — tell the user to re-run `/lodestar-onboard $ARGUMENTS` once installed, and stop at this step (still do nothing destructive). Do NOT proceed to later steps in this run.
  2. **Generate Markdown docs now** *(zero install, works anywhere)* — explore the repo (Glob/Grep/Read; dispatch the Explore agent if available) and write `docs/REPO/architecture/overview.md` by hand: entry points, a module/directory map, the key runtime flows, a mermaid diagram, and a "where to find X" table. This is what the `architecture-overview` skill consumes. It is **not** machine-queryable JSON like Graphify and can drift (re-generate to refresh), but it removes the install burden and needs no external tool.
- Optionally mention the deterministic middle ground for later: `ast-grep` (`npm i -g @ast-grep/cli`, no sudo) for structural queries across ~20 languages.

## 3b. Completeness check (graphify repos only)

Node counts are never compared against the source tree, so a partial map looks exactly like a complete one. Run the check and **show the user the numbers**:

```bash
python3 .lodestar/templates/hooks/lodestar-graph-coverage.py \
  --graph docs/REPO/architecture/graph.json --root ./REPO
```

It splits the difference four ways: **covered** (has nodes), **missing** (code graphify would scan, but no nodes → a real gap), **skipped** (excluded on purpose — noise dirs, `.graphifyignore`/`.gitignore`, generated lockfiles), and **stale** (graph references a file no longer on disk). Only `missing` is a defect; the split is what makes the number meaningful, since otherwise every `node_modules/` file reads as a gap.

- **Missing files reported** → rebuild once with `graphify extract <repo> --force` and re-check. If files are *still* missing, do not silently commit a partial map: tell the user which files have no nodes, and note that queries about them will come back empty so those parts need reading from source.
- The checker reports whether it used graphify's **own** classifier (authoritative) or its bundled fallback list (**approximate** — graphify not importable from this interpreter). Pass the distinction on rather than presenting an approximate number as exact.
- Never block onboarding on this. Report, record, continue.

Record which path was taken (graphify / markdown / deferred) so a later re-run is unambiguous. This becomes the repo's `architecture` in the manifest (step 6) and decides how `/lodestar-freshness` keeps the map current.

**Stamp a freshness fingerprint.** A map is only trustworthy while it matches the code, and `CLAUDE.md` tells agents to *trust* it — so record when it was built. After producing the map, capture the current commit and time:
- `lastMappedSha` = `git -C $ARGUMENTS rev-parse HEAD` (the commit the map corresponds to).
- `lastMappedAt` = current ISO-8601 UTC timestamp.

These go under the repo's `mapping` in the manifest (step 6) so drift is cheaply detectable later (`lastMappedSha..HEAD` for code under the repo). If the architecture step was **deferred** (Graphify not installed, user chose to re-run later), do not stamp a fingerprint — there is no map yet.

## 4. File repo docs — pre-fill from evidence, TODO only the unknowable
Create `docs/REPO/conventions.md` from `.lodestar/templates/docs/repo-conventions.md` (else a short stub). Then **actively fill it in from what you just read** — do not leave a field TODO when the repo already answers it.

**The rule for every doc you touch (per-repo *and* the shared docs below): two tiers.**
- **Derivable from the repo → fill it, with a cited basis.** Anything you can ground in a concrete source — `package.json`/`requirements`/`pyproject` (deps, scripts), config files, `.env.example` (variable *names*), routes/resolvers/serializers/models, `dbmate.yml`, the Graphify graph. Write the value and note where it came from (e.g. `Scheme: JWT — from djangorestframework-simplejwt`).
- **Not in the code, or a guess → leave `<!-- TODO: human — ... -->`.** Runtime/tribal/risky facts: token TTLs & rotation, staging/prod URLs, secret-manager name, deprecation windows, the *business meaning* of a domain term, "why" decisions. **Never invent these** — a confidently-wrong doc is worse than an honest TODO.

Pre-fill `docs/REPO/conventions.md`: build/run/lint/test commands (from scripts), notable patterns and entry points (from the code/graph). Leave TODO only for judgment calls.

## 4b. Enrich the shared `_shared/` docs from this repo's evidence
As each repo is absorbed, replace the TODOs in `docs/_shared/*` that **this** repo now answers (same two-tier rule; never overwrite a human's filled-in value):
- **`api-contract.md`** — style/transport (apollo→GraphQL, DRF→REST), served-by/consumed-by (this repo's role), the concrete endpoints/resources/operations (from routes/resolvers/serializers or the graph).
- **`auth-model.md`** — scheme (from the auth dep: `jsonwebtoken`/`passport`/`simplejwt`/`django.contrib.auth`), where it's enforced (middleware / DRF permission classes / shield), where the client stores it (from the frontend deps). TODO the TTLs, rotation, recovery.
- **`env-matrix.md`** — the config mechanism this repo uses and the variable **names** from its `.env.example`; the dev endpoint. TODO the staging/prod URLs and secret store.
- **`local-setup.md`** — this repo's prereqs and real install/run/migrate commands (from scripts / `dbmate.yml` / requirements).
- **`glossary.md`** — candidate domain terms from model/type names; TODO their *meanings* (business semantics — do not guess).

Only fill the slice this repo substantiates; later `/lodestar-onboard` runs fill their own. Say which fields you filled and from what.

## 5. Install matching skills
For each stack-scoped skill in `.lodestar/catalog/skills/` whose `stacks` intersect the detected tags, copy it into `./.claude/skills/`. Parameterize any `REPO` placeholder in the skill body with the actual repo name and doc paths so its body points at `docs/REPO/…`.
- Typical mappings: `graphql-apollo-*` → `graphql-contract`, `backend-standards`; `react-craco` → `frontend-standards`; `react-native` → `mobile-standards`; `drf` → `drf-api-contract`, `django-backend-standards`.

## 5b. Enrich the API-contract spine (only if a matching stack is detected)
`docs/_shared/api-contract.md` was seeded generic at init. If — and only if — this repo's detected stacks include an API style with a richer stub, offer to replace that file's body with the matching stub, but **only when the file is still the untouched generic template** (never overwrite content a human has filled in):
- GraphQL (`graphql-apollo-server`/`graphql-apollo-client`) → seed from `.lodestar/templates/docs/_shared/graphql-contract.md`.
- REST/DRF (`drf`) → seed from `.lodestar/templates/docs/_shared/rest-api-contract.md`.
Keep the filename `api-contract.md` either way — the cross-links in the other shared docs point at it. If no API-style stack is detected, leave the generic stub as-is and say nothing about GraphQL/REST.

## 5c. Surface any catalog gap (don't bury it in the manifest)

If **no stack-scoped** skill, agent, or guardrail matched this repo's stacks, the repo got only the universal core. That is a real outcome the user should see, not a string in a JSON file — a detected-but-unwritten gap is invisible.

1. Record it in the manifest as `catalogGaps` (below), naming the unmatched stack tags.
2. **Generate `docs/EXTENDING.md` in the workspace** from `.lodestar/templates/docs/extending-gap.md`, filling in the unmatched stacks, the repo they came from, and today's date. If the file already exists, append a new section for this repo rather than overwriting — several repos can each contribute a gap. This is the workspace's own "here's what's missing and how to add it" doc; it points at the kit's contributor guide for the mechanics.
3. **Say it in the report** (§7): which stacks had no pack, what the repo got instead (universal core only), and that `docs/EXTENDING.md` now describes how to add one.

Do not invent catalog entries to fill the gap on the spot — an ad-hoc agent written into a workspace is unversioned and unshared. Authoring a catalog entry is the supported path.

## 6. Update the map and manifest
- Append the repo + its detected stacks to `docs/repo-map.md`.
- Add to `.claude/lodestar.manifest.json` under `repos`:
  ```json
  {
    "name": "REPO",
    "path": "$ARGUMENTS",
    "stacks": [ ... ],
    "architecture": "graphify|markdown|deferred",
    "docs": "docs/REPO/",
    "mapping": {
      "lastMappedSha": "<HEAD sha>",
      "lastMappedAt": "<ISO-8601 UTC>",
      "build": "full",
      "coverage": {
        "filesTotal": 0, "filesCovered": 0, "filesMissing": 0,
        "filesSkipped": 0, "filesStale": 0, "mode": "graphify|fallback"
      }
    }
  }
  ```
  When §5c found a gap, also set `catalogGaps` on the repo entry:
  ```json
  "catalogGaps": { "unmatchedStacks": ["laravel", "nextjs"], "doc": "docs/EXTENDING.md" }
  ```
  Include `mapping` only when a map was actually produced (omit it for a **deferred** architecture). `coverage` comes from §3b (graphify repos only) — recording it makes incompleteness as visible as drift, and lets a later run see whether coverage regressed. `build: full` records that the baseline was a full extraction. Merge any newly installed skills into `skills`.

## 7. Report
Summarize: stacks detected (naming any with **no catalog pack**, per §5c), graph status **including coverage** (`N/M code files covered`, and the count of any missing files — say plainly if the graph is incomplete and which files an agent therefore cannot see), docs created, skills installed. Remind the user that enforcement (`/lodestar-guardrails`), delegation (`/lodestar-agents`), and **map freshness** (`/lodestar-freshness` — keeps the architecture map in sync with the code so a stale graph never misleads an agent) are separate opt-in commands they can now run, since the stacks and architecture are known.
