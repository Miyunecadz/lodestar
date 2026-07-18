#!/usr/bin/env bash
# Apply (or update) the "protect-main" branch ruleset that enforces trunk-based development:
#   - a pull request is required before merging (blocks direct pushes to the default branch)
#   - the `ci` status check must pass
#   - force-pushes and branch deletion are blocked
#
# Requires: gh (authenticated, with admin on the repo). Usage:
#   .github/rulesets/apply.sh [owner/repo]
set -euo pipefail
REPO="${1:-Miyunecadz/lodestar}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install it (https://cli.github.com), run 'gh auth login', then re-run."
  echo "Or apply via the UI: Settings → Rules → Rulesets → New → import $DIR/protect-main.json"
  exit 1
fi

# Update the existing ruleset if one with this name exists; otherwise create it.
ID="$(gh api "repos/$REPO/rulesets" --jq '.[] | select(.name=="protect-main") | .id' 2>/dev/null || true)"
if [ -n "${ID:-}" ]; then
  echo "Updating existing ruleset (id $ID) on $REPO…"
  gh api --method PUT "repos/$REPO/rulesets/$ID" --input "$DIR/protect-main.json"
else
  echo "Creating ruleset 'protect-main' on $REPO…"
  gh api --method POST "repos/$REPO/rulesets" --input "$DIR/protect-main.json"
fi
echo "✅ Ruleset applied. main now requires a PR + passing 'ci' check; force-push/deletion blocked."
