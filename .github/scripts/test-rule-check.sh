#!/usr/bin/env bash
# Smoke-test the installed-rule drift checker against a throwaway workspace.
#
# The workspace is built the way a real one is: `.lodestar/catalog/guardrails/` is the
# shipped catalog, and `.claude/guardrails/` holds rules installed from it through
# `test-catalog.py`'s `install_rule` — the same transform `/lodestar-guardrails` §5
# specifies. Reusing it rather than re-implementing the copy here matters: a private copy
# of the field list in this gate would make the gate agree with itself while the product
# drifted, which is the failure the checker exists to end.
#
# Set LODESTAR_TEST_PYTHON to run under another interpreter.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECKER="$ROOT/kit/templates/hooks/lodestar-rule-check.py"
PY="${LODESTAR_TEST_PYTHON:-python3}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

pass=0
fail=0

check() {  # check "<label>" "<want-exit>" <cmd...>
  local label="$1" want="$2"; shift 2
  local out rc
  set +e; out="$("$@" 2>&1)"; rc=$?; set -e
  if [ "$rc" != "$want" ]; then
    echo "FAIL: $label → exit $rc, want $want"; echo "${out//$'\n'/$'\n'    }"
    fail=$((fail + 1)); return
  fi
  echo "ok: $label → exit $rc"; pass=$((pass + 1))
}

says() {  # says "<label>" "<needle>" <cmd...>
  local label="$1" needle="$2"; shift 2
  local out
  set +e; out="$("$@" 2>&1)"; set -e
  case "$out" in
    *"$needle"*) echo "ok: $label"; pass=$((pass + 1)) ;;
    *) echo "FAIL: $label (no '$needle' in output)"; echo "${out//$'\n'/$'\n'    }"
       fail=$((fail + 1)) ;;
  esac
}

says_not() {  # says_not "<label>" "<needle>" <cmd...>
  local label="$1" needle="$2"; shift 2
  local out
  set +e; out="$("$@" 2>&1)"; set -e
  case "$out" in
    *"$needle"*) echo "FAIL: $label (unexpected '$needle')"; echo "${out//$'\n'/$'\n'    }"
                 fail=$((fail + 1)) ;;
    *) echo "ok: $label"; pass=$((pass + 1)) ;;
  esac
}

# --- build the workspace: real catalog, rules installed from it ----------------------
WS="$WORK/ws"
mkdir -p "$WS/.claude/guardrails" "$WS/.lodestar/catalog"
cp -R "$ROOT/kit/catalog/guardrails" "$WS/.lodestar/catalog/guardrails"

# block-commit-to-default-branch is here for its `surface: both` — the one field value with
# an alias, and so the one that a plain text comparison would misreport.
INSTALLED="block-env-files block-destructive-commands block-secret-files design-guidance-on-ui-edits block-commit-to-default-branch"
ROOT="$ROOT" WS="$WS" INSTALLED="$INSTALLED" "$PY" - <<'PYEOF'
import importlib.util, os
root, ws = os.environ["ROOT"], os.environ["WS"]
spec = importlib.util.spec_from_file_location(
    "tc", os.path.join(root, ".github", "scripts", "test-catalog.py"))
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)
rules = os.path.join(ws, ".claude", "guardrails")
for rule_id in os.environ["INSTALLED"].split():
    tc.install_rule(os.path.join(root, "kit", "catalog", "guardrails", "%s.md" % rule_id), rules)
print("installed %s rules through the picker's transform" % len(os.listdir(rules)))
PYEOF

RUN=("$PY" "$CHECKER" --workspace "$WS")

# --- 1. a workspace installed from the current catalog is in sync --------------------
check "in-sync workspace"          0 "${RUN[@]}"
check "in-sync under --check"      0 "${RUN[@]}" --check
says  "reports every rule ok"      "5 ok" "${RUN[@]}"
says  "--verbose names a rule ok"  "ok        block-env-files" "${RUN[@]}" --verbose

