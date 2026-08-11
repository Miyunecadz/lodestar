#!/usr/bin/env python3
"""Lodestar rule drift check — is an installed guardrail still what the catalog says?

`/lodestar-guardrails` copies a catalog entry into `.claude/guardrails/<id>.md` once. From
then on the two are unconnected: `install.sh` refreshes `.lodestar/catalog/` wholesale on
every update and never touches what you generated, which is the right default and also
means a **corrected rule never reaches the file that enforces it**. `block-env-files`'
pattern has been fixed twice since it first shipped; a workspace that adopted it before
those fixes is still enforcing the old regex, and nothing says so.

This is what says so. It compares each installed rule against its catalog source and
reports the fields that differ:

    lodestar-rule-check.py                       # report, exit 0
    lodestar-rule-check.py --check               # exit 1 if anything drifted (CI / doctor)
    lodestar-rule-check.py --json                # machine-readable
    lodestar-rule-check.py --rule block-env-files
    lodestar-rule-check.py --workspace PATH --catalog PATH

**It reports; it never rewrites.** A difference is not automatically a defect — installed
rules are meant to be edited (`block-env-files` tells you to add your own env tiers to
`permission_rules` right in its body). Without provenance nothing here can tell your edit
from a stale copy, so it names the difference and leaves the judgement to you. Adopting the
catalog version is `/lodestar-guardrails`, re-ticking the rule.

What is compared is exactly what the picker copies — see COMPARED. Catalog-only keys
(`id`, `title`, `category`, `recommended`, `emits`) are picker inputs that never reach an
installed rule, and `name` / `enabled` are written fresh rather than copied, so none of them
is a difference. `.github/scripts/validate.py` gates COMPARED against the fields the hooks
actually read, so this list cannot quietly fall behind the engine.

Requires Python 3.8+ (see MIN_PYTHON), stdlib only, and stays a single self-contained file
like the other hooks — see `.claude/skills/hook-engine-invariants`.
"""

import json
import os
import sys

MIN_PYTHON = (3, 8)

RULES_REL = os.path.join(".claude", "guardrails")
CATALOG_REL = os.path.join(".lodestar", "catalog", "guardrails")

# Exactly the fields `/lodestar-guardrails` §5 copies from a catalog entry into an installed
# rule. Anything the engine, the commit checker, or the permission applier reads has to be
# here — a field the picker copies but this list omits is drift nothing would report, which
# is the failure this script exists to end. `validate.py` keeps the list honest.
COMPARED = [
    "event", "pattern", "severity", "stacks", "allow_if_untracked",
    "only_on_default_branch", "match", "allow_paths", "ignore_case", "surface",
    "permission_rules", "commit_check", "commit_severity", "requires_manifest_missing",
]

# Fields whose value is a membership test wherever it is read — `stacks` via `any(s in …)`,
# `allow_paths` via `any(re.search(…))`, `permission_rules` merged into a de-duplicated deny
# list. Order carries no meaning in any of them, so comparing them order-sensitively would
# report a reshuffle as a behaviour change. `surface` belongs here too but is handled apart:
# it has an alias, and sorting alone would miss it (see `normalise`).
UNORDERED = {"stacks", "allow_paths", "permission_rules"}


# ---------------------------------------------------------------- frontmatter
# Duplicated from the other hooks on purpose: each script has to stay a single
# self-contained file a user can copy into `.claude/hooks/` on its own.
# `.github/scripts/test-hook-parity.py` is what keeps the copies in agreement.


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


def redirect_of(body):
    """The part of a rule body shown when the rule fires. Mirrors the engine's copy."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "---":
            return "\n".join(lines[:i]).strip()
    return body.strip()


def rationale_of(body):
    """Everything below the first bare `---` — the half a human reads, not the model."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "---":
            return "\n".join(lines[i + 1:]).strip()
    return ""


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


def read_rule(path):
    """(frontmatter, body) for a rule file, or None if it cannot be read or parsed.

    None is not "empty": an installed rule the parser cannot read is one the *engine*
    cannot read either, so it is silently enforcing nothing. That is the same failure class
    as a stale copy, so it is reported rather than skipped.
    """
    try:
        with open(path, "r") as f:
            fm, body = parse_frontmatter(f.read())
    except (IOError, OSError, UnicodeDecodeError):
        return None
    if not fm:
        return None
    return fm, body


def normalise(field, value):
    """A field's value as the hooks would use it, so formatting is not reported as drift.

    `surface` goes through `surfaces_of` rather than a plain sort, because it has an alias:
    `both` is the pre-permission-surface spelling of `[agent, commit]` and every hook expands
    it before use. Comparing the raw text would report a rule rewritten from one spelling to
    the other as drift, when the set of enforcing mechanisms did not move — and five shipped
    entries still say `both`. A rule with no `surface` at all defaults to `agent`, on both
    sides, for the same reason.
    """
    if field == "surface":
        return sorted(surfaces_of({"surface": value}))
    if value is None:
        return None
    if field in UNORDERED:
        return sorted(str(v) for v in as_list(value))
    if isinstance(value, list):
        return [str(v) for v in value]
    return value


