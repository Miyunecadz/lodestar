# `.claude/` — this repo's own Claude Code config

Dev tooling for building Lodestar. Never shipped: `install.sh` copies only from
[`../kit/`](../kit/), so anything added here is safe. Layout and clone-time setup live in
[`../CONTRIBUTING.md`](../CONTRIBUTING.md).

| Path | What it does |
|---|---|
| `settings.json` | registers the guardrail engine (PreToolUse) and the two dev hooks (PostToolUse); holds the CI-gate allow-list and the `permissions.deny` block |
| `guardrails/` | four dogfooded rules — installed copies of the catalog entries of the same name, produced by the picker's transform (`id:` → `name:`, plus `enabled: true`). **Re-derive them from `kit/catalog/guardrails/` rather than hand-editing**, or they drift out of the product |
| `hooks/dev-*.py` | dev-only, no kit equivalent: run `validate.py` after a catalog edit and `shellcheck` after a shell edit, so a CI failure surfaces at the edit instead of at push |
| `commands/` | the four-stage ticket-to-PR workflow — see below |
| `agents/` | `gate-runner` (run a scoped or full gate set, report only failures), `kit-boundary-reviewer` (the invariants CI cannot check), `change-reviewer` (correctness against the ticket and the analysis) |
| `skills/` | loaded on demand when a task matches |
| `handoff/` | per-issue state passed between the three stages; gitignored, safe to delete |
| `lodestar.manifest.json` | records which deny entries `lodestar-permissions.py` owns; **do not hand-edit** |

`settings.json` runs the **shipped** hooks in place from `kit/templates/hooks/`. There is
deliberately no dev copy of them — see CONTRIBUTING.md for why.

## The ticket-to-PR workflow

```
/implement-ticket <issue>   necessity analysis → APPROVED/NOT_APPROVED gate
                            → implement → scoped gates → handoff
/review-ticket <issue>      is the implementation correct for the ticket?
                            → APPROVED / CHANGES_REQUIRED
/create-pr <issue>          branch, fragment, commit, push, draft PR
/pr-review <pr>             is this PR safe to merge? final diff, commits,
                            description, CI status, drift since stage 2
```

Each stage refuses to start until the previous one recorded its verdict in
`handoff/<issue>.md`, and **only `/create-pr` may commit, push, or open a PR** — the other
three are explicitly forbidden. The split is the point: an unnecessary issue stops at stage 1
before any code is written, stage 2 reviews against the ticket rather than against the
implementation's own reasoning, and stage 4 re-checks the *actual* PR, because a stage-2
approval describes the diff that existed then.

Stage 2 records the SHA it reviewed. Stage 4 compares it to the PR head, so the expensive
re-review runs only when the diff actually moved.

`validation-scope` maps changed paths to the gates those paths can actually break, so a
docs edit does not pay for the whole suite of temp-workspace smoke tests. `ci.yml` stays
authoritative for what the gates *are*.
