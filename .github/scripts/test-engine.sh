#!/usr/bin/env bash
# Smoke-test the guardrail engine end to end against a temp rule set.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENGINE="$ROOT/templates/hooks/lodestar-guardrails.py"

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
pattern: '(^|/)\.env(\.(?!example)[^/]+)?$'
severity: block
---
Never edit real .env files.
EOF
cat > "$WORK/.claude/guardrails/block-rm.md" <<'EOF'
---
name: block-destructive-commands
enabled: true
event: bash
pattern: '\brm\s+-[a-zA-Z]*[rf]'
severity: block
---
Irreversible.
EOF
cat > "$WORK/.claude/guardrails/scan.md" <<'EOF'
---
name: scan-secrets-before-commit
enabled: true
event: bash
pattern: 'git commit'
severity: warn
---
Scan the staged diff.
EOF

verdict() {  # reads stdin JSON hook input, prints DENY|WARN|ALLOW
  python3 "$ENGINE" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("DENY" if d.get("hookSpecificOutput",{}).get("permissionDecision")=="deny" else ("WARN" if d.get("systemMessage") else "ALLOW"))'
}
expect() {  # expect "<label>" "<want>" "<json>"
  got="$(printf '%s' "$3" | verdict)"
  if [ "$got" != "$2" ]; then echo "FAIL: $1 → got $got, want $2"; exit 1; fi
  echo "ok: $1 → $got"
}

expect ".env deny"          DENY  '{"tool_name":"Edit","tool_input":{"file_path":"api/.env"}}'
expect ".env.example allow" ALLOW '{"tool_name":"Edit","tool_input":{"file_path":"api/.env.example"}}'
expect "rm -rf deny"        DENY  '{"tool_name":"Bash","tool_input":{"command":"rm -rf build"}}'
expect "git commit warn"    WARN  '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}'
expect "ls allow"           ALLOW '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'
expect "Read tool allow"    ALLOW '{"tool_name":"Read","tool_input":{"file_path":"api/.env"}}'
echo "✅ engine smoke test passed"
