#!/usr/bin/env bash
# Smoke-test the guardrail engine end to end against a temp rule set.
#
# Set LODESTAR_TEST_PYTHON to run the whole suite under another interpreter. CI uses it
# to run everything below against the declared floor (MIN_PYTHON in the engine), because
# a version-floor break does not fail loudly — it makes every rule silently inert.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENGINE="$ROOT/kit/templates/hooks/lodestar-guardrails.py"
PY="${LODESTAR_TEST_PYTHON:-python3}"

echo "interpreter under test: $("$PY" -V 2>&1)"
"$PY" -c "import py_compile,sys; py_compile.compile('$ENGINE', doraise=True)" && echo "engine compiles"

# Every shipped hook must PARSE at the floor, whatever interpreter is running this.
# This catches 3.9+ syntax on a modern box; the CI floor job catches runtime-only
# constructs like the dict-union operator, which parses everywhere but raises on 3.8.
python3 - "$ROOT" <<'PYEOF'
import ast, glob, os, re, sys
root = sys.argv[1]
engine = os.path.join(root, "kit/templates/hooks/lodestar-guardrails.py")
m = re.search(r"^MIN_PYTHON = \((\d+), (\d+)\)", open(engine).read(), re.M)
if not m:
    sys.exit("MIN_PYTHON not declared in the engine — the floor must be stated in code")
floor = (int(m.group(1)), int(m.group(2)))
bad = []
for path in sorted(glob.glob(os.path.join(root, "kit/templates/hooks/*.py"))):
    try:
        ast.parse(open(path).read(), feature_version=floor)
    except SyntaxError as e:
        bad.append("%s: %s" % (os.path.basename(path), e))
if bad:
    sys.exit("syntax above the %d.%d floor:\n  %s" % (floor[0], floor[1], "\n  ".join(bad)))
print("ok: every shipped hook parses at the %d.%d floor" % floor)
PYEOF

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
export CLAUDE_PROJECT_DIR="$WORK"
mkdir -p "$WORK/.claude/guardrails"

cat > "$WORK/.claude/guardrails/block-env-files.md" <<'EOF'
---
name: block-env-files
enabled: true
event: file
pattern: '(^|/)\.env(?!.*\.(example|sample|template|dist|defaults)$)(\.[^/]+)?$'
severity: block
---
Never edit real .env files.
EOF
cat > "$WORK/.claude/guardrails/block-rm.md" <<'EOF'
---
name: block-destructive-commands
enabled: true
event: bash
pattern: '(\brm\s+-[a-zA-Z]*[rf]|\bgit\s+reset\s+--hard)'
severity: block
match: argv
allow_paths: ['^/tmp/', '^/var/tmp/']
---
Irreversible.
EOF
cat > "$WORK/.claude/guardrails/scan.md" <<'EOF'
---
name: scan-secrets-before-commit
enabled: true
event: bash
pattern: '(^|[;&|]\s*)git(\s+-\S+)*\s+commit\b'
severity: warn
match: argv
---
Scan the staged diff.
EOF
cat > "$WORK/.claude/guardrails/migrations.md" <<'EOF'
---
name: block-edit-applied-migrations
enabled: true
event: file
pattern: 'db/migrations/.*\.sql$'
severity: block
allow_if_untracked: true
---
Applied migrations are immutable.
EOF
cat > "$WORK/.claude/guardrails/patch-package.md" <<'EOF'
---
name: mobile-use-patch-package
enabled: true
event: file
pattern: '(^|/)node_modules/'
severity: block
stacks: [react-native]
---
Use patch-package.
EOF
cat > "$WORK/.claude/guardrails/design-guidance.md" <<'EOF'
---
name: design-guidance-on-ui-edits
enabled: true
event: file
pattern: '\.(tsx|jsx|vue|svelte)$'
severity: warn
stacks: [has-frontend]
requires_manifest_missing: designGuidance.installed
surface: agent
---
No design guidance is installed for this workspace.
EOF
cat > "$WORK/.claude/guardrails/on-default-branch.md" <<'EOF'
---
name: block-commit-to-default-branch
enabled: true
event: bash
pattern: '(^|[;&|]\s*)git(\s+-\S+)*\s+(commit|push)\b'
severity: block
only_on_default_branch: true
match: argv
---
Branch first.
EOF

