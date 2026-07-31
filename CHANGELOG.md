# Changelog

All notable changes to Lodestar are documented here.

## [0.9.0] — Unreleased

Graph-completeness pass — a map can be *born* incomplete, and nothing checked. Node counts were never compared against the source tree, so a graph missing whole files looked identical to a complete one. Because `CLAUDE.md` tells agents to prefer querying the graph over re-reading source, that misleads an agent exactly like a stale map does. Closes #5.

### Added
- **Coverage checker** (`kit/templates/hooks/lodestar-graph-coverage.py`) — compares the code files on disk against the `source_file`s present in `graph.json` and splits the difference four ways: **covered**, **missing** (code graphify would scan but has no nodes → a real gap), **skipped** (excluded on purpose — noise dirs, `.graphifyignore`/`.gitignore`, generated lockfiles), **stale** (graph references a file no longer on disk). Only `missing` is a defect, and the split is what makes the number usable: without it every `node_modules/` file reads as a gap. Manifest mode iterates the onboarded graphify repos; `--graph`/`--root` checks one tree; `--json` feeds the manifest; `--exit-code` gates CI.
- **Authoritative classification when possible.** "Which files should be covered" is graphify's own question, so the checker imports graphify's real classifier and ignore rules (`classify_file`, `_is_noise_dir`, `_is_ignored`, `.graphifyignore` handling). graphify is normally installed as an isolated tool (uv/pipx), so it also locates the CLI's venv and adds its `site-packages` before giving up. When it genuinely can't import — or a future graphify renames an internal it depends on — it falls back to a bundled copy of the extension list and labels every result **approximate** rather than presenting a guess as exact. The mode is always reported.
- **`mapping.coverage` + `mapping.build` in the manifest** — `filesTotal` / `filesCovered` / `filesMissing` / `filesSkipped` / `filesStale` / `mode`, so incompleteness is as visible as drift and a later rebuild can be compared against the last one. `/lodestar-refresh` flags a refresh that *lowers* coverage as a regression rather than reporting success.
- **Coverage test suite** (`.github/scripts/test-coverage.sh`, 27 checks, wired into CI as a sixth gate) — synthetic repo plus hand-written complete / partial / stale graphs, so it needs no graphify install and exercises the fallback classifier. Asserts the missing/skipped/stale split, that `--exit-code` fails only on missing files, manifest iteration with a non-graphify repo skipped, and four degradation paths.

### Changed
- **Onboarding does a full build, not an incremental one.** `/lodestar-onboard` now runs `graphify extract <repo> --force` (adding `--code-only` when no LLM backend is configured), which skips the incremental manifest gate and semantic cache so the baseline inherits no state from an earlier partial run. `graphify update` stays the right tool for the per-commit lockstep hook, where each commit is a small delta and speed matters — the distinction is now stated in both commands.
- **`/lodestar-refresh` also rebuilds fully** (`extract --force` rather than `update --force`): the command exists because the map is already known to be wrong, so inheriting incremental state is the wrong trade. It re-checks coverage afterwards, since a refresh is exactly when an undercount surfaces.
- **`/lodestar-onboard` reports coverage to the user** and never blocks on it — if files are still missing after a full rebuild, it says which ones, and that queries about them will come back empty so that code must be read from source.
- **`/lodestar-freshness`** suggests running the coverage check in CI (`--exit-code`) rather than per-commit, where it would add latency for little gain.
- **`install.sh`** refreshes `lodestar-graph-coverage.py` on update, if already installed.

### Notes on scope
- **The issue's specific evidence did not reproduce, and the fix does not depend on it.** The report was that rebuilding unchanged code found *more* nodes than the committed graph (259 vs 253). On a synthetic repo I saw the opposite asymmetry — the incremental path retained 2 nodes a full rebuild did not produce, while **both** covered 100% of files. Node counts differing between the two paths is expected, since incremental merges into existing state. That is why the assertion here is at **file-coverage** level, which is the invariant that actually matters for "can an agent see this file", rather than a node-count comparison that would be noisy by design.
- **Exposing a completeness command from graphify itself** (item 3 of the issue) is out of scope for this repo — graphify is a separate project. This implements the Lodestar-side check against the graph it already produces.
- One real bug surfaced while testing: graphify applies its generated-file skip list (`package-lock.json`, `go.sum`, …) in its **walker**, not in `classify_file`, which reports those files as code. The first version of the checker therefore reported every lockfile as a *missing* file — the exact false-gap failure that makes a coverage number worthless. The skip list is now applied in both modes.

