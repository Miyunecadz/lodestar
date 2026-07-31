#!/usr/bin/env bash
# Smoke-test the guardrail engine end to end against a temp rule set.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENGINE="$ROOT/kit/templates/hooks/lodestar-guardrails.py"

python3 -c "import py_compile,sys; py_compile.compile('$ENGINE', doraise=True)" && echo "engine compiles"

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

verdict() {  # reads stdin JSON hook input, prints DENY|WARN|ALLOW
  python3 "$ENGINE" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("DENY" if d.get("hookSpecificOutput",{}).get("permissionDecision")=="deny" else ("WARN" if d.get("systemMessage") else "ALLOW"))'
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
expect "Read tool allow"    ALLOW '{"tool_name":"Read","tool_input":{"file_path":"api/.env"}}'

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

echo "✅ engine smoke test passed"
