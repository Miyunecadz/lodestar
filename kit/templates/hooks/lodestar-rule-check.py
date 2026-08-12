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

    lodestar-rule-check.py                       # report; exit 0 unless it could not run
    lodestar-rule-check.py --check               # exit 1 if anything drifted (CI / doctor)
    lodestar-rule-check.py --json                # machine-readable
    lodestar-rule-check.py --rule block-env-files
    lodestar-rule-check.py --workspace PATH --catalog PATH

Without `--check` a difference is reported and the exit stays 0. The two exceptions are the
cases where nothing was compared at all: an interpreter below MIN_PYTHON, and a `--rule`
naming no installed rule. Silence there would read as a clean report.

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

**Finding the catalog source is itself a failure mode**, and the states below are separated
because a stale rule used to hide in every one of them:

    ok                 every compared field and both body halves agree
    drifted            at least one differs — the report names it
    renamed            `name:` resolves to nothing, the filename does; compared anyway
    retired            neither resolves, but the manifest records the id as adopted
    catalog-unreadable the source file is there and this parser cannot read it
    local              neither resolves and the id was never adopted — not compared
    unreadable         the installed rule has no frontmatter, so nothing enforces it
    settings-hook      an adopted `emits: settings-hook` entry — see below

`local` is the only one of those that is not a finding, and telling it from `retired` is what
the manifest's `guardrails` list is read for: an id nobody adopted is somebody's own rule, an
adopted id that has left the catalog is a rule that kept enforcing after its source was
withdrawn. With no manifest the two are indistinguishable, and the benign reading is taken.

`emits: settings-hook` entries (the three autolint routers) install as shell logic inside
`.claude/settings.json`, not as a rule file, and nothing pins the shape of what the picker
writes there — so their content cannot be compared field-by-field the way a rule file can.
They are **named as not compared** rather than left out, because a report that silently
skipped them read as a clean bill of health for rules it had never looked at.

