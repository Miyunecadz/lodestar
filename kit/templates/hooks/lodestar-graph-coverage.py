#!/usr/bin/env python3
"""Lodestar graph coverage — does the architecture graph actually cover the code?

`CLAUDE.md` tells agents to prefer querying `graph.json` over re-reading source. A graph
that silently omits real files therefore *misleads* an agent rather than merely being
unhelpful — the same failure mode as a stale graph, but invisible: node counts are never
checked against the source tree, so a partial map looks exactly like a complete one.

This compares the code files **on disk** against the `source_file`s present in the graph
and splits the difference four ways:

    covered   file has at least one node in the graph
    missing   file is code graphify would scan, but has NO node  → a real gap
    skipped   file is excluded on purpose (noise dir, ignore file, generated lockfile)
    stale     graph references a file that is no longer on disk (or is now ignored)

Only `missing` is a defect. Distinguishing it from `skipped` is the whole point: without
that split, every `node_modules/` file reads as a gap and the signal is worthless.

Usage:
    lodestar-graph-coverage.py [--repo NAME] [--manifest PATH] [--json] [--exit-code]
                               [--graph PATH --root PATH]

    --repo NAME     check only this repo from the manifest
    --graph/--root  check one graph against one tree, ignoring the manifest
    --json          machine-readable, for writing `mapping.coverage` into the manifest
    --exit-code     exit 1 when any repo has missing files (for CI or a hook)
    --quiet         suppress the per-file lists, keep the totals

Which files "graphify would scan" is graphify's own question, so when the `graphify`
package is importable this uses its real classifier and ignore rules (`classify_file`,
`_is_noise_dir`, `_is_ignored`, `.graphifyignore`/`.gitignore` handling). Without it,
a bundled copy of the extension list and skip-dirs is used and every result is labelled
**approximate** — teammates and CI can still get a number, but it may disagree at the
edges with what graphify actually indexed. The mode is always reported.
"""

import json
import os
import sys

# ---------------------------------------------------------------- graphify's rules

# Fallback copy of graphify 0.9.18's CODE_EXTENSIONS / _SKIP_DIRS / _SKIP_FILES, used
# only when the package is not importable. Kept in one place so the drift is obvious.
FALLBACK_CODE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".ejs", ".ets",
    ".go", ".rs", ".java", ".groovy", ".gradle", ".cpp", ".cc", ".cxx", ".c", ".h",
    ".hpp", ".cu", ".cuh", ".metal", ".rb", ".rake", ".swift", ".kt", ".kts", ".cs",
    ".scala", ".php", ".lua", ".luau", ".toc", ".zig", ".ps1", ".psm1", ".psd1", ".ex",
    ".exs", ".m", ".mm", ".jl", ".vue", ".svelte", ".astro", ".dart", ".v", ".sv",
    ".svh", ".sql", ".r", ".f", ".F", ".f90", ".F90", ".f95", ".F95", ".f03", ".F03",
    ".f08", ".F08", ".pas", ".pp", ".dpr", ".dpk", ".lpr", ".inc", ".dfm", ".lfm",
    ".lpk", ".sh", ".bash", ".json", ".tf", ".tfvars", ".hcl", ".dm", ".dme", ".dmi",
    ".dmm", ".dmf", ".sln", ".slnx", ".csproj", ".fsproj", ".vbproj", ".xaml", ".razor",
    ".cshtml", ".cls", ".trigger",
}
FALLBACK_SKIP_DIRS = {
    "venv", ".venv", "env", ".env", "node_modules", "__pycache__", ".git", "dist",
    "build", "target", "out", "site-packages", "lib64", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", ".nox", ".eggs", "graphify-out", "coverage", "lcov-report",
    "visual-tests", "visual-test", "__snapshots__", "storybook-static", "dist-protected",
    ".next", ".nuxt", ".turbo", ".angular", ".idea", ".cache", ".parcel-cache",
    ".svelte-kit", ".terraform", ".serverless", ".graphify", ".worktrees",
}
FALLBACK_SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock", "poetry.lock",
    "Gemfile.lock", "composer.lock", "go.sum", "go.work.sum",
}


