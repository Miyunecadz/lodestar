#!/usr/bin/env python3
"""Lodestar catalog + consistency validator (used by CI).

Checks, with stdlib only:
  - every guardrail has the required frontmatter, valid enums, and a compilable regex;
  - every agent/skill has the required frontmatter;
  - VERSION matches the top CHANGELOG entry;
  - every CHANGELOG heading's release status matches the actual git tags.
Exits non-zero (listing every problem) if anything is off.
"""
import os
import re
import sys
import glob
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
errors = []


def frontmatter(path):
    """Return a dict of top-level `key: value` pairs from the file's --- frontmatter."""
    with open(path) as f:
        text = f.read()
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = {}
    for line in parts[1].splitlines():
        if not line.strip() or line[:1] in (" ", "\t", "#"):
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


VALID_SURFACES = ("agent", "commit", "permission")


def surfaces_of(value):
    """Frontmatter `surface` → the set of mechanisms it names.

    Accepts a scalar or an inline list. `both` is the pre-permission-surface spelling
    of `[agent, commit]` and stays valid, so installed rule files keep working.
    """
    raw = (value or "").strip()
    if raw.startswith("[") and raw.endswith("]"):
        names = {p.strip().strip('"').strip("'").lower() for p in raw[1:-1].split(",") if p.strip()}
    else:
        names = {raw.lower()} if raw else set()
    if "both" in names:
        names.discard("both")
        names |= {"agent", "commit"}
    return names


def check_guardrails():
    for path in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/guardrails/*.md"))):
        rel = os.path.relpath(path, ROOT)
        fm = frontmatter(path)
        for key in ("id", "severity", "stacks", "event", "pattern", "emits", "surface"):
            if key not in fm:
                errors.append(f"{rel}: missing frontmatter key '{key}'")
        if fm.get("severity") not in ("block", "warn"):
            errors.append(f"{rel}: severity must be block|warn (got {fm.get('severity')!r})")
        if fm.get("event") not in ("file", "bash", "all"):
            errors.append(f"{rel}: event must be file|bash|all (got {fm.get('event')!r})")
        if fm.get("emits") not in ("rule", "settings-hook"):
            errors.append(f"{rel}: emits must be rule|settings-hook (got {fm.get('emits')!r})")
        surfaces = surfaces_of(fm.get("surface"))
        if not surfaces:
            errors.append(f"{rel}: missing frontmatter key 'surface'")
        unknown = sorted(surfaces - set(VALID_SURFACES))
        if unknown:
            errors.append(
                f"{rel}: unknown surface(s) {unknown} — valid are "
                f"{list(VALID_SURFACES)} or the legacy scalar 'both'")
        # A permission-surface rule needs the deny entries spelled out: a regex does
        # not translate to a gitignore-style glob, so the author states both forms.
        if "permission" in surfaces:
            entries = fm.get("permission_rules", "").strip()
            parsed = [p.strip().strip('"').strip("'")
                      for p in entries.strip("[]").split(",") if p.strip()]
            if not parsed:
                errors.append(f"{rel}: surface 'permission' needs a non-empty permission_rules list")
            for entry in parsed:
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*\(.+\)", entry):
                    errors.append(
                        f"{rel}: permission_rules entry {entry!r} is not a Tool(pattern) rule "
                        f"(e.g. 'Read(./.env)')")
        # A commit-surface rule needs something the pre-commit checker can actually run:
        # a `file` pattern (checked against staged paths) or a named built-in check.
        if "commit" in surfaces:
            check = fm.get("commit_check") or ("staged-paths" if fm.get("event") == "file" else None)
            if check not in ("staged-paths", "secret-scan", "default-branch"):
                errors.append(
                    f"{rel}: surface {fm['surface']} needs commit_check "
                    f"(staged-paths|secret-scan|default-branch) or event: file (got {check!r})")
            if fm.get("commit_severity") not in (None, "block", "warn"):
                errors.append(f"{rel}: commit_severity must be block|warn (got {fm.get('commit_severity')!r})")
        pat = fm.get("pattern")
        if pat:
            try:
                re.compile(pat)
            except re.error as e:
                errors.append(f"{rel}: pattern is not a valid regex: {e}")


def check_agents():
    for path in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/agents/*.md"))):
        rel = os.path.relpath(path, ROOT)
        fm = frontmatter(path)
        if "id" not in fm and "name" not in fm:
            errors.append(f"{rel}: needs an 'id' or 'name'")
        for key in ("stacks", "tools", "description"):
            if key not in fm:
                errors.append(f"{rel}: missing frontmatter key '{key}'")


def check_skills():
    for path in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/skills/*/SKILL.md"))):
        rel = os.path.relpath(path, ROOT)
        fm = frontmatter(path)
        for key in ("name", "description"):
            if key not in fm:
                errors.append(f"{rel}: missing frontmatter key '{key}'")