Requires Python 3.8+ (see MIN_PYTHON), stdlib only, and stays a single self-contained file
like the other hooks — see `.claude/skills/hook-engine-invariants`.
"""

import json
import os
import sys

MIN_PYTHON = (3, 8)

RULES_REL = os.path.join(".claude", "guardrails")
CATALOG_REL = os.path.join(".lodestar", "catalog", "guardrails")
MANIFEST_REL = os.path.join(".claude", "lodestar.manifest.json")

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


def adopted_ids(workspace):
    """The guardrail ids the manifest records as installed, or None if it cannot say.

    None is not the empty set, and the difference decides a verdict: with no manifest, a rule
    with no catalog entry cannot be told from one the user wrote, so the benign reading has to
    be taken. `/lodestar-guardrails` §7 writes this key on every run, so a workspace set up
    through the picker has it.
    """
    try:
        with open(os.path.join(workspace, MANIFEST_REL), "r") as f:
            data = json.load(f)
    except (IOError, OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    ids = data.get("guardrails")
    if not isinstance(ids, list):
        return None
    return {str(i) for i in ids}


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


def collect(rules_dir, catalog_dir, only=None, adopted=None):
    """Every installed rule's status. Sorted by filename, so output is stable."""
    try:
        names = sorted(n for n in os.listdir(rules_dir) if n.endswith(".md"))
    except (IOError, OSError):
        return None
    results = []
    seen = set()
    for name in names:
        installed = read_rule(os.path.join(rules_dir, name))
        file_id = name[:-3]
        rule_id = file_id
        if installed is not None:
            rule_id = str(installed[0].get("name") or file_id)
        if only and rule_id != only:
            continue
        seen.add(rule_id)
        if installed is None:
            results.append({"rule": rule_id, "file": name, "status": "unreadable"})
            continue
        # `name:` first — that is the id the engine enforces under. The filename is the
        # fallback, because it is what the picker itself wrote: a rule whose `name:` was
        # edited away from it is still that catalog entry's copy, and comparing it against
        # the filename's entry is what stops an edited `name:` from parking a stale rule in
        # the uncompared `local` bucket.
        source, matched_by = None, None
        for candidate, how in ((rule_id, "name"), (file_id, "file")):
            path = os.path.join(catalog_dir, "%s.md" % candidate)
            if os.path.isfile(path):
                source, matched_by = path, how
                break
        if source is None:
            # A rule can be authored locally, and docs/EXTENDING.md says so — but an id the
            # manifest records as adopted had a catalog entry once. Its absence now means the
            # entry was retired or renamed while the copy kept enforcing.
            results.append({"rule": rule_id, "file": name,
                            "status": "retired" if adopted and rule_id in adopted else "local"})
            continue
        catalog = read_rule(source)
        if catalog is None:
            # The source is present and unparseable, so there is nothing to compare against.
            # Reporting it as locally authored would be the stale copy's best hiding place.
            results.append({"rule": rule_id, "file": name, "status": "catalog-unreadable",
                            "source": os.path.basename(source)})
            continue
        diff = compare(installed, catalog)
        drifted = bool(diff["fields"]) or diff["redirect_differs"] or diff["rationale_differs"]
        record = dict(diff, rule=rule_id, file=name,
                      status="drifted" if drifted else "ok")
        if matched_by == "file":
            record["status"] = "renamed"
            record["catalog_id"] = file_id
        results.append(record)

    # Adopted `emits: settings-hook` entries have no rule file to walk — they went into
    # `.claude/settings.json` as shell logic. Naming them is the whole point: the report used
    # to omit them, so a workspace could read as fully in sync on rules never looked at.
    for rule_id in sorted((adopted or set()) - seen):
        if only and rule_id != only:
            continue
        path = os.path.join(catalog_dir, "%s.md" % rule_id)
        entry = read_rule(path) if os.path.isfile(path) else None
        if entry and entry[0].get("emits") == "settings-hook":
            results.append({"rule": rule_id, "file": MANIFEST_REL, "status": "settings-hook"})
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
        if r["status"] == "retired":
            lines.append("RETIRED   %s — the manifest records this rule as adopted and the"
                         " catalog has no entry of that name any more, so it cannot be"
                         " compared. An entry withdrawn because it was wrong keeps enforcing"
                         " here until you remove the file." % r["rule"])
            lines.append("")
            continue
        if r["status"] == "catalog-unreadable":
            lines.append("CATALOG   %s — its source %s has no frontmatter this parser can"
                         " read, so nothing could be compared. Re-run install.sh (or"
                         " /lodestar-update) to replace the catalog."
                         % (r["rule"], r["source"]))
            lines.append("")
            continue
        if r["status"] == "settings-hook":
            lines.append("NOT COMPARED %s — an adopted `emits: settings-hook` entry. It was"
                         " installed into .claude/settings.json as shell logic, not as a rule"
                         " file, so this checker cannot compare it. Re-run"
                         " /lodestar-guardrails to re-emit it from the current catalog."
                         % r["rule"])
            lines.append("")
            continue
        if r["status"] == "renamed":
            lines.append("RENAMED   %s — its `name:` matches no catalog entry, so it was"
                         " compared against %s instead, the entry its filename names. The"
                         " engine enforces it under `name:`. To keep it as your own rule,"
                         " rename the file too."
                         % (r["rule"], r["catalog_id"]))
        else:
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
                        ("drifted", "renamed", "retired", "catalog-unreadable", "unreadable",
                         "local", "ok") if counts.get(s))
    # Counted apart from the rules: a settings-hook entry is not a file in this directory, and
    # folding it into the total would make the count of installed rules wrong.
    lines.append("%d installed rule(s): %s"
                 % (len(results) - counts.get("settings-hook", 0), summary or "none"))
    if counts.get("settings-hook"):
        lines.append("plus %d adopted settings-hook entr%s, not compared — see above"
                     % (counts["settings-hook"],
                        "y" if counts["settings-hook"] == 1 else "ies"))
    if counts.get("drifted") or counts.get("renamed"):
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

    results = collect(rules_dir, catalog_dir, only=option(argv, "--rule"),
                      adopted=adopted_ids(workspace))
    if results is None:
        print("lodestar-rule-check: cannot read %s." % rules_dir)
        return 0
    if option(argv, "--rule") and not results:
        print("lodestar-rule-check: no installed rule named %r in %s."
              % (option(argv, "--rule"), rules_dir))
        return 1

    # Every status where a stale rule could be sitting unexamined, and none where it could
    # not: `local` was never the catalog's, and `settings-hook` is named as uncomparable
    # rather than asserted to have moved — failing on either would report absence of
    # evidence as evidence, and a report people learn to ignore protects nobody.
    failed = [r for r in results if r["status"] in
              ("drifted", "renamed", "retired", "catalog-unreadable", "unreadable")]

    if "--json" in argv:
        print(json.dumps({
            "workspace": os.path.abspath(workspace),
            "rulesDir": rules_dir,
            "catalogDir": catalog_dir,
            "rules": results,
            "drifted": len([r for r in results if r["status"] == "drifted"]),
            "unreadable": len([r for r in results if r["status"] == "unreadable"]),
            "renamed": len([r for r in results if r["status"] == "renamed"]),
            "retired": len([r for r in results if r["status"] == "retired"]),
            "catalogUnreadable": len([r for r in results
                                      if r["status"] == "catalog-unreadable"]),
            "notCompared": len([r for r in results if r["status"] == "settings-hook"]),
            "failing": len(failed),
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
