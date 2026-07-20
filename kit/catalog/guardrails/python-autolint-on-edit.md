---
id: python-autolint-on-edit
title: Auto-format Python on edit
category: quality
severity: warn
recommended: false
stacks: [has-python-lint]
event: file
pattern: '\.py$'
emits: settings-hook
---

After editing a `.py` file, run that repo's formatter/linter on just the changed file (`ruff --fix` / `black` / `flake8`). This emits a `settings.json` PostToolUse hook that must ROUTE by which repo the edited file lives in and skip any repo with no Python linter configured. Warns, does not block.
