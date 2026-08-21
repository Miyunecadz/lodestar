#!/usr/bin/env python3
"""Execute the REAL catalog guardrails against a fixture table.

`test-engine.sh` verifies the engine against hand-written copies of a few rules. That
tests the engine, which is necessary and not the same thing: if a catalog pattern and
its test copy drift apart, both keep passing. So the twenty-one shipped patterns —
described in `docs/CONCEPTS.md` §4 as the product — had nothing asserting that a rule
installed as-is produces the verdict its title promises.

This harness installs the actual `kit/catalog/guardrails/<id>.md` into a throwaway
workspace, applying the same `id:` → `name:` transform `/lodestar-guardrails` §5 does,
and runs the shipped engine against it. That transform was previously assumed rather
than exercised.

**One rule is installed at a time.** Several rules match `git commit`, so a shared rule
set would blur which one produced a verdict — and the verdict is the whole claim.

Two kinds of entry, routed by `emits`:

  emits: rule           installed and run through the engine, verdict asserted
  emits: settings-hook  never reaches the engine — the picker writes a settings.json
                        PostToolUse hook, whose matcher selects on tool name, so this
                        pattern lands inside that hook's shell logic. Asserting an engine
                        verdict would test a path that does not exist in production, so
                        the pattern is matched directly instead.

Fixture format — `.github/fixtures/guardrails.tsv`, tab-separated:

    rule-id <TAB> verdict <TAB> input <TAB> context

  verdict   DENY | WARN | ALLOW
  input     a file path for `event: file`, a command for `event: bash`
  context   optional `key=value,key=value`:
              branch=default   run with HEAD on the repo's default branch
              untracked=1      leave the file untracked by git, for the
                               `allow_if_untracked` case
              path=<path>      for `match: content` rules, the file being edited
                               (the input is then the edited *content*)

Paths are workspace-relative and resolved against the throwaway workspace, whose
manifest declares one repo per stack the catalog targets.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CATALOG = os.path.join(ROOT, "kit", "catalog", "guardrails")
ENGINE = os.path.join(ROOT, "kit", "templates", "hooks", "lodestar-guardrails.py")
FIXTURES = os.path.join(ROOT, ".github", "fixtures", "guardrails.tsv")
PY = os.environ.get("LODESTAR_TEST_PYTHON", sys.executable)

# One repo per stack the catalog targets, so a stack-scoped rule has both a repo it
# belongs in and a repo it must stay out of. No `designGuidance.installed` key: that
# absence is what `requires_manifest_missing` keys off.
MANIFEST = {
    "repos": [
        {"name": "web", "path": "web", "stacks": ["react-craco", "has-eslint", "has-frontend"]},
        {"name": "next", "path": "next", "stacks": ["nextjs", "has-frontend", "has-eslint"]},
        {"name": "mobile", "path": "mobile", "stacks": ["react-native"]},
        {"name": "api", "path": "api", "stacks": ["python-django", "has-python-lint"]},
        {"name": "php", "path": "php", "stacks": ["laravel", "has-pint"]},
        {"name": "svc", "path": "svc", "stacks": ["node-dbmate"]},
    ]
}

# Every file-event fixture path is created and committed unless its row says
# `untracked=1`. This is not tidiness — `allow_if_untracked` rules skip files git does
# not track, so an untracked path is allowed for a reason that has nothing to do with
# the pattern or the stack. Mutation-testing this harness caught exactly that: making
# the Django migration rule `stacks: [all]` did not fail any case, because its
# wrong-stack negative was passing on untracked-ness rather than on scope.


def frontmatter(text):
    """The catalog entry's frontmatter as raw `key: value` strings, order preserved."""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, ""
    fm = {}
    for line in parts[1].splitlines():
        if not line.strip() or line[:1] in (" ", "\t", "#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip()
    return fm, parts[2].strip()


# Exactly the fields `/lodestar-guardrails` §5 copies from a catalog entry into an
# installed rule file. A field missing here is a field the picker would silently drop.
COPIED = [
    "event", "pattern", "severity", "stacks", "allow_if_untracked",
    "only_on_default_branch", "match", "allow_paths", "ignore_case", "surface",
    "permission_rules", "commit_check", "commit_severity", "requires_manifest_missing",
]


def install_rule(entry_path, rules_dir):
    """Write the catalog entry as an installed rule, the way the picker does.

    `id:` becomes `name:` and `enabled: true` is added; everything the engine's context
    layer reads is copied verbatim. Doing the transform here rather than hand-writing
    the rule file is the point — it is the step that was never exercised.
    """
    text = open(entry_path).read()
    fm, body = frontmatter(text)
    rule_id = fm.get("id")
    lines = ["---", "name: %s" % rule_id, "enabled: true"]
    for key in COPIED:
        if key in fm:
            lines.append("%s: %s" % (key, fm[key]))
    lines += ["---", "", body, ""]
    with open(os.path.join(rules_dir, "%s.md" % rule_id), "w") as f:
        f.write("\n".join(lines))
    return fm


def git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, check=False)