verdict() {  # reads stdin JSON hook input, prints DENY|WARN|ALLOW|NOTENFORCING
  # NOTENFORCING is checked first and separately from WARN on purpose: an inert rule set
  # used to be indistinguishable from a clean pass, which is the whole bug in issue #29.
  "$PY" "$ENGINE" | python3 -c '
import sys, json
d = json.load(sys.stdin)
msg = d.get("systemMessage") or ""
if "ARE NOT ENFORCING" in msg:
    print("NOTENFORCING")
elif d.get("hookSpecificOutput", {}).get("permissionDecision") == "deny":
    print("DENY")
elif msg:
    print("WARN")
else:
    print("ALLOW")'
}
expect() {  # expect "<label>" "<want>" "<json>"
  got="$(printf '%s' "$3" | verdict)"
  if [ "$got" != "$2" ]; then echo "FAIL: $1 → got $got, want $2"; exit 1; fi
  echo "ok: $1 → $got"
}

# --- baseline behaviour (unchanged by the context layer) ---
expect ".env deny"          DENY  '{"tool_name":"Edit","tool_input":{"file_path":"api/.env"}}'
expect ".env.example allow" ALLOW '{"tool_name":"Edit","tool_input":{"file_path":"api/.env.example"}}'
expect ".env.local.example allow" ALLOW '{"tool_name":"Edit","tool_input":{"file_path":"api/.env.local.example"}}'
expect ".env.staging deny"        DENY  '{"tool_name":"Edit","tool_input":{"file_path":"api/.env.staging"}}'
expect "rm -rf deny"        DENY  '{"tool_name":"Bash","tool_input":{"command":"rm -rf build"}}'
expect "git commit warn"    WARN  '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}'
expect "ls allow"           ALLOW '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'
# The engine is registered for Bash|Edit|Write|MultiEdit, so a Read never reaches it.
# That is why the secrets rules also declare `surface: permission` — the deny entries
# in settings.json are what actually stop this, not the hook.
expect "Read tool not seen by the engine" ALLOW '{"tool_name":"Read","tool_input":{"file_path":"api/.env"}}'

# --- shell-aware matching: quoted text runs nothing (issue #11, finding 4) ---
expect "rm -rf in quoted arg allow" ALLOW \
  '{"tool_name":"Bash","tool_input":{"command":"gh api -X POST /repos/o/r/issues -f body=\"then run rm -rf dist\""}}'
expect "echoed rm -rf allow"        ALLOW '{"tool_name":"Bash","tool_input":{"command":"echo \"rm -rf /\""}}'
expect "nested shell rm -rf deny"   DENY  '{"tool_name":"Bash","tool_input":{"command":"bash -c \"rm -rf /\""}}'
expect "unbalanced quote deny"      DENY  '{"tool_name":"Bash","tool_input":{"command":"rm -rf oops\""}}'
expect "commit msg mentioning commit warn" WARN \
  '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"docs: explain git commit\""}}'
expect "echoed git commit allow"    ALLOW '{"tool_name":"Bash","tool_input":{"command":"echo \"git commit -m nope\""}}'
expect "compound git commit warn"   WARN  '{"tool_name":"Bash","tool_input":{"command":"cd api && git commit -m x"}}'

# --- allow_paths: temp prefixes are exempt, anything mixed in is not ---
expect "rm -rf in /tmp allow"     ALLOW '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/scratch/x"}}'
expect "rm -rf mixed paths deny"  DENY  '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/scratch/x src"}}'
expect "rm -rf compound deny"     DENY  '{"tool_name":"Bash","tool_input":{"command":"cd /tmp && rm -rf /tmp/x"}}'

# --- allow_if_untracked: brand-new migrations are writable, committed ones are not ---
git -C "$WORK" init -q
git -C "$WORK" config user.email ci@example.com
git -C "$WORK" config user.name ci
mkdir -p "$WORK/db/migrations"
printf -- '-- migrate:up\n' > "$WORK/db/migrations/001_committed.sql"
git -C "$WORK" add db/migrations/001_committed.sql
git -C "$WORK" commit -qm "add migration"
printf -- '-- migrate:up\n' > "$WORK/db/migrations/002_new.sql"   # created, never committed
expect "tracked migration deny"   DENY  "{\"tool_name\":\"Edit\",\"cwd\":\"$WORK\",\"tool_input\":{\"file_path\":\"$WORK/db/migrations/001_committed.sql\"}}"
expect "untracked migration allow" ALLOW "{\"tool_name\":\"Edit\",\"cwd\":\"$WORK\",\"tool_input\":{\"file_path\":\"$WORK/db/migrations/002_new.sql\"}}"
expect "unborn migration allow"    ALLOW "{\"tool_name\":\"Write\",\"cwd\":\"$WORK\",\"tool_input\":{\"file_path\":\"$WORK/db/migrations/003_scaffolded.sql\"}}"

