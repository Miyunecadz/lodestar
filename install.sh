#!/usr/bin/env bash
# Lodestar installer / updater — copies the kit into a target workspace.
#
# Usage:
#   ./install.sh /path/to/your-workspace              # from a clone (contributors, offline)
#   curl -fsSL <raw-url>/install.sh | bash -s -- /path/to/your-workspace
#                                                     # bootstrap: no clone left behind
#   ./install.sh /path/to/workspace --ref v0.6.0      # pin the kit to a released tag
#
# Two ways to run it, one behaviour:
#   - Next to a `kit/` directory (a clone), it copies from there. Nothing is downloaded,
#     so this is also the offline / air-gapped path.
#   - Piped from curl with no `kit/` alongside it, it fetches the kit into a temp dir
#     (shallow clone of a release tag), installs, and removes the temp dir. No clone is
#     left behind and none is needed later — updates re-fetch from the recorded remote.
#
# Re-running is SAFE: it refreshes only the kit (catalog, templates, commands, the
# guardrail engine, VERSION) and NEVER touches anything you generated — your manifest,
# .claude/guardrails/*, .claude/agents/*, .claude/settings.json, CLAUDE.md, or docs/.
# Inside a workspace you can also just run /lodestar-update, which does this for you.
set -euo pipefail

REPO_URL="${LODESTAR_REPO:-https://github.com/Miyunecadz/lodestar.git}"
REF="${LODESTAR_REF:-}"
# Where this script itself lives — empty when piped from curl, since a script read from
# stdin has no location. Never fall back to cwd: that would silently pick up whatever
# `kit/` happened to be in the current directory.
SELF="${BASH_SOURCE[0]:-}"
if [ -n "$SELF" ] && [ -f "$SELF" ]; then
  KIT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
else
  KIT_DIR=""
fi
TARGET=""

while [ $# -gt 0 ]; do
  case "$1" in
    --ref)
      REF="${2:-}"
      if [ -z "$REF" ]; then echo "--ref needs a value (e.g. --ref v0.6.0)"; exit 1; fi
      shift 2
      ;;
    --ref=*) REF="${1#--ref=}"; shift ;;
    -h|--help) sed -n '2,20p' "$0" 2>/dev/null || echo "Usage: $0 <path-to-workspace> [--ref vX.Y.Z]"; exit 0 ;;
    *)
      if [ -z "$TARGET" ]; then TARGET="$1"; else echo "Unexpected argument: $1"; exit 1; fi
      shift
      ;;
  esac
done

if [ -z "$TARGET" ]; then
  echo "Usage: $0 <path-to-workspace> [--ref vX.Y.Z]"
  echo "  The workspace is the folder that CONTAINS your repositories."
  exit 1
fi
if [ ! -d "$TARGET" ]; then
  echo "Target '$TARGET' does not exist. Create it (or pass an existing folder) and retry."
  exit 1
fi
TARGET="$(cd "$TARGET" && pwd)"

# --- Where does the kit come from? ---------------------------------------------------
# A clone has `kit/` next to this script. Piped from curl it does not, so fetch one into
# a temp dir that is removed on exit — the workspace never ends up owning a clone.
SOURCE_KIND="local"
SOURCE_ORIGIN="$KIT_DIR"
TMP_DIR=""
# Must return 0: a failing last command in an EXIT trap becomes the script's exit status.
cleanup() {
  if [ -n "$TMP_DIR" ]; then rm -rf "$TMP_DIR"; fi
  return 0
}
trap cleanup EXIT

# An explicit --ref means "install that release", so fetch it even from a clone —
# otherwise we would install whatever the clone has checked out while recording the
# tag the user asked for.
if [ -n "$REF" ] || [ -z "$KIT_DIR" ] || [ ! -d "$KIT_DIR/kit" ]; then
  if ! command -v git >/dev/null 2>&1; then
    echo "This bootstrap needs git to fetch the kit. Install git, or clone the repo and run"
    echo "its install.sh directly (that path needs no network):"
    echo "  git clone $REPO_URL ~/tools/lodestar && ~/tools/lodestar/install.sh \"$TARGET\""
    exit 1
  fi
  if [ -z "$REF" ]; then
    # Newest release tag, resolved without cloning. Update is a deliberate move between
    # releases, so never install the tip of main by default.
    REF="$(git ls-remote --tags --refs "$REPO_URL" 2>/dev/null \
            | awk -F/ '{print $NF}' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' \
            | sort -V | tail -1)"
  fi
  if [ -z "$REF" ]; then
    echo "Could not resolve a release tag from $REPO_URL (no network, or no tags yet)."
    echo "Pass one explicitly: --ref v0.6.0"
    exit 1
  fi
  TMP_DIR="$(mktemp -d)"
  echo "Fetching Lodestar $REF …"
  if ! git clone --quiet --depth 1 --branch "$REF" "$REPO_URL" "$TMP_DIR/lodestar"; then
    echo "Failed to fetch $REF from $REPO_URL."
    exit 1
  fi
  if [ ! -d "$TMP_DIR/lodestar/kit" ]; then
    # v0.5.0 moved the kit source under kit/. Earlier tags ship their own installer that
    # understands their own layout, so send the user there instead of failing on a copy.
    echo "$REF predates the kit/ layout (introduced in v0.5.0) and cannot be installed by this script."
    echo "To install that version, clone the tag and run its own installer:"
    echo "  git clone --branch $REF $REPO_URL /tmp/lodestar-$REF"
    echo "  /tmp/lodestar-$REF/install.sh \"$TARGET\""
    exit 1
  fi
  KIT_DIR="$TMP_DIR/lodestar"
  SOURCE_KIND="remote"
  SOURCE_ORIGIN="$REPO_URL"
