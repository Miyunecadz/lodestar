---
id: php-autolint-on-edit
title: Auto-format PHP files on edit (Pint)
category: quality
severity: warn
recommended: false
stacks: [has-pint]
event: file
pattern: '\.php$'
surface: agent
emits: settings-hook
---

After editing a PHP file, run this repo's formatter on just the changed file — `./vendor/bin/pint <file>` (Laravel Pint, which wraps PHP-CS-Fixer and ships with Laravel). This emits a `settings.json` PostToolUse hook that must ROUTE by which repo the edited file lives in and skip any repo with no Pint config. It overlaps a pre-commit hook but fires earlier — per-edit rather than per-commit.

Scoped to `has-pint` rather than `laravel` because a PHP repo may use PHP-CS-Fixer or PHP_CodeSniffer directly; running Pint where it isn't configured would reformat against the wrong ruleset. **Surface: `agent`** — formatting is not a safety property, and a commit-time reformat would rewrite a teammate's staged content behind their back.