def show(value):
    if value is None:
        return "(absent)"
    if isinstance(value, list):
        return "[%s]" % ", ".join(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


# ---------------------------------------------------------------- comparison


def compare(installed, catalog):
    """One installed rule against its catalog source → the differences, as dicts."""
    inst_fm, inst_body = installed
    cat_fm, cat_body = catalog
    fields = []
    for field in COMPARED:
        got = normalise(field, inst_fm.get(field))
        want = normalise(field, cat_fm.get(field))
        if got != want:
            fields.append({"field": field, "installed": show(got), "catalog": show(want)})
    return {
        "fields": fields,
        "redirect_differs": redirect_of(inst_body) != redirect_of(cat_body),
        "rationale_differs": rationale_of(inst_body) != rationale_of(cat_body),
    }


def collect(rules_dir, catalog_dir, only=None):
    """Every installed rule's status. Sorted by filename, so output is stable."""
    try:
        names = sorted(n for n in os.listdir(rules_dir) if n.endswith(".md"))
    except (IOError, OSError):
        return None
    results = []
    for name in names:
        installed = read_rule(os.path.join(rules_dir, name))
        rule_id = name[:-3]
        if installed is not None:
            rule_id = str(installed[0].get("name") or rule_id)
        if only and rule_id != only:
            continue
        if installed is None:
            results.append({"rule": rule_id, "file": name, "status": "unreadable"})
            continue
        source = os.path.join(catalog_dir, "%s.md" % rule_id)
        catalog = read_rule(source) if os.path.isfile(source) else None
        if catalog is None:
            # Not a failure: a rule can be authored locally, and docs/EXTENDING.md says so.
            results.append({"rule": rule_id, "file": name, "status": "local"})
            continue
        diff = compare(installed, catalog)
        drifted = bool(diff["fields"]) or diff["redirect_differs"] or diff["rationale_differs"]
        results.append(dict(diff, rule=rule_id, file=name,
                            status="drifted" if drifted else "ok"))
    return results


# ---------------------------------------------------------------- output


ADVICE = (
    "A difference is not automatically a defect: installed rules are meant to be edited, and\n"
    "nothing here can tell your edit from a stale copy. Nothing was rewritten. To take the\n"
    "catalog's version, re-run /lodestar-guardrails and re-tick the rule."
)


def render(results, rules_dir, catalog_dir, verbose=False):
    lines = ["installed %s" % rules_dir, "catalog   %s" % catalog_dir, ""]
    for r in results:
        if r["status"] == "ok":
            if verbose:
                lines.append("ok        %s" % r["rule"])
            continue
        if r["status"] == "local":
            if verbose:
                lines.append("local     %s — no catalog entry of that name; not compared"
                             % r["rule"])
            continue
        if r["status"] == "unreadable":
            lines.append("UNREADABLE %s — no frontmatter this parser can read, so the engine"
                         " is not enforcing it either" % r["file"])
            lines.append("")
            continue
        lines.append("DRIFTED   %s" % r["rule"])
        for f in r["fields"]:
            lines.append("  %s" % f["field"])
            lines.append("    installed  %s" % f["installed"])
            lines.append("    catalog    %s" % f["catalog"])
        if r["redirect_differs"]:
            lines.append("  redirect     differs — this is the text sent to the model on a block")
        if r["rationale_differs"]:
            lines.append("  rationale    differs — the half below the `---`, read by humans only")
        lines.append("")

    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    summary = ", ".join("%d %s" % (counts[s], s) for s in
                        ("drifted", "unreadable", "local", "ok") if counts.get(s))
    lines.append("%d installed rule(s): %s" % (len(results), summary or "none"))
    if counts.get("drifted"):
        lines.append("")
        lines.append(ADVICE)
    return "\n".join(lines)


# ---------------------------------------------------------------- main


def option(argv, name):
    if name in argv:
        i = argv.index(name)
        return argv[i + 1] if i + 1 < len(argv) else None
    return None


def main(argv):
    workspace = option(argv, "--workspace") or find_workspace()
    if not workspace:
        print("lodestar-rule-check: no .claude/guardrails here — nothing to compare.")
        return 0

    rules_dir = os.path.join(workspace, RULES_REL)
    catalog_dir = option(argv, "--catalog") or os.path.join(workspace, CATALOG_REL)
    if not os.path.isdir(catalog_dir):
        # Fail loudly rather than reporting every rule as locally authored: "no catalog"
        # and "every rule diverges from the catalog" would otherwise look identical.
        print("lodestar-rule-check: no catalog at %s — run install.sh (or /lodestar-update) "
              "to place it, or pass --catalog." % catalog_dir)
        return 0

    results = collect(rules_dir, catalog_dir, only=option(argv, "--rule"))
    if results is None:
        print("lodestar-rule-check: cannot read %s." % rules_dir)
        return 0
    if option(argv, "--rule") and not results:
        print("lodestar-rule-check: no installed rule named %r in %s."
              % (option(argv, "--rule"), rules_dir))
        return 1

    failed = [r for r in results if r["status"] in ("drifted", "unreadable")]

    if "--json" in argv:
        print(json.dumps({
            "workspace": os.path.abspath(workspace),
            "rulesDir": rules_dir,
            "catalogDir": catalog_dir,
            "rules": results,
            "drifted": len([r for r in results if r["status"] == "drifted"]),
            "unreadable": len([r for r in results if r["status"] == "unreadable"]),
        }, indent=2))
    else:
        print(render(results, rules_dir, catalog_dir, verbose="--verbose" in argv))

    return 1 if ("--check" in argv and failed) else 0


if __name__ == "__main__":
    try:
        if sys.version_info < MIN_PYTHON:
            print("lodestar-rule-check: needs Python %d.%d+ but this is %s — no rule was "
                  "compared, so this is not a clean report."
                  % (MIN_PYTHON[0], MIN_PYTHON[1], "%d.%d.%d" % sys.version_info[:3]))
            sys.exit(1)
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:
        # Same reasoning as the other hooks: never take down whatever invoked this. But an
        # error is not a clean bill of health, so `--check` must not read as "no drift".
        print("lodestar-rule-check: could not complete (%s) — nothing was compared." % exc)
        sys.exit(1 if "--check" in sys.argv[1:] else 0)
