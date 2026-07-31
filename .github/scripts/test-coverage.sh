#!/usr/bin/env bash
# Smoke-test the graph completeness checker: a synthetic repo plus hand-built graphs
# standing in for complete, partial, and stale maps. No graphify install required —
# the checker's fallback classifier is what CI exercises.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COV="$ROOT/kit/templates/hooks/lodestar-graph-coverage.py"

python3 -c "import py_compile; py_compile.compile('$COV', doraise=True)" && echo "checker compiles"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
REPO="$WORK/api"
mkdir -p "$REPO/src" "$REPO/node_modules/dep" "$REPO/dist" "$REPO/.venv/lib"

printf 'def a(): pass\n'        > "$REPO/src/a.py"
printf 'def b(): pass\n'        > "$REPO/src/b.py"
printf 'export const c = 1;\n'  > "$REPO/src/c.ts"
printf 'x\n'                    > "$REPO/README.md"          # doc, not code
printf 'module.exports={}\n'    > "$REPO/node_modules/dep/i.js"   # skipped dir
printf 'var x=1\n'              > "$REPO/dist/bundle.js"          # skipped dir
printf 'def v(): pass\n'        > "$REPO/.venv/lib/v.py"          # skipped dir
printf '{}\n'                   > "$REPO/package-lock.json"       # code ext, but skip-listed
printf '{}\n'                   > "$REPO/yarn.lock"               # not a code extension at all

graph() {  # graph <out> <source_file>...
  local out="$1"; shift
  python3 - "$out" "$@" <<'PY'
import json, sys
out, sources = sys.argv[1], sys.argv[2:]
nodes = [{"id": f"n{i}", "label": s, "file_type": "code", "source_file": s}
         for i, s in enumerate(sources)]
json.dump({"nodes": nodes, "edges": []}, open(out, "w"))
PY
}

pass=0; fail=0
field() {  # field <graph> <json-key>
  set +e
  python3 "$COV" --graph "$1" --root "$REPO" --json 2>/dev/null \
    | python3 -c "import json,sys;print(json.load(sys.stdin).get('$2'))"
  set -e
}
expect_field() {  # expect_field "<label>" <graph> <key> <want>
  local got; got="$(field "$2" "$3")"
  if [ "$got" = "$4" ]; then echo "ok: $1 ($3=$got)"; pass=$((pass+1))
  else echo "FAIL: $1 → $3=$got, want $4"; fail=$((fail+1)); fi
}
expect_exit() {  # expect_exit "<label>" <graph> <want-exit> [extra-args...]
  local label="$1" g="$2" want="$3"; shift 3
  local rc
  set +e; python3 "$COV" --graph "$g" --root "$REPO" "$@" >/dev/null 2>&1; rc=$?; set -e
  if [ "$rc" = "$want" ]; then echo "ok: $label → exit $rc"; pass=$((pass+1))
  else echo "FAIL: $label → exit $rc, want $want"; fail=$((fail+1)); fi
}

# --- a complete graph: every real code file has a node -------------------------------
graph "$WORK/complete.json" src/a.py src/b.py src/c.ts
expect_field "complete: total counts real code only" "$WORK/complete.json" filesTotal 3
expect_field "complete: all covered"                 "$WORK/complete.json" filesCovered 3
expect_field "complete: none missing"                "$WORK/complete.json" filesMissing 0
expect_field "complete: 100%"                        "$WORK/complete.json" coveragePct 100.0
expect_exit  "complete: --exit-code passes" "$WORK/complete.json" 0 --exit-code

# Intentional skips, never gaps — that split is what makes the number usable:
# the node_modules/dist/.venv subtrees + package-lock.json (code extension, skip-listed).
# yarn.lock is not a code extension, so it belongs in neither bucket.
expect_field "skips are counted separately" "$WORK/complete.json" filesSkipped 4
graph "$WORK/withlock.json" src/a.py src/b.py src/c.ts
expect_field "skip-listed lockfile is not a gap" "$WORK/withlock.json" filesMissing 0

# --- the bug this issue is about: a graph born missing real files --------------------
graph "$WORK/partial.json" src/a.py
expect_field "partial: missing detected"   "$WORK/partial.json" filesMissing 2
expect_field "partial: covered is honest"  "$WORK/partial.json" filesCovered 1
expect_field "partial: pct reflects gap"   "$WORK/partial.json" coveragePct 33.3
expect_exit  "partial: --exit-code fails"  "$WORK/partial.json" 1 --exit-code
expect_exit  "partial: default exit is 0"  "$WORK/partial.json" 0

