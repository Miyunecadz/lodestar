Every pull request edited the same single line of `VERSION` and inserted at the same spot — the top — of `CHANGELOG.md`. Two open PRs therefore conflicted every time, structurally: not because of the branching model or the merge method, but because both files have exactly one hot line. Across five consecutive PRs the conflicts were never once in real code.

Feature PRs now add a file to `changelog.d/` instead, and two PRs adding two different files cannot conflict.

### Added
- **`changelog.d/`** — one Markdown fragment per PR, holding the body of the changelog section. No `## [version]` heading; that is the release script's job.
- **`.github/scripts/release.py <version>`** — folds every fragment into a new `CHANGELOG.md` section, bumps `VERSION`, deletes the fragments, and **stamps the previous version's release date**. That last step was manual before, which is why it was missed for twelve versions. Refuses an already-tagged version and refuses to run with no fragments; `--dry-run` shows the plan.
- **`validate.py` checks fragments** are `.md`, non-empty, and carry no `## [version]` heading — a fragment is not read by a reviewer until release, so what would have been a review comment has to be a check.

### Changed
- **`validate.py` accepts both valid states of the top heading.** `— Unreleased` while the release PR is open and no tag exists, a date once merged and tagged. The previous rule assumed a version bump in every PR, which no longer happens.
- **`CONTRIBUTING.md` and `docs/CI.md`** describe the fragment flow; the old "bump `VERSION` and add a matching top entry" instruction is gone.
