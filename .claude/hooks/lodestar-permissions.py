#!/usr/bin/env python3
"""Lodestar permission surface — apply `permissions.deny` rules from the rule files.

A PreToolUse hook is not the strongest thing Lodestar can reach for. Claude Code's own
`permissions.deny` in `.claude/settings.json` is:

  - **broader** — it covers every tool, including `Read`, which the engine's
    `Bash|Edit|Write|MultiEdit` matcher cannot see;
  - **unconditional** — deny rules merge across settings scopes and a deny in any
    scope wins, so a local file cannot loosen a project one;
  - **fail-closed** — there is no interpreter to crash, so there is no path where the
    rule silently stops applying (the engine deliberately allows the action on an
    internal error, which is right for a hook and wrong for a secret).

So a rule that is really "never touch this path" belongs there. This script is what
puts it there: it reads the same `.claude/guardrails/*.md` files as the other two
surfaces and merges the `permission_rules` of every rule declaring `surface:
permission` into `permissions.deny`.

    .claude/guardrails/*.md   ← one rule set, three enforcement surfaces
      surface: agent       → lodestar-guardrails.py     (PreToolUse)
      surface: commit      → lodestar-precommit-check.py (pre-commit)
      surface: permission  → this script                 (settings.json)

Why a script rather than the picker editing JSON directly: this has to be **idempotent
and reversible**. Re-running must not duplicate entries, must not disturb entries the
user wrote by hand, and unticking a rule must remove exactly the entries that rule
contributed and nothing else. Ownership is recorded in the manifest under
`guardrailSurfaces.permission.entries`, so the next run knows which lines are its own.

Usage:
    lodestar-permissions.py [--workspace PATH] [--list|--check|--dry-run] [--verbose]

    --list      print the deny entries the current rule set asks for, then exit
    --check     exit 1 if settings.json does not match the rule set (CI / doctor)
    --dry-run   report what would change, write nothing

Exit status: 0 for everything except `--check` finding drift. A failure to apply is
reported and exits 0 — this runs from a picker, and a broken permission merge must not
take the rest of the install down with it.
"""

import json
import os
import sys
from datetime import datetime, timezone

MANIFEST_REL = os.path.join(".claude", "lodestar.manifest.json")
SETTINGS_REL = os.path.join(".claude", "settings.json")
RULES_REL = os.path.join(".claude", "guardrails")


# ---------------------------------------------------------------- frontmatter
# Duplicated from the other two hooks on purpose: each script has to stay a single
# self-contained file a user can copy into `.claude/hooks/` on its own.


def coerce(val):
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        return [p.strip().strip('"').strip("'") for p in inner.split(",") if p.strip()] if inner else []
    val = val.strip('"').strip("'")
    low = val.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    return val


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm = {}
    for line in parts[1].splitlines():
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = coerce(val)
    return fm, parts[2].strip()


def as_list(val):
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [p.strip().strip('"').strip("'") for p in val.strip("[]").split(",") if p.strip()]
    return []


def surfaces_of(fm):
    """The set of enforcement mechanisms a rule declares. Mirrors the engine's copy."""
    raw = fm.get("surface")
    if raw is None:
        return {"agent"}
    names = {str(s).strip().lower() for s in as_list(raw) if str(s).strip()}
    if "both" in names:
        names.discard("both")
        names |= {"agent", "commit"}
    return names or {"agent"}


# ---------------------------------------------------------------- workspace


def find_workspace(start="."):
    override = os.environ.get("LODESTAR_WORKSPACE") or os.environ.get("CLAUDE_PROJECT_DIR")
    if override and os.path.isdir(os.path.join(override, RULES_REL)):
        return override
    current = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(current, RULES_REL)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def load_json(path, default):
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else default
    except (IOError, OSError, ValueError):
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------- rules


def desired_entries(workspace):
    """[(rule_id, [entry, ...])] for every enabled rule on the permission surface.

    Order follows the sorted rule filenames so the emitted block is stable across
    runs — a settings.json that reshuffles on every invocation is a diff nobody wants
    to review.
    """
    out = []
    rules_dir = os.path.join(workspace, RULES_REL)
    try:
        names = sorted(os.listdir(rules_dir))
    except (IOError, OSError):
        return out
    for name in names:
        if not name.endswith(".md"):
            continue
        try:
            with open(os.path.join(rules_dir, name), "r") as f:
                fm, _ = parse_frontmatter(f.read())
        except (IOError, OSError, UnicodeDecodeError):
            continue
        if not fm or fm.get("enabled") is False:
            continue
        if "permission" not in surfaces_of(fm):
            continue
        entries = [e for e in as_list(fm.get("permission_rules")) if e]
        if not entries:
            continue
        out.append((str(fm.get("name") or name[:-3]), entries))
    return out