out="$(python3 "$COV" --graph "$WORK/partial.json" --root "$REPO" 2>&1 || true)"
for want in "src/b.py" "src/c.ts" "MISSING"; do
  if printf '%s' "$out" | grep -qF "$want"; then echo "ok: report names $want"; pass=$((pass+1))
  else echo "FAIL: report omits $want"; fail=$((fail+1)); fi
done

# --- stale: graph references a file that no longer exists ---------------------------
graph "$WORK/stale.json" src/a.py src/b.py src/c.ts src/deleted.py
expect_field "stale detected"            "$WORK/stale.json" filesStale 1
expect_field "stale is not counted missing" "$WORK/stale.json" filesMissing 0
expect_exit  "stale alone does not fail" "$WORK/stale.json" 0 --exit-code

# --- a skipped path appearing in the graph is not a gap -----------------------------
graph "$WORK/withskipped.json" src/a.py src/b.py src/c.ts node_modules/dep/i.js
expect_field "graphed skip → stale, not missing" "$WORK/withskipped.json" filesMissing 0

# --- degradation: never crash, never fail a build on our own bug --------------------
printf 'not json\n' > "$WORK/broken.json"
expect_exit "unreadable graph exits 0" "$WORK/broken.json" 0 --exit-code
printf '{"nodes": "wrong type"}\n' > "$WORK/wrongshape.json"
expect_exit "wrong-shaped graph exits 0" "$WORK/wrongshape.json" 0 --exit-code
expect_exit "absent graph exits 0" "$WORK/nope.json" 0 --exit-code

# --- manifest mode: iterate repos, skip non-graphify ---------------------------------
WS="$WORK/ws"
mkdir -p "$WS/.claude" "$WS/api/src" "$WS/web/src" "$WS/docs/api/architecture" "$WS/docs/web/architecture"
printf 'def a(): pass\n' > "$WS/api/src/a.py"
printf 'def b(): pass\n' > "$WS/web/src/b.py"
cat > "$WS/.claude/lodestar.manifest.json" <<'EOF'
{"repos":[
  {"name":"api","path":"api","architecture":"graphify","docs":"docs/api/"},
  {"name":"web","path":"web","architecture":"markdown","docs":"docs/web/"}
]}
EOF
graph "$WS/docs/api/architecture/graph.json" src/a.py
set +e
man_out="$(python3 "$COV" --manifest "$WS/.claude/lodestar.manifest.json" 2>&1)"; set -e
if printf '%s' "$man_out" | grep -q "api: 1/1"; then echo "ok: manifest mode checks graphify repo"; pass=$((pass+1))
else echo "FAIL: manifest mode: $man_out"; fail=$((fail+1)); fi
if printf '%s' "$man_out" | grep -q "web: skipped"; then echo "ok: markdown repo skipped"; pass=$((pass+1))
else echo "FAIL: markdown repo not skipped"; fail=$((fail+1)); fi
set +e; python3 "$COV" --manifest "$WORK/absent.json" >/dev/null 2>&1; rc=$?; set -e
if [ "$rc" = 0 ]; then echo "ok: absent manifest exits 0"; pass=$((pass+1))
else echo "FAIL: absent manifest exit $rc"; fail=$((fail+1)); fi

# --- mode is always reported, so an approximate number is never passed off as exact --
mode="$(field "$WORK/complete.json" mode)"
if [ "$mode" = "graphify" ] || [ "$mode" = "fallback" ]; then
  echo "ok: mode reported ($mode)"; pass=$((pass+1))
else echo "FAIL: unexpected mode '$mode'"; fail=$((fail+1)); fi
approx="$(field "$WORK/complete.json" approximate)"
if { [ "$mode" = "fallback" ] && [ "$approx" = "True" ]; } || { [ "$mode" = "graphify" ] && [ "$approx" = "False" ]; }; then
  echo "ok: approximate flag matches mode"; pass=$((pass+1))
else echo "FAIL: mode=$mode but approximate=$approx"; fail=$((fail+1)); fi

echo
if [ "$fail" -gt 0 ]; then echo "❌ coverage test: $fail failed, $pass passed"; exit 1; fi
echo "✅ graph coverage test passed ($pass checks)"
