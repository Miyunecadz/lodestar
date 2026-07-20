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


def git(*args):
    """Run git, returning stdout (stripped) or None on any failure."""
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def is_code(path):
    return path.endswith(EXTS)


def changed_code_files(sha, repo_rel):
    """Code files under repo_rel that changed in sha..HEAD. None if the range
    can't be evaluated (e.g. sha not in history)."""
    prefix = "" if repo_rel in ("", ".") else repo_rel.rstrip("/") + "/"
    diff = git("diff", "--name-only", f"{sha}..HEAD", "--")
    if diff is None:
        return None
    files = [f for f in diff.splitlines()
             if f.startswith(prefix) and is_code(f)]
    return files


def find_manifest(explicit):
    if explicit:
        return explicit
    root = git("rev-parse", "--show-toplevel") or "."
    return os.path.join(root, ".claude", "lodestar.manifest.json")


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
        repo_rel = (r.get("path") or f"./{name}").lstrip("./")
        mapping = r.get("mapping")

        if not mapping:
            lines.append(f"  • {name} [{arch}]: never mapped — run /lodestar-onboard or /lodestar-refresh.")
            continue

        sha = mapping.get("lastMappedSha")
        if not sha:
            lines.append(f"  • {name} [{arch}]: lockstep-maintained (graph rebuilt per commit) — OK.")
            continue

        changed = changed_code_files(sha, repo_rel)
        if changed is None:
            lines.append(f"  • {name} [{arch}]: mapped at {sha[:9]}, but that commit isn't in history — re-map to reset.")
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
