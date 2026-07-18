---
description: Pick which role-based agents to generate for this workspace from a stack-aware catalog. Roles are narrow and composable; breadth stays in the orchestrator.
argument-hint: (run after onboarding at least one repo)
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion
---

You are the Lodestar agent generator. Agents here are **role-based, not repo-based**: a role has a crisp done-condition and a minimal tool profile. Agents **reference** skills/docs — they never copy their content. Narrate each step.

## 1. Load context
- Read `.claude/lodestar.manifest.json`. Collect onboarded repos and the union of their stacks.
- If there are no repos yet, tell the user to run `/onboard-repo` first and stop.

## 2. Build the candidate list
- Read every entry in `.lodestar/catalog/agents/*.md`.
- Keep an entry if its `stacks` is `[all]` or intersects the workspace stacks.
- Separate `axis: cross-repo` roles (reviewer, planner, orchestrator, implementer) from `axis: stack-scoped` roles (migration-writer, resolver-writer, test-writer, release-runner).

## 3. Present the picker
Use AskUserQuestion with **multiSelect: true**, grouped into "Cross-repo roles" and "Stack-scoped roles". Pre-check every entry with `recommended: true`. For each option, show the role's one-line purpose and its tool profile (especially if read-only).

## 4. Resolve repo targeting
For each chosen **stack-scoped** role, determine which repo(s) it applies to (the repos whose stacks match the role's `stacks`). If more than one matches, ask the user which repo(s) to generate it for — generate one agent per selected repo, suffixed with the repo name (e.g. `migration-writer-backend`).

## 5. Write the agents
For each resulting agent, write `.claude/agents/<id>.md` with proper Claude Code agent frontmatter:
```
---
name: <id>
description: <the catalog description — this is the delegation trigger>
tools: <the catalog tools list>
---
<the catalog body, with REPO placeholders filled in, and explicit "load skill X / read docs/REPO/… on start" lines>
```
Keep the body **thin**. If a body would restate a skill's content, replace that with a pointer to the skill instead. Read-only roles (e.g. reviewer) must NOT include Edit/Write in `tools`.

## 6. Update the manifest & report
- Set `.claude/lodestar.manifest.json` `agents` to the generated ids.
- Report which agents were created, their tool profiles, and which repo each is scoped to. Note that the main session acts as the orchestrator that delegates to these roles — it holds the breadth; the roles hold the depth.
