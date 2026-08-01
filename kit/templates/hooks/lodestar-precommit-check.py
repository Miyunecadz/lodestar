#!/usr/bin/env python3
"""Lodestar commit-surface guardrails — enforce `commit` rules for ANY committer.

The PreToolUse engine (`lodestar-guardrails.py`) only fires when *Claude* is about to
act. A human editing in their IDE, a teammate, or CI never touches that code path, so a
rule labelled "safety" was in practice enforced against one committer out of many. This
script closes that gap: it runs as a **pre-commit hook** and applies the same rule files
to the staged change, whoever is committing.

    .claude/guardrails/*.md   ← one rule set, several enforcement surfaces
      surface: agent       → PreToolUse only (lodestar-guardrails.py)
      surface: commit      → pre-commit only (this script)
      surface: permission  → settings.json permissions.deny (lodestar-permissions.py)
      surface: both        → [agent, commit], the pre-permission spelling

`surface` accepts a scalar or an inline list (`[agent, commit, permission]`). This
script runs the `commit` half and ignores the rest.

Usage (wired by /lodestar-guardrails into lefthook / husky / core.hooksPath / .git/hooks):

    lodestar-precommit-check.py [--list] [--verbose]

    --list     print the commit-surface rules that would run, then exit
    --verbose  also report rules that passed

Exit status: 1 only when a `block` rule matched. Everything else — a `warn` match, no
rules, a missing tool, an unreadable manifest, an internal error — exits 0. A guardrail
that breaks unrelated commits would be worse than the gap it closes; `git commit
--no-verify` (or `LEFTHOOK=0`) remains the documented escape hatch.

Requires Python 3.8+ (see MIN_PYTHON), stdlib only. Failing open is the right default
here, but it must be *visible*: an interpreter under the floor says so rather than
letting the commit through under a generic "skipped".
"""

import json
import os
import re
import subprocess
import sys
import tempfile

GIT_TIMEOUT = 10  # generous: gitleaks on a large staged diff

# Kept in step with lodestar-guardrails.py — the two hooks share a rule set, so a floor
# that differed between them would mean a rule enforcing on one surface and not the other.
MIN_PYTHON = (3, 8)

# How to ask gitleaks to scan the staged diff, newest spelling first. `protect` was
# deprecated in favour of `git`; on a release where it no longer exists the invocation
# fails, which must read as a tool failure and not as "credentials found".
GITLEAKS_SUBCOMMANDS = (
    ["git", "--staged"],      # gitleaks 8.19+
    ["protect", "--staged"],  # older releases
)

# Conservative fallback patterns, used only when no real scanner is installed. Kept
# narrow on purpose — a false positive here interrupts someone else's commit.
SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block"),
    (r"gh[pousr]_[A-Za-z0-9]{36,}", "GitHub token"),
    (r"xox[abposr]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"sk-[A-Za-z0-9]{32,}", "API secret key"),
    (r"(?i)\b(aws_secret_access_key|secret_access_key)\b\s*[:=]\s*['\"][A-Za-z0-9/+=]{30,}['\"]", "AWS secret"),
]


def run(args, cwd=".", timeout=GIT_TIMEOUT):
    """Run a command. Returns (returncode, stdout) or (None, "") if it could not run."""
    try:
        proc = subprocess.run(
            args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout
        )
        return proc.returncode, proc.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError, ValueError):
        return None, ""


def have(tool):
    rc, _ = run([tool, "--version"])
    return rc is not None


# ---------------------------------------------------------------- rule loading


def coerce(val):
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        return [p.strip().strip('"').strip("'") for p in inner.split(",") if p.strip()] if inner else []
    val = val.strip('"').strip("'")
    low = val.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    return val


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm = {}
    for line in parts[1].splitlines():
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = coerce(val)
    return fm, parts[2].strip()


def as_list(val):
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [p.strip().strip('"').strip("'") for p in val.strip("[]").split(",") if p.strip()]
    return []


def surfaces_of(fm):
    """The set of enforcement mechanisms a rule declares. Mirrors the engine's copy."""
    raw = fm.get("surface")
    if raw is None:
        return {"agent"}
    names = {str(s).strip().lower() for s in as_list(raw) if str(s).strip()}
    if "both" in names:
        names.discard("both")
        names |= {"agent", "commit"}
    return names or {"agent"}


