#!/usr/bin/env python3
"""Lodestar catalog + consistency validator (used by CI).

Checks, with stdlib only:
  - every guardrail has the required frontmatter, valid enums, and a compilable regex;
  - every agent/skill has the required frontmatter;
  - every guardrail has positive and negative behaviour fixtures;
  - every guardrail's block-time message fits the redirect budget;
  - changelog.d/ fragments are well-formed;
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


def check_fragments():
    """Changelog fragments must be releasable without a human reading them first.

    Feature PRs add a file here instead of editing `CHANGELOG.md` and `VERSION`, which
    is what stops two open PRs conflicting on the same hot line. The cost of that is
    that nobody sees a fragment until release time, so what would have been a review
    comment has to be a check.
    """
    directory = os.path.join(ROOT, "changelog.d")
    if not os.path.isdir(directory):
        return
    for name in sorted(os.listdir(directory)):
        if name == "README.md":
            continue
        rel = f"changelog.d/{name}"
        if not name.endswith(".md"):
            errors.append(f"{rel}: fragments must be .md files")
            continue
        body = open(os.path.join(directory, name)).read().strip()
        if not body:
            errors.append(f"{rel} is empty")
        elif re.search(r"^##\s*\[", body, re.M):
            errors.append(
                f"{rel} contains a '## [version]' heading — a fragment is the section "
                "body only; release.py writes the heading")


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
def check_fixture_coverage():
    """Every guardrail needs a positive and a negative behaviour fixture.

    A pattern that compiles is not a pattern that matches what its title claims. This
    is the gate that stops a new catalog entry shipping with nothing asserting its
    behaviour; `.github/scripts/test-catalog.py` is what actually runs them.

    Both directions are required. A rule with only positives cannot regress into
    matching everything, and a rule with only negatives cannot regress into matching
    nothing — and silent non-enforcement is the failure mode that matters here.
    """
    path = os.path.join(ROOT, ".github/fixtures/guardrails.tsv")
    if not os.path.exists(path):
        errors.append(".github/fixtures/guardrails.tsv is missing")
        return
    positive, negative = {}, {}
    for lineno, line in enumerate(open(path), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            errors.append(f".github/fixtures/guardrails.tsv:{lineno}: needs 3 tab-separated fields")
            continue
        rule_id, want = parts[0].strip(), parts[1].strip()
        if want not in ("DENY", "WARN", "ALLOW"):
            errors.append(
                f".github/fixtures/guardrails.tsv:{lineno}: verdict must be "
                f"DENY|WARN|ALLOW (got {want!r})")
            continue
        bucket = negative if want == "ALLOW" else positive
        bucket[rule_id] = bucket.get(rule_id, 0) + 1
    for entry in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/guardrails/*.md"))):
        rule_id = os.path.basename(entry)[:-3]
        if not positive.get(rule_id):
            errors.append(
                f"guardrail '{rule_id}' has no positive fixture — add a case to "
                ".github/fixtures/guardrails.tsv showing it fires")
        if not negative.get(rule_id):
            errors.append(
                f"guardrail '{rule_id}' has no negative (ALLOW) fixture — add a case "
                "showing what it must NOT match; a rule that matches everything passes "
                "positives just fine")
# Ceiling on the part of a rule body that reaches the model when the rule fires. Issue
# #30 suggested ~600; the well-written redirects actually land between 223 and 829, and
# trimming to 600 would mean deleting things the model needs to act on. 900 sits above
# every current rule and well below where they started (1500–2400), so it cannot be met
# by accident but does catch a slide back to pasting rationale into the payload.
REDIRECT_BUDGET = 900


def redirect_of(body):
    """The block-time payload: everything above the first bare `---` line in the body."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "---":
            return "\n".join(lines[:i]).strip()
    return body.strip()


def check_redirect_budget():
    """A rule's block-time message must stay short enough to read as an instruction.

    `docs/CONCEPTS.md` §2: "a good block doesn't say 'denied,' it says 'don't edit an
    applied migration — create a new one with `db:new`.' Redirect, don't just refuse."
    A redirect buried under design rationale still redirects, technically.
    """
    for path in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/guardrails/*.md"))):
        name = os.path.basename(path)[:-3]
        text = open(path).read()
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue  # frontmatter check reports this separately
        payload = redirect_of(parts[2].strip())
        if not payload:
            errors.append(
                f"guardrail '{name}' has an empty block message — the text above the "
                "`---` separator is what the model is shown"
            )
        elif len(payload) > REDIRECT_BUDGET:
            errors.append(
                f"guardrail '{name}' block message is {len(payload)} chars, over the "
                f"{REDIRECT_BUDGET} budget — move design rationale below a `---` line; "
                "it stays in the file, it just stops being sent on every block"
            )


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
        errors.append(
            f"VERSION ({version}) != top CHANGELOG entry ({top}) — both are written by "
            "`.github/scripts/release.py <version>`; a feature PR should not touch either "
            "(add a changelog.d/ fragment instead)")

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
            # The top entry has two legitimate states, because `release.py` writes the
            # section in a PR and `release.yml` creates the tag when that PR merges:
            #   pending  — written, not yet merged, so no tag exists
            #   released — merged and tagged, which is the steady state between releases
            if ver in tags:
                if not dated:
                    errors.append(
                        f"CHANGELOG [{ver}] is tagged as v{ver} but its heading reads "
                        f"{suffix!r} — run `.github/scripts/release.py <next>`, which "
                        "stamps the previous version's date"
                    )
            elif not pending:
                errors.append(
                    f"CHANGELOG [{ver}] has no v{ver} tag yet, so as the top entry it "
                    f"must read '— Unreleased', not {suffix!r}"
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
    check_fixture_coverage()
    check_redirect_budget()
    check_fragments()
    check_version()
    if errors:
        print("❌ validation failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("✅ catalog + version validation passed")


if __name__ == "__main__":
    main()
