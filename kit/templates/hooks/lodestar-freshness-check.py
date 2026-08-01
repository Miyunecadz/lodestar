#!/usr/bin/env python3
"""Lodestar graph-freshness drift detector — offline, stdlib only.

Reads `.claude/lodestar.manifest.json` and, for each onboarded repo, decides
whether its architecture map has drifted from the code. Drift = code under the
repo path changed since the map was last built.

How it decides, per repo:
  - `mapping.lastMappedSha` set  → diff `<sha>..HEAD` for code under the repo path
    (exact; this is how a markdown-mode repo, mapped by /lodestar-refresh outside a
    commit, records provenance).
  - `mapping.lastMappedSha` null → the repo is graphify-LOCKSTEP maintained
    (the pre-commit hook rebuilds it in the same commit); report it as up-to-date
    but note it is auto-maintained, not asserted here.
  - no `mapping` at all           → never mapped; report as such.

**Every git command runs inside the repo it is asking about.** `lastMappedSha` is
recorded from that repo's own HEAD (`/lodestar-onboard` §3b), so the range is only
meaningful in that repo's history. Both supported workspace layouts fall out of the
same code path once the repo's git root is resolved explicitly:

  - **monorepo** — the workspace root is the git repo, the logical repos are
    subdirectories. Git root is the workspace; changed paths are filtered by the
    repo's prefix within it.
  - **separate sub-repos** (the default in `docs/ARCHITECTURE.md` §6) — each repo is
    its own git repo and the workspace root may not be a repo at all. Git root is the
    repo itself and there is no prefix to filter by.

Resolving the root per repo rather than running git in the invocation directory is
what makes the second layout work: before, the diff ran against whatever repository
the caller happened to stand in — usually none — so every repo reported a fingerprint
that "isn't in history" whether or not the code had actually moved.

Never fails a commit and prints nothing alarming on its own: it exits 0 with a
report unless `--exit-code` is passed (then exit 1 if any repo has drifted — for
use as a CI gate or a status check).

Usage:
    lodestar-freshness-check.py [--exit-code] [--repo NAME] [--manifest PATH]

Code-file heuristic mirrors what a mapper cares about; tune EXTS as needed. The
check only inspects tracked files via `git`, so vendored/generated trees that are
gitignored are already excluded.
"""
import json
import os
import subprocess
import sys

EXTS = (
    ".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte",
    ".php", ".rb", ".go", ".rs", ".java", ".kt", ".swift", ".c", ".cc",
    ".cpp", ".h", ".hpp", ".cs", ".scala", ".sql", ".graphql", ".gql",
)


def git(*args, cwd=None):
    """Run git in `cwd`, returning stdout (stripped) or None on any failure."""
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=cwd, capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, NotADirectoryError, OSError):
        return None


def is_code(path):
    return path.endswith(EXTS)


def repo_scope(workspace, repo):
    """Locate the git repository that owns a manifest repo entry.

    Returns (repo_abs, git_root, prefix):
      git_root  the repository `lastMappedSha` belongs to, or None when the path is
                not inside one (no git, deleted repo, not initialised yet)
      prefix    where the repo sits inside that root, as a path prefix for filtering
                changed files — "" when the repo *is* the root

    The monorepo and separate-sub-repos layouts differ only in what this returns:
    a monorepo yields the workspace root and a "web/" prefix, separate repos yield
    the repo itself and "".
    """
    rel = repo.get("path") or "./{}".format(repo.get("name") or "")
    repo_abs = os.path.normpath(os.path.join(workspace, rel))
    git_root = git("rev-parse", "--show-toplevel", cwd=repo_abs)
    if not git_root:
        return repo_abs, None, None
    git_root = os.path.normpath(git_root)
    inner = os.path.relpath(repo_abs, git_root)
    prefix = "" if inner == "." else inner.replace(os.sep, "/").rstrip("/") + "/"
    return repo_abs, git_root, prefix


