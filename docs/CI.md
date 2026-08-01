# CI, Releases & Branch Protection

Lodestar uses trunk-based development: one long-lived branch (`main`), short-lived feature
branches, and every change reaching `main` goes through a pull request.

## Workflows (`.github/workflows/`)

| Workflow | Trigger | Does |
|---|---|---|
| `ci.yml` → job `ci` | every PR + push to `main` | shellchecks **every** `.sh` in the repo (discovered with `find`, so a new script cannot be forgotten), validates the catalog + `VERSION`↔`CHANGELOG`, and smoke-tests the guardrail engine, the installer, the commit-surface checker, graph coverage, graph freshness, and the permission surface. **Required status check.** |
| `ci.yml` → job `python-floor` | every PR + push to `main` | re-runs the two **enforcement** suites (`test-engine.sh`, `test-precommit.sh`) under Python **3.8** and **3.x**, reported as the checks `python 3.8` and `python 3.x`. **Both required.** |
| `release.yml` | push to `main` that changes `VERSION` | tags `vX.Y.Z` and cuts a GitHub Release from that version's `CHANGELOG` section. No manual tagging. |
| `guard-default-branch.yml` | push to `main` | **backstop**: fails if a commit reached `main` without a merged PR (see the note below). |

### Why a Python matrix

The hooks ship to machines whose `python3` is not the runner's, and a version-floor break is silent by construction: the engine catches the error, exits 0 with no decision, and every rule — `block` rules included — becomes inert behind one line of `systemMessage`. A single-interpreter CI cannot see that. `MIN_PYTHON` in both hooks is the source of truth for the floor; the matrix must be changed with it. Both suites honour `LODESTAR_TEST_PYTHON`, so the same check runs locally:

```bash
LODESTAR_TEST_PYTHON="$(uv python find 3.8)" bash .github/scripts/test-engine.sh
```

Helper scripts live in `.github/scripts/` (`validate.py`, `test-engine.sh`, `test-install.sh`, `test-precommit.sh`, `test-coverage.sh`) and run locally too. `test-install.sh` builds a throwaway local git repo as its "remote", so it exercises the bootstrap and tag-pinning paths without network access. `test-precommit.sh` builds a throwaway git repo, stages violations, and asserts the checker blocks only what it should — including that it never breaks a commit on a broken rule or a missing tool. `test-coverage.sh` builds a synthetic repo plus hand-written complete/partial/stale graphs, so it runs without a graphify install and exercises the checker's fallback classifier. `test-freshness.sh` builds a workspace in **each** supported layout — a monorepo, and sibling repos under a root that is not a git repo — and asserts the drift verdict is the same regardless of where the checker is invoked from; the layout is the axis that matters, because `lastMappedSha` belongs to a specific repository's history. `test-permissions.sh` exercises the deny-list merge, where the interesting property is not the write but its reversibility: re-running must not duplicate, a hand-written entry must survive, and unticking a rule must remove exactly the entries that rule contributed. `test-graph-refresh.sh` drives the pre-commit hook that stages the graph, stubbing graphify via `LODESTAR_GRAPHIFY_BIN` so it needs no graphify install; what it pins is the contract that hook cannot break — it never fails a commit (missing tool, failing tool, no manifest, no artifacts) and stages exactly the artifacts it found and nothing else.

## Cutting a release (trunk-based)

1. On a feature branch, bump `VERSION` and add the matching `## [X.Y.Z]` section to `CHANGELOG.md`.
2. Open a PR. `ci` must pass (it checks that `VERSION` and the top `CHANGELOG` entry agree).
3. Merge to `main` → `release.yml` tags `vX.Y.Z` and publishes the GitHub Release automatically.

## Enforcing "no direct merge to the default branch"

> **A workflow cannot prevent a push** — it runs *after* the commit lands. Real prevention is a
> **branch ruleset**. `guard-default-branch.yml` is only a detective backstop (it fails loudly on a
> bypass); the ruleset is what actually blocks direct pushes.

The ruleset lives in [`.github/rulesets/protect-main.json`](../.github/rulesets/protect-main.json) and enforces, on the default branch:

- **Pull request required before merging** → blocks direct pushes/commits to `main`.
- **Required status check: `ci`** → nothing merges unless CI is green.
- **Block force-pushes** (`non_fast_forward`) and **block branch deletion**.
- `required_approving_review_count: 0` — solo-friendly: a PR is required, but you can merge your own.

Apply it (needs the `gh` CLI, authenticated, with admin on the repo):

```bash
.github/rulesets/apply.sh Miyunecadz/lodestar
```

Or via the UI: **Settings → Rules → Rulesets → New ruleset → Import** and pick `protect-main.json`.

Once active, you push feature branches and open PRs; `main` no longer accepts direct pushes. To
grant yourself an emergency bypass, add your admin role to `bypass_actors` in the JSON and re-apply.
