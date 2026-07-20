---
description: Refresh an onboarded repo's architecture map after the code has drifted — re-run the mapping (Graphify or Markdown) and update the freshness fingerprint.
argument-hint: <repo-name> (e.g. web) — omit to refresh every drifted repo
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
effort: medium   # markdown-mode needs a real mapping synthesis pass
---

You refresh the architecture map for a repo whose code has drifted from its committed map. graphify repos on a lockstep hook (`/lodestar-freshness`) stay fresh on their own — this command is for **markdown-mode** repos (which need the LLM mapping pass and so are *never* rebuilt silently) and for **on-demand** graphify rebuilds where no hook is installed. Narrate each step.

## 1. Resolve scope
- Read `.claude/lodestar.manifest.json`. Resolve `$ARGUMENTS` to a repo entry. If empty, run the drift check (below) and refresh every repo it flags.
- If the repo isn't in the manifest, tell the user to `/lodestar-onboard` it first and stop.

## 2. Check drift first (don't rebuild needlessly)
- If `.claude/hooks/lodestar-freshness-check.py` exists, run `python3 .claude/hooks/lodestar-freshness-check.py --repo <name>` and show its verdict.
- Otherwise compute it inline: diff `mapping.lastMappedSha..HEAD` for code files under the repo's `path`. No `lastMappedSha` → treat as needing a first real map.
- If the repo is **not** drifted, say so and stop — nothing to do. (Force a rebuild anyway only if the user explicitly asks.)

## 3. Rebuild the map — by architecture
Read the repo's `architecture` from the manifest:

- **graphify** — run `graphify update <path> --force`, then copy `graph.json` / `GRAPH_REPORT.md` / `graph.html` into `docs/<repo>/architecture/`. If the `graphify` CLI is absent, say so and stop (don't fall back to a hand-written graph — that would misrepresent the format). This is the manual equivalent of the lockstep hook; suggest `/lodestar-freshness` if they want it automated.
- **markdown** — re-run the mapping pass that `/lodestar-onboard` step 3 uses: explore the repo (Glob/Grep/Read; dispatch the Explore agent if available) and regenerate `docs/<repo>/architecture/overview.md` — entry points, module/directory map, key runtime flows, a mermaid diagram, and a "where to find X" table. **Preserve any human-authored prose** that isn't a re-derivable structural fact; you're refreshing the machine-derived map, not discarding annotations.
- **deferred** (onboarding never mapped it) — there's nothing to refresh; point the user back to `/lodestar-onboard <path>`.

## 4. Update the fingerprint
After a successful rebuild, stamp the manifest so drift detection resets:
```json
"mapping": { "lastMappedSha": "<git rev-parse HEAD>", "lastMappedAt": "<ISO-8601 UTC>" }
```
Use the current `HEAD` sha (this command runs outside a commit, so `HEAD` is the exact commit the fresh map corresponds to — unlike the lockstep hook, which leaves `lastMappedSha` null because the commit it belongs to doesn't exist yet).

## 5. Report
- Say which repos were refreshed, which were already fresh, and the new fingerprint.
- If you rebuilt a graphify repo by hand, remind the user that `/lodestar-freshness` can keep it in lockstep automatically so they don't have to run this.
- Commit guidance: the refreshed docs are staged/modified in the working tree — the user commits them (for markdown) or they ride the next lockstep commit (for graphify with the hook).
