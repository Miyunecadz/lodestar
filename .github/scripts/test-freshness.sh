#!/usr/bin/env bash
# Smoke-test the architecture-map drift detector against BOTH supported workspace
# layouts. The layout is the whole point of this file: `lastMappedSha` is recorded
# from a repo's own HEAD, so the checker has to run git inside that repo. Running it
# in the invocation directory only ever worked for a monorepo, and silently reported
# every repo as unresolvable in the separate-sub-repos layout that
# `docs/ARCHITECTURE.md` §6 calls the default.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECK="$ROOT/kit/templates/hooks/lodestar-freshness-check.py"

python3 -c "import py_compile; py_compile.compile('$CHECK', doraise=True)" && echo "checker compiles"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

new_repo() {  # new_repo <dir>
  mkdir -p "$1/src"
  git -C "$1" init -q .
  git -C "$1" config user.email test@example.com
  git -C "$1" config user.name "Test"
  printf 'def a(): pass\n' > "$1/src/a.py"
  git -C "$1" add -A
  git -C "$1" commit -qm init
}

manifest() {  # manifest <workspace> <json-repos-array>
  mkdir -p "$1/.claude"
  printf '{"repos": %s}\n' "$2" > "$1/.claude/lodestar.manifest.json"
}

pass=0; fail=0
report() {  # report <workspace> [extra-args...]
  local ws="$1"; shift
  ( cd "$ws" && python3 "$CHECK" --manifest .claude/lodestar.manifest.json "$@" 2>&1 )
}
expect() {  # expect "<label>" "<output>" "<repo-name>" "<substring>"
  local line
  line="$(printf '%s\n' "$2" | grep -F "• $3 " || true)"
  case "$line" in
    *"$4"*) echo "ok: $1"; pass=$((pass+1)) ;;
    *) echo "FAIL: $1"; echo "     wanted substring: $4"; echo "     got: ${line:-<no line for $3>}"; fail=$((fail+1)) ;;
  esac
}

# ---------------------------------------------------------------- separate sub-repos
# Workspace root holds sibling repos and is NOT a git repo itself. This is the layout
# the old implementation could not evaluate at all.
SEP="$WORK/separate"
mkdir -p "$SEP"
new_repo "$SEP/web"
new_repo "$SEP/api"
WEB_SHA="$(git -C "$SEP/web" rev-parse HEAD)"
API_SHA="$(git -C "$SEP/api" rev-parse HEAD)"
printf 'def b(): pass\n' > "$SEP/web/src/b.py"
git -C "$SEP/web" add -A
git -C "$SEP/web" commit -qm "drift web"

manifest "$SEP" "$(cat <<JSON
[{"name":"web","path":"./web","architecture":"markdown","mapping":{"lastMappedSha":"$WEB_SHA"}},
 {"name":"api","path":"./api","architecture":"markdown","mapping":{"lastMappedSha":"$API_SHA"}}]
JSON
)"

out="$(report "$SEP")"
expect "separate repos: changed repo reports DRIFTED"      "$out" web "DRIFTED"
expect "separate repos: drifted file named"                 "$out" web "src/b.py"
expect "separate repos: unchanged repo reports fresh"       "$out" api "fresh"

# The workspace root is not a git repo, so the checker must not depend on the caller
# standing anywhere in particular.
out="$(cd "$WORK" && python3 "$CHECK" --manifest "$SEP/.claude/lodestar.manifest.json" 2>&1)"
expect "separate repos: verdict independent of cwd (drift)" "$out" web "DRIFTED"
expect "separate repos: verdict independent of cwd (fresh)" "$out" api "fresh"

set +e
( cd "$SEP" && python3 "$CHECK" --manifest .claude/lodestar.manifest.json --exit-code >/dev/null 2>&1 )
rc=$?
set -e
if [ "$rc" -eq 1 ]; then echo "ok: separate repos: --exit-code fails on drift"; pass=$((pass+1))
else echo "FAIL: separate repos: --exit-code returned $rc, wanted 1"; fail=$((fail+1)); fi

# ---------------------------------------------------------------- monorepo
# One git repo; the logical repos are subdirectories. A change in one must not be
# attributed to its sibling — that is what the path prefix filter is for.
MONO="$WORK/mono"
mkdir -p "$MONO/web/src" "$MONO/api/src"
git -C "$MONO" init -q .
git -C "$MONO" config user.email test@example.com
git -C "$MONO" config user.name "Test"
printf 'def a(): pass\n' > "$MONO/web/src/a.py"
printf 'def a(): pass\n' > "$MONO/api/src/a.py"
git -C "$MONO" add -A
git -C "$MONO" commit -qm init
MONO_SHA="$(git -C "$MONO" rev-parse HEAD)"
printf 'def b(): pass\n' > "$MONO/web/src/b.py"
printf 'notes\n'         > "$MONO/api/NOTES.md"   # not code — must not count as drift
git -C "$MONO" add -A
git -C "$MONO" commit -qm "drift web only"

manifest "$MONO" "$(cat <<JSON
[{"name":"web","path":"./web","architecture":"markdown","mapping":{"lastMappedSha":"$MONO_SHA"}},
 {"name":"api","path":"./api","architecture":"markdown","mapping":{"lastMappedSha":"$MONO_SHA"}}]
JSON
)"

out="$(report "$MONO")"
expect "monorepo: changed subdirectory reports DRIFTED"     "$out" web "DRIFTED"
expect "monorepo: sibling stays fresh from the same sha"    "$out" api "fresh"
expect "monorepo: non-code change is not drift"             "$out" api "fresh"

# ---------------------------------------------------------------- degraded states
# Each needs distinct advice; collapsing them is what produced the old misleading
# "isn't in history" message for workspaces where git was never consulted.
manifest "$MONO" "$(cat <<JSON
[{"name":"absent","path":"./absent","architecture":"markdown","mapping":{"lastMappedSha":"$MONO_SHA"}},
 {"name":"rewritten","path":"./web","architecture":"markdown","mapping":{"lastMappedSha":"deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"}},
 {"name":"lockstep","path":"./api","architecture":"graphify","mapping":{"lastMappedSha":null}},
 {"name":"unmapped","path":"./api","architecture":"markdown"}]
JSON
)"

out="$(report "$MONO")"
expect "missing repo path is reported as such, not as drift" "$out" absent    "no git repository"
expect "unknown sha says it is not in THIS repo's history"   "$out" rewritten "isn't in this repo's history"
expect "lockstep repo reported as auto-maintained"           "$out" lockstep  "lockstep-maintained"
expect "never-mapped repo reported as such"                  "$out" unmapped  "never mapped"

# ---------------------------------------------------------------- never breaks
set +e
out="$(cd "$WORK" && python3 "$CHECK" --manifest "$WORK/nope.json" 2>&1)"; rc=$?
set -e
if [ "$rc" -eq 0 ]; then echo "ok: absent manifest exits 0"; pass=$((pass+1))
else echo "FAIL: absent manifest exited $rc"; fail=$((fail+1)); fi

printf 'not json' > "$WORK/broken.json"
set +e
( cd "$WORK" && python3 "$CHECK" --manifest "$WORK/broken.json" --exit-code >/dev/null 2>&1 ); rc=$?
set -e
if [ "$rc" -eq 0 ]; then echo "ok: unparseable manifest exits 0 even with --exit-code"; pass=$((pass+1))
else echo "FAIL: unparseable manifest exited $rc"; fail=$((fail+1)); fi

echo
if [ "$fail" -gt 0 ]; then echo "❌ freshness test: $fail failed, $pass passed"; exit 1; fi
echo "✅ graph freshness test passed ($pass checks)"
