# CI, Releases & Branch Protection

Lodestar uses trunk-based development: one long-lived branch (`main`), short-lived feature
branches, and every change reaching `main` goes through a pull request.

## Workflows (`.github/workflows/`)

| Workflow | Trigger | Does |
|---|---|---|
| `ci.yml` | every PR + push to `main` | shellchecks `install.sh`, validates the catalog + `VERSION`↔`CHANGELOG`, and smoke-tests the guardrail engine. **This is the required status check.** |
| `release.yml` | push to `main` that changes `VERSION` | tags `vX.Y.Z` and cuts a GitHub Release from that version's `CHANGELOG` section. No manual tagging. |
| `guard-default-branch.yml` | push to `main` | **backstop**: fails if a commit reached `main` without a merged PR (see the note below). |

Helper scripts live in `.github/scripts/` (`validate.py`, `test-engine.sh`) and run locally too.

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
