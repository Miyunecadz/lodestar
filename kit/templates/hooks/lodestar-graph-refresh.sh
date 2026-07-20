#!/usr/bin/env bash
# Lodestar graph-freshness hook — graphify-mode lockstep refresh (pre-commit).
#
# Installed by `/lodestar-freshness` into the detected git-hook manager
# (lefthook / husky / core.hooksPath / plain .git/hooks). On every commit it:
#   1. reads .claude/lodestar.manifest.json for repos with `architecture: graphify`
#      that live INSIDE the git repo this hook runs in,
#   2. for each such repo that has STAGED code changes, rebuilds its graph
#      (`graphify update <path> --force`), copies graph.json / GRAPH_REPORT.md /
#      graph.html into docs/<repo>/architecture/, and `git add`s them so the
#      refreshed map rides in the SAME commit as the code (lockstep),
#   3. stamps mapping.lastMappedAt in the manifest and stages it too.
#
# Contract: this hook NEVER fails a commit. Missing tool, parse error, or a
# graphify failure degrades to a one-line hint on stderr and exit 0. The escape
# hatch for any git hook still applies: `git commit --no-verify` (or LEFTHOOK=0).
#
# Only rebuilds repos whose staged files actually changed (monorepo-aware): an
# unrelated commit touches nothing. `graphify update` is incremental and can lag
# reality by a file or two at commit time; it self-heals toward completeness on
# the next rebuild and never accumulates cruft (see `lodestar-freshness-check.py`).
#
# Overridable via env: LODESTAR_GRAPHIFY_BIN (default `graphify`),
# LODESTAR_GRAPHIFY_OUT (extra directory to look for freshly written artifacts).

set -uo pipefail

hint() { printf 'lodestar-graph-refresh: %s\n' "$1" >&2; }

# Always succeed — a freshness hook must never block a commit.
finish() { exit 0; }
trap finish EXIT

GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$GIT_ROOT" ] || { hint "not inside a git repo — skipping."; finish; }

MANIFEST="$GIT_ROOT/.claude/lodestar.manifest.json"
[ -f "$MANIFEST" ] || finish   # no Lodestar workspace here → nothing to do, silently.

PY="$(command -v python3 || command -v python || true)"
[ -n "$PY" ] || { hint "python3 not found — cannot read the manifest; skipping."; finish; }

GRAPHIFY_BIN="${LODESTAR_GRAPHIFY_BIN:-graphify}"
if ! command -v "$GRAPHIFY_BIN" >/dev/null 2>&1; then
  hint "graphify CLI not found — graph left as-is (a teammate/CI without graphify is fine)."
  finish
fi

# Staged files, relative to the git root (NUL-safe against spaces/newlines).
STAGED="$(git diff --cached --name-only -z 2>/dev/null | tr '\0' '\n')"
[ -n "$STAGED" ] || finish

# Emit `name<TAB>relpath<TAB>docs` for each graphify repo that lives inside this
# git root. Paths are normalized relative to the git root so prefix-matching the
# staged list is reliable. Repos outside this git repo are skipped — this hook
# only manages what it can stage into the current commit.
repos_tsv() {
  MANIFEST="$MANIFEST" GIT_ROOT="$GIT_ROOT" "$PY" - <<'PYEOF'
import json, os, sys
root = os.environ["GIT_ROOT"]
try:
    with open(os.environ["MANIFEST"]) as f:
        m = json.load(f)
except Exception:
    sys.exit(0)
for r in (m.get("repos") or []):
    if r.get("architecture") != "graphify":
        continue
    name = r.get("name")
    path = r.get("path") or ("./" + name if name else None)
    if not name or not path:
        continue
    abs_path = os.path.normpath(os.path.join(root, path))
    try:
        rel = os.path.relpath(abs_path, root)
    except ValueError:
        continue
    if rel == ".." or rel.startswith(".." + os.sep):
        continue  # repo lives outside this git repo — not ours to stage.
    rel = "" if rel == "." else rel
    docs = r.get("docs") or ("docs/%s/" % name)
    print("\t".join([name, rel, docs.rstrip("/")]))
PYEOF
}

# Copy the three graphify artifacts into docs/<repo>/architecture/, searching the
# likely output locations newest-first, and stage whatever we find.
copy_artifacts() {
  repo_abs="$1"; docs_rel="$2"
  dest="$GIT_ROOT/$docs_rel/architecture"
  mkdir -p "$dest"
  staged_any=0
  for art in graph.json GRAPH_REPORT.md graph.html; do
    src=""
    for cand in \
      "${LODESTAR_GRAPHIFY_OUT:-}/$art" \
      "$repo_abs/graphify-out/$art" \
      "$GIT_ROOT/graphify-out/$art" \
      "$repo_abs/$art"; do
      [ -n "${cand#/}" ] || continue
      if [ -f "$cand" ]; then src="$cand"; break; fi
    done
    [ -n "$src" ] || continue
    cp "$src" "$dest/$art"
    git add -- "$dest/$art" 2>/dev/null && staged_any=1
  done
  return $((staged_any == 0))
}

# Stamp mapping.lastMappedAt for a repo and re-stage the manifest.
stamp_manifest() {
  repo_name="$1"; now="$2"
  MANIFEST="$MANIFEST" REPO="$repo_name" NOW="$now" "$PY" - <<'PYEOF'
import json, os
path = os.environ["MANIFEST"]
try:
    with open(path) as f:
        m = json.load(f)
    for r in (m.get("repos") or []):
        if r.get("name") == os.environ["REPO"]:
            mp = r.setdefault("mapping", {})
            mp["lastMappedAt"] = os.environ["NOW"]
            mp["lastMappedSha"] = None  # lockstep: graph matches the commit being made
    with open(path, "w") as f:
        json.dump(m, f, indent=2)
        f.write("\n")
except Exception:
    pass
PYEOF
}

# Is any staged path under directory $1 (relative to git root)? Empty $1 == root.
staged_touches() {
  rel="$1"
  [ -n "$rel" ] || return 0
  while IFS= read -r f; do
    case "$f" in "$rel"/*) return 0 ;; esac
  done <<STAGED_EOF
$STAGED
STAGED_EOF
  return 1
}

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"
REPOS="$(repos_tsv)"
refreshed=0

while IFS=$'\t' read -r name rel docs; do
  [ -n "$name" ] || continue
  staged_touches "$rel" || continue

  repo_abs="$GIT_ROOT/$rel"; [ -n "$rel" ] || repo_abs="$GIT_ROOT"
  hint "code staged under '$name' — rebuilding graph…"
  # </dev/null so graphify can't swallow the loop's input stream.
  if ! "$GRAPHIFY_BIN" update "$repo_abs" --force >/dev/null 2>&1 </dev/null; then
    hint "graphify update failed for '$name' — committing with the existing graph."
    continue
  fi
  if copy_artifacts "$repo_abs" "$docs"; then
    stamp_manifest "$name" "$NOW"
    git add -- "$MANIFEST" 2>/dev/null || true
    refreshed=1
    hint "graph for '$name' refreshed and staged into this commit."
  else
    hint "graphify produced no artifacts for '$name' (set LODESTAR_GRAPHIFY_OUT?) — skipped."
  fi
done <<REPOS_EOF
$REPOS
REPOS_EOF

[ "$refreshed" = "1" ] && hint "done."
finish