def flatten(pairs):
    """Entries in declaration order, de-duplicated, first occurrence wins."""
    seen, flat = set(), []
    for _, entries in pairs:
        for entry in entries:
            if entry not in seen:
                seen.add(entry)
                flat.append(entry)
    return flat


def merge_deny(existing, desired, previously_owned):
    """The new deny list, and what changed.

    Three-way merge against the last applied state, which is the only way to tell a
    user's hand-written entry from one of ours that a rule no longer asks for:

      - keep every existing entry that is either still desired or was never ours;
      - drop an entry only if we previously wrote it and no rule wants it now;
      - append newly desired entries at the end, preserving the user's ordering above.
    """
    desired_set, owned_set = set(desired), set(previously_owned)
    kept = [e for e in existing if e in desired_set or e not in owned_set]
    removed = [e for e in existing if e not in desired_set and e in owned_set]
    added = [e for e in desired if e not in kept]
    return kept + added, added, removed


# ---------------------------------------------------------------- main


def main(argv):
    workspace = None
    if "--workspace" in argv:
        i = argv.index("--workspace")
        workspace = argv[i + 1] if i + 1 < len(argv) else None
    workspace = workspace or find_workspace()
    if not workspace:
        print("lodestar-permissions: no .claude/guardrails here — nothing to apply.")
        return 0

    pairs = desired_entries(workspace)
    desired = flatten(pairs)

    if "--list" in argv:
        for rule_id, entries in pairs:
            for entry in entries:
                print(f"{rule_id}\t{entry}")
        return 0

    settings_path = os.path.join(workspace, SETTINGS_REL)
    manifest_path = os.path.join(workspace, MANIFEST_REL)
    settings = load_json(settings_path, {})
    manifest = load_json(manifest_path, {})

    permissions = settings.get("permissions")
    if not isinstance(permissions, dict):
        permissions = {}
    existing = [e for e in permissions.get("deny", []) if isinstance(e, str)]

    surfaces = manifest.get("guardrailSurfaces")
    surfaces = surfaces if isinstance(surfaces, dict) else {}
    record = surfaces.get("permission")
    record = record if isinstance(record, dict) else {}
    previously_owned = [e for e in record.get("entries", []) if isinstance(e, str)]

    new_deny, added, removed = merge_deny(existing, desired, previously_owned)
    changed = new_deny != existing

    if "--check" in argv:
        if changed:
            print("lodestar-permissions: settings.json is out of sync with the rule set.")
            for entry in added:
                print(f"  + {entry}")
            for entry in removed:
                print(f"  - {entry}")
            print("Run lodestar-permissions.py to apply.")
            return 1
        print(f"lodestar-permissions: in sync ({len(desired)} deny entr"
              f"{'y' if len(desired) == 1 else 'ies'} from {len(pairs)} rule(s)).")
        return 0

    if "--dry-run" in argv:
        print(f"lodestar-permissions: would write {len(new_deny)} deny entries "
              f"({len(added)} added, {len(removed)} removed) to {settings_path}")
        for entry in added:
            print(f"  + {entry}")
        for entry in removed:
            print(f"  - {entry}")
        return 0

    try:
        if changed:
            permissions["deny"] = new_deny
            settings["permissions"] = permissions
            write_json(settings_path, settings)
        surfaces["permission"] = {
            "rules": [rule_id for rule_id, _ in pairs],
            "entries": desired,
            "appliedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        manifest["guardrailSurfaces"] = surfaces
        write_json(manifest_path, manifest)
    except (IOError, OSError, ValueError) as exc:
        # A picker runs this. Failing here must not take the rest of the install down.
        print(f"lodestar-permissions: could not apply ({exc}) — settings left unchanged.")
        return 0

    if not pairs:
        print("lodestar-permissions: no rules declare the permission surface.")
    else:
        print(f"lodestar-permissions: {len(desired)} deny entr"
              f"{'y' if len(desired) == 1 else 'ies'} from {len(pairs)} rule(s) "
              f"({len(added)} added, {len(removed)} removed).")
    if "--verbose" in argv:
        for rule_id, entries in pairs:
            print(f"  {rule_id}")
            for entry in entries:
                print(f"    {entry}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:  # never break an install over a bug in here
        print(f"lodestar-permissions: skipped ({exc})")
        sys.exit(0)
