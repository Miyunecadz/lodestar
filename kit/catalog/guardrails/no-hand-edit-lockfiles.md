---
id: no-hand-edit-lockfiles
title: No hand-editing lockfiles
category: dependencies
severity: block
recommended: true
stacks: [all]
event: file
pattern: '(^|/)(yarn\.lock|package-lock\.json|pnpm-lock\.yaml|poetry\.lock|Pipfile\.lock|Cargo\.lock|go\.sum|Gemfile\.lock|composer\.lock)$'
emits: rule
---

Lockfiles are machine-generated; hand-edits produce inconsistent, unresolvable dependency trees. Change dependencies via the package manager and let it rewrite the lockfile for you — e.g. `yarn add` / `npm install` / `pnpm add` (JS), `poetry add` / `pipenv install` (Python), `cargo add` (Rust), `go get` (Go), `bundle add` (Ruby), `composer require` (PHP).
