#!/usr/bin/env python3
"""Fold `changelog.d/` fragments into CHANGELOG.md and bump VERSION.

Why fragments exist: every pull request used to edit the same single line of `VERSION`
and insert at the same spot — the top — of `CHANGELOG.md`. Two open PRs therefore
conflicted every time, structurally, no matter how they were merged. The conflicts were
never in real code; they were always those two files.

So feature PRs no longer touch either. Each adds one **new file** under `changelog.d/`,
and two PRs adding two different files cannot conflict. This script is what turns a pile
of fragments into a release, and it is the only thing that writes `VERSION`.

    python3 .github/scripts/release.py 0.19.0        # write the release
    python3 .github/scripts/release.py 0.19.0 --dry-run

It also **stamps the previous version's release date**. That was a manual step before —
`VERSION` is bumped in the PR *before* the tag exists, so the heading says `Unreleased`
until someone remembers to date it later. Doing it here means the reminder is a script,
not a habit.

Fragment files are Markdown bodies with no `## [version]` heading of their own — the
heading is this script's job. Name them `<issue>-<slug>.md` so the directory sorts
usefully and two PRs never pick the same name.
"""

import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FRAGMENTS = os.path.join(ROOT, "changelog.d")
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")
VERSION = os.path.join(ROOT, "VERSION")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def tag_date(version):
    """The date `vX.Y.Z` was tagged, or None if the tag does not exist here."""
    proc = subprocess.run(
        ["git", "log", "-1", "--format=%cI", "v" + version],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        return None
    out = proc.stdout.decode("utf-8", "replace").strip()
    return out[:10] or None


def read_fragments():
    """[(filename, body)] sorted by name, skipping the directory's own README."""
    if not os.path.isdir(FRAGMENTS):
        return []
    out = []
    for name in sorted(os.listdir(FRAGMENTS)):
        if not name.endswith(".md") or name == "README.md":
            continue
        body = open(os.path.join(FRAGMENTS, name)).read().strip()
        if not body:
            sys.exit("%s is empty — a fragment with nothing in it is a merge conflict "
                     "waiting to be nothing at all" % name)
        if re.search(r"^##\s*\[", body, re.M):
            sys.exit("%s contains a '## [version]' heading — fragments are bodies only, "
                     "the heading is release.py's job" % name)
        out.append((name, body))
    return out


def stamp_previous(text):
    """Date the top heading if its version is already tagged.

    `VERSION` is bumped in the PR *before* release.yml creates the tag, so the newest
    heading legitimately reads `Unreleased` for the minutes between merge and tag. It
    stops being legitimate at the next release, which is exactly now.
    """
    m = re.search(r"^##\s*\[(\d+\.\d+\.\d+)\]\s*—\s*Unreleased\s*$", text, re.M)
    if not m:
        return text, None
    previous = m.group(1)
    date = tag_date(previous)
    if not date:
        return text, None
    return text[:m.start()] + "## [%s] — %s" % (previous, date) + text[m.end():], previous


def main(argv):
    dry_run = "--dry-run" in argv
    args = [a for a in argv if not a.startswith("-")]
    if len(args) != 1 or not SEMVER.match(args[0]):
        sys.exit("usage: release.py <major.minor.patch> [--dry-run]")
    version = args[0]

    if tag_date(version):
        sys.exit("v%s is already tagged — pick the next version" % version)

    fragments = read_fragments()
    if not fragments:
        sys.exit("no fragments in changelog.d/ — nothing to release")

    text = open(CHANGELOG).read()
    if re.search(r"^##\s*\[%s\]" % re.escape(version), text, re.M):
        sys.exit("CHANGELOG.md already has a [%s] section" % version)

    text, stamped = stamp_previous(text)

    body = "\n\n".join(b for _, b in fragments)
    section = "## [%s] — Unreleased\n\n%s\n\n" % (version, body)
    anchor = re.search(r"^##\s*\[", text, re.M)
    if not anchor:
        sys.exit("CHANGELOG.md has no '## [' section to insert above")
    text = text[:anchor.start()] + section + text[anchor.start():]

    print("release %s" % version)
    if stamped:
        print("  stamped %s with its release date" % stamped)
    for name, _ in fragments:
        print("  + %s" % name)

    if dry_run:
        print("\n--dry-run: nothing written")
        return 0

    open(CHANGELOG, "w").write(text)
    open(VERSION, "w").write(version + "\n")
    for name, _ in fragments:
        os.remove(os.path.join(FRAGMENTS, name))
    print("\nwrote CHANGELOG.md, VERSION, and removed %d fragment(s)." % len(fragments))
    print("Commit on a branch and open a PR — merging it triggers release.yml.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