### Upgrading

Nothing to do — existing graphs are untouched. Coverage is recorded the next time a repo is onboarded or refreshed. To check an already-onboarded workspace now: `python3 .lodestar/templates/hooks/lodestar-graph-coverage.py`.

## [0.8.0] — Unreleased

Enforcement-surface pass — the safety guardrails were `PreToolUse` hooks, so they held against Claude and nobody else. A teammate in their IDE, or CI, could commit exactly what every "safety" rule exists to prevent. Rules now declare which surface they hold on, and commit-surface rules are enforced by a generated pre-commit hook for every committer. Closes #3.

### Added
- **`surface:` on every catalog guardrail** — `agent` (Claude tool-use only), `commit` (any committer), or `both`. Validated by CI, and stated in each rule body with the reason for that choice.
- **Commit-surface checker** (`kit/templates/hooks/lodestar-precommit-check.py`) — stdlib-only, runs as a pre-commit hook, reads the **same** `.claude/guardrails/*.md` rule files so the two surfaces cannot drift. Three checks: `staged-paths` (rule pattern vs staged paths, where `allow_if_untracked` maps onto git status — `A` is a new file, `M` an already-committed one), `secret-scan` (staged diff via `gitleaks`, else conservative built-ins), and `default-branch` (refuse a direct trunk commit). Exits 1 only on a `block` match; a warn, no rules, a missing tool, an invalid regex, or any internal error exits 0.
- **Six rules now hold for every committer** (`surface: both`) — `block-env-files`, `block-secret-files`, `block-edit-applied-migrations` (+ Django variant), `block-commit-to-default-branch`, and `scan-secrets-before-commit`.
- **`commit_check` / `commit_severity` rule fields** — pick the commit-side check, and override severity on the commit surface only (a rule can remind Claude but hard-stop a commit).
- **`/lodestar-guardrails` §6 installs the commit surface** (opt-in). Detects the git-hook manager — lefthook / husky / `core.hooksPath` / plain `.git/hooks` — and integrates **without clobbering**, coexisting with the freshness hook from #2 (each adds its own distinct pre-commit entry). Declining is fine, but the command then states plainly which rules therefore hold for Claude only. Records `guardrailSurfaces.commit` in the manifest.
- **Commit-surface test suite** (`.github/scripts/test-precommit.sh`, 23 checks, wired into CI as a fourth gate) — real git repo with staged changes: `.env` blocked but `.env.example` allowed, private keys blocked, agent-only rules ignored at commit time, new migration allowed while a modified one is blocked, secret scanning, stack scoping, `--list`, trunk vs feature branch, and four degradation paths that must never break a commit.

### Changed
- **`install.sh` refreshes `lodestar-precommit-check.py`** on update, if already installed — same opt-in-preserving rule as the other hooks.
- **Docs state the surface split explicitly** — `docs/EXTENDING.md` documents the fields and why three obvious-looking candidates stay `agent`-only; `docs/ARCHITECTURE.md` covers surfaces as a design concept; `kit/catalog/CATALOG.md` lists the commit-surface entries; the README's "advisory vs enforced" principle now names *enforced for whom* as a second, separate choice.

### Notes on scope
- **`protect-generated-files` stays `agent`-only on purpose.** Its pattern matches `graph.json`, which the freshness hook from #2 deliberately rebuilds and stages into the same commit — a commit-time block would break the lockstep map. This is the interaction that issue #2 flagged as an open edge case.
- **`no-hand-edit-lockfiles` and `protect-dbmate-schema` likewise.** Legitimate tooling commits those files constantly, and a pre-commit hook cannot distinguish a package-manager rewrite from a hand-edit.
- **`commit-message-style` needs a `commit-msg` hook** and `protect-default-branch` (force-push) needs `pre-push` — different git events from the `pre-commit` surface installed here. Both are noted in their bodies and on the roadmap.
- **`scan-secrets-before-commit` blocks only with `gitleaks` installed.** Without it the built-in patterns warn instead: heuristics precise enough to nag are not precise enough to stop a teammate's commit.
- A pre-commit hook is bypassable with `--no-verify`; server-side branch protection remains the only enforcement a determined committer cannot skip, and the docs say so.

### Upgrading