# --- 2. a superseded pattern is drift, and both values are shown ---------------------
# This is the real regression: block-env-files' pattern has been corrected twice since it
# first shipped, and an adopter installed before that keeps enforcing the old one.
OLD='(^|/)\.env($|\.[^/]+$)'
"$PY" - "$WS/.claude/guardrails/block-env-files.md" "$OLD" <<'PYEOF'
import re, sys
path, old = sys.argv[1], sys.argv[2]
text = open(path).read()
open(path, "w").write(re.sub(r"(?m)^pattern:.*$", "pattern: '%s'" % old, text, count=1))
PYEOF
check "drift under --check"        1 "${RUN[@]}" --check
check "drift without --check"      0 "${RUN[@]}"
says  "names the drifted rule"     "DRIFTED   block-env-files" "${RUN[@]}"
says  "names the field"            "  pattern" "${RUN[@]}"
says  "shows the installed value"  "installed  $OLD" "${RUN[@]}"
says  "shows the catalog value"    "catalog    (^|/)\\.env(?!" "${RUN[@]}"
says  "says nothing was rewritten" "Nothing was rewritten" "${RUN[@]}"
says  "points at the way to adopt" "/lodestar-guardrails" "${RUN[@]}"

# The file must be reported, never repaired — installed rules are meant to be editable.
says "drifted rule left untouched" "$OLD" cat "$WS/.claude/guardrails/block-env-files.md"

# --- 3. --rule narrows, and the untouched rules stay clean ---------------------------
check "--rule on the drifted one"  1 "${RUN[@]}" --check --rule block-env-files
check "--rule on a clean one"      0 "${RUN[@]}" --check --rule block-secret-files
check "--rule with no such rule"   1 "${RUN[@]}" --rule not-a-rule

# --- 4. --json carries the same verdict ---------------------------------------------
says "--json reports the drift" '"status": "drifted"' "${RUN[@]}" --json
says "--json counts it"         '"drifted": 1'        "${RUN[@]}" --json

"$PY" - "$WS/.claude/guardrails/block-env-files.md" "$ROOT/kit/catalog/guardrails/block-env-files.md" <<'PYEOF'
import re, sys
installed, catalog = sys.argv[1], sys.argv[2]
want = re.search(r"(?m)^pattern:.*$", open(catalog).read()).group(0)
text = open(installed).read()
open(installed, "w").write(re.sub(r"(?m)^pattern:.*$", want.replace("\\", "\\\\"), text, count=1))
PYEOF
check "restored rule is in sync"   0 "${RUN[@]}" --check

# --- 5. formatting is not drift ------------------------------------------------------
# `stacks`, `surface`, `allow_paths` and `permission_rules` are membership tests wherever
# they are read, so a reordered list is the same rule. Reporting it would train people to
# ignore the report.
"$PY" - "$WS/.claude/guardrails/block-secret-files.md" <<'PYEOF'
import re, sys
path = sys.argv[1]
text = open(path).read()
text = re.sub(r"(?m)^surface: \[agent, commit, permission\]$",
              "surface: [permission, commit, agent]", text)
open(path, "w").write(text)
PYEOF
check "reordered list is not drift" 0 "${RUN[@]}" --check
says_not "and is not reported"      "DRIFTED   block-secret-files" "${RUN[@]}"

# `both` is the pre-permission-surface spelling of `[agent, commit]`, and every hook expands
# it before use. Rewriting one to the other moves no enforcement, so it must not surface as
# drift in every workspace that adopted the rule under the older spelling.
"$PY" - "$WS/.claude/guardrails/block-commit-to-default-branch.md" <<'PYEOF'
import re, sys
path = sys.argv[1]
text = open(path).read()
open(path, "w").write(re.sub(r"(?m)^surface: both$", "surface: [agent, commit]", text))
PYEOF
says     "the alias was really rewritten" "surface: [agent, commit]" \
  cat "$WS/.claude/guardrails/block-commit-to-default-branch.md"
check    'the both alias equals its expansion' 0 "${RUN[@]}" --check
says_not "and is not reported"             "DRIFTED   block-commit-to-default-branch" "${RUN[@]}"

