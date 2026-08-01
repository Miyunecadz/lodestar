# Spike: adopt Impeccable's deterministic detector as a Lodestar guardrail?

**Decision: defer the guardrail, document the integration path.** Ship `frontend-design` as the default guidance skill (done in 0.11.0) and treat Impeccable as an **opt-in quality gate** wired through the existing settings-hook / CI mechanisms, not as an entry in the block/warn guardrail engine.

Raised by issue #6, which recommended a spike rather than an adoption. This is that spike.

## What Impeccable actually is

Verified against [impeccable.style](https://impeccable.style/) and [github.com/pbakaus/impeccable](https://github.com/pbakaus/impeccable) (checked 2026-07-31):

| | Detail |
|---|---|
| What | Design-quality skill pack for AI harnesses (Claude Code, Cursor, Codex, Copilot, Gemini CLI), by Paul Bakaus |
| License | Apache 2.0, open source |
| Cost | Free |
| Guidance surface | 23 commands (`polish`, `audit`, `critique`, `animate`, …) — a shared design vocabulary |
| **Detector** | `npx impeccable detect src/` — **deterministic rules, no LLM and no API key** |
| Output | `--json` for CI; also scans a single HTML file or a URL (via Puppeteer) |
| Install | `/plugin marketplace add pbakaus/impeccable`, `npx impeccable install`, or `npx skills add pbakaus/impeccable` |
| Also | Chrome extension for overlay detection on a live page |

The architectural claim in issue #6 holds up: a deterministic, no-LLM rules engine that flags anti-patterns pre-ship **is** the same shape as Lodestar's guardrail engine. That is why it was worth a spike rather than a dismissal.

## Why defer the guardrail

**1. It would break the engine's dependency contract.** `lodestar-guardrails.py` is Python **stdlib-only**, offline, and starts in milliseconds — that is what lets it run on every single `Edit`/`Write` without anyone noticing. Impeccable's detector is a Node CLI (`npx`, Node 22.12+ per the install docs, first run resolves a package). A `PreToolUse` rule that shells out to `npx` on every UI edit adds a process spawn and a possible network fetch to the hot path, and a rule that cannot run degrades to "allow" — a guardrail that is usually skipped is worse than an honest CI check.

**2. Rule-set surface is still moving fast.** The count alone has been reported as **46** (issue #6, written a few weeks ago), **59** (impeccable.style today), and **60** (a secondary source today). A fast-moving upstream is a good sign for the project and a bad basis for a *pinned catalog entry* whose message text has to describe what it enforces. The catalog's job is to be stable enough to fork.

**3. Exit codes are not part of the documented contract yet.** The README documents the commands and `--json` but not exit codes; a secondary source states `0` clean / `2` on findings. Building a blocking gate on an undocumented exit code is how a tool upgrade turns into everyone's commits failing.

**4. It is a quality linter, and Lodestar already has a shape for those.** Design anti-patterns are the same category as lint findings: many, subjective at the edges, and best surfaced in bulk on changed files. Lodestar's answer for that is `emits: settings-hook` (the per-repo lint router, fires after an edit, routes by repo, skips repos without the tool) and CI — not `emits: rule`. Slotting Impeccable into the engine would put a 59-rule aesthetic judgement behind the same mechanism that blocks committing a private key, and those two things should not share a severity vocabulary.

**5. Adoption asymmetry.** `frontend-design` is an official Anthropic plugin — one `/plugin install`, no runtime. Impeccable is excellent but adds a Node toolchain requirement to workspaces that may be Python- or PHP-only. Lodestar's frontend detection (`has-frontend`) fires on a Django app with a few templates.

## The integration path, if you want it

None of the above argues against Impeccable — only against putting it in the block/warn engine. Two clean ways in, both opt-in and both consistent with existing patterns:

**A. Catalog entry, `emits: settings-hook`** (mirrors `autolint-on-edit`):

```markdown
---
id: impeccable-detect-on-edit
category: quality
severity: warn
stacks: [has-impeccable]      # new capability tag: impeccable in devDependencies or .impeccable config
event: file
pattern: '(^|/)(src|app|pages|components)/.*\.(tsx|jsx|vue|svelte|css)$'
surface: agent
emits: settings-hook
---
```
Routes by repo, runs `npx impeccable detect --json <file>`, reports findings, and no-ops where the tool is absent. Gated on a `has-impeccable` detector so it never fires in a workspace that has not opted in — the same discipline `php-autolint-on-edit` uses for Pint.

**B. CI step** — the stronger gate, and where the tool's own docs point:

```yaml
- run: npx impeccable detect --json src/
```
This is the right home for a 59-rule pre-ship check: it runs once per PR on the whole surface, its failure is visible and reviewable, and a rule-set upgrade breaks a build rather than an interactive edit loop.

## Revisit when

- Exit codes land in the documented CLI contract, **and**
- the rule set settles across a couple of minor releases, **and**
- someone actually wants it in a real workspace (a `has-impeccable` detector costs one line, so this should be pulled by demand, not pushed).

At that point option A is a ~40-line catalog entry with no engine changes, because the settings-hook mechanism already exists. Nothing in 0.11.0 blocks it.

## What shipped instead (0.11.0)

The part of issue #6 that was unambiguously right — that a frontend workspace could end up with **no** design guidance, silently:

- `ui-designer` is `recommended: true` (frontend-scoped), so a detected frontend gets a design role by default.
- Declining the `frontend-design` plugin is **recorded** in `designGuidance` and **re-offered** on later runs, instead of becoming permanent by forgetting.
- `design-guidance-on-ui-edits` warns on UI edits while `designGuidance.installed` is false — **self-silencing** once guidance is recorded, and still firing after a decline.

Note what that guardrail deliberately does **not** do: issue #6 asked it to check whether a design skill is "loaded in the session". A `PreToolUse` hook has no view of loaded skills, so it checks recorded workspace state instead. Same intent, actually checkable.

Sources: [impeccable.style](https://impeccable.style/) · [pbakaus/impeccable](https://github.com/pbakaus/impeccable) · [Frontend Design plugin](https://claude.com/plugins/frontend-design)
