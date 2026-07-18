# <repo> — Conventions

<!-- TODO: One of these per repo, filed at `docs/<repo>/conventions.md`. Hand-written,
     repo-specific. `/lodestar-onboard` scaffolds this alongside the GENERATED
     `docs/<repo>/architecture/` (Graphify). Keep the human judgment here; leave the
     structural map to the generated graph. Fill from the repo's package.json and code. -->

Repo-specific conventions for **`<repo>`** <!-- TODO: name -->.
For the cross-repo picture see [`../_shared/`](../_shared/) and [`../../repo-map.md`](../../repo-map.md).

## Build & run

<!-- TODO: Pull the real commands from this repo's package.json `scripts`. -->

| Task | Command | Notes |
|---|---|---|
| Install | <!-- TODO: e.g. `npm install` --> | |
| Dev / run | <!-- TODO: e.g. `npm run dev` --> | |
| Build | <!-- TODO: e.g. `npm run build` --> | |
| <!-- TODO --> | | |

## Lint & format

<!-- TODO: eslint/prettier config location, whether it runs on commit (husky), how to fix. -->

- Lint: <!-- TODO: e.g. `npm run lint` -->
- Format: <!-- TODO: e.g. `npm run format` / prettier -->
- Pre-commit: <!-- TODO: husky hook? what does it run? -->

## Tests

<!-- TODO: Test runner, how to run all / one, coverage, where tests live. -->

- Run all: <!-- TODO: e.g. `npm test` -->
- Run one: <!-- TODO: e.g. `npm test -- <pattern>` -->
- Location / naming: <!-- TODO: e.g. `*.test.ts` next to source -->

## Notable patterns

<!-- TODO: The conventions a contributor must follow to match existing code.
     e.g. folder structure, how resolvers/components are organized, state management,
     error handling, codegen, naming. -->

- <!-- TODO -->
- <!-- TODO -->

## Gotchas

<!-- TODO: The non-obvious traps — the "wish someone had told me" list.
     e.g. required env vars, generated files not to edit, ordering dependencies,
     platform quirks (pods, native modules), flaky steps. -->

- <!-- TODO -->
- <!-- TODO -->