Existing installs keep working unchanged — the commit surface is opt-in. Re-run `/lodestar-guardrails` to adopt the `surface` metadata and install the pre-commit hook; until then every rule behaves exactly as before (Claude-only).
## [0.7.0] — Unreleased

Distribution pass — installing Lodestar no longer leaves you holding a clone you never asked for, and updates move between released tags instead of pulling whatever is on `main`. Closes #9.

### Added
- **Bootstrap installer — no persistent clone.** `curl -fsSL <raw-url>/install.sh | bash -s -- <workspace>` fetches the kit into a temp dir (shallow clone of a release tag), copies it in, and removes the temp dir. A script read from stdin has no location, so this is detected by the absence of a `kit/` directory next to the script — never by falling back to the current directory, which would silently pick up an unrelated `kit/`.
- **`--ref` / `LODESTAR_REF` to pin a version.** `install.sh <workspace> --ref v0.6.0` installs a specific release. An explicit ref always fetches from the remote, even when run from a clone — otherwise it would install whatever the clone had checked out while recording the tag the user asked for.
- **`.lodestar/source.json`** — records `kind` (`remote`/`local`), `origin` (URL or clone path), `ref`, and `version`: enough to update from, deliberately not a clone. `.lodestar/SOURCE` is still written for compatibility with installs that predate this.
- **Installer smoke test** (`.github/scripts/test-install.sh`, 24 checks, wired into CI) — clone mode, re-run/update mode, generated content surviving an update, piped bootstrap picking the newest tag, no temp dir or clone left behind, `--ref` pinning, and four refusals that must write nothing. Builds a throwaway local git repo as the "remote", so it needs no network. CI also shellchecks the test itself.

### Changed
- **`/lodestar-update` is remote-aware and tag-based.** With a `remote` source it resolves the newest release tag (`git ls-remote --tags`), fetches it into a temp dir, re-syncs, and cleans up. With a `local` source it keeps today's `git pull --ff-only` + local re-run, so contributors and offline installs behave exactly as before. `/lodestar-update <version>` pins or rolls back to any release from v0.5.0 onward; a rollback is called out as such before it runs. On a local install an explicit version reads the clone's `origin` URL and fetches the tag rather than mutating the user's working copy.
- **README splits the user path from the contributor path** — bootstrap one-liner first (with a download-and-read-first alternative), then install-from-a-clone for offline/air-gapped/contributing, then a note on what each mode records and how updates differ. `git` is now listed under requirements.

### Fixed
- **`install.sh` exited 1 on every successful run.** The `EXIT` trap's last command was a `[ -n "$TMP_DIR" ]` test that fails when there is no temp dir, and a failing final command in an exit trap becomes the script's exit status — so callers (including `/lodestar-update`) saw a successful install as a failure. The handler now returns 0 explicitly.
- **A tag older than v0.5.0 failed mid-copy.** Those tags predate the `kit/` layout, so `cp` aborted partway with a cryptic error after files had already been written. The installer now checks for `kit/` right after fetching and refuses with instructions to use that tag's own installer, leaving the workspace untouched.

### Upgrading

Existing clone-based installs keep working with no action — `source.json` is written on the next update and records the clone path, preserving `git pull` + re-install. To stop carrying a clone: re-install with the bootstrap one-liner over the same workspace (generated content is untouched), then delete the clone.

## [0.6.0] — Unreleased

Guardrail engine pass — rules were stateless regex matchers, so several shipped rules over-blocked legitimate work or under-enforced what their names promised. The engine now computes a small context layer that rules opt into declaratively. Closes #11.

### Added
- **Context layer in the guardrail engine** (`kit/templates/hooks/lodestar-guardrails.py`) — lazy, stdlib-only, computed at most once per invocation and shared by every rule: **git** (tracked status, current vs default branch), **stack** (target path → onboarded repo → detected stacks, from the manifest), **shell** (the command split into quoted vs unquoted words). Every probe fails **protective**: no git, no manifest, or an unparseable command means a rule behaves exactly as it did before. The hook still never raises — any internal error allows the action.
- **Rule context flags** — `stacks:` (now enforced), `allow_if_untracked`, `only_on_default_branch`, `match: argv`, `allow_paths`, `ignore_case`. Documented with the two invariants in `docs/EXTENDING.md`.
- **`block-commit-to-default-branch`** — the branch-aware rule `protect-default-branch` could never be: blocks `git commit`/`git push` while HEAD is the repo's default branch, resolving the default from `origin/HEAD` → `init.defaultBranch` → an existing local `main`/`master`. Silent when the branch cannot be determined, so it never blocks work on a detached HEAD or outside git.
- **Engine smoke test grew to 24 cases** (`.github/scripts/test-engine.sh`) — covers quoted-argument false positives, nested-shell payloads, unbalanced quotes, the temp-path allow-list, tracked vs untracked vs unborn migrations, default vs feature branch, and per-repo stack scoping in a mixed workspace.

