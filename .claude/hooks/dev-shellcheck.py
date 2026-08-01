#!/usr/bin/env python3
"""Dev-only PostToolUse hook: shellcheck a shell file right after it is written.

Gate 1 of CI is `shellcheck --severity=error` over install.sh and the test scripts. This
runs the same check on the single file just edited, so a quoting bug is caught at the
edit rather than in CI.

Not part of the kit — `install.sh` only copies from `kit/`. Silent on success, and
silent when shellcheck is not installed (it is a CI tool, not a hard local dependency).

Same invariants as the shipped hooks: stdlib only, never raises, always exits 0.
"""
import json
import os
import shutil
import subprocess
import sys

TIMEOUT = 20


def is_shell(path: str) -> bool:
    if not path:
        return False
    base = os.path.basename(path)
    return base.endswith(".sh") or base == "install.sh"


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("{}")
        return

    path = (data.get("tool_input", {}) or {}).get("file_path", "")
    if not is_shell(path) or not os.path.isfile(path):
        print("{}")
        return

    if not shutil.which("shellcheck"):
        print("{}")  # not installed locally; CI still gates it
        return

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or "."
    try:
        proc = subprocess.run(
            ["shellcheck", "--severity=error", path],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        print("{}")
        return

    if proc.returncode == 0:
        print("{}")
        return

    out = proc.stdout.decode("utf-8", "replace").strip()
    print(json.dumps({
        "systemMessage": (
            f"shellcheck --severity=error fails on {os.path.basename(path)} "
            f"(CI gate 1 will reject this):\n\n" + out
        )
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"systemMessage": f"dev-shellcheck error: {e}"}))
    finally:
        sys.exit(0)
