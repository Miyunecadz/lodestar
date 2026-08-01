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

A bare pattern only sees a string, but several rules encode intent that depends on
state a regex cannot see — is this migration already committed, which repo is this
file in, am I on the default branch, is that `rm -rf` inside a quoted argument. So a
rule may opt into a small **context layer** the engine computes lazily, at most once
per invocation:

    stacks: [react-native]        # skip unless the target repo's detected stacks match
    allow_if_untracked: true      # file rules: skip for a file git does not track yet
    surface: [agent, permission]  # which mechanisms enforce this rule (see below)
    only_on_default_branch: true  # bash rules: fire only when HEAD is the default branch
    match: argv                   # bash rules: match shell words, not the raw string
    allow_paths: ['^/tmp/']       # bash rules: skip when every operand is under an allowed prefix
    ignore_case: false            # opt out of the default case-insensitive match
    requires_manifest_missing: k  # fire only while manifest key `k` is absent/false — a
                                  # reminder that silences itself once the gap is closed

A rule also declares which mechanisms enforce it. This engine only ever runs the
`agent` half; the others are listed so one rule file describes the whole picture:

    agent       this PreToolUse hook — Claude's Bash/Edit/Write/MultiEdit calls
    commit      lodestar-precommit-check.py — any committer, via pre-commit
    permission  settings.json `permissions.deny` — Claude Code core, all tools
                including Read, applied by lodestar-permissions.py

`surface` accepts a scalar or an inline list; the legacy scalar `both` still means
`[agent, commit]`. **A rule that does not include `agent` is skipped here** — before
the permission surface existed nothing declared a non-agent surface, so this engine
ignored the field entirely and ran every rule it found.

Design notes:
- Python 3.8+, stdlib only. See MIN_PYTHON below — an interpreter under the floor is
  reported loudly rather than silently allowing everything.
- Never raises out of the hook — on any error it allows the action (exit 0).
- Every context probe is best-effort and fails **protective**: when the engine cannot
  determine something (no git, no manifest, unparseable command), it behaves as it did
  before the context layer rather than silently dropping a rule.
- Failing protective is scoped to *one rule*. A failure that takes out the **whole rule
  set** is a different animal — it turns fail-protective into fail-open for everything —
  so it is reported as NOT ENFORCING rather than as a one-line error. See RuleSetError.
- File rules match the PATH (`file_path`), which is what Lodestar's file guardrails target.
  A rule may set `match: content` to test the edited text instead.
