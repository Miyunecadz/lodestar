#!/usr/bin/env bash
# Smoke-test install.sh end to end: clone mode, bootstrap mode, tag pinning, and the
# refusals. Uses a throwaway local git repo as the "remote", so it needs no network and
# does not depend on which tags this checkout happens to have fetched.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

pass=0
fail=0
check() {  # check "<label>" "<want-exit>" <cmd...>
  local label="$1" want="$2"; shift 2
  local out rc
  set +e; out="$("$@" 2>&1)"; rc=$?; set -e
  if [ "$rc" != "$want" ]; then
    echo "FAIL: $label → exit $rc, want $want"; echo "${out//$'\n'/$'\n'    }"; fail=$((fail + 1)); return
  fi
  echo "ok: $label → exit $rc"; pass=$((pass + 1))
}
expect_file() {  # expect_file "<label>" <path>
  if [ -f "$2" ]; then echo "ok: $1"; pass=$((pass + 1))
  else echo "FAIL: $1 (missing $2)"; fail=$((fail + 1)); fi
}
expect_json() {  # expect_json "<label>" <file> <key> <want>
  local got
  got="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2],''))" "$2" "$3")"
  if [ "$got" = "$4" ]; then echo "ok: $1 ($3=$got)"; pass=$((pass + 1))
  else echo "FAIL: $1 → $3=$got, want $4"; fail=$((fail + 1)); fi
}

# --- build a local "remote" with two tags: one current, one pre-kit/ layout ----------
REMOTE="$WORK/remote"
git init -q "$REMOTE"
git -C "$REMOTE" config user.email ci@example.com
git -C "$REMOTE" config user.name ci
cp -R "$ROOT/kit" "$ROOT/install.sh" "$ROOT/VERSION" "$REMOTE/"
git -C "$REMOTE" add -A
git -C "$REMOTE" commit -qm "kit layout"
git -C "$REMOTE" tag v9.9.8
git -C "$REMOTE" rm -rq kit
git -C "$REMOTE" commit -qm "pre-kit layout"
git -C "$REMOTE" tag v0.0.1          # stands in for a tag older than v0.5.0
git -C "$REMOTE" reset -q --hard v9.9.8
git -C "$REMOTE" tag v9.9.9          # newest tag → what a default bootstrap must pick

VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"

# --- 1. clone mode: copies from the kit/ next to the script, records a path ----------
mkdir -p "$WORK/ws-clone"
check "clone install" 0 "$ROOT/install.sh" "$WORK/ws-clone"
expect_file "catalog copied"   "$WORK/ws-clone/.lodestar/catalog/CATALOG.md"
expect_file "commands copied"  "$WORK/ws-clone/.claude/commands/lodestar-update.md"
expect_json "records kind"     "$WORK/ws-clone/.lodestar/source.json" kind local
expect_json "records version"  "$WORK/ws-clone/.lodestar/source.json" version "$VERSION"
check "clone re-run (update mode)" 0 "$ROOT/install.sh" "$WORK/ws-clone"

# --- source.json must survive an origin that is not shell-safe (issue #35) -----------
# `origin` is a filesystem path on a clone install and a hand-set $LODESTAR_REPO on a
# remote one. Either can carry a quote or a backslash — a WSL path, a directory someone
# named oddly, a fork URL. Interpolating that into a heredoc produced invalid JSON, which
# /lodestar-update cannot read; the write succeeds and the failure surfaces much later.
ODD="$WORK/od\"d dir"
mkdir -p "$ODD"
cp -R "$ROOT/kit" "$ROOT/install.sh" "$ROOT/VERSION" "$ODD/"
mkdir -p "$WORK/ws-odd"
check "install from a path with a space and a quote" 0 "$ODD/install.sh" "$WORK/ws-odd"
expect_json "odd-path origin round-trips" "$WORK/ws-odd/.lodestar/source.json" origin "$ODD"
expect_json "odd-path kind"               "$WORK/ws-odd/.lodestar/source.json" kind local

# generated content must survive an update
mkdir -p "$WORK/ws-clone/.claude/guardrails"
echo "mine" > "$WORK/ws-clone/.claude/guardrails/custom.md"
echo "{}"   > "$WORK/ws-clone/.claude/lodestar.manifest.json"
check "update over generated content" 0 "$ROOT/install.sh" "$WORK/ws-clone"
expect_file "user rule kept"     "$WORK/ws-clone/.claude/guardrails/custom.md"
expect_file "user manifest kept" "$WORK/ws-clone/.claude/lodestar.manifest.json"

# --- 2. bootstrap mode: piped, no kit/ alongside → fetch newest tag, leave no clone --
mkdir -p "$WORK/ws-boot"
before="$(find /tmp -maxdepth 1 -name 'tmp.*' 2>/dev/null | wc -l)"
# shellcheck disable=SC2016  # $1/$2 are for the inner bash, deliberately unexpanded here
check "piped bootstrap" 0 env LODESTAR_REPO="$REMOTE" \
  bash -c 'cat "$1" | bash -s -- "$2"' _ "$ROOT/install.sh" "$WORK/ws-boot"
expect_json "bootstrap kind"  "$WORK/ws-boot/.lodestar/source.json" kind remote
expect_json "bootstrap ref"   "$WORK/ws-boot/.lodestar/source.json" ref v9.9.9
expect_json "bootstrap origin" "$WORK/ws-boot/.lodestar/source.json" origin "$REMOTE"
after="$(find /tmp -maxdepth 1 -name 'tmp.*' 2>/dev/null | wc -l)"
if [ "$before" = "$after" ]; then echo "ok: no temp dir left behind"; pass=$((pass + 1))
else echo "FAIL: temp dirs $before → $after"; fail=$((fail + 1)); fi
if [ -z "$(find "$WORK/ws-boot" -maxdepth 2 -name '.git' -print -quit)" ]; then
  echo "ok: no clone in the workspace"; pass=$((pass + 1))
else echo "FAIL: workspace contains a clone"; fail=$((fail + 1)); fi

# --- 3. --ref pins, and fetches even when a local kit/ is present --------------------
mkdir -p "$WORK/ws-pin"
check "--ref pins a tag" 0 env LODESTAR_REPO="$REMOTE" bash "$ROOT/install.sh" "$WORK/ws-pin" --ref v9.9.8
expect_json "pinned kind" "$WORK/ws-pin/.lodestar/source.json" kind remote
expect_json "pinned ref"  "$WORK/ws-pin/.lodestar/source.json" ref v9.9.8

# --- 4. refusals leave the workspace untouched --------------------------------------
mkdir -p "$WORK/ws-old"
check "pre-kit tag refused" 1 env LODESTAR_REPO="$REMOTE" bash "$ROOT/install.sh" "$WORK/ws-old" --ref v0.0.1
if [ -z "$(ls -A "$WORK/ws-old")" ]; then echo "ok: refusal wrote nothing"; pass=$((pass + 1))
else echo "FAIL: refusal left files"; fail=$((fail + 1)); fi

mkdir -p "$WORK/ws-bad"
check "missing tag refused"  1 env LODESTAR_REPO="$REMOTE" bash "$ROOT/install.sh" "$WORK/ws-bad" --ref v1.2.3
check "no target refused"    1 bash "$ROOT/install.sh"
check "bad target refused"   1 bash "$ROOT/install.sh" "$WORK/does-not-exist"
check "--ref without value"  1 bash "$ROOT/install.sh" "$WORK/ws-bad" --ref

echo
if [ "$fail" -gt 0 ]; then echo "❌ installer smoke test: $fail failed, $pass passed"; exit 1; fi
echo "✅ installer smoke test passed ($pass checks)"