fi

MODE="install"
[ -d "$TARGET/.lodestar" ] && MODE="update"
echo "Lodestar $MODE"
echo "  from: $SOURCE_ORIGIN${REF:+ ($REF)}"
echo "  into: $TARGET"

# 1. Kit files (catalog + templates) — safe to overwrite wholesale. Remove first so a
#    re-run replaces rather than nesting (cp -R into an existing dir would nest).
mkdir -p "$TARGET/.lodestar"
rm -rf "$TARGET/.lodestar/catalog" "$TARGET/.lodestar/templates"
cp -R "$KIT_DIR/kit/catalog"   "$TARGET/.lodestar/catalog"
cp -R "$KIT_DIR/kit/templates" "$TARGET/.lodestar/templates"

# 2. Commands — overwrite the lodestar-* set. Clean up any pre-rename command files.
mkdir -p "$TARGET/.claude/commands"
rm -f "$TARGET/.claude/commands/onboard-repo.md" \
      "$TARGET/.claude/commands/guardrails.md" \
      "$TARGET/.claude/commands/gen-agents.md"
cp "$KIT_DIR/kit/commands/"lodestar-*.md "$TARGET/.claude/commands/"

# 3. Engine/hook scripts — refresh each ONLY if it was already installed (so an update
#    ships fixes without opting a workspace into a feature it never enabled). On a fresh
#    workspace, /lodestar-guardrails and /lodestar-freshness install these later.
if [ -f "$TARGET/.claude/hooks/lodestar-guardrails.py" ]; then
  cp "$KIT_DIR/kit/templates/hooks/lodestar-guardrails.py" "$TARGET/.claude/hooks/lodestar-guardrails.py"
  echo "  refreshed the guardrail engine (.claude/hooks/lodestar-guardrails.py)"
fi
for hook in lodestar-graph-refresh.sh lodestar-freshness-check.py lodestar-precommit-check.py; do
  if [ -f "$TARGET/.claude/hooks/$hook" ]; then
    cp "$KIT_DIR/kit/templates/hooks/$hook" "$TARGET/.claude/hooks/$hook"
    case "$hook" in *.sh) chmod +x "$TARGET/.claude/hooks/$hook" ;; esac
    echo "  refreshed hook (.claude/hooks/$hook)"
  fi
done

# 4. Record where to update FROM and what is installed. For a remote install this is a
#    URL + tag, which is all `/lodestar-update` needs — deliberately not a clone. For a
#    clone install it stays the local path, so contributors and offline users keep
#    today's behaviour.
VERSION="unknown"
if [ -f "$KIT_DIR/VERSION" ]; then
  cp "$KIT_DIR/VERSION" "$TARGET/.lodestar/VERSION"
  VERSION="$(tr -d '[:space:]' < "$KIT_DIR/VERSION")"
fi
printf '%s\n' "$SOURCE_ORIGIN" > "$TARGET/.lodestar/SOURCE"
cat > "$TARGET/.lodestar/source.json" <<JSON
{
  "kind": "$SOURCE_KIND",
  "origin": "$SOURCE_ORIGIN",
  "ref": "${REF:-}",
  "version": "$VERSION"
}
JSON

if [ "$MODE" = "install" ]; then
  cat <<EOF

✅ Lodestar $VERSION installed.

Next steps — from the workspace root ($TARGET):
  cd "$TARGET"
  claude
  > /lodestar-init                  # create the router, shared docs, repo-map
  > /lodestar-onboard ./<each-repo> # absorb each repo (docs + graph + skills)
  > /lodestar-guardrails            # tick the safety + quality rules you want (enforced)
  > /lodestar-agents                # tick the role agents you want (delegation)

Nothing is enforced or generated until you run those commands.
To update later: run /lodestar-update from the workspace.
EOF
  if [ "$SOURCE_KIND" = "remote" ]; then
    echo "No clone was left behind — updates re-fetch $REPO_URL at the tag you pick."
  fi
else
  cat <<EOF

✅ Lodestar kit updated (your generated rules, agents, docs, and manifest were left untouched).
Version now: $VERSION.
New catalog entries won't apply until you re-run /lodestar-guardrails and /lodestar-agents
and tick them.
EOF
fi