# --- only_on_default_branch: fires on trunk, silent on a feature branch ---
expect "commit on default branch deny" DENY "{\"tool_name\":\"Bash\",\"cwd\":\"$WORK\",\"tool_input\":{\"command\":\"git commit -m x\"}}"
git -C "$WORK" switch -qc feat/thing
expect "commit on feature branch warn" WARN "{\"tool_name\":\"Bash\",\"cwd\":\"$WORK\",\"tool_input\":{\"command\":\"git commit -m x\"}}"

# --- stacks scoping: a react-native rule must not fire in a non-RN repo (finding 2) ---
mkdir -p "$WORK/mobile" "$WORK/web"
cat > "$WORK/.claude/lodestar.manifest.json" <<EOF
{"repos":[{"name":"mobile","path":"$WORK/mobile","stacks":["react-native"]},
          {"name":"web","path":"$WORK/web","stacks":["react-craco"]}]}
EOF
expect "node_modules in RN repo deny"     DENY  "{\"tool_name\":\"Edit\",\"cwd\":\"$WORK\",\"tool_input\":{\"file_path\":\"$WORK/mobile/node_modules/p/index.js\"}}"
expect "node_modules in web repo allow"   ALLOW "{\"tool_name\":\"Edit\",\"cwd\":\"$WORK\",\"tool_input\":{\"file_path\":\"$WORK/web/node_modules/p/index.js\"}}"
expect "node_modules outside repos deny"  DENY  "{\"tool_name\":\"Edit\",\"cwd\":\"$WORK\",\"tool_input\":{\"file_path\":\"$WORK/tools/node_modules/p/index.js\"}}"

# --- requires_manifest_missing: a reminder that silences itself (issue #6) -----------
mkdir -p "$WORK/ui"
cat > "$WORK/.claude/lodestar.manifest.json" <<EOF
{"repos":[{"name":"ui","path":"$WORK/ui","stacks":["has-frontend"]}]}
EOF
expect "UI edit warns while guidance missing" WARN \
  "{\"tool_name\":\"Edit\",\"cwd\":\"$WORK\",\"tool_input\":{\"file_path\":\"$WORK/ui/Button.tsx\"}}"
cat > "$WORK/.claude/lodestar.manifest.json" <<EOF
{"repos":[{"name":"ui","path":"$WORK/ui","stacks":["has-frontend"]}],
 "designGuidance":{"installed":false,"status":"declined"}}
EOF
expect "still warns after a decline"          WARN \
  "{\"tool_name\":\"Edit\",\"cwd\":\"$WORK\",\"tool_input\":{\"file_path\":\"$WORK/ui/Button.tsx\"}}"
cat > "$WORK/.claude/lodestar.manifest.json" <<EOF
{"repos":[{"name":"ui","path":"$WORK/ui","stacks":["has-frontend"]}],
 "designGuidance":{"installed":true,"skill":"frontend-design"}}
EOF
expect "silent once guidance is recorded"     ALLOW \
  "{\"tool_name\":\"Edit\",\"cwd\":\"$WORK\",\"tool_input\":{\"file_path\":\"$WORK/ui/Button.tsx\"}}"
expect "non-UI file never warns"              ALLOW \
  "{\"tool_name\":\"Edit\",\"cwd\":\"$WORK\",\"tool_input\":{\"file_path\":\"$WORK/ui/server.py\"}}"
rm -f "$WORK/.claude/lodestar.manifest.json"
expect "no manifest → reminder still appears" WARN \
  "{\"tool_name\":\"Edit\",\"cwd\":\"$WORK\",\"tool_input\":{\"file_path\":\"$WORK/ui/Button.tsx\"}}"

