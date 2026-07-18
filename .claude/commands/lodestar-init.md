---
description: Initialize Lodestar in the current workspace — create the thin root CLAUDE.md, docs/_shared skeleton, repo-map, and workspace-wide skills.
argument-hint: (run from the workspace root that contains your repos)
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion
effort: low   # mechanical: copy templates, fill the repo registry, write the manifest
---

You are initializing Lodestar in the current workspace. The workspace root is the current directory — it holds several sibling repositories. Lodestar's catalog and templates were installed under `.lodestar/`.

Do the following, narrating each step:

## 1. Sanity-check the workspace
- Confirm `.lodestar/catalog/` and `.lodestar/templates/` exist. If not, tell the user to run `install.sh <workspace>` first and stop.
- Detect repositories: list immediate subdirectories that contain a `.git` folder. Show the list. If none, warn and ask whether to continue.

## 2. Confirm placement (once per workspace)
The workspace root may not be a git repo. Ask the user (AskUserQuestion) how Lodestar files should be tracked:
- **Personal / untracked** (default) — leave the root as a plain folder.
- **Git workspace repo** — `git init` the root and add the detected repos to `.gitignore`.
Apply their choice. Record it in the manifest.

## 3. Create the thin root CLAUDE.md
- Copy `.lodestar/templates/CLAUDE.md` to `./CLAUDE.md` (do NOT overwrite an existing one without asking).
- Fill in the **repo registry**: one line per detected repo. Leave the loading-policy section verbatim — it is the discipline that keeps the router thin.

## 4. Scaffold shared docs
- Create `docs/_shared/` and copy these **stack-neutral** stubs from `.lodestar/templates/docs/_shared/`: `auth-model.md`, `env-matrix.md`, `local-setup.md`, `glossary.md`. Leave their TODO markers for now — no repo has been deeply read yet, so there is little to substantiate. `/lodestar-onboard` fills these in from evidence as each repo is absorbed (see its step 4b), replacing the TODOs it can ground in code and leaving only the unknowable. Do NOT assume an API style here.
- Seed the contract spine as `docs/_shared/api-contract.md` from the **generic** `.lodestar/templates/docs/_shared/api-contract.md`. Every other shared doc links to this stable filename. `/lodestar-onboard` may later enrich it from a stack-specific stub (GraphQL/REST) once a matching stack is actually detected — but only if the file is still the untouched generic template. Do NOT copy `graphql-contract.md` / `rest-api-contract.md` here.
- Create `docs/repo-map.md` from `.lodestar/templates/repo-map.md`, **pre-filled with the detected repos** (name, role, stack, docs path — all derivable from detection). This is the registry the router points at.

## 5. Install workspace-wide skills
Copy stack-agnostic skills from `.lodestar/catalog/skills/` into `./.claude/skills/`:
- `planning-workflow` and `architecture-overview` always.
Do NOT copy stack-scoped skills here — those are added per repo by `/lodestar-onboard`.

## 6. Write the manifest
Create `./.claude/lodestar.manifest.json`:
```json
{
  "version": "0.3.0",
  "placement": "<personal|git-workspace>",
  "repos": [],
  "skills": ["planning-workflow", "architecture-overview"],
  "guardrails": [],
  "agents": []
}
```

## 7. Report and suggest next steps
Summarize what was created. Then tell the user to run, for each repo:
`/lodestar-onboard ./<repo>` — followed by `/lodestar-guardrails` and `/lodestar-agents` once repos are onboarded.

Do not create guardrails or agents here — those are separate, opt-in commands.
