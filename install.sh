#!/usr/bin/env bash
# Lodestar installer — copies the kit into a target workspace.
# Usage: ./install.sh /path/to/your-workspace
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
echo "Installing Lodestar from: $KIT_DIR"
echo "                     into: $TARGET"

# 1. Catalog + templates go under a hidden .lodestar/ so they don't clutter the workspace.
mkdir -p "$TARGET/.lodestar"
cp -R "$KIT_DIR/catalog"   "$TARGET/.lodestar/catalog"
cp -R "$KIT_DIR/templates" "$TARGET/.lodestar/templates"

# 2. Commands go where Claude Code looks for them.
mkdir -p "$TARGET/.claude/commands"
cp "$KIT_DIR/.claude/commands/"*.md "$TARGET/.claude/commands/"

# 3. Record the kit version installed.
if [ -f "$KIT_DIR/VERSION" ]; then
  cp "$KIT_DIR/VERSION" "$TARGET/.lodestar/VERSION"
fi

cat <<EOF

✅ Lodestar installed.

Next steps — from the workspace root ($TARGET):
  cd "$TARGET"
  claude
  > /lodestar-init                 # create the router, shared docs, repo-map
  > /onboard-repo ./<each-repo>    # absorb each repo (docs + graph + skills)
  > /guardrails                    # tick the safety + quality rules you want (enforced)
  > /gen-agents                    # tick the role agents you want (delegation)

Nothing is enforced or generated until you run those commands.
EOF