# --- surface filtering: this engine runs the `agent` half and only that (issue #23) --
# Before the permission surface existed nothing declared a non-agent surface, so the
# engine ignored the field entirely. It now filters, or a permission-only rule would
# be enforced twice and reported twice.
rm -f "$WORK"/.claude/guardrails/*.md
surface_rule() {  # surface_rule <file> <surface-value>
  cat > "$WORK/.claude/guardrails/$1.md" <<EOF
---
name: $1
enabled: true
event: file
pattern: 'surfaced\.txt$'
severity: block
surface: $2
EOF
  printf -- '---\nblocked.\n' >> "$WORK/.claude/guardrails/$1.md"
}
probe="{\"tool_name\":\"Edit\",\"cwd\":\"$WORK\",\"tool_input\":{\"file_path\":\"$WORK/surfaced.txt\"}}"

surface_rule s-agent      "agent";                          expect "surface: agent runs here"            DENY  "$probe"
rm -f "$WORK"/.claude/guardrails/*.md
surface_rule s-both       "both";                           expect "surface: both still runs here"       DENY  "$probe"
rm -f "$WORK"/.claude/guardrails/*.md
surface_rule s-list       "[agent, commit, permission]";    expect "a list containing agent runs here"   DENY  "$probe"
rm -f "$WORK"/.claude/guardrails/*.md
surface_rule s-commit     "commit";                         expect "surface: commit is skipped here"     ALLOW "$probe"
rm -f "$WORK"/.claude/guardrails/*.md
surface_rule s-permission "permission";                     expect "surface: permission is skipped here" ALLOW "$probe"
rm -f "$WORK"/.claude/guardrails/*.md
surface_rule s-plist      "[commit, permission]";           expect "a list without agent is skipped"     ALLOW "$probe"
rm -f "$WORK"/.claude/guardrails/*.md
cat > "$WORK/.claude/guardrails/s-default.md" <<'EOF'
---
name: s-default
enabled: true
event: file
pattern: 'surfaced\.txt$'
severity: block
---
blocked.
EOF
expect "no surface field defaults to agent" DENY "$probe"

# --- the block payload stops at the rationale separator (issue #30) ---
rm -f "$WORK"/.claude/guardrails/*.md
cat > "$WORK/.claude/guardrails/split.md" <<'EOF'
---
name: split-rule
enabled: true
event: file
pattern: 'surfaced\.txt$'
severity: block
---
REDIRECT: do this instead.

---

RATIONALE: why this rule chose its surface, how the matcher works, and what it
deliberately does not cover. Written for whoever opens the file, not for the model.
EOF
emit() { printf '%s' "$probe" | "$PY" "$ENGINE"; }
reason() { emit | python3 -c 'import sys,json;print(json.load(sys.stdin).get("hookSpecificOutput",{}).get("permissionDecisionReason",""))'; }
usermsg() { emit | python3 -c 'import sys,json;print(json.load(sys.stdin).get("systemMessage",""))'; }

if reason | grep -q "REDIRECT"; then echo "ok: the redirect reaches the model"; else echo "FAIL: redirect missing"; exit 1; fi
if reason | grep -q "RATIONALE"; then echo "FAIL: rationale leaked into the block payload"; exit 1; else echo "ok: rationale stays out of the block payload"; fi
# The user still gets told what happened — the two fields have different readers, so
# dropping systemMessage entirely would leave a block with no user-facing explanation.
if usermsg | grep -q "split-rule"; then echo "ok: the user is told which rule fired"; else echo "FAIL: user message does not name the rule"; exit 1; fi
if [ "$(usermsg | wc -c)" -lt 200 ]; then echo "ok: the user message is a one-liner, not a second copy"; else echo "FAIL: user message is not compact"; exit 1; fi

# A rule with no separator sends its whole body, exactly as before the split existed.
rm -f "$WORK"/.claude/guardrails/*.md
cat > "$WORK/.claude/guardrails/unsplit.md" <<'EOF'
---
name: unsplit-rule
enabled: true
event: file
pattern: 'surfaced\.txt$'
severity: block
---
WHOLE BODY, no separator anywhere in here.
EOF
if reason | grep -q "WHOLE BODY"; then echo "ok: an unsplit rule still sends its full body"; else echo "FAIL: unsplit rule lost its body"; exit 1; fi

# --- a failed rule set must be loud, not silently empty (issue #29) ---
# The 3.8 dict-union bug made load_rules raise for *every* file. The engine caught it,
# exited 0 with no decision, and the action proceeded: fail-protective for one rule had
# become fail-open for the whole set. These assert the two halves stay distinguishable.
rm -f "$WORK"/.claude/guardrails/*.md

# A directory named like a rule file fails to open for every reader, no chmod needed.
mkdir -p "$WORK/.claude/guardrails/unreadable.md"
expect "a rule set where nothing loads reports NOT ENFORCING" NOTENFORCING "$probe"
rmdir "$WORK/.claude/guardrails/unreadable.md"

# One broken rule among several must not take the others down with it.
mkdir -p "$WORK/.claude/guardrails/unreadable.md"
cat > "$WORK/.claude/guardrails/still-good.md" <<'EOF'
---
name: still-good
enabled: true
event: file
pattern: 'surfaced\.txt$'
severity: block
---
blocked.
EOF
expect "one broken rule does not disable the rest" DENY "$probe"
rmdir "$WORK/.claude/guardrails/unreadable.md"
rm -f "$WORK"/.claude/guardrails/*.md

# An empty rules directory is a legitimate "nothing to enforce", not a failure.
expect "no rules at all is ALLOW, not NOT ENFORCING" ALLOW "$probe"

echo "✅ engine smoke test passed"
