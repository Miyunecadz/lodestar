# Walkthrough: adopting Lodestar on a 3-repo workspace

This is a concrete, end-to-end walkthrough of putting Lodestar on a realistic
workspace. It follows one team, `acme`, from three unrelated folders to a
coordinated, self-documenting workspace with enforced guardrails and role
agents — then walks a real feature through it.

The workspace has three repos:

| Repo | Stack |
|---|---|
| `admin-panel-be` | Node + Apollo GraphQL server + dbmate (MariaDB) + Redis/Bull |
| `admin-panel-fe` | React 18 + CRACO + Apollo Client + ag-grid + Tailwind |
| `mobile` | React Native 0.72 + NativeWind + React Navigation + Apollo Client + Firebase |

The backend serves a GraphQL API; both the web admin panel and the mobile app
consume it. That API boundary is the spine of the whole system — remember it,
because it's the one edge Lodestar keeps by hand.

---

## 1. Starting point

Before Lodestar, the workspace is just three sibling repos in a folder. The root
is not a git repo — it's plain directory holding three independent repos, each
with its own `.git`, CI, and history.

```
~/code/acme/
├── admin-panel-be/          ← its own git repo
│   ├── .git/
│   ├── package.json         (apollo-server, ioredis, bull, dbmate)
│   ├── dbmate.yml
│   ├── db/
│   │   ├── migrations/
│   │   └── schema.sql
│   └── src/
├── admin-panel-fe/          ← its own git repo
│   ├── .git/
│   ├── package.json         (@craco/craco, @apollo/client, ag-grid, tailwindcss)
│   ├── craco.config.js
│   └── src/
└── mobile/                  ← its own git repo
    ├── .git/
    ├── package.json         (react-native, @apollo/client, nativewind, firebase)
    ├── android/
    ├── ios/
    └── src/
```

Claude Code launched here has no shared picture: it sees whatever repo you point
it at, one at a time, with no map of how they connect.

---

## 2. Install

You've already cloned Lodestar to `~/tools/lodestar`. Install it into the
workspace by pointing the installer at the folder that contains your repos:

```bash
~/tools/lodestar/install.sh ~/code/acme
```

The installer is deliberately minimal. It copies the catalog and templates into
a hidden `.lodestar/`, drops the four generator commands where Claude Code looks
for them, and records the kit version. It does not touch your repos and does not
enforce or generate anything yet.

```
~/code/acme/
├── .lodestar/               ← the catalog + templates (the reusable asset)
│   ├── catalog/
│   │   ├── guardrails/      (block-edit-applied-migrations.md, block-env-files.md, …)
│   │   ├── agents/          (feature-planner.md, migration-writer.md, reviewer.md, …)
│   │   └── skills/          (planning-workflow/, backend-standards/, graphql-contract/, …)
│   ├── templates/           (CLAUDE.md router, docs/_shared/ stubs, repo-map)
│   └── VERSION
├── .claude/
│   └── commands/            ← the four generators, now available as slash commands
│       ├── lodestar-init.md
│       ├── onboard-repo.md
│       ├── guardrails.md
│       └── gen-agents.md
├── admin-panel-be/          ← untouched
├── admin-panel-fe/          ← untouched
└── mobile/                  ← untouched
```

Now launch Claude Code from the root and start initializing:

```bash
cd ~/code/acme
claude
```

---

## 3. `/lodestar-init`

`/lodestar-init` lays down the router and the shared knowledge scaffold. It
detects the sibling repos, asks how you want the Lodestar files tracked, then
writes the thin `CLAUDE.md`, the `docs/_shared/` stubs, `docs/repo-map.md`, the
two workspace-wide skills, and the manifest.

```
> /lodestar-init

Detected 3 repositories: admin-panel-be, admin-panel-fe, mobile

? How should Lodestar files be tracked in this workspace?
  › Personal / untracked (default) — leave the root as a plain folder
    Git workspace repo — git init the root and .gitignore the repos

Placement: personal
Created  CLAUDE.md                        (thin router + repo registry)
Created  docs/_shared/                    (5 stubs, with TODO markers)
Created  docs/repo-map.md                 (registry, pre-filled with 3 repos)
Installed skills: planning-workflow, architecture-overview
Created  .claude/lodestar.manifest.json
```