- Block wins over warn; all matching messages are combined.
"""

import os
import sys
import re
import json
import glob
import shlex
import subprocess

GIT_TIMEOUT = 2  # seconds; a hook must never hang a tool call

# The oldest interpreter this hook is tested against. 3.8 is what Ubuntu 20.04 LTS and
# RHEL 8 ship as `python3`, and CI runs the engine suite against it. Raising this floor
# means raising it in README.md, docs/EXTENDING.md and the CI matrix too.
MIN_PYTHON = (3, 8)


class RuleSetError(Exception):
    """The rule set as a whole could not be loaded.

    Distinct from a single rule failing: one bad rule file is skipped and the rest still
    enforce, but if nothing loads then *no* guardrail is enforcing and the user must be
    told in terms they cannot miss in a busy session.
    """


def not_enforcing(detail: str) -> str:
    """The one message that must never look like a routine warning."""
    return (
        "⛔ LODESTAR GUARDRAILS ARE NOT ENFORCING — "
        + detail
        + ".\nEvery rule in `.claude/guardrails/` is inert for this action, including "
        "`block` rules. Treat this workspace as having no guardrails until it is fixed."
    )


def rules_dir() -> str:
    base = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    return os.path.join(base, ".claude", "guardrails")


def coerce(val: str):
    """Scalar or inline-list frontmatter value → Python value."""
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [p.strip().strip('"').strip("'") for p in inner.split(",") if p.strip()]
    val = val.strip('"').strip("'")
    low = val.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    return val


def redirect_of(body):
    """The part of a rule body that goes to the model when the rule fires.

    A rule file is written for two readers. The model needs the redirect — what to do
    instead — and nothing else. A human opening the file wants the design rationale:
    why this surface, how the matching works, what the rule deliberately does not cover.
    A bare `---` line separates them; everything above it is the redirect.

    Both halves stay in the file, so the rationale is still there for whoever reads it.
    A rule with no separator sends its whole body, which is what every rule did before
    this existed — an older or hand-written rule file keeps working unchanged.
    """
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "---":
            return "\n".join(lines[:i]).strip()
    return body.strip()


def parse_frontmatter(text: str):
    """Minimal YAML frontmatter parser — scalars and inline lists. Returns (dict, body)."""
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
        fm[key.strip()] = coerce(val)
    return fm, body


def as_list(val):
    """Frontmatter value → list, tolerating a scalar or a stringified list."""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [p.strip().strip('"').strip("'") for p in val.strip("[]").split(",") if p.strip()]
    return []


def surfaces_of(fm: dict):
    """The set of enforcement mechanisms a rule declares.

    Scalar or list, defaulting to `agent`. `both` is the pre-permission-surface
    spelling of `[agent, commit]` and stays valid so existing installed rule files
    keep working across an update.
    """
    raw = fm.get("surface")
    if raw is None:
        return {"agent"}
    names = {str(s).strip().lower() for s in as_list(raw) if str(s).strip()}
    if "both" in names:
        names.discard("both")
        names |= {"agent", "commit"}
    return names or {"agent"}


def shell_words(command: str):
    """Split a command into words, keeping quoted and unquoted text apart.

    Returns a list of (plain, quoted, full) per word — `plain` is the text that was
    written unquoted, `quoted` the concatenated string literals, `full` both together —
    or None when quoting is unbalanced.

    Rolled by hand rather than via shlex because quoting matters *within* a word:
    `-f body="rm -rf x"` is one word whose payload is inert text, and shlex's
    whitespace_split mode cannot report that distinction.
    """
    words, plain, quoted, seen = [], [], [], False
    quote = ""
    i, n = 0, len(command)
    while i < n:
        ch = command[i]
        if quote:
            if ch == quote:
                quote = ""
            elif ch == "\\" and quote == '"' and i + 1 < n:
                quoted.append(command[i + 1])
                i += 1
            else:
                quoted.append(ch)
        elif ch in "\"'":
            quote, seen = ch, True
        elif ch == "\\" and i + 1 < n:
            plain.append(command[i + 1])
            i += 1
        elif ch.isspace():
            if plain or quoted or seen:
                words.append(("".join(plain), "".join(quoted), "".join(plain) + "".join(quoted)))
                plain, quoted, seen = [], [], False
        else:
            plain.append(ch)
        i += 1
    if quote:
        return None  # unbalanced quote — refuse to guess
    if plain or quoted or seen:
        words.append(("".join(plain), "".join(quoted), "".join(plain) + "".join(quoted)))
    return words


# Flags that introduce a nested shell payload: the quoted string after them IS a command.
NESTED_SHELL_FLAGS = ("-c", "-lc", "-ic", "--command")


def command_targets(command: str):
    """The strings an `match: argv` bash rule should be tested against.

    The raw command string matches text that runs nothing — a `rm -rf` inside a quoted
    JSON argument or an echoed message. Matching the *unquoted* words instead drops those
    false positives, while nested shell payloads (`bash -c "…"`) are kept as their own
    target so wrapping a destructive command in quotes is not a bypass.
    """
    words = shell_words(command)
    if words is None:
        return [command]  # unparseable → fall back to the raw string, stay protective
    targets = [" ".join(plain for plain, _, _ in words if plain)]
    prev = ""
    for plain, quoted, _ in words:
        if quoted and (prev in NESTED_SHELL_FLAGS or prev.endswith("eval")):
            targets.append(quoted)
        if plain:
            prev = plain
    return [t for t in targets if t]


def command_operands(command: str):
    """Non-flag operands of a simple command (the paths it would act on).

    Returns None for a compound command (`&&`, `;`, `|`, backgrounding) — operand
    analysis is only sound for a single command, so callers must stay protective.
    """
    if re.search(r"(\|\||&&|[;|&]|\$\(|`)", command):
        return None
    words = shell_words(command)
    if words is None:
        return None
    return [full for _, _, full in words[1:] if full and not full.startswith("-")]


class Context:
    """Per-invocation, lazily computed repo/git/shell context. Never raises."""

    def __init__(self, tool_input: dict, cwd: str):
        self.tool_input = tool_input
        self.project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or cwd or "."
        self.cwd = cwd or self.project_dir
        self._cache = {}

    # ---- helpers ----

    def abspath(self, path: str) -> str:
        if not path:
            return self.cwd
        return path if os.path.isabs(path) else os.path.normpath(os.path.join(self.cwd, path))

    def _nearest_dir(self, path: str) -> str:
        """The closest existing directory at or above `path` (a brand-new file has none)."""
        d = self.abspath(path)
        if not os.path.isdir(d):
            d = os.path.dirname(d)
        while d and not os.path.isdir(d):
            parent = os.path.dirname(d)
            if parent == d:
                return self.cwd
            d = parent
        return d or self.cwd

    def _git(self, args, cwd: str):
        """Run a git command. Returns stdout on success, None on any failure."""
        key = ("git", tuple(args), cwd)
        if key not in self._cache:
            out = None
            try:
                proc = subprocess.run(
                    ["git"] + list(args),
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    timeout=GIT_TIMEOUT,
                )
                if proc.returncode == 0:
                    out = proc.stdout.decode("utf-8", "replace").strip()
            except (OSError, subprocess.SubprocessError, ValueError):
                out = None
            self._cache[key] = out
        return self._cache[key]

    # ---- git context ----

    def in_git_repo(self, cwd: str) -> bool:
        return self._git(["rev-parse", "--git-dir"], cwd) is not None

    def is_tracked(self, path: str) -> bool:
        """Does git track this file? Unknown (no git, no repo) → True, staying protective."""
        cwd = self._nearest_dir(path)
        if not self.in_git_repo(cwd):
            return True
        return self._git(["ls-files", "--error-unmatch", "--", self.abspath(path)], cwd) is not None

    @property
    def branch(self):
        """Current branch name, or None when detached / not a repo."""
        return self._git(["symbolic-ref", "--short", "HEAD"], self.cwd)

    @property
    def default_branch(self):
        """The repo's default branch, or None when it cannot be determined."""
        head = self._git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], self.cwd)
        if head and "/" in head:
            return head.split("/", 1)[1]
        configured = self._git(["config", "--get", "init.defaultBranch"], self.cwd)
        if configured:
            return configured
        for candidate in ("main", "master"):
            if self._git(["rev-parse", "--verify", "--quiet", "refs/heads/" + candidate], self.cwd):
                return candidate
        return None

    @property
    def on_default_branch(self) -> bool:
        """True only when we positively know HEAD is the default branch."""
        branch, default = self.branch, self.default_branch
        return bool(branch and default and branch == default)

    # ---- stack context ----

    @property
    def manifest(self) -> dict:
        if "manifest" not in self._cache:
            data = {}
            path = os.path.join(self.project_dir, ".claude", "lodestar.manifest.json")
            try:
                with open(path, "r") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
            except (IOError, OSError, ValueError):
                data = {}
            self._cache["manifest"] = data
        return self._cache["manifest"]

    def manifest_missing(self, dotted: str) -> bool:
        """Is this dotted manifest path absent, false, or empty?

        Lets a rule be a *self-silencing* reminder: it fires while some setup is missing
        and goes quiet once the manifest records it, instead of nagging forever (which
        trains people to ignore it) or being silent from the start (which is the gap).
        Note the direction of failure: no manifest at all means "missing", so the
        reminder appears rather than being suppressed by its own absence.
        """
        node = self.manifest
        for part in str(dotted).split("."):
            if not isinstance(node, dict) or part not in node:
                return True
            node = node[part]
        if isinstance(node, (list, dict, str)):
            return len(node) == 0
        return not bool(node)

    def stacks_for(self, path: str):
        """Detected stacks of the repo containing `path`, or None when unknown.

        None means "no manifest, or the path is outside every onboarded repo" — the
        caller must not skip a rule on that basis.
        """
        repos = self.manifest.get("repos")
        if not isinstance(repos, list) or not repos:
            return None
        target = self.abspath(path)
        best, best_len = None, -1
        for repo in repos:
            if not isinstance(repo, dict):
                continue
            repo_path = repo.get("path")
            if not isinstance(repo_path, str) or not repo_path:
                continue
            root = self.abspath(repo_path)
            if target == root or target.startswith(root.rstrip(os.sep) + os.sep):
                if len(root) > best_len:
                    best, best_len = repo, len(root)
        if best is None:
            return None
        stacks = [s for s in as_list(best.get("stacks")) if s]
        return stacks or None


