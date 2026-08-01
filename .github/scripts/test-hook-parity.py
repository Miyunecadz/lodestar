#!/usr/bin/env python3
"""Assert the frontmatter helpers duplicated across the three hooks stay in agreement.

The duplication is deliberate — see `.claude/skills/hook-engine-invariants`: each hook
must work when copied into `.claude/hooks/` alone, so there is no shared module to
import. That property is worth keeping, but it has a cost, and issue #28 is what the
cost looks like: the same rule file parsed by two hooks, scoped differently by each,
so a rule enforced on one surface silently was not on the other.

A shared module would trade one invariant for another. This gate keeps both: the files
stay independent, and divergence stops being silent. It compares **behaviour**, not
source — the implementations differ in style for good reasons (the engine caches context
in an object across one invocation; the commit hook is a one-shot process), and an
AST or text diff would drown real drift in noise.

What is NOT compared here: `stacks_for` and `default_branch`. Those legitimately differ
in shape between the two hooks and are covered by their own suites.

Exit 1 on any disagreement. Run from anywhere; paths are resolved from this file.
"""

import importlib.util
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOOKS = os.path.join(ROOT, "kit", "templates", "hooks")
FILES = [
    "lodestar-guardrails.py",
    "lodestar-precommit-check.py",
    "lodestar-permissions.py",
]

# Inputs chosen for the edges where a hand-rolled parser drifts: empty and whitespace
# lists, quoting styles, the legacy `both` spelling, a value containing a colon, a
# comment line, a missing closing fence, CRLF.
FRONTMATTER_CASES = [
    "---\nname: a\nenabled: true\n---\nbody",
    "---\nname: a\nsurface: both\n---\nbody",
    "---\nname: a\nsurface: [agent, commit, permission]\n---\nbody",
    "---\nname: a\nsurface: [ agent ,  commit ]\n---\nbody",
    "---\nname: a\nstacks: []\n---\nbody",
    "---\nname: a\nstacks: [  ]\n---\nbody",
    '---\nname: a\npattern: "(^|/)\\.env$"\n---\nbody',
    "---\nname: a\npattern: '(^|/)id_rsa$'\n---\nbody",
    "---\nname: a\nmessage: see http://x/y for why\n---\nbody",
    "---\n# a comment\nname: a\n---\nbody",
    "---\nname: a\nenabled: false\n---\nbody",
    "---\nname: a\nenabled: FALSE\n---\nbody",
    "---\nname: a\n---\n",
    "---\nname: a\nno_colon_here\n---\nbody",
    "no frontmatter at all",
    "---\nunterminated: yes\n",
    "",
    "---\r\nname: a\r\nenabled: true\r\n---\r\nbody",
]

COERCE_CASES = [
    "true", "false", "TRUE", "False", " true ", "yes", "1", "",
    "[]", "[ ]", "[a]", "[a, b]", "[ 'a' , \"b\" ]", "['a','b']",
    '"quoted"', "'quoted'", "plain", "  spaced  ", "a: b", "[unclosed",
]

AS_LIST_CASES = [
    None, [], ["a"], ["a", "b"], "a", "a, b", "[a, b]", "[]", "", "  ",
    True, False, 0, 1, {"k": "v"},
]

SURFACES_CASES = [
    {}, {"surface": "agent"}, {"surface": "commit"}, {"surface": "permission"},
    {"surface": "both"}, {"surface": ["agent"]}, {"surface": ["both", "permission"]},
    {"surface": ["agent", "commit", "permission"]}, {"surface": []},
    {"surface": ""}, {"surface": "  "}, {"surface": "AGENT"}, {"surface": None},
]


def load(filename):
    path = os.path.join(HOOKS, filename)
    spec = importlib.util.spec_from_file_location(filename.replace(".py", "").replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def norm(value):
    """Comparable, order-insensitive for sets (surfaces_of returns one)."""
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, tuple):
        return [norm(v) for v in value]
    return value


def call(module, name, arg):
    fn = getattr(module, name, None)
    if fn is None:
        return "<missing>"
    try:
        return norm(fn(arg))
    except Exception as exc:  # a helper that raises where another does not IS drift
        return "<raised %s: %s>" % (type(exc).__name__, exc)


def main():
    modules = [(f, load(f)) for f in FILES]
    checks = [
        ("parse_frontmatter", FRONTMATTER_CASES),
        ("coerce", COERCE_CASES),
        ("as_list", AS_LIST_CASES),
        ("surfaces_of", SURFACES_CASES),
    ]

    failures, compared = [], 0
    for name, cases in checks:
        present = [(f, m) for f, m in modules if hasattr(m, name)]
        if len(present) < 2:
            continue
        for case in cases:
            results = [(f, call(m, name, case)) for f, m in present]
            compared += 1
            first_file, first = results[0]
            for other_file, other in results[1:]:
                if json.dumps(first, default=str, sort_keys=True) != \
                   json.dumps(other, default=str, sort_keys=True):
                    failures.append(
                        "%s(%r)\n    %s → %r\n    %s → %r"
                        % (name, case, first_file, first, other_file, other)
                    )
        print("ok: %s agrees across %d hooks (%d cases)" % (name, len(present), len(cases)))

    if failures:
        print("\n❌ hook parity: %d disagreement(s) across %d comparisons\n" % (len(failures), compared))
        for f in failures:
            print("  " + f)
        print(
            "\nThe frontmatter helpers are duplicated on purpose (each hook must work when\n"
            "copied alone). Fix the divergence in place — do not extract a shared module."
        )
        return 1

    print("\n✅ hook parity: %d comparisons agree" % compared)
    return 0


if __name__ == "__main__":
    sys.exit(main())