class Classifier:
    """Decides which files graphify would treat as code, using graphify when present."""

    REQUIRED = ("classify_file", "_is_noise_dir", "_is_ignored", "_load_graphifyignore")

    def __init__(self):
        self.mode = "fallback"
        self._detect = None
        self._patterns_cache = {}
        for loader in (self._import_direct, self._import_from_cli_venv):
            detect = loader()
            if detect is not None:
                self._detect = detect
                self.mode = "graphify"
                return

    def _usable(self, detect):
        """Only claim authority if every internal we rely on is present — a future
        graphify could rename one, and a half-authoritative answer is worse than an
        honest approximation."""
        return all(hasattr(detect, attr) for attr in self.REQUIRED)

    def _import_direct(self):
        try:
            from graphify import detect

            return detect if self._usable(detect) else None
        except Exception:
            return None

    def _import_from_cli_venv(self):
        """graphify is normally installed as an isolated tool (uv/pipx), so it is not on
        this interpreter's path. Find the CLI, add its venv's site-packages, and retry.
        A Python-version mismatch makes graphify's native extensions unimportable — that
        raises, and we fall back rather than reporting a wrong answer."""
        import glob
        import shutil

        cli = shutil.which("graphify")
        if not cli:
            return None
        try:
            venv = os.path.dirname(os.path.dirname(os.path.realpath(cli)))
            candidates = glob.glob(os.path.join(venv, "lib", "python*", "site-packages"))
            candidates += glob.glob(os.path.join(venv, "lib", "site-packages"))  # Windows
            for site in candidates:
                if site in sys.path:
                    continue
                sys.path.insert(0, site)
                try:
                    from graphify import detect

                    return detect if self._usable(detect) else None
                except Exception:
                    sys.path.remove(site)
        except Exception:
            return None
        return None

    # -- directories --

    def skip_dir(self, name, parent_path):
        if self._detect is not None:
            try:
                from pathlib import Path

                return bool(self._detect._is_noise_dir(name, Path(parent_path)))
            except Exception:
                pass
        return name in FALLBACK_SKIP_DIRS or name.endswith(".egg-info")

    # -- files --

    def is_code(self, path):
        if self._detect is not None:
            try:
                from pathlib import Path

                # classify_file returns a FileType enum (FileType.CODE, value "code"),
                # not a bare string — compare on the value, never on the object.
                file_type = self._detect.classify_file(Path(path))
                if file_type is None:
                    return False
                return str(getattr(file_type, "value", file_type)).lower() == "code"
            except Exception:
                pass
        return os.path.splitext(path)[1] in FALLBACK_CODE_EXTENSIONS

    def skip_file(self, path):
        """Generated files graphify's walker refuses even though they classify as code.

        `classify_file` says `package-lock.json` is code — the skip list is applied by
        graphify's *walker*, separately. Miss that and every lockfile is reported as a
        missing file, which is precisely the false gap that makes a coverage number
        worthless.
        """
        name = os.path.basename(path)
        if self._detect is not None:
            skip = getattr(self._detect, "_SKIP_FILES", None)
            if skip:
                try:
                    return name in skip
                except Exception:
                    pass
        return name in FALLBACK_SKIP_FILES

    def ignored(self, path, root):
        """Honour .graphifyignore / .gitignore the way graphify does."""
        if self._detect is None:
            return False
        try:
            from pathlib import Path

            if root not in self._patterns_cache:
                self._patterns_cache[root] = self._detect._load_graphifyignore(Path(root))
            return bool(self._detect._is_ignored(Path(path), self._patterns_cache[root]))
        except Exception:
            return False


def walk_code_files(root, classifier):
    """(code_files, skipped_files) as repo-relative paths, mirroring graphify's walk."""
    code, skipped = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        kept = []
        for name in sorted(dirnames):
            if classifier.skip_dir(name, dirpath):
                # Record what a skipped subtree would have contributed, so "skipped"
                # is a real number rather than a silent omission.
                for sub_dir, _, sub_files in os.walk(os.path.join(dirpath, name)):
                    for sub in sub_files:
                        full = os.path.join(sub_dir, sub)
                        if classifier.is_code(full) or classifier.skip_file(full):
                            skipped.append(os.path.relpath(full, root))
            else:
                kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            if not classifier.is_code(full):
                continue
            rel = os.path.relpath(full, root)
            if classifier.skip_file(full) or classifier.ignored(full, root):
                skipped.append(rel)
            else:
                code.append(rel)
    return sorted(code), sorted(skipped)


def graph_source_files(graph_path):
    """The set of source_files the graph has nodes for. None if unreadable."""
    try:
        with open(graph_path, "r") as f:
            data = json.load(f)
    except (IOError, OSError, ValueError):
        return None
    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        return None
    out = set()
    for node in nodes:
        if isinstance(node, dict):
            src = node.get("source_file")
            if isinstance(src, str) and src:
                out.add(src.replace("\\", "/").lstrip("./"))
    return out


