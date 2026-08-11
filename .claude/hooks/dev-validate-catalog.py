#!/usr/bin/env python3
"""Dev-only PostToolUse hook: run the catalog validator right after a catalog edit.

Adding a catalog entry has four obligations (entry frontmatter, the id listed in
CATALOG.md, the totals line, docs/EXTENDING.md for a new flag) and CI is the only thing
that checks them. That feedback arrives at push time, long after the edit. This runs
`.github/scripts/validate.py` the moment a relevant file is written, so a missing
frontmatter key or a stale totals line surfaces while the change is still in hand.

Not part of the kit — `install.sh` only copies from `kit/`. Silent on success.

Same invariants as the shipped hooks: stdlib only, never raises, always exits 0.
"""
import json
import os
import subprocess
import sys

TIMEOUT = 30  # validate.py is pure stdlib over ~100 files; this is generous

# Any of these being touched can invalidate the catalog contract. Mirror what
# validate.py actually reads — watching a path it never opens spends a subprocess to
# re-prove an untouched result, and missing one it does read defeats the point.
WATCHED = (
    os.path.join("kit", "catalog"),
    os.path.join(".github", "fixtures"),
    "changelog.d",
    "VERSION",
    "CHANGELOG.md",
)


def relevant(path: str, project_dir: str) -> bool:
    if not path:
        return False
    try:
        rel = os.path.relpath(os.path.abspath(path), project_dir)
    except ValueError:
        return False
    if rel.startswith(".."):
        return False  # outside the repo
    return any(rel == w or rel.startswith(w + os.sep) for w in WATCHED)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("{}")
        return

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or "."
    project_dir = os.path.abspath(project_dir)
    tool_input = data.get("tool_input", {}) or {}

    if not relevant(tool_input.get("file_path", ""), project_dir):
        print("{}")
        return

    validator = os.path.join(project_dir, ".github", "scripts", "validate.py")
    if not os.path.isfile(validator):
        print("{}")
        return

    try:
        proc = subprocess.run(
            [sys.executable, validator],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        print("{}")  # cannot run it — say nothing rather than cry wolf
        return

    if proc.returncode == 0:
        print("{}")
        return

    out = proc.stdout.decode("utf-8", "replace").strip()
    print(json.dumps({
        "systemMessage": (
            "validate.py fails after this edit — fix it now, not at push time:\n\n"
            + out
            + "\n\nReminder: a catalog entry needs its frontmatter, a backticked id in "
              "kit/catalog/CATALOG.md, an updated `Totals: **N entries**` line, and a "
              "docs/EXTENDING.md note for any new flag or surface."
        )
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"systemMessage": f"dev-validate-catalog error: {e}"}))
    finally:
        sys.exit(0)
