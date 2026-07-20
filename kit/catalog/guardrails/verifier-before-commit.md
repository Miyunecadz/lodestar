---
id: verifier-before-commit
title: Review staged diff before committing
category: quality
severity: warn
recommended: false
stacks: [all]
event: bash
pattern: 'git commit'
emits: rule
---

Before committing a non-trivial change, dispatch the `reviewer` agent on the staged diff (`git diff --cached`) to catch issues a regex can't — logic errors, missing cases, leaked debug code. This is advisory: it reminds you, it does not block the commit.