def load_rules(event: str):
    """Rules applying to `event`.

    One unreadable or malformed rule file is skipped so the rest keep enforcing. But if
    rule files exist and *every one* of them fails, that is not "no rules to apply" — it
    is a systematic failure (an interpreter under MIN_PYTHON, an unreadable directory, a
    regression in the parser) wearing the same costume. Raise instead, so main() can say
    so out loud rather than returning an empty list that reads as "all clear".
    """
    out, seen, failed = [], 0, 0
    try:
        paths = glob.glob(os.path.join(rules_dir(), "*.md"))
    except Exception as e:
        raise RuleSetError("cannot read %s (%s)" % (rules_dir(), e))
    for path in paths:
        seen += 1
        try:
            with open(path, "r") as f:
                fm, body = parse_frontmatter(f.read())
            if not fm or fm.get("enabled") is False:
                continue
            if "agent" not in surfaces_of(fm):
                continue  # enforced elsewhere (commit hook, permissions.deny) — not here
            rule_event = fm.get("event", "all")
            if rule_event not in ("all", event):
                continue
            if not fm.get("pattern"):
                continue
            out.append(dict(fm, _message=redirect_of(body)))
        except Exception:
            failed += 1  # a broken rule must never take the rest of the set down
            continue
    if seen and failed == seen:
        raise RuleSetError("all %d rule file(s) in %s failed to load" % (seen, rules_dir()))
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


