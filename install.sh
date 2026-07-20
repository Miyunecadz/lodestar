#!/usr/bin/env bash
# Lodestar installer / updater — copies the kit into a target workspace.
#
# Usage:
#   ./install.sh /path/to/your-workspace        # first install, or re-run to update
#
# Re-running is SAFE: it refreshes only the kit (catalog, templates, commands, the
# guardrail engine, VERSION) and NEVER touches anything you generated — your manifest,
# .claude/guardrails/*, .claude/agents/*, .claude/settings.json, CLAUDE.md, or docs/.
# Inside a workspace you can also just run /lodestar-update, which pulls the latest
# source and re-runs this script for you.
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-}"

if [ -z "$TARGET" ]; then
  echo "Usage: $0 <path-to-workspace>"
  echo "  The workspace is the folder that CONTAINS your repositories."
  exit 1
fi
if [ ! -d "$TARGET" ]; then
  echo "Target '$TARGET' does not exist. Create it (or pass an existing folder) and retry."
  exit 1
fi
TARGET="$(cd "$TARGET" && pwd)"

MODE="install"
[ -d "$TARGET/.lodestar" ] && MODE="update"
echo "Lodestar $MODE"
echo "  from: $KIT_DIR"
echo "  into: $TARGET"

# 1. Kit files (catalog + templates) — safe to overwrite wholesale. Remove first so a
#    re-run replaces rather than nesting (cp -R into an existing dir would nest).
mkdir -p "$TARGET/.lodestar"
rm -rf "$TARGET/.lodestar/catalog" "$TARGET/.lodestar/templates"
cp -R "$KIT_DIR/catalog"   "$TARGET/.lodestar/catalog"
cp -R "$KIT_DIR/templates" "$TARGET/.lodestar/templates"

# 2. Commands — overwrite the lodestar-* set. Clean up any pre-rename command files.
mkdir -p "$TARGET/.claude/commands"
rm -f "$TARGET/.claude/commands/onboard-repo.md" \
      "$TARGET/.claude/commands/guardrails.md" \
      "$TARGET/.claude/commands/gen-agents.md"
cp "$KIT_DIR/.claude/commands/"lodestar-*.md "$TARGET/.claude/commands/"

# 3. Engine/hook scripts — refresh each ONLY if it was already installed (so an update
#    ships fixes without opting a workspace into a feature it never enabled). On a fresh
#    workspace, /lodestar-guardrails and /lodestar-freshness install these later.
if [ -f "$TARGET/.claude/hooks/lodestar-guardrails.py" ]; then
  cp "$KIT_DIR/templates/hooks/lodestar-guardrails.py" "$TARGET/.claude/hooks/lodestar-guardrails.py"
  echo "  refreshed the guardrail engine (.claude/hooks/lodestar-guardrails.py)"
fi
for hook in lodestar-graph-refresh.sh lodestar-freshness-check.py; do
  if [ -f "$TARGET/.claude/hooks/$hook" ]; then
    cp "$KIT_DIR/templates/hooks/$hook" "$TARGET/.claude/hooks/$hook"
    case "$hook" in *.sh) chmod +x "$TARGET/.claude/hooks/$hook" ;; esac
    echo "  refreshed the freshness hook (.claude/hooks/$hook)"
  fi
done

# 4. Record version + source path (so /lodestar-update knows where to pull from).
[ -f "$KIT_DIR/VERSION" ] && cp "$KIT_DIR/VERSION" "$TARGET/.lodestar/VERSION"
printf '%s\n' "$KIT_DIR" > "$TARGET/.lodestar/SOURCE"

if [ "$MODE" = "install" ]; then
  cat <<EOF

✅ Lodestar installed.

Next steps — from the workspace root ($TARGET):
  cd "$TARGET"
  claude
  > /lodestar-init                  # create the router, shared docs, repo-map
  > /lodestar-onboard ./<each-repo> # absorb each repo (docs + graph + skills)
  > /lodestar-guardrails            # tick the safety + quality rules you want (enforced)
  > /lodestar-agents                # tick the role agents you want (delegation)

Nothing is enforced or generated until you run those commands.
To update later: run /lodestar-update from the workspace (or re-run this script).
EOF
else
  cat <<EOF

✅ Lodestar kit updated (your generated rules, agents, docs, and manifest were left untouched).
Version now: $(cat "$TARGET/.lodestar/VERSION" 2>/dev/null || echo "unknown").
New catalog entries won't apply until you re-run /lodestar-guardrails and /lodestar-agents
and tick them.
EOF
fi
