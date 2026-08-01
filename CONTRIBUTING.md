# Contributing to Lodestar

## Repo layout: `kit/` = product, `.claude/` = how we build it

Lodestar ships a **kit** that `install.sh` copies into a user's workspace. To keep
"what we ship" cleanly separate from "how we develop," the repo is split in two:

```
kit/                     ← THE PRODUCT (everything install.sh distributes)
  catalog/               guardrails, agents, skills (stack-tagged)
  templates/             CLAUDE.md router, docs/_shared stubs, hooks, mcp, git
  commands/              the lodestar-*.md slash-command specs
.claude/                 ← THIS REPO'S OWN dev tooling (never shipped)
  agents/ skills/ workflows/ settings.json   (add freely)
docs/ examples/          human docs
.github/                 CI + release pipeline
install.sh VERSION CHANGELOG.md README.md LICENSE
```

**`install.sh` only ever copies from `kit/`.** Nothing in `.claude/` reaches a user's
workspace, so you can add dev-only agents, skills, workflows, or a `settings.json`
here without any risk of leaking into the product.

Because the command specs now live in `kit/commands/` (not `.claude/commands/`), the
`lodestar-*` commands are **not** live as slash commands while you work in this repo.
To exercise them end to end, install Lodestar into a scratch workspace:

```bash
./install.sh /tmp/lodestar-scratch && cd /tmp/lodestar-scratch && claude
```

## One-time setup after cloning

The repo dogfoods its own guardrails, and two of the three surfaces work the moment you
open the clone: the PreToolUse engine and `permissions.deny` are both wired through the
committed `.claude/settings.json`.

The **commit surface is not**, because `.git/hooks/` cannot be tracked. Wire it once:

```bash
cp .claude/hooks/lodestar-precommit-check.py .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Without it your commits skip the `commit`-surface rules — which for this repo means a
staged real `.env` and a direct commit to `main` both go unchallenged locally. Server-side
branch protection still catches the second one; nothing catches the first. `git commit
--no-verify` is the deliberate bypass once it is wired.

If you use [mise](https://mise.jdx.dev), `mise.toml` loads a gitignored `.env` into the
shell so `gh` picks up `GH_TOKEN` without a separate login. Entirely optional.

## Adding to the kit

See [`docs/EXTENDING.md`](docs/EXTENDING.md) — add a catalog entry (guardrail / agent /
skill), a template, or a stack detector. Everything is plain Markdown; no code changes.

## Before you push

CI runs ten gates (see `.github/workflows/ci.yml`); run them locally:

```bash
find . -name '*.sh' -not -path './.git/*' -print0 | xargs -0 -r shellcheck --severity=error
python3 .github/scripts/validate.py          # catalog frontmatter + VERSION↔CHANGELOG
python3 .github/scripts/test-hook-parity.py  # the duplicated hook helpers still agree
bash   .github/scripts/test-engine.sh        # guardrail engine (agent surface)
python3 .github/scripts/test-catalog.py      # the REAL catalog rules vs their fixtures
bash   .github/scripts/test-install.sh       # installer: clone, bootstrap, pinning, refusals
bash   .github/scripts/test-precommit.sh     # commit surface: staged-diff enforcement
bash   .github/scripts/test-coverage.sh      # graph completeness: on-disk code vs graph nodes
bash   .github/scripts/test-freshness.sh     # map drift, in BOTH workspace layouts
bash   .github/scripts/test-permissions.sh   # permission surface: idempotent, reversible deny merge
bash   .github/scripts/test-graph-refresh.sh # the pre-commit hook that stages the graph
```

If you touched a hook in `kit/templates/hooks/`, also run the two enforcement suites
against the Python floor (`MIN_PYTHON` in the hooks). CI does this in the `python-floor`
job because a version-floor break is silent — it makes every rule inert rather than
failing:

```bash
FLOOR="$(uv python find 3.8)"   # or any 3.8 interpreter on your PATH
LODESTAR_TEST_PYTHON="$FLOOR" bash .github/scripts/test-engine.sh
LODESTAR_TEST_PYTHON="$FLOOR" bash .github/scripts/test-precommit.sh
```

Do **not** edit `VERSION` or `CHANGELOG.md`. Add one file to
[`changelog.d/`](changelog.d/README.md) instead — `<issue>-<slug>.md`, holding the body
of the changelog section you would have written. Those two files have exactly one hot
line each, so every PR that touched them conflicted with every other open PR; two PRs
adding two different fragments cannot. `.github/scripts/release.py <version>` folds the
fragments in, bumps `VERSION`, and stamps the previous release's date at release time.

Commits: keep the subject to one line, no co-author trailer (matches the
`commit-message-style` guardrail the kit ships).
