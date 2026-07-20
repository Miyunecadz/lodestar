---
description: Install graph-freshness for onboarded repos — a lockstep pre-commit rebuild (graphify) and/or drift detection (markdown), wired into the repo's existing git-hook manager.
argument-hint: (run after onboarding at least one repo)
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion
effort: low   # mechanical: detect the hook manager, copy the hook, wire config
---

You install **graph freshness** into the workspace. Onboarding produces an architecture map (`docs/<repo>/architecture/`) that `CLAUDE.md` tells agents to *trust* over re-reading source — so a stale map actively misleads. This command keeps the map in sync with the code. It is **opt-in and non-destructive**: it never clobbers an existing git hook, and every mechanism degrades to a hint rather than blocking a commit. Narrate each step.

## 1. Load context
- Read `.claude/lodestar.manifest.json`. If there are no `repos`, tell the user to run `/lodestar-onboard` first and stop.
- For each repo note its `architecture` (`graphify` / `markdown` / deferred) and `path`. Freshness works differently per mode:
  - **graphify** → deterministic, offline (~1s). Install the **lockstep pre-commit hook** so a rebuilt graph rides in the same commit as the code.
  - **markdown** → regeneration needs the LLM mapping pass, too slow for a commit hook. Install **drift detection** only; the actual rebuild is the on-demand `/lodestar-refresh <repo>`.

## 2. Locate the git repo(s) and detect the hook manager
Freshness operates inside a single git repository — a hook can only stage files that live in the repo it runs in. Determine, for the code you want kept fresh, which git repo it belongs to (`git -C <path> rev-parse --show-toplevel`):
- **Monorepo** (workspace root is itself the git repo; the logical repos are subdirectories, docs live alongside): one install covers every logical repo. This is the common, fully-supported case.
- **Separate sub-repos** (each onboarded repo is its own git repo, docs live in the workspace root outside them): a sub-repo's pre-commit hook can rebuild its graph but **cannot** stage docs that live in another repo. Say so plainly, and offer drift-detection there instead of lockstep (or install the hook in whichever repo also tracks `docs/`).

For the target git repo, detect the hook manager and integrate **without clobbering** (a naive `.git/hooks/pre-commit` gets overwritten by `lefthook install` / `husky`):
- **lefthook** (`lefthook.yml` present) → add a `pre-commit` command that runs the hook script.
- **husky** (`.husky/` present) → add a line to `.husky/pre-commit`.
- **`core.hooksPath` set** (`git config core.hooksPath`) → write into that directory, chaining any existing hook.
- **none** → write `.git/hooks/pre-commit` (chain an existing one if present — source it, don't overwrite).

Confirm the detected manager with the user before writing.

## 3. Confirm scope (AskUserQuestion)
Present what will be installed and let the user pick:
- **graphify repos** → lockstep pre-commit refresh (recommended when the `graphify` CLI is available; note it no-ops for teammates/CI without graphify).
- **markdown repos** → drift detection + `/lodestar-refresh` (recommended).
- Whether to also install the **union merge driver** for `graph.json` (recommended for graphify repos on teams).

## 4. Install the freshness hook (graphify lockstep)
- Copy `.lodestar/templates/hooks/lodestar-graph-refresh.sh` → `.claude/hooks/lodestar-graph-refresh.sh` and `chmod +x`.
- Wire it into the detected manager so it runs on **pre-commit**, e.g.:
  - **lefthook** — add under `pre-commit.commands`:
    ```yaml
    pre-commit:
      commands:
        lodestar-graph-refresh:
          run: bash "$CLAUDE_PROJECT_DIR/.claude/hooks/lodestar-graph-refresh.sh"
    ```
  - **plain `.git/hooks/pre-commit`** — ensure it invokes `bash .claude/hooks/lodestar-graph-refresh.sh` (append to an existing hook rather than replacing it).
- The hook reads the manifest itself: it rebuilds only graphify repos with **staged** code, copies `graph.json`/`GRAPH_REPORT.md`/`graph.html` into `docs/<repo>/architecture/`, `git add`s them + the fingerprint into the same commit, and **always exits 0** (missing tool / failure → hint only). `git commit --no-verify` (or `LEFTHOOK=0`) is the escape hatch.

## 5. Install the union merge driver (only if chosen, graphify repos)
So two branches that both rebuilt a graph merge cleanly:
- Append the lines from `.lodestar/templates/git/gitattributes-graphify` to the workspace `.gitattributes` (create it if absent) and stage it — this part **is** committed and shared.
- Register the driver **per-clone** (cannot be committed); run and tell the user teammates must run it too (or it falls back to a normal 3-way merge — nothing breaks):
  ```bash
  git config merge.graphify-union.name   "graphify union merge for graph.json"
  git config merge.graphify-union.driver "graphify merge-driver %O %A %B"
  ```

## 6. Install drift detection (markdown repos, and as a general check)
- Copy `.lodestar/templates/hooks/lodestar-freshness-check.py` → `.claude/hooks/lodestar-freshness-check.py`.
- It reads the manifest and, per repo, diffs `mapping.lastMappedSha..HEAD` for code under the repo path — reporting any **markdown** repo whose code moved since it was last mapped, and pointing at `/lodestar-refresh <repo>`. graphify lockstep repos are reported as auto-maintained.
- Offer to surface it where the user will see it (pick per the user's setup, don't force one):
  - a **post-commit** or **post-merge/post-checkout** hook that runs `python3 .claude/hooks/lodestar-freshness-check.py` (report-only, never blocks), and/or
  - a CI step: `python3 .claude/hooks/lodestar-freshness-check.py --exit-code` (fails the build on drift).

## 7. Update the manifest & report
- Record what was installed under a `freshness` key in `.claude/lodestar.manifest.json`, e.g.:
  ```json
  "freshness": {
    "hookManager": "lefthook",
    "graphifyLockstep": ["api"],
    "driftCheck": ["web"],
    "mergeDriver": true
  }
  ```
- Report: which repos got lockstep vs drift detection, the hook manager wired, whether the merge driver was set up (and that teammates must run the per-clone `git config`), and the `--no-verify` escape hatch. Remind the user this is re-synced by `/lodestar-update` (the engine files refresh; the manifest is left alone).