def scope_for(event: str, tool_input: dict) -> str:
    """The path a rule's context questions are asked about."""
    if event == "bash":
        return ""  # → the invocation cwd
    return tool_input.get("file_path", "")


def stack_allows(rule: dict, ctx: Context, scope: str) -> bool:
    """Is this rule in scope for the repo the action targets?"""
    stacks = as_list(rule.get("stacks"))
    if not stacks or "all" in stacks:
        return True
    repo_stacks = ctx.stacks_for(scope)
    if repo_stacks is None:
        return True  # unknown repo → do not silently drop the rule
    return any(s in repo_stacks for s in stacks)


def suppressed(rule: dict, ctx: Context, event: str, tool_input: dict) -> bool:
    """Does the context say this match should not fire after all?"""
    needs_missing = rule.get("requires_manifest_missing")
    if needs_missing and not ctx.manifest_missing(needs_missing):
        return True  # the thing this rule reminds about is recorded — stay quiet

    if event == "file":
        if rule.get("allow_if_untracked") is True:
            path = tool_input.get("file_path", "")
            if path and not ctx.is_tracked(path):
                return True
        return False

    # bash
    if rule.get("only_on_default_branch") is True and not ctx.on_default_branch:
        return True
    allow_paths = as_list(rule.get("allow_paths"))
    if allow_paths:
        operands = command_operands(tool_input.get("command", ""))
        # Only an *absolute* operand can be checked against an allow prefix. A relative
        # path would have to be resolved against cwd, which would exempt every relative
        # delete whenever the workspace itself sits under an allowed prefix.
        if operands and all(os.path.isabs(os.path.expanduser(o)) for o in operands):
            resolved = [os.path.expanduser(o) for o in operands]
            try:
                if all(any(re.search(a, r) for a in allow_paths) for r in resolved):
                    return True
            except re.error:
                return False
    return False