def has_commit(sha, git_root):
    """Is this sha a commit in that repository's history?"""
    return git("cat-file", "-e", sha + "^{commit}", cwd=git_root) is not None


def changed_code_files(sha, git_root, prefix):
    """Code files under `prefix` that changed in sha..HEAD, within `git_root`.

    None means the diff itself could not be evaluated — distinct from an empty list,
    which means the range resolved and nothing changed.
    """
    diff = git("diff", "--name-only", "{}..HEAD".format(sha), "--", cwd=git_root)
    if diff is None:
        return None
    return [f for f in diff.splitlines() if f.startswith(prefix) and is_code(f)]


def find_manifest(explicit):
    if explicit:
        return explicit
    root = git("rev-parse", "--show-toplevel") or "."
    return os.path.join(root, ".claude", "lodestar.manifest.json")


def workspace_of(manifest_path):
    """The workspace root that owns a manifest — `<workspace>/.claude/<file>`.

    Derived from the manifest path rather than from git, because the workspace root
    is frequently not a git repository at all.
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(manifest_path)))


def main(argv):
    exit_code = "--exit-code" in argv
    only = None
    if "--repo" in argv:
        i = argv.index("--repo")
        only = argv[i + 1] if i + 1 < len(argv) else None
    manifest_path = None
    if "--manifest" in argv:
        i = argv.index("--manifest")
        manifest_path = argv[i + 1] if i + 1 < len(argv) else None
    manifest_path = find_manifest(manifest_path)
    workspace = workspace_of(manifest_path)

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except (IOError, OSError, ValueError) as e:
        print(f"lodestar-freshness-check: cannot read {manifest_path}: {e}")
        return 0

    repos = manifest.get("repos") or []
    if not repos:
        print("No onboarded repos in the manifest — nothing to check.")
        return 0

    any_drift = False
    lines = []
    for r in repos:
        name = r.get("name")
        if only and name != only:
            continue
        arch = r.get("architecture", "unknown")
        mapping = r.get("mapping")

        if not mapping:
            lines.append(f"  • {name} [{arch}]: never mapped — run /lodestar-onboard or /lodestar-refresh.")
            continue

        sha = mapping.get("lastMappedSha")
        if not sha:
            lines.append(f"  • {name} [{arch}]: lockstep-maintained (graph rebuilt per commit) — OK.")
            continue

        repo_abs, git_root, prefix = repo_scope(workspace, r)

        # Three ways this can go wrong, and they need different advice: the repo is
        # not a git checkout here, the fingerprint predates a history rewrite, or the
        # diff itself failed. Lumping them together is what made the old message
        # ("isn't in history") appear for workspaces where git was never consulted.
        if git_root is None:
            lines.append(f"  • {name} [{arch}]: no git repository at {repo_abs} — cannot check drift.")
            continue
        if not has_commit(sha, git_root):
            lines.append(f"  • {name} [{arch}]: mapped at {sha[:9]}, but that commit isn't in this repo's history — re-map to reset.")
            any_drift = True
            continue

        changed = changed_code_files(sha, git_root, prefix)
        if changed is None:
            lines.append(f"  • {name} [{arch}]: mapped at {sha[:9]}, but the diff against HEAD could not be evaluated.")
            any_drift = True
        elif changed:
            any_drift = True
            preview = ", ".join(changed[:3]) + (" …" if len(changed) > 3 else "")
            verb = "run /lodestar-refresh" if arch == "markdown" else "rebuild the graph"
            lines.append(f"  • {name} [{arch}]: DRIFTED — {len(changed)} code file(s) changed since {sha[:9]} ({preview}). {verb}.")
        else:
            lines.append(f"  • {name} [{arch}]: fresh (no code change since {sha[:9]}).")

    print("Lodestar graph freshness:")
    print("\n".join(lines) if lines else "  (no matching repo)")
    if exit_code and any_drift:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:  # never explode in a hook/CI context
        print(f"lodestar-freshness-check: {e}")
        sys.exit(0)
