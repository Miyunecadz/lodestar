---
id: autolint-on-edit
title: Auto-lint source files on edit
category: quality
severity: warn
recommended: false
stacks: [has-eslint]
event: file
pattern: 'src/.*\.(js|jsx|ts|tsx)$'
emits: settings-hook
---

After editing a source file, run that repo's linter/formatter (`eslint --fix` / `prettier`) on just the changed file. This emits a `settings.json` PostToolUse hook that must ROUTE by which repo the edited file lives in and skip any repo with no linter configured. It overlaps husky pre-commit hooks but fires earlier — per-edit rather than per-commit.
