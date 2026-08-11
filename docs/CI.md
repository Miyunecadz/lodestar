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

Helper scripts live in `.github/scripts/` (`validate.py`, `test-engine.sh`, `test-install.sh`, `test-precommit.sh`, `test-coverage.sh`) and run locally too. `validate.py` also checks each `CHANGELOG.md` heading's **release status against the actual `v*` tags**: a tagged version must carry its release date, an untagged one below the top must say `— not released` so an uncut version cannot look pending, and the top entry must be `— Unreleased` and not already tagged. That last rule is the one that catches a forgotten `VERSION` bump — the mistake that left 0.8.0 and 0.9.0 written up but never cut. The `ci` job checks out with `fetch-depth: 0` for this; without tags the check skips rather than reporting every published version as unreleased. `test-install.sh` builds a throwaway local git repo as its "remote", so it exercises the bootstrap and tag-pinning paths without network access. `test-precommit.sh` builds a throwaway git repo, stages violations, and asserts the checker blocks only what it should — including that it never breaks a commit on a broken rule or a missing tool. `test-coverage.sh` builds a synthetic repo plus hand-written complete/partial/stale graphs, so it runs without a graphify install and exercises the checker's fallback classifier. `test-freshness.sh` builds a workspace in **each** supported layout — a monorepo, and sibling repos under a root that is not a git repo — and asserts the drift verdict is the same regardless of where the checker is invoked from; the layout is the axis that matters, because `lastMappedSha` belongs to a specific repository's history. `test-permissions.sh` exercises the deny-list merge, where the interesting property is not the write but its reversibility: re-running must not duplicate, a hand-written entry must survive, and unticking a rule must remove exactly the entries that rule contributed. `test-catalog.py` is the one gate that executes the **product**: it installs each real `kit/catalog/guardrails/<id>.md` the way `/lodestar-guardrails` does — exercising the `id:` → `name:` transform, which was previously assumed rather than tested — and asserts the engine's verdict against `.github/fixtures/guardrails.tsv`. `test-engine.sh` tests the engine against hand-written rules, which is a different claim: if a test copy and the catalog drift apart, both keep passing. `validate.py` refuses a guardrail with no positive-and-negative fixture pair, so a new entry cannot ship untested. `test-hook-parity.py` feeds one corpus of frontmatter through all three hooks' duplicated helpers and asserts they agree — the duplication is deliberate (each hook must work when copied alone), so this is what keeps it from drifting silently; it compares behaviour rather than source, because the implementations differ in style for good reasons. `test-graph-refresh.sh` drives the pre-commit hook that stages the graph, stubbing graphify via `LODESTAR_GRAPHIFY_BIN` so it needs no graphify install; what it pins is the contract that hook cannot break — it never fails a commit (missing tool, failing tool, no manifest, no artifacts) and stages exactly the artifacts it found and nothing else.

## Cutting a release (trunk-based)

Feature PRs never touch `VERSION` or `CHANGELOG.md` — they add a fragment to
[`changelog.d/`](../changelog.d/README.md). Both files have exactly one hot line, so any
two PRs that edited them conflicted with each other structurally, regardless of branching
or merge method. Two PRs adding two different fragment files cannot.

1. On a branch, run `.github/scripts/release.py X.Y.Z` (`--dry-run` first if you like). It
   folds every fragment into a new `## [X.Y.Z] — Unreleased` section, bumps `VERSION`,
   deletes the fragments, and **stamps the previous version's release date** — that last
   step used to be manual, which is why it got forgotten for twelve versions.
2. Open a PR. `ci` must pass; it checks `VERSION` against the top `CHANGELOG` heading and
   every heading's release status against the real tags.
3. Merge to `main` → the `VERSION` change triggers `release.yml`, which tags `vX.Y.Z` and
   publishes the GitHub Release from that section. No manual tagging.

The top heading has two valid states, which is why `validate.py` accepts both: `—
Unreleased` while the release PR is open and no tag exists yet, and a date once it has
merged and been tagged. Every heading below the top must be dated if tagged, or say
`— not released` if it never shipped.

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
