---
id: autolint-on-edit
title: Auto-lint source files on edit
category: quality
severity: warn
recommended: false
stacks: [has-eslint]
event: file
pattern: '(^|/)(src|app|pages|components|lib|hooks)/.*\.(js|jsx|ts|tsx)$'
surface: agent
emits: settings-hook
---

After editing a source file, run that repo's linter/formatter (`eslint --fix` / `prettier`) on just the changed file. This emits a `settings.json` PostToolUse hook that must ROUTE by which repo the edited file lives in and skip any repo with no linter configured. It overlaps husky pre-commit hooks but fires earlier — per-edit rather than per-commit.

---

The path list covers the common roots across frameworks, not just `src/`: a Next.js App Router repo keeps routes in `app/`, a Pages Router repo in `pages/`, and plenty of repos put shared code in `components/`, `lib/`, or `hooks/` at the top level. Matching only `src/` silently skipped all of those.