def touch(work, rel):
    path = os.path.join(work, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("fixture\n")


def build_workspace(work, tracked, untracked):
    os.makedirs(os.path.join(work, ".claude", "guardrails"))
    with open(os.path.join(work, ".claude", "lodestar.manifest.json"), "w") as f:
        json.dump(MANIFEST, f, indent=2)
    git(["init", "-q", work], ROOT)
    git(["config", "user.email", "ci@example.com"], work)
    git(["config", "user.name", "ci"], work)
    git(["symbolic-ref", "HEAD", "refs/heads/main"], work)
    for rel in sorted(tracked):
        touch(work, rel)
    git(["add", "-A", "-f"], work)
    git(["-c", "commit.gpgsign=false", "commit", "-qm", "fixture"], work)
    for rel in sorted(untracked):  # written after the commit, so git never saw them
        touch(work, rel)
    git(["switch", "-q", "-c", "feature"], work)  # off the default branch by default
    return work


def verdict(payload, work):
    proc = subprocess.run(
        [PY, ENGINE], input=json.dumps(payload).encode(), cwd=work,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env=dict(os.environ, CLAUDE_PROJECT_DIR=work),
    )
    try:
        data = json.loads(proc.stdout.decode("utf-8", "replace") or "{}")
    except ValueError:
        return "MALFORMED"
    hook = data.get("hookSpecificOutput") or {}
    if hook.get("permissionDecision") == "deny":
        return "DENY"
    return "WARN" if data.get("systemMessage") else "ALLOW"


def read_fixtures():
    rows = []
    with open(FIXTURES) as f:
        for lineno, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                sys.exit("%s:%d: need at least 3 tab-separated fields" % (FIXTURES, lineno))
            rule_id, want, value = parts[0].strip(), parts[1].strip(), parts[2]
            ctx = {}
            if len(parts) > 3 and parts[3].strip():
                for item in parts[3].strip().split(","):
                    k, _, v = item.partition("=")
                    ctx[k.strip()] = v.strip()
            rows.append((lineno, rule_id, want, value, ctx))
    return rows


def main():
    if not os.path.exists(FIXTURES):
        sys.exit("missing fixture table: %s" % FIXTURES)
    rows = read_fixtures()
    entries = {os.path.basename(p)[:-3]: os.path.join(CATALOG, os.path.basename(p))
               for p in sorted(os.listdir(CATALOG)) if p.endswith(".md")}

    unknown = sorted({r[1] for r in rows} - set(entries))
    if unknown:
        sys.exit("fixtures reference rules not in the catalog: %s" % ", ".join(unknown))

    # Split the fixture paths by whether git should see them, then build once.
    tracked, untracked = set(), set()
    for _, rule_id, _, value, ctx in rows:
        fm, _ = frontmatter(open(entries[rule_id]).read())
        if fm.get("emits") == "settings-hook" or fm.get("event") == "bash":
            continue
        rel = ctx.get("path") or value
        (untracked if ctx.get("untracked") else tracked).add(rel)

    work = build_workspace(tempfile.mkdtemp(prefix="lodestar-catalog-"), tracked, untracked)
    rules_dir = os.path.join(work, ".claude", "guardrails")
    default_work = None  # built lazily: a second workspace whose HEAD is on `main`

    passed, failures = 0, []
    try:
        for lineno, rule_id, want, value, ctx in rows:
            for stale in os.listdir(rules_dir):
                os.remove(os.path.join(rules_dir, stale))
            fm = install_rule(entries[rule_id], rules_dir)

            if fm.get("emits") == "settings-hook":
                # Never installed as an engine rule — assert the pattern itself, which is
                # what the generated PostToolUse hook's own shell logic tests.
                hit = re.search(fm["pattern"].strip("'\""), value) is not None
                got = "WARN" if hit else "ALLOW"
            else:
                target = work
                if ctx.get("branch") == "default":
                    if default_work is None:
                        default_work = build_workspace(
                            tempfile.mkdtemp(prefix="lodestar-catalog-main-"), tracked, untracked)
                        subprocess.run(["git", "switch", "-q", "main"], cwd=default_work,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    shutil.copy(os.path.join(rules_dir, "%s.md" % rule_id),
                                os.path.join(default_work, ".claude", "guardrails"))
                    target = default_work

                if fm.get("event") == "bash":
                    payload = {"tool_name": "Bash", "tool_input": {"command": value}}
                elif fm.get("match") == "content":
                    payload = {"tool_name": "Edit", "tool_input": {
                        "file_path": os.path.join(target, ctx["path"]), "new_string": value}}
                else:
                    payload = {"tool_name": "Edit", "tool_input": {
                        "file_path": os.path.join(target, value)}}
                payload["cwd"] = target
                got = verdict(payload, target)
                if target is not work:
                    os.remove(os.path.join(default_work, ".claude", "guardrails", "%s.md" % rule_id))

            if got == want:
                passed += 1
            else:
                failures.append("%s:%d  %s  %r → %s, want %s"
                                % (os.path.basename(FIXTURES), lineno, rule_id, value, got, want))
    finally:
        shutil.rmtree(work, ignore_errors=True)
        if default_work:
            shutil.rmtree(default_work, ignore_errors=True)

    covered = {r[1] for r in rows}
    missing = sorted(set(entries) - covered)
    if missing:
        failures.append("no fixture coverage for: %s" % ", ".join(missing))

    if failures:
        print("❌ catalog fixtures: %d failed, %d passed\n" % (len(failures), passed))
        for f in failures:
            print("  " + f)
        return 1
    print("✅ catalog fixtures: %d cases across %d rules" % (passed, len(covered)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