### Fixed
- **`stacks:` is enforced at match time.** `load_rules` filtered only on `enabled` and `event`, so a rule scoped to one stack fired in **every** repo of a workspace — `mobile-use-patch-package` (`stacks: [react-native]`) denied `node_modules` edits in plain Node and CRA repos, where its "run `npx patch-package`" advice is wrong. The engine now resolves the target path to its onboarded repo and skips a rule whose `stacks` don't intersect. A path outside every repo still matches, so nothing is silently dropped.
- **`block-edit-applied-migrations` no longer blocks the migration it tells you to create.** The rule matched every write under `db/migrations/`, including the empty skeleton `dbmate new` had just scaffolded — making its own redirect impossible to follow. With `allow_if_untracked: true` it fires only for migrations git already tracks (tracked standing in for "applied", which is not detectable offline). Same fix for the Django variant.
- **`block-destructive-commands` no longer fires on text that deletes nothing.** It matched the raw command string, so `rm -rf` inside a quoted JSON argument or an echoed warning was blocked. `match: argv` tests unquoted words only, while payloads handed to a nested shell (`bash -c "…"`, `eval "…"`) are still matched so quoting is not a bypass; `allow_paths` exempts deletes whose every operand is an absolute path under `/tmp`, `/var/tmp`, or `/var/folders`. Relative operands and compound commands never qualify for the exemption.
- **Frontmatter parser handles inline lists.** `stacks: [react-native]` parsed as the string `"[react-native]"`, which is why rule metadata could not express scoping at all.
- **The three `git commit` rules are anchored to real invocations.** `scan-secrets-before-commit`, `verifier-before-commit`, and `commit-message-style` all keyed on the bare substring `git commit`, matching it inside quoted strings and unrelated compound commands. All three now use a command-boundary pattern with `match: argv`, and each body states plainly that a `PreToolUse` hook cannot confirm the step it asks for ran — they are checklist prompts, not gates.

### Changed
- **`protect-default-branch` retitled to "Block bare force-push to any branch"** — it is force-push-only and always was; the body now says so and points at `block-commit-to-default-branch` for the branch-aware half. The id is unchanged, so existing installs keep working.
- **`/lodestar-guardrails` copies the context flags** when installing a rule into `.claude/guardrails/` — a rule installed without its `stacks`/flags silently loses its scoping.

### Upgrading

`/lodestar-update` refreshes the **engine**, but your enabled rules in `.claude/guardrails/` are generated content and are deliberately left untouched. They keep working as-is (a rule with no context flags behaves exactly as before), so **re-run `/lodestar-guardrails`** to adopt the corrected rules and pick up `block-commit-to-default-branch`.

## [0.5.0] — Unreleased

Repo layout pass — separate what Lodestar *ships* from how this repo is *built*. Purely structural: the installed workspace is byte-identical to 0.4.0.

### Changed
- **Kit source now lives under `kit/`.** `catalog/`, `templates/`, and the `lodestar-*` command specs (previously in `.claude/commands/`) moved to `kit/catalog/`, `kit/templates/`, `kit/commands/`. `install.sh`, the CI validator, the engine smoke test, and doc/README links were repointed. The target-workspace layout it produces (`.lodestar/…`, `.claude/commands/…`) is unchanged.
- **Root `.claude/` is now this repo's own dev tooling**, not a product surface — free for contributor agents/skills/workflows/settings. See `CONTRIBUTING.md`. `install.sh` only ever copies from `kit/`, so nothing in `.claude/` can leak into the product. (Side effect: the `lodestar-*` commands are no longer live while developing this repo — install into a scratch workspace to exercise them.)

## [0.4.0] — Unreleased

Graph-freshness pass — the onboarded architecture map now stays in sync with the code instead of silently drifting. Because `CLAUDE.md` tells agents to *trust* the graph over re-reading source, a stale map was a correctness risk, not just staleness. Closes the core of #2.

