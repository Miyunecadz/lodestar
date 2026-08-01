# Changelog

All notable changes to Lodestar are documented here.

## [0.12.0] — Unreleased

Drift detection asked its question in the wrong repository. `mapping.lastMappedSha` is recorded from an onboarded repo's own HEAD, but the checker ran `git diff` in whatever directory it was invoked from — so it only ever worked when the workspace root *was* the git repo. In the separate-sub-repos layout that `ARCHITECTURE.md` §6 calls the default, the range could never resolve and every repo reported `that commit isn't in history`, drifted or not. Closes #21.

### Fixed
- **`lodestar-freshness-check.py` resolves each repo's git root and runs there.** Both layouts now fall out of one code path: a monorepo yields the workspace root plus a path prefix to filter by, separate sub-repos yield the repo itself and no prefix. The verdict no longer depends on the caller's working directory.
- **Three degraded states are now distinct**, because they need different advice: *no git repository at that path* (nothing to check), *the fingerprint is not in this repo's history* (a rewrite — re-map to reset), and *the diff could not be evaluated*. Collapsing them is what let a workspace where git was never consulted report a stale-fingerprint error.
- **`workspace_of()` derives the workspace from the manifest path**, not from `git rev-parse`, since the workspace root frequently is not a repository.

### Added
- **`.github/scripts/test-freshness.sh`** (new CI gate, 15 checks) — builds a workspace in each supported layout and asserts drift, freshness, cwd-independence, per-repo isolation in a monorepo, every degraded state, and that a missing or unparseable manifest still exits 0. Verified to fail against the previous implementation.

### Upgrading
Run `/lodestar-update`, which refreshes `.claude/hooks/lodestar-freshness-check.py` if you have it installed. No manifest or rule changes. If drift detection has been reporting `isn't in history` for every repo, that was this bug — the fingerprints in your manifest are fine and no re-map is needed.

## [0.11.0] — Unreleased

Design-guidance pass — Lodestar *referenced* Anthropic's `frontend-design` skill but only as a soft, opt-in dependency, so a frontend workspace could generate UI with no anti-slop guidance behind it and no signal that anything was missing. Closes #6.

### Added
- **`design-guidance-on-ui-edits`** — warns on edits to UI files while `designGuidance.installed` is false in the manifest, naming the two commands that fix it. It is **self-silencing**: once guidance is recorded it never fires again, and if the plugin was *declined* it keeps reminding rather than going quiet forever. A workspace with no manifest still gets the reminder — failing toward visible is the point.
- **`requires_manifest_missing` engine flag** — a rule fires only while a dotted manifest path is absent, `false`, or empty. This is the general primitive behind the above: it makes a reminder self-silencing instead of a permanent nag (which trains people to ignore every warn) or a one-shot message (indistinguishable from no rule). Documented in `docs/EXTENDING.md` with the failure-direction caveat.
- **`docs/spikes/impeccable-design-detector.md`** — the evaluation issue #6 asked for, with a decision and reasons.

### Changed
- **`ui-designer` is `recommended: true`.** It stays frontend-scoped, so it is pre-checked by default in exactly the workspaces that have a frontend and stays invisible in a backend-only one. A detected frontend no longer ends up with no design role at all.
- **Declining the `frontend-design` plugin is recorded and re-offered.** `/lodestar-agents` §5b now puts **install** first and marked recommended, then writes `designGuidance` (`skill` / `installed` / `decidedAt`, plus `status: declined`) into the manifest. A later run re-asks instead of treating one decline as permanent, and the report says plainly that UI has no anti-slop guidance behind it. The command must only write `installed: true` once the skill is genuinely available — a wrongly-recorded `true` silences the backstop for good.
- **`ui-designer`'s fallback text** now says it flags missing guidance *every* time, not once, and that proceeding without it is a quality cliff rather than a neutral choice.

### Spike outcome: Impeccable — defer, with a documented path

Issue #6 recommended evaluating [Impeccable](https://impeccable.style/) (Apache 2.0, free, by Paul Bakaus) as a stronger, deterministic complement. Verified today: the detector is real and genuinely LLM-free (`npx impeccable detect src/`, `--json` for CI), and the architectural claim in the issue is right — a no-LLM rules engine flagging anti-patterns pre-ship is the same shape as Lodestar's guardrail engine.

**Deferred as a guardrail-engine entry**, for four reasons: the engine is Python-stdlib-only and offline, and shelling out to `npx` on every UI edit puts a process spawn (and possible package fetch) on the hot path, where a rule that cannot run degrades to "allow"; the rule set is moving fast (reported as 46 in the issue, 59 on the site today, 60 elsewhere today), which is a good sign upstream and a poor basis for a pinned catalog entry whose text must describe what it enforces; exit codes are not in the documented CLI contract yet, and building a blocking gate on an undocumented exit code is how an upgrade breaks everyone's commits; and it is a *quality linter*, for which Lodestar already has the right shape — `emits: settings-hook` and CI — rather than the mechanism that blocks committing a private key.

The spike documents both integration paths (a `has-impeccable`-gated settings-hook entry, or a `npx impeccable detect --json` CI step), so adopting it later needs no engine changes. Nothing here blocks it.