def matches(rule: dict, event: str, target: str, command: str) -> bool:
    flags = 0 if rule.get("ignore_case") is False else re.IGNORECASE
    haystacks = [target]
    if event == "bash" and rule.get("match") == "argv":
        haystacks = command_targets(command)
    try:
        return any(re.search(rule["pattern"], h, flags) for h in haystacks)
    except re.error:
        return False


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

    ctx = Context(tool_input, data.get("cwd", ""))
    scope = scope_for(event, tool_input)
    command = tool_input.get("command", "") if event == "bash" else ""

    try:
        rules = load_rules(event)
    except RuleSetError as e:
        print(json.dumps({"systemMessage": not_enforcing(str(e))}))
        return

    blocking, warning = [], []
    for rule in rules:
        target = field_for(rule, event, tool_input)
        if not target:
            continue
        if not stack_allows(rule, ctx, scope):
            continue
        if not matches(rule, event, target, command):
            continue
        if suppressed(rule, ctx, event, tool_input):
            continue
        severity = str(rule.get("severity") or rule.get("action") or "warn").lower()
        (blocking if severity == "block" else warning).append(rule)

    if blocking:
        # The two fields have different readers, so they carry different payloads.
        # `permissionDecisionReason` goes to the model — it gets the full redirect,
        # because that is what it must act on, and it is where the token cost lands.
        # `systemMessage` goes to the *user*, who needs to know what stopped them and
        # not a wall of instructions addressed to someone else. Sending the same body
        # to both was the duplication; sending only one would leave the user with an
        # unexplained block.
        msg = "\n\n".join(f"**[{r.get('name','rule')}]**\n{r['_message']}" for r in blocking)
        names = ", ".join(str(r.get("name", "rule")) for r in blocking)
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": hook_event,
                "permissionDecision": "deny",
                "permissionDecisionReason": msg,
            },
            "systemMessage": "Lodestar blocked this action — %s. See Claude's redirect above." % names,
        }))
    elif warning:
        msg = "\n\n".join(f"**[{r.get('name','rule')}]**\n{r['_message']}" for r in warning)
        print(json.dumps({"systemMessage": msg}))
    else:
        print("{}")


if __name__ == "__main__":
    try:
        if sys.version_info < MIN_PYTHON:
            # Checked before anything else runs: on an interpreter under the floor the
            # engine may raise somewhere arbitrary, and the message it produced then was
            # a bare TypeError easily mistaken for a one-off glitch.
            raise RuleSetError(
                "this hook needs Python %d.%d+ but `python3` is %s"
                % (MIN_PYTHON[0], MIN_PYTHON[1], "%d.%d.%d" % sys.version_info[:3])
            )
        main()
    except RuleSetError as e:
        print(json.dumps({"systemMessage": not_enforcing(str(e))}))
    except Exception as e:
        # Never let a hook error block the user's action — but say plainly that the
        # action went unchecked, since exiting without a decision allows it.
        print(json.dumps({"systemMessage": not_enforcing(
            "lodestar-guardrails crashed before it could check this action (%s)" % e
        )}))
    finally:
        sys.exit(0)
