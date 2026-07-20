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

## Adding to the kit

See [`docs/EXTENDING.md`](docs/EXTENDING.md) — add a catalog entry (guardrail / agent /
skill), a template, or a stack detector. Everything is plain Markdown; no code changes.

## Before you push

CI runs three gates (see `.github/workflows/ci.yml`); run them locally:

```bash
shellcheck --severity=error install.sh
python3 .github/scripts/validate.py          # catalog frontmatter + VERSION↔CHANGELOG
bash   .github/scripts/test-engine.sh        # guardrail engine smoke test
```

Bump `VERSION` and add a matching top entry to `CHANGELOG.md` in the same change —
`validate.py` enforces that they agree, and a bump on `main` cuts a release.

Commits: keep the subject to one line, no co-author trailer (matches the
`commit-message-style` guardrail the kit ships).
