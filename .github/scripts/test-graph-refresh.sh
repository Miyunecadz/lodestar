#!/usr/bin/env bash
# Smoke-test the graph-freshness pre-commit hook (kit/templates/hooks/lodestar-graph-refresh.sh).
#
# This is the shell script with the most reach in the kit: /lodestar-freshness installs it
# into users' git-hook managers, it runs on EVERY commit, and it `git add`s into the commit
# being made. Until now it had no test at all — which is how a guard that never fired
# (issue #38) survived. graphify is stubbed via LODESTAR_GRAPHIFY_BIN, so this needs no
# graphify install and can exercise the artifact-discovery paths directly.
#
# The contract under test: the hook NEVER fails a commit, and stages exactly the artifacts
# it found — no more.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOK="$ROOT/kit/templates/hooks/lodestar-graph-refresh.sh"

bash -n "$HOOK" && echo "hook parses"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
pass=0; fail=0

ok()   { echo "ok: $1"; pass=$((pass + 1)); }
bad()  { echo "FAIL: $1"; fail=$((fail + 1)); }
check(){ if [ "$2" = "$3" ]; then ok "$1 ($3)"; else bad "$1 → '$2', want '$3'"; fi; }

# A fresh workspace: one git repo, one graphify-mapped sub-repo with staged code.
new_ws() {  # new_ws <name> → echoes the git root
  local ws="$WORK/$1"
  mkdir -p "$ws/api/src" "$ws/.claude"
  git init -q "$ws"
  git -C "$ws" config user.email ci@example.com
  git -C "$ws" config user.name ci
  cat > "$ws/.claude/lodestar.manifest.json" <<'JSON'
{"repos":[{"name":"api","path":"api","architecture":"graphify","docs":"docs/api/"}]}
JSON
  printf 'print("hi")\n' > "$ws/api/src/app.py"
  git -C "$ws" add api/src/app.py
  echo "$ws"
}

# A graphify stub that writes the three artifacts wherever we tell it to.
stub_graphify() {  # stub_graphify <bin-dir> <out-dir-or-empty>
  local bin="$1" out="$2"
  mkdir -p "$bin"
  cat > "$bin/graphify" <<STUB
#!/usr/bin/env bash
# args: update <repo_abs> --force
out="$out"
[ -n "\$out" ] || out="\$2/graphify-out"
mkdir -p "\$out"
printf '{"nodes":[]}' > "\$out/graph.json"
printf '# report'     > "\$out/GRAPH_REPORT.md"
printf '<html></html>' > "\$out/graph.html"
exit 0
STUB
  chmod +x "$bin/graphify"
}

run_hook() {  # run_hook <ws> [env assignments...]
  local ws="$1"; shift
  (cd "$ws" && env "$@" bash "$HOOK" >/dev/null 2>&1; echo "rc=$?")
}

staged_list() { git -C "$1" diff --cached --name-only | sort | tr '\n' ' '; }

# --- 1. LODESTAR_GRAPHIFY_OUT set: artifacts are found there and staged ---------------
WS="$(new_ws out-set)"
stub_graphify "$WORK/bin-set" "$WORK/custom-out"
rc="$(run_hook "$WS" "PATH=$WORK/bin-set:$PATH" "LODESTAR_GRAPHIFY_BIN=$WORK/bin-set/graphify" "LODESTAR_GRAPHIFY_OUT=$WORK/custom-out")"
check "override set: hook never fails a commit" "$rc" "rc=0"
for art in graph.json GRAPH_REPORT.md graph.html; do
  if [ -f "$WS/docs/api/architecture/$art" ]; then ok "override set: $art copied"
  else bad "override set: $art missing"; fi
done
if git -C "$WS" diff --cached --name-only | grep -q "docs/api/architecture/graph.json"; then
  ok "override set: artifacts staged into the commit"
else bad "override set: artifacts not staged"; fi