### Notes on scope
- **Item C of the issue was not implementable as written.** It asked for a guardrail that fires when "no design skill is loaded in the session" — a `PreToolUse` hook has no view of which skills are loaded. The rule checks recorded workspace state instead (`designGuidance.installed`), which is the same intent and is actually checkable. Flagged before implementing.

### Upgrading

Re-run `/lodestar-agents` in a frontend workspace: `ui-designer` is now pre-checked, and the plugin prompt records its outcome. Re-run `/lodestar-guardrails` to pick up `design-guidance-on-ui-edits`. Until then nothing changes.

## [0.10.0] — Unreleased

Catalog-coverage pass — onboarding a Laravel/PHP + Next.js monorepo produced **zero** stack-specific entries for either repo, two of the most common web stacks, and the gap was recorded only as a string in the manifest. Closes #4.

### Added
- **Laravel · PHP pack** (7 entries) — `laravel-endpoint-writer` (route + controller + FormRequest + API Resource + policy, contract updated), `eloquent-migration-writer` (new migration with a real `down()`, model updated to match), `test-writer-php` (Pest or PHPUnit, matching the repo's existing style rather than introducing a second one), `laravel-backend-standards` skill, plus guardrails: `block-edit-applied-migrations-laravel` (blocks migrations git already tracks, leaves a freshly scaffolded one writable, enforced on the **commit** surface too), `protect-laravel-generated` (`bootstrap/cache/`, `storage/framework/`, Vite/Mix output), and `php-autolint-on-edit` (Pint, scoped to `has-pint`).
- **Next.js pack** (3 entries) — `nextjs-route-writer` (deliberate server/client boundary), `nextjs-frontend-standards` skill, and `nextjs-no-public-secrets`, a content-matching guardrail that warns when a `NEXT_PUBLIC_` variable looks like a secret. Every `NEXT_PUBLIC_` value is inlined into the client bundle, so prefixing a secret publishes it; it **warns** rather than blocks because the name alone cannot distinguish a Stripe publishable key from a secret one.
- **Stack detectors** — `laravel` (`artisan` / `laravel/framework`), `php` (`composer.json`), `nextjs` (`next` dep or `next.config.*`), `has-pint`, `has-pest`. Onboarding also records **which router** a Next.js repo uses (`app/` vs `pages/`): the file conventions and data-fetching APIs differ, and an agent that guesses writes code that silently never runs.
- **A detected gap now produces a document, not a manifest string.** New `kit/templates/docs/extending-gap.md` → generated as the workspace's `docs/EXTENDING.md` when a repo's stacks match no catalog entry, naming the unmatched tags, what the repo got instead (universal core only), and how to add a pack — upstream (preferred) or locally, with the trade-off that `/lodestar-update` refreshes `.lodestar/catalog/`. Appends per repo rather than overwriting. Onboarding also states the gap in its summary and records `catalogGaps.unmatchedStacks` + the doc path in the manifest.
- **Two validator checks** — CI now fails when `CATALOG.md`'s `Totals: **N entries**` line disagrees with the files on disk, or when any guardrail/agent/skill is missing from the listing. Both were verified to fail on deliberate drift; a pack nobody can find in the index is a pack nobody adopts.

### Fixed
- **`block-env-files` blocked per-tier templates.** Its lookahead only excused a bare `.env.example`, so `.env.local.example` / `.env.staging.sample` — committed templates that exist precisely so nobody needs the real file — were treated as live secrets. The lookahead now checks the end of the name. Found while probing the new Next.js rule, whose test case was being masked by this. Real `.env.local` / `.env.production` are still blocked; the engine suite now uses the catalog's actual pattern instead of a simplified copy, so this cannot regress unnoticed.
- **`autolint-on-edit` only matched `src/`.** Next.js App Router routes live in `app/`, Pages Router in `pages/`, and plenty of repos keep `components/`, `lib/`, or `hooks/` at the top level — all silently skipped. The pattern now covers those roots.

### Notes on scope
- **The issue's second half was already stale.** It says "the promised `docs/EXTENDING.md` was never generated", but the kit has shipped `docs/EXTENDING.md` as a contributor guide since before this work. The real gap was that a *workspace* had nothing — so the fix generates a workspace-local `docs/EXTENDING.md` about that workspace's unmatched stacks, and points at the kit guide for the mechanics. Two files, two audiences; the kit's guide is stack-agnostic and ships to everyone, so writing detected gaps into it would have been wrong.
- **Packs are deliberately thin.** Three guardrails, three narrow agents, one conventions skill for Laravel; the skill points at `docs/REPO/` and the agents point at the skill. Restating framework documentation in a catalog entry goes stale and burns context on every load — the pack's job is to encode *where things go in this repo* and *what must not happen*, not to teach the framework.
- **Not scaffolding stub packs** (item 3 of the issue, marked optional). A generated stub agent is an unversioned file in `.claude/` that looks official, and `/lodestar-update` will not maintain it. The generated `EXTENDING.md` steers to authoring a catalog entry instead, which is the shareable path. Happy to add scaffolding if you'd rather have it.

### Upgrading

Re-run `/lodestar-onboard ./<repo>` on a Laravel or Next.js repo to pick up the new detectors and skills, then `/lodestar-guardrails` and `/lodestar-agents` to tick the new entries. Existing repos are unaffected until you do.

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
