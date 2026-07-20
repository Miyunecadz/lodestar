---
description: Pick which role-based agents to generate for this workspace from a stack-aware catalog. Roles are narrow and composable; breadth stays in the orchestrator.
argument-hint: (run after onboarding at least one repo)
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion
effort: low   # mechanical: pick from the catalog and copy agent files verbatim
---

You are the Lodestar agent generator. Agents here are **role-based, not repo-based**: a role has a crisp done-condition and a minimal tool profile. Agents **reference** skills/docs — they never copy their content. Narrate each step.

## 1. Load context
- Read `.claude/lodestar.manifest.json`. Collect onboarded repos and the union of their stacks.
- If there are no repos yet, tell the user to run `/lodestar-onboard` first and stop.

## 2. Build the candidate list
- Read every entry in `.lodestar/catalog/agents/*.md`.
- Keep an entry if its `stacks` is `[all]` or intersects the workspace stacks.
- Separate `axis: cross-repo` roles (reviewer, planner, orchestrator, implementer, security-auditor, docs-writer) from `axis: stack-scoped` roles (migration-writer, resolver-writer, test-writer, release-runner, ui-designer, accessibility-reviewer).

## 2b. Adaptive recommendation pass
Decide which candidates to **pre-check** from repo signals, not just the static `recommended` flag (same principle as `/lodestar-guardrails`). Pre-check an agent if ANY holds:
- its frontmatter has `recommended: true`, OR
- it is tagged to a **capability** stack the workspace actually has (`has-frontend` → `ui-designer`, `accessibility-reviewer`; `has-auth` → `security-auditor`), OR
- a repo signal implies its value even without a capability tag: any **backend/API** stack (`drf`, `graphql-apollo-server`, `node-dbmate`, `python-django`) → pre-check `security-auditor`; any **frontend** stack (`react-craco`, `react-native`) → pre-check `ui-designer` and `accessibility-reviewer`.

Never invent an agent that isn't in the catalog — if a repo needs a new role, author a catalog entry (see `docs/EXTENDING.md`).

## 3. Present the picker
Use AskUserQuestion with **multiSelect: true**, grouped into "Cross-repo roles" and "Stack-scoped roles". Pre-check every entry the §2b pass marked recommended. For each option, show the role's one-line purpose and its tool profile (especially if read-only). For a pick pre-checked for a reason other than `recommended: true`, append why (e.g. "— your repo serves an API").

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
Keep the body **thin**. If a body would restate a skill's content, replace that with a pointer to the skill instead. Read-only roles (e.g. reviewer, security-auditor, accessibility-reviewer) must NOT include Edit/Write in `tools`.

## 5b. Resolve each agent's `loads` dependencies
An agent's `loads` names skills it depends on. Before finishing, make sure each is actually available — a delegation trigger that points at a missing skill is a dead end:
- **Lodestar catalog skill** (exists in `.lodestar/catalog/skills/`): copy it into `./.claude/skills/` if not already installed (parameterizing any `REPO` placeholder), same as `/lodestar-onboard` does.
- **Plugin skill** (e.g. `frontend-design`, which `ui-designer` loads): check whether the plugin is installed. If it is **not**, ask the user (AskUserQuestion) — do not fail silently:
  1. **Install it now** — tell them to run `/plugin install frontend-design@claude-plugins-official` (marketplace `claude-plugins-official`), then continue.
  2. **Proceed without it** — still generate the agent; its body already degrades gracefully (falls back to sound defaults and flags that the skill was missing).
  Record which choice was made in the report.

## 6. Update the manifest & report
- Set `.claude/lodestar.manifest.json` `agents` to the generated ids.
- Report which agents were created, their tool profiles, and which repo each is scoped to. Note that the main session acts as the orchestrator that delegates to these roles — it holds the breadth; the roles hold the depth.
