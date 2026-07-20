#!/usr/bin/env python3
"""Lodestar guardrail engine — self-contained, no plugin dependency.

Claude Code invokes this as a PreToolUse hook (see .claude/settings.json). It reads
declarative rule files from `.claude/guardrails/*.md` and, for the tool about to run,
either DENIES it (severity: block) or surfaces an advisory message (severity: warn).

Rule file format (one rule per file, written by `/lodestar-guardrails`):

    ---
    name: block-env-files
    enabled: true
    event: file          # 'file' → matches the edited path; 'bash' → matches the command
    pattern: '(^|/)\\.env($|\\.[^/]+$)'
    severity: block      # 'block' denies the action; 'warn' advises only
    ---
    Message shown to Claude, redirecting to the right action.

Design notes:
- stdlib only; never raises out of the hook — on any error it allows the action (exit 0).
- File rules match the PATH (`file_path`), which is what Lodestar's file guardrails target.
  A rule may set `match: content` to test the edited text instead.
- Block wins over warn; all matching messages are combined.
"""

import os
import sys
import re
import json
import glob


def rules_dir() -> str:
    base = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    return os.path.join(base, ".claude", "guardrails")


def parse_frontmatter(text: str):
    """Minimal scalar YAML frontmatter parser. Returns (dict, body)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm, body = {}, parts[2].strip()
    for line in parts[1].splitlines():
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        key, _, val = line.partition(":")
        val = val.strip().strip('"').strip("'")
        low = val.lower()
        if low == "true":
            val = True
        elif low == "false":
            val = False
        fm[key.strip()] = val
    return fm, body


def load_rules(event: str):
    out = []
    for path in glob.glob(os.path.join(rules_dir(), "*.md")):
        try:
            with open(path, "r") as f:
                fm, body = parse_frontmatter(f.read())
        except (IOError, OSError, UnicodeDecodeError):
            continue
        if not fm or fm.get("enabled") is False:
            continue
        rule_event = fm.get("event", "all")
        if rule_event not in ("all", event):
            continue
        if not fm.get("pattern"):
            continue
        out.append(fm | {"_message": body})
    return out


def field_for(rule: dict, event: str, tool_input: dict) -> str:
    """The string a rule tests against."""
    if event == "bash":
        return tool_input.get("command", "")
    # file event
    if rule.get("match") == "content":
        if "edits" in tool_input:  # MultiEdit
            return " ".join(e.get("new_string", "") for e in tool_input["edits"])
        return tool_input.get("content") or tool_input.get("new_string", "")
    return tool_input.get("file_path", "")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("{}")
        return

    hook_event = data.get("hook_event_name", "PreToolUse")
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    if tool_name == "Bash":
        event = "bash"
    elif tool_name in ("Edit", "Write", "MultiEdit"):
        event = "file"
    else:
        print("{}")
        return

    blocking, warning = [], []
    for rule in load_rules(event):
        target = field_for(rule, event, tool_input)
        if not target:
            continue
        try:
            if re.search(rule["pattern"], target, re.IGNORECASE):
                severity = str(rule.get("severity") or rule.get("action") or "warn").lower()
                (blocking if severity == "block" else warning).append(rule)
        except re.error:
            continue

    if blocking:
        msg = "\n\n".join(f"**[{r.get('name','rule')}]**\n{r['_message']}" for r in blocking)
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": hook_event,
                "permissionDecision": "deny",
                "permissionDecisionReason": msg,
            },
            "systemMessage": msg,
        }))
    elif warning:
        msg = "\n\n".join(f"**[{r.get('name','rule')}]**\n{r['_message']}" for r in warning)
        print(json.dumps({"systemMessage": msg}))
    else:
        print("{}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Never let a hook error block the user's action.
        print(json.dumps({"systemMessage": f"lodestar-guardrails error: {e}"}))
    finally:
        sys.exit(0)