def redirect_of(body):
    """The part of a rule body shown when the rule fires. Mirrors the engine's copy.

    A bare `---` line separates the redirect from the design rationale below it. Both
    stay in the file; only the redirect is printed, because a blocked committer needs
    the fix and not a paragraph on why the rule chose its enforcement surface. A rule
    with no separator prints its whole body, as every rule did before the split.
    """
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "---":
            return "\n".join(lines[:i]).strip()
    return body.strip()


def find_workspace(start="."):
    """Locate the Lodestar workspace holding the rules.

    A sub-repo can live below the workspace root (separate-repos layout), so walk up
    until `.claude/guardrails` appears. `LODESTAR_WORKSPACE` overrides.
    """
    override = os.environ.get("LODESTAR_WORKSPACE") or os.environ.get("CLAUDE_PROJECT_DIR")
    if override and os.path.isdir(os.path.join(override, ".claude", "guardrails")):
        return override
    current = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(current, ".claude", "guardrails")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def load_commit_rules(workspace):
    """Rules that declare a `commit` enforcement surface."""
    out = []
    rules_dir = os.path.join(workspace, ".claude", "guardrails")
    try:
        names = sorted(os.listdir(rules_dir))
    except (IOError, OSError):
        return out
    for name in names:
        if not name.endswith(".md"):
            continue
        try:
            with open(os.path.join(rules_dir, name), "r") as f:
                fm, body = parse_frontmatter(f.read())
        except (IOError, OSError, UnicodeDecodeError):
            continue
        if not fm or fm.get("enabled") is False:
            continue
        if "commit" not in surfaces_of(fm):
            continue
        check = fm.get("commit_check") or ("staged-paths" if fm.get("event") == "file" else "")
        if not check:
            continue  # a bash rule with no commit-side equivalent
        fm["_check"] = check
        fm["_message"] = redirect_of(body)
        fm["_severity"] = str(fm.get("commit_severity") or fm.get("severity") or "warn").lower()
        out.append(fm)
    return out


# ---------------------------------------------------------------- git context


def git_root():
    """Absolute path of the repository being committed, or None.

    Not the same thing as the workspace. `git diff --cached` reports paths relative to
    THIS, while manifest repo paths are relative to the workspace — and in the
    separate-sub-repos layout (each repo its own git repo, `.claude/` in the parent)
    the two differ. Resolving a staged path against the wrong one names a file that
    exists under no onboarded repo, which silently disables stack scoping.
    """
    rc, out = run(["git", "rev-parse", "--show-toplevel"])
    if rc == 0 and out.strip():
        return os.path.abspath(out.strip())
    return None


def staged_files():
    """[(status, path)] for the staged change. Renames report their destination."""
    rc, out = run(["git", "diff", "--cached", "--name-status", "--diff-filter=ACMR"])
    if rc != 0:
        return []
    entries = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0][:1]
        path = parts[-1]  # rename → new name
        entries.append((status, path))
    return entries


def current_branch():
    rc, out = run(["git", "symbolic-ref", "--short", "HEAD"])
    return out.strip() if rc == 0 else None


def default_branch():
    rc, out = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
    if rc == 0 and "/" in out:
        return out.strip().split("/", 1)[1]
    rc, out = run(["git", "config", "--get", "init.defaultBranch"])
    if rc == 0 and out.strip():
        return out.strip()
    for candidate in ("main", "master"):
        rc, _ = run(["git", "rev-parse", "--verify", "--quiet", "refs/heads/" + candidate])
        if rc == 0:
            return candidate
    return None


def manifest_repos(workspace):
    path = os.path.join(workspace, ".claude", "lodestar.manifest.json")
    try:
        with open(path, "r") as f:
            data = json.load(f)
        repos = data.get("repos")
        return repos if isinstance(repos, list) else []
    except (IOError, OSError, ValueError):
        return []


def stacks_for(path, workspace, repos):
    """Detected stacks of the repo containing `path`, or None when unknown."""
    if not repos:
        return None
    target = os.path.abspath(path)
    best, best_len = None, -1
    for repo in repos:
        if not isinstance(repo, dict) or not isinstance(repo.get("path"), str):
            continue
        root = os.path.abspath(os.path.join(workspace, repo["path"]))
        if target == root or target.startswith(root.rstrip(os.sep) + os.sep):
            if len(root) > best_len:
                best, best_len = repo, len(root)
    if best is None:
        return None
    stacks = [s for s in as_list(best.get("stacks")) if s]
    return stacks or None


def in_scope(rule, path, workspace, repos):
    wanted = as_list(rule.get("stacks"))
    if not wanted or "all" in wanted:
        return True
    have_stacks = stacks_for(path, workspace, repos)
    if have_stacks is None:
        return True  # unknown repo → do not silently drop a safety rule
    return any(s in have_stacks for s in wanted)