# --- 2. LODESTAR_GRAPHIFY_OUT unset: falls back to <repo>/graphify-out ----------------
# The guard here used to be `[ -n "${cand#/}" ]`, which never skipped the unset override,
# so the loop stat'd `/graph.json` at the filesystem root (issue #38).
WS="$(new_ws out-unset)"
stub_graphify "$WORK/bin-unset" ""
rc="$(run_hook "$WS" "PATH=$WORK/bin-unset:$PATH" "LODESTAR_GRAPHIFY_BIN=$WORK/bin-unset/graphify")"
check "override unset: hook never fails a commit" "$rc" "rc=0"
if [ -f "$WS/docs/api/architecture/graph.json" ]; then ok "override unset: falls back to <repo>/graphify-out"
else bad "override unset: no artifact found"; fi

# --- 3. graphify writes nothing → nothing is staged -----------------------------------
# The #38 trap was the loop testing `/graph.json` at the filesystem root when the override
# was unset. That cannot be asserted directly without writing to `/`, so this pins the
# observable half: when no candidate location holds an artifact, the hook stages nothing.
WS="$(new_ws nothing-found)"
mkdir -p "$WORK/bin-none"
cat > "$WORK/bin-none/graphify" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$WORK/bin-none/graphify"
rc="$(run_hook "$WS" "PATH=$WORK/bin-none:$PATH" "LODESTAR_GRAPHIFY_BIN=$WORK/bin-none/graphify")"
check "no artifacts: hook never fails a commit" "$rc" "rc=0"
check "no artifacts: nothing extra staged" "$(staged_list "$WS")" "api/src/app.py "

# --- 4. graphify missing entirely → skip, do not fail ---------------------------------
WS="$(new_ws no-graphify)"
rc="$(run_hook "$WS" "LODESTAR_GRAPHIFY_BIN=$WORK/definitely-not-here")"
check "no graphify: hook never fails a commit" "$rc" "rc=0"
check "no graphify: nothing extra staged" "$(staged_list "$WS")" "api/src/app.py "

# --- 5. graphify fails → commit still proceeds with the existing graph ----------------
WS="$(new_ws graphify-fails)"
mkdir -p "$WORK/bin-fail"
cat > "$WORK/bin-fail/graphify" <<'STUB'
#!/usr/bin/env bash
echo "boom" >&2; exit 2
STUB
chmod +x "$WORK/bin-fail/graphify"
rc="$(run_hook "$WS" "LODESTAR_GRAPHIFY_BIN=$WORK/bin-fail/graphify")"
check "graphify failure: hook never fails a commit" "$rc" "rc=0"
check "graphify failure: nothing extra staged" "$(staged_list "$WS")" "api/src/app.py "

# --- 6. Staged changes outside the mapped repo must not trigger a rebuild -------------
WS="$(new_ws unrelated)"
git -C "$WS" reset -q
mkdir -p "$WS/web"
printf 'x\n' > "$WS/web/index.js"
git -C "$WS" add web/index.js
stub_graphify "$WORK/bin-unrelated" "$WORK/unrelated-out"
rc="$(run_hook "$WS" "LODESTAR_GRAPHIFY_BIN=$WORK/bin-unrelated/graphify" "LODESTAR_GRAPHIFY_OUT=$WORK/unrelated-out")"
check "unrelated commit: hook never fails a commit" "$rc" "rc=0"
check "unrelated commit: no graph staged" "$(staged_list "$WS")" "web/index.js "

# --- 7. No manifest at all → silent no-op --------------------------------------------
WS="$(new_ws no-manifest)"
rm -f "$WS/.claude/lodestar.manifest.json"
rc="$(run_hook "$WS")"
check "no manifest: hook never fails a commit" "$rc" "rc=0"

echo
if [ "$fail" -gt 0 ]; then echo "❌ graph-refresh test: $fail failed, $pass passed"; exit 1; fi
echo "✅ graph-refresh test passed ($pass checks)"
