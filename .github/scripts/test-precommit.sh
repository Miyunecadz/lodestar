#!/usr/bin/env bash
# Smoke-test the commit-surface guardrail checker against a real git repo with staged
# changes. Exit 1 means "commit blocked"; everything else must exit 0.
#
# Set LODESTAR_TEST_PYTHON to run the suite under another interpreter — CI uses it to
# cover the floor declared as MIN_PYTHON in the checker.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECK="$ROOT/kit/templates/hooks/lodestar-precommit-check.py"
PY="${LODESTAR_TEST_PYTHON:-python3}"

echo "interpreter under test: $("$PY" -V 2>&1)"
"$PY" -c "import py_compile; py_compile.compile('$CHECK', doraise=True)" && echo "checker compiles"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
WS="$WORK/workspace"
mkdir -p "$WS/.claude/guardrails"
git init -q "$WS"
git -C "$WS" config user.email ci@example.com
git -C "$WS" config user.name ci
git -C "$WS" symbolic-ref HEAD refs/heads/main

# Rules, exactly as /lodestar-guardrails would install them (surface fields included).
w() { cat > "$WS/.claude/guardrails/$1"; }
w env.md <<'EOF'
---
name: block-env-files
enabled: true
event: file
pattern: '(^|/)\.env(\.(?!example)[^/]+)?$'
severity: block
surface: both
---
Real .env files hold live credentials. Use .env.example instead.
EOF
w keys.md <<'EOF'
---
name: block-secret-files
enabled: true
event: file
pattern: '(\.pem$|\.key$|(^|/)id_rsa$)'
severity: block
surface: both
---
Private keys must never be committed.
EOF
w migrations.md <<'EOF'
---
name: block-edit-applied-migrations
enabled: true
event: file
pattern: 'db/migrations/.*\.sql$'
severity: block
surface: both
allow_if_untracked: true
---
Applied migrations are immutable — add a new one.
EOF
w secrets.md <<'EOF'
---
name: scan-secrets-before-commit
enabled: true
event: bash
pattern: 'git commit'
severity: warn
surface: both
commit_check: secret-scan
commit_severity: block
---
Scan the staged diff for credentials before committing.
EOF
w lockfiles.md <<'EOF'
---
name: no-hand-edit-lockfiles
enabled: true
event: file
pattern: '(^|/)yarn\.lock$'
severity: block
surface: agent
---
Agent-only: lockfiles are committed by tooling all the time.
EOF
w mobile.md <<'EOF'
---
name: mobile-use-patch-package
enabled: true
event: file
pattern: '(^|/)vendored/'
severity: block
surface: both
stacks: [react-native]
---
Stack-scoped: only applies to react-native repos.
EOF
# `surface` may be a list now. This checker takes the `commit` member and ignores the
# rest; `both` above is the legacy spelling of [agent, commit] and must keep working.
w listed-surface.md <<'EOF'
---
name: listed-surface-rule
enabled: true
event: file
pattern: '(^|/)listed-surface\.txt$'
severity: block
surface: [agent, commit, permission]
---
A rule naming several surfaces is still enforced at commit time.
EOF
w permission-only.md <<'EOF'
---
name: permission-only-rule
enabled: true
event: file
pattern: '(^|/)permission-only\.txt$'
severity: block
surface: [permission]
permission_rules: [Read(./permission-only.txt)]
---
Enforced by permissions.deny, not by this hook.
EOF

pass=0; fail=0
run_check() { (cd "${2:-$WS}" && LODESTAR_WORKSPACE="$WS" "$PY" "$CHECK" 2>&1); }
expect() {  # expect "<label>" "<want-exit>" [<cwd>]
  local label="$1" want="$2" cwd="${3:-$WS}" out rc
  set +e; out="$(run_check _ "$cwd")"; rc=$?; set -e
  if [ "$rc" != "$want" ]; then
    echo "FAIL: $label → exit $rc, want $want"; echo "$out" | head -12 | sed 's/^/    /'; fail=$((fail+1)); return
  fi
  echo "ok: $label → exit $rc"; pass=$((pass+1))
}
contains() {  # contains "<label>" "<needle>"
  local out
  set +e; out="$(run_check)"; set -e
  if printf '%s' "$out" | grep -qF "$2"; then echo "ok: $1"; pass=$((pass+1))
  else echo "FAIL: $1 (no '$2' in output)"; echo "$out" | head -12 | sed 's/^/    /'; fail=$((fail+1)); fi
}
unstage() { git -C "$WS" reset -q; }

# --- clean tree: nothing staged, nothing to say --------------------------------------
expect "empty index allows" 0

# --- secrets in a path ---------------------------------------------------------------
printf 'API_KEY=live\n' > "$WS/.env"
git -C "$WS" add -f .env
expect "staged .env blocks" 1
contains "message redirects" ".env.example"
unstage
printf 'API_KEY=\n' > "$WS/.env.example"; git -C "$WS" add .env.example
expect "staged .env.example allows" 0
unstage

mkdir -p "$WS/certs"; printf -- '-----BEGIN PRIVATE KEY-----\n' > "$WS/certs/server.key"
git -C "$WS" add certs/server.key
expect "staged private key blocks" 1
unstage

# --- agent-only rules must NOT fire at commit time -----------------------------------
printf 'lockfile\n' > "$WS/yarn.lock"; git -C "$WS" add yarn.lock
expect "agent-only rule ignored" 0
unstage