The resulting tree:

```
~/code/acme/
├── CLAUDE.md                             ← thin router (see below)
├── docs/
│   ├── _shared/                          ← cross-repo truth (stubs to fill in)
│   │   ├── graphql-contract.md           ← the spine: the API every repo agrees on
│   │   ├── env-matrix.md
│   │   ├── auth-model.md
│   │   ├── local-setup.md
│   │   └── glossary.md
│   └── repo-map.md                       ← the registry the router points at
├── .claude/
│   ├── commands/                         (the four generators)
│   ├── skills/
│   │   ├── planning-workflow/            ← when scoping a feature, before code
│   │   └── architecture-overview/        ← when tracing a flow across repos
│   └── lodestar.manifest.json
├── .lodestar/                            (catalog + templates)
├── admin-panel-be/
├── admin-panel-fe/
└── mobile/
```

The router stays tiny on purpose — it's the only thing that loads in full on
every session. It carries the repo registry and the loading policy, nothing
else:

```markdown
# acme — Workspace Router

## Repositories

- **admin-panel-be** — GraphQL API (Node/Apollo/dbmate/Redis). See docs/admin-panel-be/.
- **admin-panel-fe** — React/CRACO admin panel (Apollo Client/ag-grid/Tailwind). See docs/admin-panel-fe/.
- **mobile** — React Native app (Apollo Client/NativeWind/Firebase). See docs/mobile/.

Full map and cross-repo relationships: docs/repo-map.md

## Loading policy (do not remove — this keeps the router thin)
- Do not read docs eagerly. Skills declare when they apply — trust their triggers.
- Stay in the relevant repo. Don't load another repo's docs for a task in this one.
- Cross-repo truth lives in docs/_shared/. The API contract there is the spine.
- Architecture graphs are queryable — prefer docs/<repo>/architecture/graph.json over re-reading source.
```

Note what `/lodestar-init` did *not* do: no per-repo skills, no guardrails, no
agents. Stack-scoped work waits until each repo is onboarded and its stack is
known.

---

## 4. `/onboard-repo` for each repo

Onboarding is informational and non-destructive: it detects the stack, generates
the architecture graph, files repo docs, and installs the skills that match the
detected stack tags. Run it once per repo.

### `/onboard-repo ./admin-panel-be`

```
> /onboard-repo ./admin-panel-be

Detected stacks: graphql-apollo-server, node-dbmate, redis-queue, has-eslint, has-husky
  apollo-server-express in deps  → graphql-apollo-server
  dbmate.yml present             → node-dbmate
  bull + ioredis in deps         → redis-queue
  eslint config present          → has-eslint
  .husky/ present                → has-husky

Graphify: running graphify ./admin-panel-be …
  → docs/admin-panel-be/architecture/{graph.html, GRAPH_REPORT.md, graph.json}
Created  docs/admin-panel-be/conventions.md   (pre-filled from package.json scripts)
Installed skills: backend-standards, graphql-contract
```

The stack tags select the skills: `graphql-apollo-server` and `node-dbmate` map
to `backend-standards`, and `graphql-apollo-server` also pulls in
`graphql-contract` (the shared-surface skill). Each skill body is parameterized
to point at `docs/admin-panel-be/…`, so it routes to the right docs without
copying them.

### `/onboard-repo ./admin-panel-fe`

```
> /onboard-repo ./admin-panel-fe

Detected stacks: react-craco, graphql-apollo-client, has-eslint, has-husky
  @craco/craco in deps   → react-craco
  @apollo/client in deps → graphql-apollo-client
  eslint config present  → has-eslint
  .husky/ present        → has-husky

Graphify: running graphify ./admin-panel-fe …
  → docs/admin-panel-fe/architecture/{graph.html, GRAPH_REPORT.md, graph.json}
Created  docs/admin-panel-fe/conventions.md
Installed skills: frontend-standards   (graphql-contract already present — skipped)
```