### Added
- **`/lodestar-freshness`** — opt-in, transport-aware installer for map freshness. Detects the repo's git-hook manager (lefthook / husky / `core.hooksPath` / plain `.git/hooks`) and wires freshness in **without clobbering** existing hooks.
- **graphify lockstep pre-commit rebuild** (`templates/hooks/lodestar-graph-refresh.sh`) — on commit, rebuilds any graphify repo with **staged** code and stages the refreshed `graph.json`/`GRAPH_REPORT.md`/`graph.html` into the *same* commit, so code and map move together on every branch/checkout/pull. Monorepo-aware (only changed repos rebuild), offline (~1s), and **never blocks a commit** — a missing `graphify` CLI or a failure degrades to a hint (`--no-verify`/`LEFTHOOK=0` remain the escape hatch).
- **Union merge driver** for graphs (`templates/git/gitattributes-graphify`) — `.gitattributes` marks `graph.json`/`GRAPH_REPORT.md` for `merge=graphify-union` so two branches that both rebuilt a graph merge cleanly; falls back to normal 3-way merge where the per-clone driver isn't registered.
- **Markdown-mode drift detection** (`templates/hooks/lodestar-freshness-check.py`) — offline, stdlib-only. Diffs `mapping.lastMappedSha..HEAD` for code under each repo and reports drift (with `--exit-code` for a CI gate). No silent LLM rebuilds.
- **`/lodestar-refresh <repo>`** — on-demand re-map for markdown repos (re-runs the mapping pass, preserving human prose) and manual graphify rebuilds; re-stamps the fingerprint.
- **Freshness fingerprint in the manifest** — `/lodestar-onboard` now records each repo's `architecture`, `docs` path, and `mapping` (`lastMappedSha`/`lastMappedAt`); `/lodestar-freshness` records a `freshness` block (hook manager, lockstep vs drift-checked repos, merge driver).

### Changed
- **`install.sh` / `/lodestar-update`** re-sync the freshness hooks (`lodestar-graph-refresh.sh`, `lodestar-freshness-check.py`) — but only if a workspace already installed them, mirroring the guardrail-engine refresh. Generated content (manifest, `.gitattributes`, git-hook wiring) is never touched.
- `docs/ARCHITECTURE.md` documents the freshness layer, the manifest fingerprint, and updates the roadmap; `catalog/CATALOG.md` lists the new templates.

## [0.3.0] — Unreleased

Distribution & updatability pass — Lodestar is now branded, collision-safe, and updatable in place (no more delete-and-re-clone).

### Added
- **`/lodestar-update`** — pulls the latest source and re-syncs the kit (catalog, templates, commands, guardrail engine) **without touching anything you generated** (rules, agents, docs, manifest). Reports new catalog entries to adopt.
- **Re-runnable installer** — `install.sh` is now idempotent (no directory nesting), refreshes an already-installed guardrail engine, cleans up pre-rename command files, and records the source path + version so updates are a one-command re-sync.
- **CI / release pipeline** (`.github/`) — trunk-based: `ci.yml` (shellcheck, catalog + `VERSION`↔`CHANGELOG` validation, guardrail-engine smoke test) gates PRs; `release.yml` auto-tags and cuts a GitHub Release when `VERSION` bumps on `main`; `guard-default-branch.yml` is a direct-push backstop. A `protect-main` branch ruleset (`.github/rulesets/`) enforces PR-before-merge + the `ci` check + no force-push. See [`docs/CI.md`](docs/CI.md).

### Changed
- **Branded, collision-safe commands** — namespaced under a `lodestar-` prefix: `/onboard-repo` → `/lodestar-onboard`, `/guardrails` → `/lodestar-guardrails`, `/gen-agents` → `/lodestar-agents` (`/lodestar-init` unchanged). Avoids clashing with other tools' commands. Existing installs pick up the rename on the next `/lodestar-update`.

## [0.2.0] — Unreleased

Architecture, portability, and adaptivity pass over the 0.1.0 baseline. Catalog now **38 entries** — 17 universal · 14 Node·GraphQL·RN · 7 Python·Django.