# --- migrations: add is fine, modify is not (allow_if_untracked ↔ A vs M) -------------
mkdir -p "$WS/db/migrations"
printf -- '-- migrate:up\n' > "$WS/db/migrations/001_init.sql"
git -C "$WS" add db/migrations/001_init.sql
expect "new migration allows (status A)" 0
git -C "$WS" -c commit.gpgsign=false commit -qm "init migration" --no-verify
printf -- '-- migrate:up\n-- edited\n' > "$WS/db/migrations/001_init.sql"
git -C "$WS" add db/migrations/001_init.sql
expect "modified migration blocks (status M)" 1
unstage
git -C "$WS" checkout -q -- db/migrations/001_init.sql

# --- secret scanning of staged content ----------------------------------------------
printf 'aws = "AKIAIOSFODNN7EXAMPLE"\n' > "$WS/config.py"
git -C "$WS" add config.py
if command -v gitleaks >/dev/null 2>&1; then
  expect "staged AWS key blocks (gitleaks)" 1
else
  # No scanner → built-ins warn instead of blocking, on purpose.
  expect "staged AWS key warns (no gitleaks)" 0
  contains "warn names the finding" "AWS access key id"
  contains "warn explains downgrade" "gitleaks"
fi
unstage
git -C "$WS" rm -q --cached config.py 2>/dev/null || true

# --- stack scoping is honored at commit time ----------------------------------------
mkdir -p "$WS/web/vendored" "$WS/mobile/vendored"
cat > "$WS/.claude/lodestar.manifest.json" <<EOF
{"repos":[{"name":"web","path":"web","stacks":["react-craco"]},
          {"name":"mobile","path":"mobile","stacks":["react-native"]}]}
EOF
printf 'x\n' > "$WS/web/vendored/a.js"; git -C "$WS" add web/vendored/a.js
expect "out-of-stack path allows" 0
unstage
printf 'x\n' > "$WS/mobile/vendored/a.js"; git -C "$WS" add mobile/vendored/a.js
expect "in-stack path blocks" 1
unstage

# --- --list reports the commit-surface rule set -------------------------------------
set +e; listed="$(cd "$WS" && LODESTAR_WORKSPACE="$WS" "$PY" "$CHECK" --list)"; set -e
for want in block-env-files block-secret-files block-edit-applied-migrations scan-secrets-before-commit; do
  if printf '%s' "$listed" | grep -q "$want"; then echo "ok: --list has $want"; pass=$((pass+1))
  else echo "FAIL: --list missing $want"; fail=$((fail+1)); fi
done
if printf '%s' "$listed" | grep -q "no-hand-edit-lockfiles"; then
  echo "FAIL: --list leaked an agent-only rule"; fail=$((fail+1))
else echo "ok: --list excludes agent-only rules"; pass=$((pass+1)); fi
if printf '%s' "$listed" | grep -q "listed-surface-rule"; then
  echo "ok: --list includes a rule whose surface list contains commit"; pass=$((pass+1))
else echo "FAIL: --list dropped a list-valued commit surface"; fail=$((fail+1)); fi
if printf '%s' "$listed" | grep -q "permission-only-rule"; then
  echo "FAIL: --list leaked a permission-only rule"; fail=$((fail+1))
else echo "ok: --list excludes permission-only rules"; pass=$((pass+1)); fi

# --- degrade, never break a commit --------------------------------------------------
printf 'API_KEY=live\n' > "$WS/.env"; git -C "$WS" add -f .env   # a real violation is staged
printf -- '---\nname: broken\nenabled: true\nevent: file\npattern: "([unclosed"\nseverity: block\nsurface: both\n---\nbroken\n' \
  > "$WS/.claude/guardrails/broken.md"
expect "invalid regex does not crash" 1     # still blocks on .env, ignores the broken rule
rm "$WS/.claude/guardrails/broken.md"
unstage

printf 'x\n' > "$WS/ok.txt"; git -C "$WS" add ok.txt
mv "$WS/.claude/guardrails" "$WORK/rules-away"
expect "no rules dir allows" 0
mv "$WORK/rules-away" "$WS/.claude/guardrails"

# outside any workspace → silent no-op
mkdir -p "$WORK/elsewhere"; git init -q "$WORK/elsewhere"
set +e; out="$(cd "$WORK/elsewhere" && env -u LODESTAR_WORKSPACE -u CLAUDE_PROJECT_DIR "$PY" "$CHECK"; echo "rc=$?")"; set -e
if [ "$out" = "rc=0" ]; then echo "ok: no workspace → silent exit 0"; pass=$((pass+1))
else echo "FAIL: no workspace → '$out'"; fail=$((fail+1)); fi

# --- default-branch check ------------------------------------------------------------
w trunk.md <<'EOF'
---
name: block-commit-to-default-branch
enabled: true
event: bash
pattern: 'git commit'
severity: block
surface: both
commit_check: default-branch
---
Create a feature branch first: git switch -c feat/<name>.
EOF
expect "commit on default branch blocks" 1
git -C "$WS" switch -qc feat/thing
expect "commit on feature branch allows" 0

echo
if [ "$fail" -gt 0 ]; then echo "❌ commit-surface test: $fail failed, $pass passed"; exit 1; fi
echo "✅ commit-surface test passed ($pass checks)"