`react-craco` maps to `frontend-standards`; `graphql-apollo-client` would map to
`graphql-contract`, but that skill is already installed from the backend, so it's
left as-is — a single source of truth, shared across both consumers.

### `/onboard-repo ./mobile`

```
> /onboard-repo ./mobile

Detected stacks: react-native, graphql-apollo-client, has-eslint
  react-native in deps   → react-native
  @apollo/client in deps → graphql-apollo-client
  eslint config present  → has-eslint

Graphify: not installed — skipping graph generation.
Created  docs/mobile/architecture/README.md   (install + run instructions instead)
Created  docs/mobile/conventions.md
Installed skills: mobile-standards   (graphql-contract already present — skipped)
```

### The Graphify step and its fallback

When the `graphify` CLI is installed, onboarding runs it and files
`graph.html`, `GRAPH_REPORT.md`, and `graph.json` under
`docs/<repo>/architecture/`. Because Graphify is deterministic, re-running it is
cheap — that's how Lodestar beats architecture-doc drift for *structure*.

When Graphify is not installed (as with `mobile` above), onboarding does not
fail. It writes `docs/mobile/architecture/README.md` with the exact install and
run commands so you can generate the graph later:

```bash
uv tool install graphifyy        # or: pipx install graphifyy
graphify install
graphify ./mobile                # then move outputs into docs/mobile/architecture/
```

One caveat holds for every graph: Graphify draws only *static* edges (imports,
calls). The backend, web, and mobile repos talk over GraphQL at *runtime* — they
don't import each other — so no per-repo graph shows that connection. The
cross-repo spine stays hand-written in `docs/_shared/graphql-contract.md`. That's
the correct division of labor: the parser knows static structure, a human states
the runtime contract.

---

## 5. `/guardrails`

With the stacks known, `/guardrails` turns advisory docs into enforced rules. It
collects the union of stacks across all onboarded repos, filters the guardrail
catalog to the ones that apply, and presents a multi-select menu grouped by
category. Recommended (safety) rules come pre-checked; each option is tagged
`[block]` or `[warn]`.

```
> /guardrails

Workspace stacks: graphql-apollo-server, node-dbmate, redis-queue,
                  react-craco, graphql-apollo-client, react-native, has-eslint, has-husky

Select guardrails to enforce  (space = toggle, enter = confirm)

Database
  [x] Block edits to applied DB migrations           [block]  (recommended)
  [x] Protect the dbmate-generated schema            [block]  (recommended)
Secrets
  [x] Block reads and writes of .env files           [block]  (recommended)
Dependencies
  [x] No hand-editing lockfiles                       [block]  (recommended)
  [x] Persist node_modules edits with patch-package   [block]
Generated
  [x] Protect generated and binary artifacts          [block]  (recommended)
Quality
  [x] Auto-lint source files on edit                  [warn]
  [ ] Review staged diff before committing            [warn]
```

Here the team accepts all five recommended safety rules, adds
`mobile-use-patch-package` (because `mobile` uses patch-package) and
`autolint-on-edit`, and leaves the commit-review reminder off. Confirming writes:

```
Enabled — block (stop + redirect):
  .claude/hookify.block-edit-applied-migrations.local.md
  .claude/hookify.protect-dbmate-schema.local.md
  .claude/hookify.block-env-files.local.md
  .claude/hookify.no-hand-edit-lockfiles.local.md
  .claude/hookify.protect-generated-files.local.md
  .claude/hookify.mobile-use-patch-package.local.md

Enabled — warn (inform, don't stop):
  .claude/settings.json  (autolint-on-edit → PostToolUse lint router)

Manifest updated.
```

### Block versus warn

The severity of a rule decides what happens when it fires, and that's a
deliberate choice — match enforcement strength to the cost of a violation.

