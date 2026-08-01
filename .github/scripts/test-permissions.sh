#!/usr/bin/env bash
# Smoke-test the permission surface applier. The behaviour that matters is not "does
# it write a deny list" — it is that the write is **idempotent and reversible**:
# re-running must not duplicate, a hand-written entry must survive, and unticking a
# rule must remove exactly what that rule contributed and nothing else.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APPLY="$ROOT/kit/templates/hooks/lodestar-permissions.py"

python3 -c "import py_compile; py_compile.compile('$APPLY', doraise=True)" && echo "applier compiles"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
# Both are workspace overrides the applier honours; a value inherited from the
# environment would silently redirect every write in this test.
unset LODESTAR_WORKSPACE CLAUDE_PROJECT_DIR
WS="$WORK/ws"
mkdir -p "$WS/.claude/guardrails"

rule() {  # rule <file> <name> <surface> [permission_rules-inline-list]
  {
    echo "---"
    echo "name: $2"
    echo "enabled: true"
    echo "event: file"
    echo "pattern: 'x'"
    echo "severity: block"
    echo "surface: $3"
    [ -n "${4:-}" ] && echo "permission_rules: $4"
    echo "---"
    echo "body"
  } > "$WS/.claude/guardrails/$1.md"
}

run() { ( cd "$WS" && python3 "$APPLY" "$@" 2>&1 ); }
deny() {  # the deny array, one entry per line
  python3 - "$WS/.claude/settings.json" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
for e in d.get("permissions", {}).get("deny", []):
    print(e)
PY
}
owned() {  # entries the manifest records as ours
  python3 - "$WS/.claude/lodestar.manifest.json" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
for e in d.get("guardrailSurfaces", {}).get("permission", {}).get("entries", []):
    print(e)
PY
}

pass=0; fail=0
check() {  # check "<label>" "<got>" "<want>"
  if [ "$2" = "$3" ]; then echo "ok: $1"; pass=$((pass+1))
  else echo "FAIL: $1"; echo "     want: [$3]"; echo "     got:  [$2]"; fail=$((fail+1)); fi
}
contains() {  # contains "<label>" "<haystack>" "<needle>"
  case "$2" in *"$3"*) echo "ok: $1"; pass=$((pass+1)) ;;
  *) echo "FAIL: $1 (missing '$3' in: $2)"; fail=$((fail+1)) ;; esac
}

# ---------------------------------------------------------------- nothing to do
rule agent-only agent-only agent
check "no permission rules → empty deny" "$(deny | tr '\n' ' ')" ""
out="$(run)"
contains "reports that no rule declares the surface" "$out" "no rules declare the permission surface"

# ---------------------------------------------------------------- first apply
rule envs block-env-files "[agent, permission]" "[Read(./.env), Read(./**/.env)]"
run > /dev/null
check "entries applied" "$(deny | tr '\n' ' ')" "Read(./.env) Read(./**/.env) "
check "ownership recorded" "$(owned | tr '\n' ' ')" "Read(./.env) Read(./**/.env) "

# ---------------------------------------------------------------- idempotent
run > /dev/null; run > /dev/null
check "re-running does not duplicate" "$(deny | wc -l | tr -d ' ')" "2"

# ---------------------------------------------------------------- user entries survive
python3 - "$WS/.claude/settings.json" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d["permissions"]["deny"].insert(0, "Bash(curl *)")     # hand-written, not ours
d["hooks"] = {"PreToolUse": [{"matcher": "Bash"}]}     # unrelated key
json.dump(d, open(p, "w"), indent=2)
PY
run > /dev/null
contains "hand-written entry preserved" "$(deny | tr '\n' ' ')" "Bash(curl *)"
hooks="$(python3 -c "import json;print('PreToolUse' in json.load(open('$WS/.claude/settings.json')).get('hooks',{}))")"
check "unrelated settings keys preserved" "$hooks" "True"

# ---------------------------------------------------------------- adding a rule
rule keys block-secret-files "[agent, permission]" "[Read(./**/*.pem)]"
run > /dev/null
contains "new rule's entry added" "$(deny | tr '\n' ' ')" "Read(./**/*.pem)"
contains "earlier entries kept"    "$(deny | tr '\n' ' ')" "Read(./.env)"
contains "user entry still there"  "$(deny | tr '\n' ' ')" "Bash(curl *)"

# ---------------------------------------------------------------- reversibility
# Unticking a rule = deleting its file. Its entries must go; nothing else may.
rm "$WS/.claude/guardrails/keys.md"
run > /dev/null
got="$(deny | tr '\n' ' ')"
case "$got" in *"Read(./**/*.pem)"*) echo "FAIL: removed rule's entry lingered"; fail=$((fail+1)) ;;
  *) echo "ok: removed rule's entries dropped"; pass=$((pass+1)) ;; esac
contains "unrelated entries survive removal" "$got" "Bash(curl *)"
contains "other rule's entries survive removal" "$got" "Read(./.env)"

# A disabled rule is the same as an absent one.
rule envs block-env-files "[agent, permission]" "[Read(./.env)]"
printf -- '---\nname: block-env-files\nenabled: false\nevent: file\npattern: %s\nseverity: block\nsurface: [agent, permission]\npermission_rules: [Read(./.env)]\n---\nbody\n' "'x'" > "$WS/.claude/guardrails/envs.md"
run > /dev/null
got="$(deny | tr '\n' ' ')"
case "$got" in *"Read(./.env)"*) echo "FAIL: disabled rule still applied"; fail=$((fail+1)) ;;
  *) echo "ok: disabled rule's entries dropped"; pass=$((pass+1)) ;; esac

# ---------------------------------------------------------------- --check / --dry-run
rule envs block-env-files "[agent, permission]" "[Read(./.env), Read(./secrets/**)]"
set +e
out="$(run --check)"; rc=$?
set -e
if [ "$rc" -eq 1 ]; then echo "ok: --check exits 1 when out of sync"; pass=$((pass+1))
else echo "FAIL: --check exited $rc, wanted 1"; fail=$((fail+1)); fi
contains "--check names the missing entry" "$out" "+ Read(./secrets/**)"

before="$(deny | tr '\n' ' ')"
run --dry-run > /dev/null
check "--dry-run writes nothing" "$(deny | tr '\n' ' ')" "$before"

run > /dev/null
set +e
run --check > /dev/null; rc=$?
set -e
if [ "$rc" -eq 0 ]; then echo "ok: --check exits 0 once applied"; pass=$((pass+1))
else echo "FAIL: --check exited $rc after applying"; fail=$((fail+1)); fi

out="$(run --list)"
contains "--list attributes entries to their rule" "$out" "block-env-files	Read(./.env)"

# ---------------------------------------------------------------- never breaks
set +e
( cd "$WORK" && python3 "$APPLY" > /dev/null 2>&1 )
rc=$?
set -e
if [ "$rc" -eq 0 ]; then echo "ok: no workspace → exits 0"; pass=$((pass+1))
else echo "FAIL: no workspace exited $rc"; fail=$((fail+1)); fi

printf 'not json' > "$WS/.claude/settings.json"
set +e
run > /dev/null 2>&1; rc=$?
set -e
if [ "$rc" -eq 0 ]; then echo "ok: unparseable settings.json → exits 0"; pass=$((pass+1))
else echo "FAIL: unparseable settings exited $rc"; fail=$((fail+1)); fi

echo
if [ "$fail" -gt 0 ]; then echo "❌ permission surface test: $fail failed, $pass passed"; exit 1; fi
echo "✅ permission surface test passed ($pass checks)"