# ---------------------------------------------------------------- checks


def check_staged_paths(rule, staged, repo_root, workspace, repos):
    """Rule pattern vs the staged paths — the commit-time twin of a `file` rule.

    `repo_root` resolves the staged paths (they come from `git diff --cached`, relative
    to the committing repo); `workspace` resolves the manifest's repo paths. They are the
    same directory in a monorepo and different ones in the separate-sub-repos layout.
    """
    flags = 0 if rule.get("ignore_case") is False else re.IGNORECASE
    hits = []
    for status, path in staged:
        try:
            if not re.search(rule["pattern"], path, flags):
                continue
        except (re.error, KeyError):
            return []
        # `allow_if_untracked` means "a file git does not track yet is fair game". At
        # commit time that is exactly an addition: A = new here, M = already committed.
        if rule.get("allow_if_untracked") is True and status == "A":
            continue
        if not in_scope(rule, os.path.join(repo_root, path), workspace, repos):
            continue
        hits.append(path)
    return hits


def gitleaks_version():
    """Best-effort version string — a support question about a spurious block is not
    answerable without it. `version` is the v8 spelling; `--version` covers the rest."""
    for args in (["gitleaks", "version"], ["gitleaks", "--version"]):
        rc, out = run(args)
        if rc == 0 and out.strip():
            return out.strip().splitlines()[0].strip()
    return "unknown"


def describe_finding(finding):
    """One gitleaks JSON finding → `file:line: rule`. Never the secret itself: this goes
    to a terminal and, on the CI path, into a build log."""
    path = finding.get("File") or "?"
    rule = finding.get("RuleID") or finding.get("Description") or "secret"
    line = finding.get("StartLine")
    where = "%s:%s" % (path, line) if isinstance(line, int) and line > 0 else str(path)
    return "%s: %s" % (where, rule)


def run_gitleaks(subcommand):
    """Scan the staged diff with one gitleaks spelling.

    Returns `(findings, failure)` where exactly one side is meaningful: a list (possibly
    empty) means the scan ran and its verdict stands; a string means gitleaks did not
    produce a verdict and the caller must degrade rather than report credentials.

    The discriminator is the **report**, not the exit code alone. gitleaks exits 1 both
    for "leaks found" and for several fatal errors — an unknown subcommand, a malformed
    `.gitleaks.toml`, an unsupported flag after an upgrade — so an exit code by itself
    cannot tell a finding from a usage message. A scan that actually ran writes a JSON
    report; one that died before scanning does not.
    """
    handle, report = tempfile.mkstemp(prefix="lodestar-gitleaks-", suffix=".json")
    os.close(handle)
    try:
        rc, out = run(
            ["gitleaks"] + subcommand
            + ["--no-banner", "--report-format", "json", "--report-path", report]
        )
        if rc is None:
            return None, "`gitleaks %s` could not be executed" % subcommand[0]
        try:
            with open(report, "r") as f:
                text = f.read().strip()
            data = json.loads(text) if text else []
        except (IOError, OSError, ValueError):
            data = None
        if rc == 0:
            return [], None  # scanned, nothing found
        if rc == 1 and isinstance(data, list) and data:
            return [describe_finding(f) for f in data[:20] if isinstance(f, dict)], None
        first = next((ln.strip() for ln in out.splitlines() if ln.strip()), "")
        detail = " — %s" % first[:160] if first else ""
        return None, "`gitleaks %s` exited %d without a findings report%s" % (
            subcommand[0], rc, detail
        )
    finally:
        try:
            os.unlink(report)
        except OSError:
            pass


def builtin_secret_scan():
    """Conservative pattern scan of the staged diff. Heuristics only — never precise
    enough to stop someone else's commit, so callers only ever warn on these."""
    rc, diff = run(["git", "diff", "--cached", "-U0"])
    if rc != 0:
        return []
    hits, path = [], "?"
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, line):
                hits.append(f"{path}: possible {label}")
                break
    return hits[:20]


