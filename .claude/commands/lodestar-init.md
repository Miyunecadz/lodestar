---
description: Initialize Lodestar in the current workspace — create the thin root CLAUDE.md, docs/_shared skeleton, repo-map, and workspace-wide skills.
argument-hint: (run from the workspace root that contains your repos)
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion
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
- Create `docs/_shared/` and copy each template from `.lodestar/templates/docs/_shared/`. These are fill-in stubs; leave TODO markers for the human. Keep the contract stub matching the workspace's API style — `graphql-contract.md` (GraphQL) or `rest-api-contract.md` (REST/DRF) — and delete the other.
- Create `docs/repo-map.md` from `.lodestar/templates/repo-map.md`, pre-filled with the detected repos. This is the registry the router points at.

## 5. Install workspace-wide skills
Copy stack-agnostic skills from `.lodestar/catalog/skills/` into `./.claude/skills/`:
- `planning-workflow` and `architecture-overview` always.
Do NOT copy stack-scoped skills here — those are added per repo by `/onboard-repo`.

## 6. Write the manifest
Create `./.claude/lodestar.manifest.json`:
```json
{
  "version": "0.1.0",
  "placement": "<personal|git-workspace>",
  "repos": [],
  "skills": ["planning-workflow", "architecture-overview"],
  "guardrails": [],
  "agents": []
}
```

## 7. Report and suggest next steps
Summarize what was created. Then tell the user to run, for each repo:
`/onboard-repo ./<repo>` — followed by `/guardrails` and `/gen-agents` once repos are onboarded.

Do not create guardrails or agents here — those are separate, opt-in commands.
