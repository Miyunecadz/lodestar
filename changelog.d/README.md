# Changelog fragments

Drop one Markdown file here per pull request. Do **not** edit `CHANGELOG.md` or `VERSION`
in a feature PR — `.github/scripts/release.py` does both at release time.

```
changelog.d/
  26-catalog-fixtures.md
  30-lean-block-messages.md
```

## Why

Every PR used to edit the same single line of `VERSION` and insert at the same spot — the
top — of `CHANGELOG.md`. Two open PRs conflicted every time, structurally: not because of
the branching model or the merge method, but because both files have exactly one hot line.
The conflicts were never in real code.

Two PRs adding two different files cannot conflict.

## Writing one

Name it `<issue>-<slug>.md` so the directory sorts usefully and two PRs never pick the
same name. The file is the **body** of the changelog section — no `## [version]` heading,
that is `release.py`'s job. Otherwise write it exactly as you would have written the
section itself:

```markdown
The engine required Python 3.9+ without saying so, and on 3.8 it did not fail — it
*allowed*. Closes #29.

### Fixed
- `fm | {...}` → `dict(fm, _message=body)`. The dict-union operator is 3.9+.

### Added
- A CI Python matrix covering the declared floor and the current release.
```

Fragments are concatenated in filename order under one version heading, so lead with the
prose that explains *why*, then the `### Fixed` / `### Added` / `### Changed` lists.

## Cutting a release

```bash
python3 .github/scripts/release.py 0.19.0 --dry-run   # see what would happen
python3 .github/scripts/release.py 0.19.0             # write it
```

That folds every fragment into a new `CHANGELOG.md` section, bumps `VERSION`, deletes the
fragments, and stamps the *previous* version's release date — which was a manual step
before, and therefore one that got forgotten. Commit on a branch and open a PR; merging it
changes `VERSION` on `main`, which is what triggers `release.yml`.
