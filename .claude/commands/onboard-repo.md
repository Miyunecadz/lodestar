---
description: Absorb a repository into the workspace — detect its stack, generate its architecture graph (Graphify), file its docs, and install the matching skills.
argument-hint: <path-to-repo> (e.g. ./backend)
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
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
| `manage.py` present | `python-django` |
| `requirements.txt` / `pyproject.toml` / `Pipfile` | `python` |
| `djangorestframework` in deps | `drf` |
| `pytest` dep or `pytest.ini` / `conftest.py` | `has-pytest` |
| `ruff` / `black` / `flake8` config or dep | `has-python-lint` |
| `.gitleaks.toml` / gitleaks or detect-secrets in pre-commit/deps | `has-gitleaks` |
| `.pre-commit-config.yaml` present | `has-precommit` |
| prettier config or dep | `has-prettier` |

Report the detected tags. Tags fall into two kinds: **stack tags** (the ecosystem — `python-django`, `react-native`) and **capability tags** (a tool is configured — `has-eslint`, `has-gitleaks`). Both feed the pickers identically; capability tags are how a rule adapts to "this repo already uses X." (Extend this table for new stacks/capabilities as needed — see `docs/EXTENDING.md`.)

## 3. Generate the architecture graph (Graphify)
- If the `graphify` CLI is available, run it against the repo and move/copy its outputs (`graph.html`, `GRAPH_REPORT.md`, `graph.json`) into `docs/REPO/architecture/`.
- If Graphify is **not** installed, create `docs/REPO/architecture/README.md` with a note and the exact install + run commands (`uv tool install graphifyy` or `pipx install`, then `graphify install`, then `graphify <repo-path>`). Do not fail — this step is optional.

## 4. File repo docs
- Create `docs/REPO/conventions.md` from `.lodestar/templates/docs/repo-conventions.md` if present, else a short stub with TODO markers (build/run commands, lint, test, notable patterns). Pre-fill anything you can read from `package.json` scripts.

## 5. Install matching skills
For each stack-scoped skill in `.lodestar/catalog/skills/` whose `stacks` intersect the detected tags, copy it into `./.claude/skills/`. Parameterize any `REPO` placeholder in the skill body with the actual repo name and doc paths so its body points at `docs/REPO/…`.
- Typical mappings: `graphql-apollo-*` → `graphql-contract`, `backend-standards`; `react-craco` → `frontend-standards`; `react-native` → `mobile-standards`; `drf` → `drf-api-contract`, `django-backend-standards`.

## 5b. Enrich the API-contract spine (only if a matching stack is detected)
`docs/_shared/api-contract.md` was seeded generic at init. If — and only if — this repo's detected stacks include an API style with a richer stub, offer to replace that file's body with the matching stub, but **only when the file is still the untouched generic template** (never overwrite content a human has filled in):
- GraphQL (`graphql-apollo-server`/`graphql-apollo-client`) → seed from `.lodestar/templates/docs/_shared/graphql-contract.md`.
- REST/DRF (`drf`) → seed from `.lodestar/templates/docs/_shared/rest-api-contract.md`.
Keep the filename `api-contract.md` either way — the cross-links in the other shared docs point at it. If no API-style stack is detected, leave the generic stub as-is and say nothing about GraphQL/REST.

## 6. Update the map and manifest
- Append the repo + its detected stacks to `docs/repo-map.md`.
- Add to `.claude/lodestar.manifest.json` under `repos`: `{ "name": "REPO", "path": "$ARGUMENTS", "stacks": [ ... ] }`. Merge any newly installed skills into `skills`.

## 7. Report
Summarize: stacks detected, graph status, docs created, skills installed. Remind the user that enforcement (`/guardrails`) and delegation (`/gen-agents`) are separate opt-in commands they can now run, since the stacks are known.