def check_secret_scan(_rule, verbose=False):
    """Scan the staged diff for credentials. Returns `(hits, note, broken)`.

    `note` is None when the result is authoritative. Otherwise it names why the scan
    could not be trusted, the hits are heuristic, and the caller downgrades `block` to
    `warn`. Both degradations — no scanner, and a scanner that failed — take the same
    path on purpose: this is the one code path that can stop a stranger's commit, and a
    broken or upgraded binary must never be reported as leaked credentials.

    `broken` separates the two anyway, for reporting only. Having no scanner is a known
    steady state and saying so on every commit is noise; a scanner that is installed and
    failing is news, and staying quiet about it would leave someone believing their
    commits are scanned when they are not.
    """
    failure = None
    if have("gitleaks"):
        if verbose:
            print(f"  gitleaks: {gitleaks_version()}")
        for subcommand in GITLEAKS_SUBCOMMANDS:
            findings, why = run_gitleaks(subcommand)
            if why is None:
                return findings, None, False
            failure = why  # try the next spelling before giving up on the scanner
        return builtin_secret_scan(), (
            "gitleaks %s is installed but produced no verdict (%s) — falling back to "
            "built-in heuristics, so this warns instead of blocking"
            % (gitleaks_version(), failure)
        ), True
    return builtin_secret_scan(), (
        "no `gitleaks` installed — built-in heuristics only, so this warns "
        "instead of blocking"
    ), False


def check_default_branch(_rule):
    branch, default = current_branch(), default_branch()
    if branch and default and branch == default:
        return [f"HEAD is on the default branch ({branch})"]
    return []


# ---------------------------------------------------------------- main


def main(argv):
    verbose = "--verbose" in argv
    workspace = find_workspace()
    if not workspace:
        return 0  # no Lodestar rules here — nothing to enforce, say nothing

    rules = load_commit_rules(workspace)
    if "--list" in argv:
        for rule in rules:
            print(f"{rule.get('name', '?')}\t{rule['_check']}\t{rule['_severity']}")
        return 0
    if not rules:
        return 0

    staged = staged_files()
    repos = manifest_repos(workspace)
    # Fail protective: with no git root to resolve against, fall back to the workspace,
    # which is correct in the monorepo layout and no worse than the old behaviour.
    repo_root = git_root() or os.path.abspath(workspace)
    if verbose:
        print(f"  workspace: {workspace}")
        print(f"  git root:  {repo_root}")
    blocking, warning = [], []

    for rule in rules:
        severity = rule["_severity"]
        try:
            if rule["_check"] == "staged-paths":
                hits = check_staged_paths(rule, staged, repo_root, workspace, repos)
            elif rule["_check"] == "secret-scan":
                hits, note, broken = check_secret_scan(rule, verbose)
                if note:
                    rule = dict(rule, _note=note, _broken=broken)
                    if severity == "block":
                        severity = "warn"
            elif rule["_check"] == "default-branch":
                hits = check_default_branch(rule)
            else:
                continue
        except Exception:
            continue  # a broken rule must never break the commit
        if not hits:
            if rule.get("_broken"):
                # A clean result from a scanner that failed is not a clean scan. Silence
                # here would read as "checked, fine" — which is the whole complaint.
                print(f"\n⚠ [{rule.get('name', 'rule')}] not fully checked")
                print(f"    {rule['_note']}")
            elif verbose:
                print(f"  ok   {rule.get('name', '?')}")
            continue
        (blocking if severity == "block" else warning).append((rule, hits))

    for rule, hits in warning:
        print(f"\n⚠ [{rule.get('name', 'rule')}] (warn)")
        for hit in hits:
            print(f"    {hit}")
        if rule.get("_note"):
            print(f"    note: {rule['_note']}")
        print(f"  {rule['_message'].splitlines()[0] if rule['_message'] else ''}")

    for rule, hits in blocking:
        print(f"\n✖ [{rule.get('name', 'rule')}] (block)")
        for hit in hits:
            print(f"    {hit}")
        print()
        print(rule["_message"])

    if blocking:
        print("\nCommit stopped by Lodestar commit-surface guardrails.")
        print("These hold for every committer, not just Claude. Fix the above, or bypass")
        print("deliberately with `git commit --no-verify` if you know why it is safe.")
        return 1
    return 0


if __name__ == "__main__":
    try:
        if sys.version_info < MIN_PYTHON:
            print(
                "⛔ LODESTAR COMMIT GUARDRAILS ARE NOT ENFORCING — this hook needs "
                "Python %d.%d+ but `python3` is %s.\n"
                "Every `commit` rule in .claude/guardrails/ is inert, including `block` "
                "rules. This commit was NOT checked."
                % (MIN_PYTHON[0], MIN_PYTHON[1], "%d.%d.%d" % sys.version_info[:3])
            )
            sys.exit(0)
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:  # never break a commit over a bug in here
        print(f"lodestar-precommit-check: skipped, commit NOT checked ({exc})")
        sys.exit(0)