- **block** rules stop the action *and redirect* to the correct one. Most rules
  are declarative **hookify** files, written as `.claude/hookify.<id>.local.md`.
  For example, `block-edit-applied-migrations`:

  ```markdown
  ---
  name: block-edit-applied-migrations
  enabled: true
  event: file
  pattern: 'db/migrations/.*\.sql$'
  severity: block
  ---

  BLOCKED. dbmate tracks applied migrations in `schema_migrations` and
  regenerates `db/schema.sql` from them; editing an already-applied migration
  desyncs the tracked schema and corrupts history. Do NOT edit this file —
  create a NEW migration with `yarn db:new <name>` and write your forward and
  rollback SQL there.
  ```

- **warn** rules inform without halting the flow. `autolint-on-edit` is the one
  rule here that needs custom logic — it must route an edited file to the linter
  of whichever repo it lives in — so it's emitted as a `settings.json` hook
  rather than a portable hookify file.

The `.local.md` suffix keeps these files out of version control by default. They
contain no secrets and are safe to share.

---

## 6. `/gen-agents`

`/gen-agents` writes opt-in role workers. Roles are narrow and composable, with
a crisp done-condition and a minimal tool profile — breadth stays in the
orchestrator, not the workers. The menu separates cross-repo roles from
stack-scoped roles, and pre-checks the recommended ones.

```
> /gen-agents

Select role agents to generate  (space = toggle, enter = confirm)

Cross-repo roles
  [x] Feature planner — turn a request into a cross-repo plan; no code   [Read, Grep, Glob, Bash]  (recommended)
  [x] Reviewer — read-only audit of a staged diff                        [Read, Grep, Glob, Bash]  (recommended)
  [x] Feature orchestrator — plan + dispatch specialists + integrate     [Read, Grep, Glob, Bash]
  [x] Implementer — cohesive multi-file change in ONE repo (safety valve)[Read, Edit, Write, Grep, Glob, Bash]

Stack-scoped roles
  [x] Migration writer (dbmate)                                          [Read, Edit, Write, Grep, Glob, Bash]  (recommended)
  [x] Resolver writer (GraphQL + shield)                                 [Read, Edit, Write, Grep, Glob, Bash]
  [ ] Release runner (mobile build/release)                              [Read, Grep, Glob, Bash]
  [ ] Test writer (jest)                                                 [Read, Edit, Write, Grep, Glob, Bash]
```

### The repo-targeting question

Stack-scoped roles are *parameterized by the repo they point at*. After you pick
them, the command works out which onboarded repos match each role's stacks. If
more than one repo matches, it asks which repo(s) to generate the role for and
writes one agent per repo, suffixed with the repo name.

Here each stack-scoped role matches exactly one repo, so no question is needed:

```
Resolving repo targets for stack-scoped roles:
  migration-writer → node-dbmate           → admin-panel-be   (single match)
  resolver-writer  → graphql-apollo-server  → admin-panel-be   (single match)

Generated .claude/agents/:
  feature-planner.md
  reviewer.md                       (read-only: no Edit/Write in tools)
  feature-orchestrator.md
  implementer.md
  migration-writer-admin-panel-be.md
  resolver-writer-admin-panel-be.md

Manifest updated.
```

Each generated agent has a thin body. It names the repo it works in, tells the
agent which skill and docs to load on start, and sets its tool profile — it never
copies the skill's content. For instance,
`.claude/agents/migration-writer-admin-panel-be.md`:

```markdown
---
name: migration-writer-admin-panel-be
description: >
  Use to add a database migration safely with dbmate in admin-panel-be.
  Creates a new migration only — never edits an already-applied one.
tools: [Read, Edit, Write, Grep, Glob, Bash]
---

You add a single, safe database migration to **admin-panel-be**.
On start, load the `backend-standards` skill and read docs/admin-panel-be/.

Done-condition: a new migration file with correct forward AND rollback SQL.

1. Create a NEW migration with `yarn db:new <name>` — never edit an existing file.
2. Write the forward migration and its matching rollback.
3. Never touch an already-applied migration or db/schema.sql (a guardrail also blocks this).
```

