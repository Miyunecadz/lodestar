#!/usr/bin/env python3
"""Lodestar catalog + consistency validator (used by CI).

Checks, with stdlib only:
  - every guardrail has the required frontmatter, valid enums, and a compilable regex;
  - every agent/skill has the required frontmatter;
  - VERSION matches the top CHANGELOG entry.
Exits non-zero (listing every problem) if anything is off.
"""
import os
import re
import sys
import glob

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
        if fm.get("surface") not in ("agent", "commit", "both"):
            errors.append(f"{rel}: surface must be agent|commit|both (got {fm.get('surface')!r})")
        # A commit-surface rule needs something the pre-commit checker can actually run:
        # a `file` pattern (checked against staged paths) or a named built-in check.
        if fm.get("surface") in ("commit", "both"):
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
    m = re.search(r"^##\s*\[(\d+\.\d+\.\d+)\]", text, re.M)
    top = m.group(1) if m else None
    if top != version:
        errors.append(f"VERSION ({version}) != top CHANGELOG entry ({top}) — bump both together")


def main():
    check_guardrails()
    check_agents()
    check_skills()
    check_version()
    if errors:
        print("❌ validation failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("✅ catalog + version validation passed")


if __name__ == "__main__":
    main()
