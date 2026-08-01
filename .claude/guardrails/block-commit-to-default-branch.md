---
name: block-commit-to-default-branch
enabled: true
severity: block
stacks: [all]
event: bash
pattern: '(^|[;&|]\s*)git(\s+-\S+)*\s+(commit|push)\b'
only_on_default_branch: true
match: argv
surface: [agent, commit]
commit_check: default-branch
---

You are on the repository's **default branch** (`main`/`master`), so this commit or push would land straight on trunk — bypassing review, CI, and any branch protection the team relies on. Create a feature branch first and commit there:

```
git switch -c feat/<short-name>
```

Already staged? The branch switch carries staged changes with it — `git switch -c` then commit as normal. Already committed to the default branch by accident? Move the commit onto a branch before pushing: `git branch feat/<name> && git reset --hard @~1` (from the default branch), then `git switch feat/<name>`.

How this knows: `only_on_default_branch: true` asks the engine for the current branch (`git symbolic-ref --short HEAD`) and the repo's default (`origin/HEAD`, falling back to `init.defaultBranch`, then an existing local `main`/`master`). The rule fires **only** when both are known and equal — a detached HEAD, a shallow checkout with no `origin/HEAD`, or no git at all leaves it silent rather than blocking legitimate work, so treat it as a mistake-catcher and not a substitute for server-side branch protection. Sibling of [[protect-default-branch]], which covers force-push on any branch.

**Surface: `both`.** The commit-time check (`commit_check: default-branch`) is the stronger half — it stops a direct trunk commit from *anyone*, not just Claude, which is what this rule was always trying to do. Still not a substitute for server-side branch protection, which is the only version a determined committer cannot bypass with `--no-verify`.