Note the tool profiles do the real work: `reviewer` is read-only (no
`Edit`/`Write`), while `migration-writer` can run `Bash`. Getting the allowlist
right matters more than the persona text.

---

## 7. A day in the life: add `phoneNumber` to users, end to end

A product request lands: **let users store a phone number, visible in the admin
panel and editable in the mobile app.** This touches all three repos, so it's a
job for the planner and orchestrator.

### The planner decomposes it

The main session delegates to `feature-planner`, which loads the
`planning-workflow` skill and reads `docs/_shared/graphql-contract.md` and
`docs/repo-map.md` first. Following the workflow, it identifies the *contract
change first*, because that drives everything else, then breaks the rest into
role-sized tasks tagged by repo and ordered by dependency:

```
Plan: add User.phoneNumber end to end

1. [contract]         docs/_shared  · Add nullable `phoneNumber: String` to the
                                      User type in graphql-contract.md (additive-first,
                                      so old clients keep working). Drives 2–5.
2. [migration-writer] admin-panel-be · New dbmate migration adding a phone_number column.
3. [resolver-writer]  admin-panel-be · Add phoneNumber to the User schema type + resolver +
                                      graphql-shield rule; update the contract doc.
4. [implementer]      admin-panel-fe · Extend the users query/fragment (Apollo hook) and add
                                      a phoneNumber column to the ag-grid users table.
5. [implementer]      mobile         · Add phoneNumber to the profile query and screen field.
6. [reviewer]         (staged diff)  · Audit before commit.

Order: 1 → 2 → 3, then 4 and 5 in parallel, then 6.
```

### The migration guardrail redirects a wrong turn

The `migration-writer-admin-panel-be` agent starts on task 2. Its first instinct
is to add the column to the existing `create_users` migration — the file that
already defines the table. That file has already been applied, and editing it
would desync the dbmate-tracked schema. The guardrail catches it before any harm:

```
Edit → admin-panel-be/db/migrations/20250104120000_create_users.sql

⛔ BLOCKED by hookify.block-edit-applied-migrations
   dbmate tracks applied migrations in schema_migrations and regenerates
   db/schema.sql from them; editing an already-applied migration desyncs the
   tracked schema and corrupts history. Do NOT edit this file — create a NEW
   migration with `yarn db:new <name>`.
```

This is the block-versus-advisory distinction paying off: a doc saying "don't
edit applied migrations" would eventually be ignored, but the hook makes it
impossible and points at the right action. The agent follows the redirect:

```bash
$ yarn db:new add_phone_number_to_users
  created db/migrations/20250718101500_add_phone_number_to_users.sql
```

It writes the forward SQL (`ALTER TABLE users ADD COLUMN phone_number VARCHAR(32) NULL;`)
and the matching rollback (`ALTER TABLE users DROP COLUMN phone_number;`), leaving
`db/schema.sql` for dbmate to regenerate on the next migrate.

### The orchestrator dispatches the roles

Instead of doing everything in one thread, the main session hands the plan to
`feature-orchestrator`, which holds the whole-system map and dispatches the
depth. It sequences the dependent tasks and parallelizes the independent ones:

```
feature-orchestrator
├── migration-writer-admin-panel-be    → new migration                (task 2)
├── resolver-writer-admin-panel-be     → schema field + shield rule +  (task 3, after 2)
│                                         updates graphql-contract.md
├── ┬ implementer  → admin-panel-fe    → Apollo hook + ag-grid column  (task 4) ┐ in
│   └ implementer  → mobile            → profile query + screen field  (task 5) ┘ parallel
└── reviewer                           → audit the staged diff         (task 6)
```

The `resolver-writer` runs after the migration because it depends on the column
existing, and it updates `docs/_shared/graphql-contract.md` in the same change so
the contract never drifts from the surface. The two `implementer` runs are
independent — one scoped to the admin panel's files, one to the mobile app's —
so they run in parallel, each pointed at its repo and each respecting the
workspace guardrails. Finally `reviewer` audits the combined staged diff
read-only and reports findings by severity. Breadth stayed at the top; the hands
stayed at the bottom.