def check_catalog_totals():
    """The CATALOG.md totals line is documentation that silently goes stale — count the
    files and make CI notice when it disagrees."""
    path = os.path.join(ROOT, "kit/catalog/CATALOG.md")
    if not os.path.exists(path):
        errors.append("kit/catalog/CATALOG.md is missing")
        return
    entries = (glob.glob(os.path.join(ROOT, "kit/catalog/guardrails/*.md"))
               + glob.glob(os.path.join(ROOT, "kit/catalog/agents/*.md"))
               + glob.glob(os.path.join(ROOT, "kit/catalog/skills/*/SKILL.md")))
    text = open(path).read()
    m = re.search(r"Totals:\s*\*\*(\d+) entries\*\*", text)
    if not m:
        errors.append("kit/catalog/CATALOG.md: no 'Totals: **N entries**' line to check")
        return
    claimed, actual = int(m.group(1)), len(entries)
    if claimed != actual:
        errors.append(f"kit/catalog/CATALOG.md claims {claimed} entries, found {actual}")


def check_catalog_listed():
    """Every catalog entry should appear in CATALOG.md — an unlisted pack is invisible."""
    text = open(os.path.join(ROOT, "kit/catalog/CATALOG.md")).read()
    for pattern in ("kit/catalog/guardrails/*.md", "kit/catalog/agents/*.md"):
        for path in sorted(glob.glob(os.path.join(ROOT, pattern))):
            entry_id = os.path.basename(path)[:-3]
            if f"`{entry_id}`" not in text:
                errors.append(f"kit/catalog/CATALOG.md does not list '{entry_id}'")
    for path in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/skills/*/SKILL.md"))):
        name = os.path.basename(os.path.dirname(path))
        if f"`{name}`" not in text:
            errors.append(f"kit/catalog/CATALOG.md does not list skill '{name}'")


def git_tags():
    """Every `vX.Y.Z` tag in this checkout, as a set of bare versions.

    Returns None when git cannot answer — a shallow clone, a tarball, no git. Release
    status is then unverifiable, and the check skips rather than inventing failures.
    """
    try:
        proc = subprocess.run(
            ["git", "tag", "--list", "v*"], cwd=ROOT, timeout=10,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.decode("utf-8", "replace")
    return {t[1:] for t in out.split() if re.fullmatch(r"v\d+\.\d+\.\d+", t)}


def check_version():
    vpath = os.path.join(ROOT, "VERSION")
    cpath = os.path.join(ROOT, "CHANGELOG.md")
    if not os.path.exists(vpath):
        errors.append("VERSION file is missing")
        return
    version = open(vpath).read().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append(f"VERSION is not semver: {version!r}")
    text = open(cpath).read() if os.path.exists(cpath) else ""
    headings = re.findall(r"^##\s*\[(\d+\.\d+\.\d+)\]\s*(.*)$", text, re.M)
    top = headings[0][0] if headings else None
    if top != version:
        errors.append(f"VERSION ({version}) != top CHANGELOG entry ({top}) — bump both together")

    # Release status is a mechanically checkable claim, and it drifted: every heading
    # read "Unreleased" including twelve published versions, which release.yml then
    # copied verbatim into the GitHub Release notes (issue #33).
    tags = git_tags()
    if not tags:
        # None = git could not answer; empty = a shallow or --no-tags clone, or a
        # tarball. Either way release status is unverifiable, and asserting against an
        # empty tag set would report every published version as never released. CI uses
        # fetch-depth: 0 so this path is not how the check passes there.
        print("note: no v* tags in this checkout — skipping the release-status check")
        return
    for index, (ver, suffix) in enumerate(headings):
        suffix = suffix.strip()
        dated = re.fullmatch(r"—\s*\d{4}-\d{2}-\d{2}", suffix)
        pending = re.fullmatch(r"—\s*Unreleased", suffix)
        never = re.fullmatch(r"—\s*not released", suffix)
        if index == 0:
            if not pending:
                errors.append(
                    f"CHANGELOG [{ver}] is the top entry and must read '— Unreleased', not {suffix!r}"
                )
            if ver in tags:
                errors.append(
                    f"CHANGELOG [{ver}] is the top entry but v{ver} is already tagged — "
                    "bump VERSION and open a new section (this is how 0.8.0/0.9.0 were skipped)"
                )
            continue
        if ver in tags:
            if not dated:
                errors.append(
                    f"CHANGELOG [{ver}] is tagged as v{ver} but its heading reads {suffix!r} — "
                    "it must carry the release date (YYYY-MM-DD)"
                )
        elif not never:
            errors.append(
                f"CHANGELOG [{ver}] has no v{ver} tag, so it must read '— not released', "
                f"not {suffix!r} — an uncut version must not look pending"
            )


def main():
    check_guardrails()
    check_agents()
    check_skills()
    check_catalog_totals()
    check_catalog_listed()
    check_version()
    if errors:
        print("❌ validation failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("✅ catalog + version validation passed")


if __name__ == "__main__":
    main()