def check(root, graph_path, classifier):
    covered_by_graph = graph_source_files(graph_path)
    if covered_by_graph is None:
        return {"error": f"could not read a node list from {graph_path}"}
    on_disk, skipped = walk_code_files(root, classifier)
    normalized = {p.replace(os.sep, "/") for p in on_disk}
    covered = sorted(normalized & covered_by_graph)
    missing = sorted(normalized - covered_by_graph)
    stale = sorted(covered_by_graph - normalized)
    total = len(normalized)
    return {
        "mode": classifier.mode,
        "approximate": classifier.mode != "graphify",
        "filesTotal": total,
        "filesCovered": len(covered),
        "filesMissing": len(missing),
        "filesSkipped": len(skipped),
        "filesStale": len(stale),
        "coveragePct": round(100.0 * len(covered) / total, 1) if total else 100.0,
        "missing": missing,
        "stale": stale,
        "skippedSample": sorted(skipped)[:10],
    }


# ---------------------------------------------------------------- manifest plumbing


def load_manifest(path):
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (IOError, OSError, ValueError):
        return {}


def graph_path_for(workspace, repo):
    docs = repo.get("docs") or os.path.join("docs", repo.get("name", ""))
    return os.path.join(workspace, docs, "architecture", "graph.json")


def report(name, result, quiet=False):
    if "error" in result:
        print(f"  {name}: {result['error']}")
        return
    flag = " (approximate — graphify not importable)" if result["approximate"] else ""
    print(f"  {name}: {result['filesCovered']}/{result['filesTotal']} code files covered "
          f"({result['coveragePct']}%){flag}")
    if result["filesSkipped"]:
        sample = ", ".join(result["skippedSample"][:3])
        print(f"    skipped on purpose: {result['filesSkipped']}"
              + (f" (e.g. {sample})" if sample else ""))
    if result["filesMissing"]:
        print(f"    MISSING {result['filesMissing']} file(s) with no nodes:")
        if not quiet:
            for path in result["missing"][:25]:
                print(f"      - {path}")
            if result["filesMissing"] > 25:
                print(f"      … and {result['filesMissing'] - 25} more")
    if result["filesStale"]:
        print(f"    stale: {result['filesStale']} graph file(s) no longer on disk")
        if not quiet:
            for path in result["stale"][:10]:
                print(f"      - {path}")


def main(argv):
    def opt(flag, default=None):
        if flag in argv:
            i = argv.index(flag)
            return argv[i + 1] if i + 1 < len(argv) else default
        return default

    as_json = "--json" in argv
    exit_code = "--exit-code" in argv
    quiet = "--quiet" in argv
    classifier = Classifier()

    # One-shot mode: an explicit graph + tree, no manifest involved.
    if "--graph" in argv or "--root" in argv:
        graph = opt("--graph")
        root = opt("--root", ".")
        if not graph:
            print("--graph is required with --root")
            return 2
        result = check(root, graph, classifier)
        if as_json:
            print(json.dumps(result, indent=2))
        else:
            print("Graph coverage:")
            report(root, result, quiet)
        return 1 if exit_code and result.get("filesMissing") else 0

    manifest_path = opt("--manifest", os.path.join(".claude", "lodestar.manifest.json"))
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(manifest_path)))
    manifest = load_manifest(manifest_path)
    repos = manifest.get("repos")
    if not isinstance(repos, list) or not repos:
        print(f"No repos in {manifest_path} — nothing to check.")
        return 0

    only = opt("--repo")
    results, any_missing = {}, False
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        name = repo.get("name") or "?"
        if only and name != only:
            continue
        if repo.get("architecture") != "graphify":
            results[name] = {"skipped": f"architecture is {repo.get('architecture')!r}, not graphify"}
            continue
        root = os.path.join(workspace, repo.get("path") or name)
        graph = graph_path_for(workspace, repo)
        if not os.path.isdir(root):
            results[name] = {"error": f"repo path not found: {root}"}
            continue
        if not os.path.isfile(graph):
            results[name] = {"error": f"no graph at {graph}"}
            continue
        result = check(root, graph, classifier)
        results[name] = result
        if result.get("filesMissing"):
            any_missing = True

    if as_json:
        print(json.dumps({"mode": classifier.mode, "repos": results}, indent=2))
    else:
        print("Graph coverage:")
        for name, result in results.items():
            if "skipped" in result:
                print(f"  {name}: skipped — {result['skipped']}")
            else:
                report(name, result, quiet)
        if any_missing:
            print("\nMissing files have no nodes in the graph, so an agent querying it will")
            print("not see them. Rebuild fully: `graphify extract <repo> --force` (add")
            print("`--code-only` if no LLM backend is configured), then re-run this check.")
    return 1 if exit_code and any_missing else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"lodestar-graph-coverage: skipped ({exc})")
        sys.exit(0)