---

## 8. Result tree

After init, onboarding, guardrails, and agents, the workspace looks like this —
every generated artifact in one place, the three repos still independent:

```
~/code/acme/
├── CLAUDE.md                                   ← thin router (repo registry + loading policy)
├── docs/
│   ├── _shared/
│   │   ├── graphql-contract.md                 ← the cross-repo spine (hand-written)
│   │   ├── env-matrix.md
│   │   ├── auth-model.md
│   │   ├── local-setup.md
│   │   └── glossary.md
│   ├── repo-map.md
│   ├── admin-panel-be/
│   │   ├── architecture/                       ← Graphify: graph.html, GRAPH_REPORT.md, graph.json
│   │   └── conventions.md
│   ├── admin-panel-fe/
│   │   ├── architecture/                       ← Graphify output
│   │   └── conventions.md
│   └── mobile/
│       ├── architecture/README.md              ← Graphify not installed: install + run notes
│       └── conventions.md
├── .claude/
│   ├── commands/                               (lodestar-init, onboard-repo, guardrails, gen-agents)
│   ├── skills/
│   │   ├── planning-workflow/                  (workspace-wide)
│   │   ├── architecture-overview/              (workspace-wide)
│   │   ├── backend-standards/                  (→ admin-panel-be)
│   │   ├── graphql-contract/                   (shared surface)
│   │   ├── frontend-standards/                 (→ admin-panel-fe)
│   │   └── mobile-standards/                   (→ mobile)
│   ├── agents/
│   │   ├── feature-planner.md
│   │   ├── reviewer.md
│   │   ├── feature-orchestrator.md
│   │   ├── implementer.md
│   │   ├── migration-writer-admin-panel-be.md
│   │   └── resolver-writer-admin-panel-be.md
│   ├── hookify.block-edit-applied-migrations.local.md   [block]
│   ├── hookify.protect-dbmate-schema.local.md           [block]
│   ├── hookify.block-env-files.local.md                 [block]
│   ├── hookify.no-hand-edit-lockfiles.local.md          [block]
│   ├── hookify.protect-generated-files.local.md         [block]
│   ├── hookify.mobile-use-patch-package.local.md        [block]
│   ├── settings.json                                    (autolint-on-edit → warn)
│   └── lodestar.manifest.json                           ← the lockfile
├── .lodestar/                                  (catalog + templates + VERSION)
├── admin-panel-be/                             ← still its own git repo
├── admin-panel-fe/                             ← still its own git repo
└── mobile/                                     ← still its own git repo
```

The manifest is the lockfile for all of it — commit or share it, and the same
setup reproduces elsewhere:

```json
{
  "version": "0.2.0",
  "placement": "personal",
  "repos": [
    { "name": "admin-panel-be", "path": "./admin-panel-be", "stacks": ["graphql-apollo-server", "node-dbmate", "redis-queue", "has-eslint", "has-husky"] },
    { "name": "admin-panel-fe", "path": "./admin-panel-fe", "stacks": ["react-craco", "graphql-apollo-client", "has-eslint", "has-husky"] },
    { "name": "mobile", "path": "./mobile", "stacks": ["react-native", "graphql-apollo-client", "has-eslint"] }
  ],
  "skills": ["planning-workflow", "architecture-overview", "backend-standards", "graphql-contract", "frontend-standards", "mobile-standards"],
  "guardrails": ["block-edit-applied-migrations", "protect-dbmate-schema", "block-env-files", "no-hand-edit-lockfiles", "protect-generated-files", "mobile-use-patch-package", "autolint-on-edit"],
  "agents": ["feature-planner", "reviewer", "feature-orchestrator", "implementer", "migration-writer-admin-panel-be", "resolver-writer-admin-panel-be"]
}
```

Adding a fourth repo later is one command — `/onboard-repo ./new-service` — and
the router never changes. Map at the top, hands at the bottom.