### Added
- **Self-contained guardrail engine** — `emits: rule` guardrails now live in `.claude/guardrails/*.md` (a folder, not the `.claude/` root) enforced by a bundled PreToolUse hook (`templates/hooks/lodestar-guardrails.py`). **No external plugin dependency**; needs only Python 3 (stdlib). Tested against every catalog pattern.
- **Adaptive pickers** — `/lodestar-guardrails` and `/lodestar-agents` now recommend entries from repo signals, not just a static `recommended` flag. New capability detectors in `/lodestar-onboard`: `has-gitleaks`, `has-precommit`, `has-prettier`, `has-frontend`, `has-auth`.
- **Universal agents (+4)** — `security-auditor` (read-only OWASP-shaped audit; can call `/security-review`) and `docs-writer` (keep docs in sync), both `stacks: [all]`; plus frontend-scoped `ui-designer` (loads the `frontend-design` plugin skill) and `accessibility-reviewer` (WCAG 2.2 AA). `/lodestar-agents` resolves an agent's `loads:` dependencies and prompts to install a missing plugin (install-or-proceed).
- **Markdown architecture fallback** — when Graphify is absent, `/lodestar-onboard` offers to generate `architecture/overview.md` instead of requiring the tool (install-or-proceed prompt). Graphify confirmed to install at user level, no sudo.
- **Cost & model guidance** — per-command `effort` defaults (`low` for scaffolding, `medium` for onboard) and a README section; the biggest budget saver is installing Graphify (offloads the one reasoning-heavy step).
- **Evidence-based doc pre-fill** — `/lodestar-onboard` now fills the per-repo and `_shared/` docs from *cited* repo evidence (deps, routes/resolvers/serializers, `.env.example`, the graph) and leaves `TODO` only for the genuinely unknowable (TTLs, prod URLs, domain semantics, "why"), instead of dropping blank stubs. Never invents — a wrong doc is worse than an honest TODO.

### Changed
- **Stack-neutral universal core** — shared docs no longer assume GraphQL. The contract spine is a single stable `docs/_shared/api-contract.md`, seeded generic at init and enriched to GraphQL/REST only when that stack is actually detected. `repo-map`, `auth-model`, `env-matrix`, `local-setup`, and `glossary` de-GraphQL'd.
- Renamed the guardrail emit keyword `emits: hookify` → `emits: rule`.

### Fixed
- `block-env-files` carve-out now actually allows template files (`.env.example`/`.sample`/`.template`/`.dist`/`.defaults`) — the old regex blocked them.
- File guardrails now match the edited **path** as intended (the previous plugin matched edited *content*, so path-based rules never fired).
- Corrected stale `<api>-contract.md` placeholders and a Graphify output filename in the docs.

## [0.1.0] — Unreleased

Initial version — not yet published.

### Layers & commands
- Five-layer architecture: thin root router, on-demand knowledge (docs + skills), Graphify code graph, enforced guardrails, role-based agents.
- Four generator commands over one catalog + picker + manifest engine: `/lodestar-init`, `/lodestar-onboard`, `/lodestar-guardrails`, `/lodestar-agents`.

### Catalog (34 entries)
- **Universal core (15)** — guardrails `block-env-files`, `no-hand-edit-lockfiles`, `protect-generated-files`, `verifier-before-commit`, `commit-message-style`, `block-destructive-commands`, `block-secret-files`, `protect-default-branch`, `scan-secrets-before-commit`; agents `reviewer`, `feature-planner`, `feature-orchestrator`, `implementer`; skills `planning-workflow`, `architecture-overview`.
- **Node·GraphQL·React·React Native pack (12)** — dbmate/GraphQL/CRACO/React Native guardrails, agents, and skills.
- **Python·Django pack (7)** — Django migration guard, python autolint, migration-writer / drf-endpoint-writer / pytest test-writer agents, django-backend-standards + drf-api-contract skills.
- Grouped index in `catalog/CATALOG.md`; core-vs-packs tiers documented in `catalog/README.md`.

### Templates & docs
- Thin `CLAUDE.md` router, `_shared/` doc stubs (GraphQL + REST API contract, env matrix, auth, runbook, glossary), `repo-map.md`, per-repo conventions, per-workspace MCP configs.
- `.claude/lodestar.manifest.json` reproducible lockfile; `install.sh`; docs (`ARCHITECTURE`, `CONCEPTS`, `EXTENDING`) and an end-to-end example.

[0.5.0]: https://github.com/Miyunecadz/lodestar
[0.4.0]: https://github.com/Miyunecadz/lodestar
[0.3.0]: https://github.com/Miyunecadz/lodestar
[0.2.0]: https://github.com/Miyunecadz/lodestar
[0.1.0]: https://github.com/Miyunecadz/lodestar