# A surface that really did change still is drift — the alias must not swallow everything.
"$PY" - "$WS/.claude/guardrails/block-commit-to-default-branch.md" <<'PYEOF'
import re, sys
path = sys.argv[1]
text = open(path).read()
open(path, "w").write(re.sub(r"(?m)^surface: \[agent, commit\]$", "surface: agent", text))
PYEOF
check "a real surface change is drift" 1 "${RUN[@]}" --check
says  "and names the field"            "  surface" "${RUN[@]}"
says  "showing the expanded sets"      "catalog    [agent, commit]" "${RUN[@]}"

"$PY" - "$WS/.claude/guardrails/block-commit-to-default-branch.md" <<'PYEOF'
import re, sys
path = sys.argv[1]
text = open(path).read()
open(path, "w").write(re.sub(r"(?m)^surface: agent$", "surface: both", text))
PYEOF
check "restored to the catalog spelling" 0 "${RUN[@]}" --check

# --- 6. the two halves of the body are distinguished ---------------------------------
# The redirect is what reaches the model on a block; the rationale below the `---` is read
# by humans only. A user who annotates the rationale should not be told their block message
# changed.
printf '\nLocal note added by the team.\n' >> "$WS/.claude/guardrails/block-destructive-commands.md"
says "rationale edit is reported"   "rationale    differs" "${RUN[@]}"
says_not "and not as a redirect"    "redirect     differs" "${RUN[@]}"
check "rationale edit fails --check" 1 "${RUN[@]}" --check

"$PY" - "$WS" <<'PYEOF'
import os, sys
path = os.path.join(sys.argv[1], ".claude", "guardrails", "block-destructive-commands.md")
text = open(path).read()
open(path, "w").write(text.replace("\nLocal note added by the team.\n", ""))
PYEOF
check "workspace clean again"       0 "${RUN[@]}" --check

# --- 7. a locally authored rule is not a failure -------------------------------------
cat > "$WS/.claude/guardrails/team-local.md" <<'EOF'
---
name: team-local
enabled: true
event: file
pattern: 'secret-sauce'
severity: warn
---
Ours, not the catalog's.
EOF
check "local rule does not fail"    0 "${RUN[@]}" --check
says  "local rule is named"         "local     team-local" "${RUN[@]}" --verbose
says_not "and is not called drift"  "DRIFTED   team-local" "${RUN[@]}"

# --- 8. an unreadable installed rule is silent non-enforcement, so it is reported -----
printf 'no frontmatter here at all\n' > "$WS/.claude/guardrails/broken.md"
check "unreadable rule fails --check" 1 "${RUN[@]}" --check
says  "unreadable rule is named"      "UNREADABLE broken.md" "${RUN[@]}"
rm "$WS/.claude/guardrails/broken.md" "$WS/.claude/guardrails/team-local.md"

# --- 9. a missing catalog is not "everything drifted" ---------------------------------
mv "$WS/.lodestar/catalog/guardrails" "$WS/.lodestar/catalog/guardrails-away"
check "missing catalog exits 0"   0 "${RUN[@]}" --check
says  "missing catalog says so"   "no catalog at" "${RUN[@]}"
says_not "and reports no drift"   "DRIFTED" "${RUN[@]}"
mv "$WS/.lodestar/catalog/guardrails-away" "$WS/.lodestar/catalog/guardrails"

# --- 10. a workspace with no rules at all is not an error ----------------------------
check "no workspace, no complaint" 0 "$PY" "$CHECKER" --workspace "$WORK"

# --- 11. and run it on THIS repo ------------------------------------------------------
# Lodestar dogfoods its own rules: `.claude/guardrails/` holds installed copies of catalog
# entries, and until now nothing compared the two — so the repo could ship one rule and
# enforce another on itself. The checker is exactly the tool for that, so point it here.
check "this repo's own rules are in sync" 0 \
  "$PY" "$CHECKER" --workspace "$ROOT" --catalog "$ROOT/kit/catalog/guardrails" --check

echo
if [ "$fail" -gt 0 ]; then echo "❌ rule-check test: $fail failed, $pass passed"; exit 1; fi
echo "✅ rule-check test passed ($pass checks)"
