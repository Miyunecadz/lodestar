#!/usr/bin/env python3
"""Lodestar catalog + consistency validator (used by CI).

Checks, with stdlib only:
  - every guardrail has the required frontmatter, valid enums, and a compilable regex;
  - every agent/skill has the required frontmatter;
  - every skill's description is a load trigger, and its body fits the size budget;
  - no two skills that can load together share an indistinguishable trigger;
  - every entry's `stacks` values are tags `/lodestar-onboard` §2 can detect;
  - every self-silencing rule's manifest key is a path a spec or hook actually writes;
  - every guardrail has positive and negative behaviour fixtures;
  - every guardrail's block-time message fits the redirect budget;
  - changelog.d/ fragments are well-formed;
  - VERSION matches the top CHANGELOG entry;
  - every CHANGELOG heading's release status matches the actual git tags.
Exits non-zero (listing every problem) if anything is off.
"""
import os
import re
import ast
import sys
import glob
import difflib
import itertools
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
errors = []


def frontmatter(path):
    """Return a dict of top-level `key: value` pairs from the file's --- frontmatter."""
    with open(path) as f:
        text = f.read()
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = {}
    for line in parts[1].splitlines():
        if not line.strip() or line[:1] in (" ", "\t", "#"):
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


VALID_SURFACES = ("agent", "commit", "permission")


def surfaces_of(value):
    """Frontmatter `surface` → the set of mechanisms it names.

    Accepts a scalar or an inline list. `both` is the pre-permission-surface spelling
    of `[agent, commit]` and stays valid, so installed rule files keep working.
    """
    raw = (value or "").strip()
    if raw.startswith("[") and raw.endswith("]"):
        names = {p.strip().strip('"').strip("'").lower() for p in raw[1:-1].split(",") if p.strip()}
    else:
        names = {raw.lower()} if raw else set()
    if "both" in names:
        names.discard("both")
        names |= {"agent", "commit"}
    return names


def stacks_of(value):
    """Frontmatter `stacks` → the list of tags it names (scalar or inline list)."""
    raw = (value or "").strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [p.strip().strip('"').strip("'") for p in raw.split(",") if p.strip()]


ONBOARD_SPEC = "kit/commands/lodestar-onboard.md"


def stack_vocabulary():
    """Every tag `/lodestar-onboard` §2 can actually detect, plus the `all` sentinel.

    Derived, not declared. `docs/EXTENDING.md` ("Add a stack detector") makes adding the
    detection signal step one and tagging entries step two, so that table already is the
    vocabulary — a second hand-maintained list here would be a rival source of truth with
    nothing keeping the two in step. This reads the spec; verifying the command's own
    behaviour is issue #25's scope, not this check's.

    Returns None when the table cannot be parsed, so the caller reports a stale parser
    rather than validating all 50 entries against an empty set and failing every one.
    """
    path = os.path.join(ROOT, ONBOARD_SPEC)
    if not os.path.exists(path):
        return None
    section = re.search(r"^##\s*2\.[^\n]*\n(.*?)(?=^##\s)", open(path).read(), re.S | re.M)
    if not section:
        return None
    tags = set(re.findall(r"^\|.*\|\s*`([a-z0-9][a-z0-9-]*)`\s*\|\s*$", section.group(1), re.M))
    if len(tags) < 10:
        return None
    return tags | {"all"}


def check_stack_vocabulary():
    """`stacks` values must be tags the onboarding step can actually detect.

    The key's presence was already required for guardrails and agents; its values were
    never checked, for any entry type. A typo (`react-nativ`) yields an entry that
    installs cleanly and then matches nothing — fail-open, and unlike a guardrail that
    stops firing there is no eventual noticing, because a pack that never activates looks
    exactly like a repo that needed no pack.
    """
    vocab = stack_vocabulary()
    if vocab is None:
        errors.append(
            f"{ONBOARD_SPEC}: could not parse the §2 stack-detection table — it is the "
            "vocabulary every entry's `stacks` is checked against, so this check cannot "
            "run until the parser or the table agree again")
        return
    for pattern in ("kit/catalog/guardrails/*.md", "kit/catalog/agents/*.md",
                    "kit/catalog/skills/*/SKILL.md"):
        for path in sorted(glob.glob(os.path.join(ROOT, pattern))):
            rel = os.path.relpath(path, ROOT)
            for tag in stacks_of(frontmatter(path).get("stacks")):
                if tag not in vocab:
                    errors.append(
                        f"{rel}: unknown stack tag {tag!r} — no `/lodestar-onboard` §2 "
                        f"signal detects it, so the entry would never install. Add the "
                        f"detector first (docs/EXTENDING.md 'Add a stack detector'), and "
                        f"check it is a `| signal | `tag` |` table row — that row "
                        f"shape is what this vocabulary is parsed from")


def check_guardrails():
    for path in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/guardrails/*.md"))):
        rel = os.path.relpath(path, ROOT)
        fm = frontmatter(path)
        for key in ("id", "severity", "stacks", "event", "pattern", "emits", "surface"):
            if key not in fm:
                errors.append(f"{rel}: missing frontmatter key '{key}'")
        if fm.get("severity") not in ("block", "warn"):
            errors.append(f"{rel}: severity must be block|warn (got {fm.get('severity')!r})")
        if fm.get("event") not in ("file", "bash", "all"):
            errors.append(f"{rel}: event must be file|bash|all (got {fm.get('event')!r})")
        if fm.get("emits") not in ("rule", "settings-hook"):
            errors.append(f"{rel}: emits must be rule|settings-hook (got {fm.get('emits')!r})")
        surfaces = surfaces_of(fm.get("surface"))
        if not surfaces:
            errors.append(f"{rel}: missing frontmatter key 'surface'")
        unknown = sorted(surfaces - set(VALID_SURFACES))
        if unknown:
            errors.append(
                f"{rel}: unknown surface(s) {unknown} — valid are "
                f"{list(VALID_SURFACES)} or the legacy scalar 'both'")
        # A permission-surface rule needs the deny entries spelled out: a regex does
        # not translate to a gitignore-style glob, so the author states both forms.
        if "permission" in surfaces:
            entries = fm.get("permission_rules", "").strip()
            parsed = [p.strip().strip('"').strip("'")
                      for p in entries.strip("[]").split(",") if p.strip()]
            if not parsed:
                errors.append(f"{rel}: surface 'permission' needs a non-empty permission_rules list")
            for entry in parsed:
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*\(.+\)", entry):
                    errors.append(
                        f"{rel}: permission_rules entry {entry!r} is not a Tool(pattern) rule "
                        f"(e.g. 'Read(./.env)')")
        # A commit-surface rule needs something the pre-commit checker can actually run:
        # a `file` pattern (checked against staged paths) or a named built-in check.
        if "commit" in surfaces:
            check = fm.get("commit_check") or ("staged-paths" if fm.get("event") == "file" else None)
            if check not in ("staged-paths", "secret-scan", "default-branch"):
                errors.append(
                    f"{rel}: surface {fm['surface']} needs commit_check "
                    f"(staged-paths|secret-scan|default-branch) or event: file (got {check!r})")
            if fm.get("commit_severity") not in (None, "block", "warn"):
                errors.append(f"{rel}: commit_severity must be block|warn (got {fm.get('commit_severity')!r})")
        pat = fm.get("pattern")
        if pat:
            try:
                re.compile(pat)
            except re.error as e:
                errors.append(f"{rel}: pattern is not a valid regex: {e}")


def check_agents():
    for path in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/agents/*.md"))):
        rel = os.path.relpath(path, ROOT)
        fm = frontmatter(path)
        if "id" not in fm and "name" not in fm:
            errors.append(f"{rel}: needs an 'id' or 'name'")
        for key in ("stacks", "tools", "description"):
            if key not in fm:
                errors.append(f"{rel}: missing frontmatter key '{key}'")


# A skill is a router, not a knowledge base: the body points at `docs/…` instead of
# restating what is there. The shipped ten run 723–1593 bytes. 2000 leaves the longest of
# them room to grow while staying out of reach by accident — past it a skill has become
# the always-on payload the router exists to avoid. Same reasoning as REDIRECT_BUDGET
# below, one layer up.
SKILL_SIZE_BUDGET = 2000

# Two triggers this alike are two triggers a reader cannot route between. Every pair of
# shipped skills currently sits at or below 0.75, so 0.80 takes near-verbatim wording —
# it cannot be met by two genuinely distinct triggers.
TRIGGER_SIMILARITY_LIMIT = 0.80


def check_skills():
    for path in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/skills/*/SKILL.md"))):
        rel = os.path.relpath(path, ROOT)
        fm = frontmatter(path)
        for key in ("name", "description", "stacks"):
            if key not in fm:
                errors.append(f"{rel}: missing frontmatter key '{key}'")
        # `docs/CONCEPTS.md` §1: the description *is* the routing decision — the model
        # reads an index of these triggers at startup and pulls the body only when one
        # matches the current task. A description that summarises the skill instead of
        # naming the task it belongs to is a skill that never loads, and nothing about
        # that failure is visible: no error, no log, no output.
        description = fm.get("description", "").strip()
        if "description" in fm and not description:
            errors.append(f"{rel}: 'description' is empty — it is the load trigger")
        elif description and not description.lower().startswith("use when"):
            errors.append(
                f"{rel}: description must be a when-to-load trigger starting 'Use when', "
                f"not a summary (got {description[:40]!r}) — see docs/EXTENDING.md "
                "'Add a skill'")
        size = os.path.getsize(path)
        if size > SKILL_SIZE_BUDGET:
            errors.append(
                f"{rel}: {size} bytes, over the {SKILL_SIZE_BUDGET} budget — a skill "
                "points at the docs, it does not restate them")


def check_skill_triggers():
    """No two skills scoped to the same stack may share an indistinguishable trigger.

    Description-based routing degrades as the catalog grows: the model chooses between
    triggers, so two that read alike make the choice arbitrary.

    What is compared is exactly: pairs sharing a literal `stacks` tag, plus every pair
    involving a `stacks: [all]` skill. That is a **lower bound on co-loading, not a
    statement of it** — `/lodestar-onboard` §2 collects *all* matching signals, so one repo
    carries several tags at once (a Django API with DRF gets both `python-django` and `drf`),
    and §5 copies matched skills into the workspace's single `.claude/skills/`, so skills
    matched by different repos sit side by side. Two skills with non-intersecting tags can
    therefore co-exist and still not be compared here.

    Same-stack is the scope issue #59 asked for ("no two enabled skills in the same stack
    share a trigger that a reader cannot tell apart"), and it is where an indistinguishable
    pair actually costs something: the model routing inside one stack has nothing else to go
    on, while across stacks the tag itself already separates them.

    Comparing every pair instead would flag nothing today — the highest ratio anywhere in the
    catalog is 0.691 (`backend-standards` / `django-backend-standards`), and no pair reaches
    the limit. It is the *next* entry that argues against it: the per-stack conventions skills
    are one family by design ("Use when editing the <X> backend repo (REPO) — …"), they
    already sit closest to the limit, and they are differentiated by a short decisive token
    (which stack, which repo) rather than by sentence shape. Adding one more of them is the
    likeliest way to produce a false positive, and a check that fires on a correct entry is a
    check the reader learns to skip. Widen this only with that in mind.
    """
    entries = []
    for path in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/skills/*/SKILL.md"))):
        fm = frontmatter(path)
        description = fm.get("description", "").strip().lower()
        if description:
            entries.append((os.path.basename(os.path.dirname(path)),
                            set(stacks_of(fm.get("stacks"))), description))
    for (a_name, a_stacks, a_desc), (b_name, b_stacks, b_desc) in itertools.combinations(entries, 2):
        if not (a_stacks & b_stacks or "all" in a_stacks or "all" in b_stacks):
            continue
        ratio = difflib.SequenceMatcher(None, a_desc, b_desc).ratio()
        if ratio >= TRIGGER_SIMILARITY_LIMIT:
            errors.append(
                f"skills '{a_name}' and '{b_name}' can load in the same workspace and "
                f"their descriptions are {ratio:.0%} alike — there is nothing for the "
                "model to route on; name the distinct task each one belongs to")


HOOKS_GLOB = "kit/templates/hooks/*.py"
PICKER_SPEC = "kit/commands/lodestar-guardrails.md"

# Every place that has to state the same list of copied frontmatter fields, and the name of
# the literal holding it. `/lodestar-guardrails` §5 is checked separately: it is prose, so
# membership is what can be asserted there, not equality.
COPY_SITES = [
    (".github/scripts/test-catalog.py", "COPIED"),
    ("kit/templates/hooks/lodestar-rule-check.py", "COMPARED"),
]

# Frontmatter keys the hooks read that are deliberately NOT copied from the catalog entry.
# `name` and `enabled` are written fresh by the picker (`name` from the entry's `id`), and
# `action` is a legacy alias for `severity` the engine still tolerates but no catalog entry
# sets. Everything else a hook reads must be copied, or the installed rule loses it.
NOT_COPIED = {"name", "enabled", "action"}


def hook_read_fields():
    """Frontmatter keys the shipped hooks actually read, from their own source.

    Derived, not declared — the same argument as `stack_vocabulary()` above. The hooks are
    the only authority on which fields matter; a hand-kept list here would be a fourth
    rival copy of the thing this check exists to keep in step.

    Returns None when the scan looks broken, so a stale pattern reports itself instead of
    validating every site against an empty set and passing.
    """
    found = set()
    for path in sorted(glob.glob(os.path.join(ROOT, HOOKS_GLOB))):
        text = open(path).read()
        found |= set(re.findall(r"(?:rule|fm)\.get\(\s*[\"']([a-z_][a-z0-9_]*)[\"']", text))
    found = {f for f in found if not f.startswith("_")}
    if len(found) < 10:
        return None
    return found - NOT_COPIED


def list_literal(rel, name):
    """The string entries of a top-level `NAME = [...]` literal, or None if unparseable."""
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return None
    m = re.search(r"^%s = \[(.*?)\n\]" % re.escape(name), open(path).read(), re.S | re.M)
    if not m:
        return None
    entries = re.findall(r"[\"']([a-z_][a-z0-9_]*)[\"']", m.group(1))
    return set(entries) or None


def picker_section_five():
    """The text of `/lodestar-guardrails` §5, or None when the heading cannot be found."""
    path = os.path.join(ROOT, PICKER_SPEC)
    if not os.path.exists(path):
        return None
    m = re.search(r"^##\s*5\.[^\n]*\n(.*?)(?=^##\s)", open(path).read(), re.S | re.M)
    return m.group(1) if m else None


def check_copied_fields():
    """One list of copied fields, stated in three places, kept identical by this check.

    An installed rule is written once by a model following `/lodestar-guardrails` §5 and
    never reconciled afterwards, so a field the spec forgets to name is a field the picker
    silently drops — and the rule enforces without its scoping, or nags forever without its
    self-silencing. That is not hypothetical: `requires_manifest_missing` was read by the
    engine and set by a shipped rule while §5 did not name it (PR #64), and the drift was
    found by reading rather than by any gate. `test-catalog.py` could not see it, because it
    copies the fields via its own list and so exercises a corrected picker.

    So: the fields the hooks read are the truth, and every site that restates them must
    agree. Equality for the two Python literals; membership for the spec, which is prose.
    """
    expected = hook_read_fields()
    if expected is None:
        errors.append(
            f"{HOOKS_GLOB}: the `rule.get(...)` / `fm.get(...)` scan found too few "
            "frontmatter fields to be believable — the hooks changed shape and this check "
            "cannot run until the pattern is fixed. It is what keeps the picker's copy "
            "list in step with what the engine reads")
        return

    for rel, name in COPY_SITES:
        actual = list_literal(rel, name)
        if actual is None:
            errors.append(
                f"{rel}: could not parse the `{name} = [...]` list — it must stay a "
                "top-level literal of quoted field names, because it is checked against "
                "what the hooks read")
            continue
        for field in sorted(expected - actual):
            errors.append(
                f"{rel}: `{name}` is missing {field!r}, which a shipped hook reads — an "
                "installed rule would lose it with no error anywhere")
        for field in sorted(actual - expected):
            errors.append(
                f"{rel}: `{name}` lists {field!r}, which no shipped hook reads — either it "
                "is stale, or the hook that read it lost the read")

    section = picker_section_five()
    if section is None:
        errors.append(
            f"{PICKER_SPEC}: could not find the §5 heading — that section is what tells the "
            "picker which fields to copy, and it is checked against what the hooks read")
        return
    for field in sorted(expected):
        if f"`{field}`" not in section and f"`{field}:" not in section:
            errors.append(
                f"{PICKER_SPEC} §5 does not name `{field}`, which a shipped hook reads — a "
                "field §5 omits is a field the picker drops, and the installed rule loses "
                "that behaviour with no error anywhere")


COMMAND_SPECS = "kit/commands/lodestar-*.md"
WRITER_HOOKS = "kit/templates/hooks/*.py"
MANIFEST_VAR = "manifest"
MANIFEST_BLOCK = re.compile(r"```json[ \t]+manifest\b(.*?)```", re.S)


def json_key_paths(fragment):
    """Dotted key paths written by a JSON fragment.

    `"k":` names a key; braces and brackets give the nesting. The blocks in a command spec
    are fragments with placeholders (`<ISO-8601 UTC>`, `[ ... ]`), so `json.loads` is not an
    option — but the nesting is what matters here, and that survives a scan.

    A path is only recorded where the key really sits, and only where the engine could walk
    to it. `{"repos": [], "skills": []}` yields `repos` and `skills`, never `repos.skills`;
    `{"repos": [{"name": "x"}]}` yields `repos` alone, because `manifest_missing()` walks
    node by node and gives up at the list — a rule keyed on `repos.name` would nag forever.
    """
    paths, stack, pending = set(), [], None
    i, n = 0, len(fragment)
    while i < n:
        char = fragment[i]
        if char == '"':
            j = i + 1
            while j < n and fragment[j] != '"':
                j += 2 if fragment[j] == "\\" else 1
            token, i = fragment[i + 1:j], j + 1
            rest = i
            while rest < n and fragment[rest].isspace():
                rest += 1
            if rest < n and fragment[rest] == ":":
                if not any(kind == "[" for kind, _ in stack):
                    paths.add(".".join([key for _, key in stack if key] + [token]))
                pending, i = token, rest + 1
            continue
        if char in "{[":
            stack.append((char, pending))
            pending = None
        elif char in "}]":
            if stack:
                stack.pop()
            pending = None
        elif char == ",":
            pending = None
        i += 1
    return paths


def subscript_path(node):
    """`manifest["a"]["b"]` → `("manifest", ["a", "b"])`; None if a subscript is not a literal."""
    parts = []
    while isinstance(node, ast.Subscript):
        key = node.slice
        if key.__class__.__name__ == "Index":  # pre-3.9 ast wraps the subscript
            key = key.value
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            return None
        parts.append(key.value)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.reverse()
    return node.id, parts


def dict_literal_paths(node, prefix):
    """Every dotted path a `{...}` literal defines below `prefix`."""
    paths = set()
    if not isinstance(node, ast.Dict):
        return paths
    for key, value in zip(node.keys, node.values):
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            continue
        path = prefix + [key.value]
        paths.add(tuple(path))
        paths |= dict_literal_paths(value, path)
    return paths


def manifest_roots(tree):
    """Variable names that hold the manifest dict.

    A hook is recognised by what it loads — `x = load_json(manifest_path, {})` makes `x` a
    root — with the name `manifest` accepted outright, since that is what every shipped hook
    calls it. The assumption is deliberate and it *underreaches*: a hook that loads the
    manifest some other way contributes no paths, so a rule keyed on what it writes fails
    this gate loudly rather than passing on a guess. Widen this if that day comes.
    """
    roots = {MANIFEST_VAR}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        args = [a.id for a in node.value.args if isinstance(a, ast.Name)]
        if not any(a.endswith("manifest_path") for a in args):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                roots.add(target.id)
    return roots


def hook_manifest_paths(source):
    """Dotted manifest paths a hook writes, from assignments rooted at the manifest dict.

    Only literal subscripts and dict literals count, so this reports what the source actually
    stores rather than what it mentions. One indirection is resolved — `surfaces["x"] = {...}`
    followed by `manifest["y"] = surfaces` — because that is how the permission surface
    records itself.

    `var_paths` is module-wide rather than per function: a hook is one self-contained file
    whose names are not reused across scopes, and keeping it flat is what lets the alias above
    resolve at all. It can only over-collect for a *non-root* variable, which reaches the
    result solely through an assignment into the manifest.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    roots = manifest_roots(tree)
    var_paths, rooted, aliased = {}, set(), []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                var, parts = target.id, []
            elif isinstance(target, ast.Subscript):
                resolved = subscript_path(target)
                if resolved is None:
                    continue
                var, parts = resolved
            else:
                continue
            found = {tuple(parts)} if parts else set()
            found |= dict_literal_paths(node.value, list(parts))
            var_paths.setdefault(var, set()).update(found)
            if var in roots:
                rooted |= found
                if isinstance(node.value, ast.Name):
                    aliased.append((tuple(parts), node.value.id))
    for prefix, name in aliased:
        rooted |= {prefix + path for path in var_paths.get(name, set())}
    return {".".join(path) for path in rooted}


def check_manifest_flags():
    """A self-silencing rule's `requires_manifest_missing` key must be one something writes.

    The key is the whole mechanism: the rule fires while the dotted path is absent, false, or
    empty, and goes quiet once the manifest records it. But the *reader* is a catalog entry and
    the *writer* is a command spec or a shipped hook, in another directory, and nothing tied
    the two. Rename either side and the rule silently changes character — it nags forever, or
    it goes quiet about a gap that is still open. Neither shows up as an error anywhere, which
    is why this is a gate and not a convention.

    The flag is matched as a *path*, not as a bag of names: `repos.skills` names two unrelated
    top-level keys, and at runtime `manifest_missing()` walks node by node and returns True the
    moment an intermediate is not a dict — so a rule keyed on it would nag forever. Prose about
    a rule is not scanned at all; prose is not what writes the manifest.

    Only fences opened as ```` ```json manifest ```` count, and only those rooted at the
    manifest itself. A spec's other blocks describe `.claude/settings.json`, `source.json`, or
    a *repo entry* inside `repos[]` — keys that are real, but not manifest paths, and a rule
    keyed on one of them would nag forever exactly like a misspelt key. The marker is what
    tells the two apart; nothing in the JSON itself does.
    """
    writers = {}
    marked = 0
    for path in sorted(glob.glob(os.path.join(ROOT, COMMAND_SPECS))):
        rel = os.path.relpath(path, ROOT)
        with open(path) as f:
            for block in MANIFEST_BLOCK.findall(f.read()):
                marked += 1
                for key_path in json_key_paths(block):
                    writers.setdefault(key_path, rel)
    for path in sorted(glob.glob(os.path.join(ROOT, WRITER_HOOKS))):
        rel = os.path.relpath(path, ROOT)
        with open(path) as f:
            for key_path in hook_manifest_paths(f.read()):
                writers.setdefault(key_path, rel)
    if not marked:
        errors.append(f"{COMMAND_SPECS}: no ```json manifest fence found in any command spec "
                      "— either the marker was dropped or the manifest is now written "
                      "somewhere this check cannot see, and it is what keeps a self-silencing "
                      "rule's manifest key writable")
        return
    if not writers:
        errors.append(f"{COMMAND_SPECS}: the ```json manifest fences define no key paths, and "
                      f"no {WRITER_HOOKS} writes one either — this check cannot run")
        return

    for path in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/guardrails/*.md"))):
        rel = os.path.relpath(path, ROOT)
        flag = frontmatter(path).get("requires_manifest_missing", "").strip()
        if not flag:
            continue
        if not [s for s in flag.split(".") if s]:
            errors.append(f"{rel}: requires_manifest_missing is {flag!r}, which names no "
                          "manifest key — the rule would fire forever")
            continue
        if flag not in writers:
            near = sorted(p for p in writers if p.split(".")[0] == flag.split(".")[0])
            hint = f" — the closest paths written are {', '.join(near)}" if near else ""
            errors.append(
                f"{rel}: requires_manifest_missing names `{flag}`, which no {COMMAND_SPECS} "
                f"```json manifest fence and no {WRITER_HOOKS} writes as a manifest path"
                f"{hint}. A key nothing writes can never go absent-to-present, so the rule can "
                "never silence itself")


def check_catalog_totals():
    """The CATALOG.md totals line is documentation that silently goes stale — count the
    files and make CI notice when it disagrees."""
    path = os.path.join(ROOT, "kit/catalog/CATALOG.md")
    if not os.path.exists(path):
        errors.append("kit/catalog/CATALOG.md is missing")
        return
    entries = (glob.glob(os.path.join(ROOT, "kit/catalog/guardrails/*.md"))
               + glob.glob(os.path.join(ROOT, "kit/catalog/agents/*.md"))
               + glob.glob(os.path.join(ROOT, "kit/catalog/skills/*/SKILL.md")))
    text = open(path).read()
    m = re.search(r"Totals:\s*\*\*(\d+) entries\*\*", text)
    if not m:
        errors.append("kit/catalog/CATALOG.md: no 'Totals: **N entries**' line to check")
        return
    claimed, actual = int(m.group(1)), len(entries)
    if claimed != actual:
        errors.append(f"kit/catalog/CATALOG.md claims {claimed} entries, found {actual}")


def check_catalog_listed():
    """Every catalog entry should appear in CATALOG.md — an unlisted pack is invisible."""
    text = open(os.path.join(ROOT, "kit/catalog/CATALOG.md")).read()
    for pattern in ("kit/catalog/guardrails/*.md", "kit/catalog/agents/*.md"):
        for path in sorted(glob.glob(os.path.join(ROOT, pattern))):
            entry_id = os.path.basename(path)[:-3]
            if f"`{entry_id}`" not in text:
                errors.append(f"kit/catalog/CATALOG.md does not list '{entry_id}'")
    for path in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/skills/*/SKILL.md"))):
        name = os.path.basename(os.path.dirname(path))
        if f"`{name}`" not in text:
            errors.append(f"kit/catalog/CATALOG.md does not list skill '{name}'")


def check_fragments():
    """Changelog fragments must be releasable without a human reading them first.

    Feature PRs add a file here instead of editing `CHANGELOG.md` and `VERSION`, which
    is what stops two open PRs conflicting on the same hot line. The cost of that is
    that nobody sees a fragment until release time, so what would have been a review
    comment has to be a check.
    """
    directory = os.path.join(ROOT, "changelog.d")
    if not os.path.isdir(directory):
        return
    for name in sorted(os.listdir(directory)):
        if name == "README.md":
            continue
        rel = f"changelog.d/{name}"
        if not name.endswith(".md"):
            errors.append(f"{rel}: fragments must be .md files")
            continue
        body = open(os.path.join(directory, name)).read().strip()
        if not body:
            errors.append(f"{rel} is empty")
        elif re.search(r"^##\s*\[", body, re.M):
            errors.append(
                f"{rel} contains a '## [version]' heading — a fragment is the section "
                "body only; release.py writes the heading")


def git_tags():
    """Every `vX.Y.Z` tag in this checkout, as a set of bare versions.

    Returns None when git cannot answer — a shallow clone, a tarball, no git. Release
    status is then unverifiable, and the check skips rather than inventing failures.
    """
    try:
        proc = subprocess.run(
            ["git", "tag", "--list", "v*"], cwd=ROOT, timeout=10,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.decode("utf-8", "replace")
    return {t[1:] for t in out.split() if re.fullmatch(r"v\d+\.\d+\.\d+", t)}
def check_fixture_coverage():
    """Every guardrail needs a positive and a negative behaviour fixture.

    A pattern that compiles is not a pattern that matches what its title claims. This
    is the gate that stops a new catalog entry shipping with nothing asserting its
    behaviour; `.github/scripts/test-catalog.py` is what actually runs them.

    Both directions are required. A rule with only positives cannot regress into
    matching everything, and a rule with only negatives cannot regress into matching
    nothing — and silent non-enforcement is the failure mode that matters here.
    """
    path = os.path.join(ROOT, ".github/fixtures/guardrails.tsv")
    if not os.path.exists(path):
        errors.append(".github/fixtures/guardrails.tsv is missing")
        return
    positive, negative = {}, {}
    for lineno, line in enumerate(open(path), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            errors.append(f".github/fixtures/guardrails.tsv:{lineno}: needs 3 tab-separated fields")
            continue
        rule_id, want = parts[0].strip(), parts[1].strip()
        if want not in ("DENY", "WARN", "ALLOW"):
            errors.append(
                f".github/fixtures/guardrails.tsv:{lineno}: verdict must be "
                f"DENY|WARN|ALLOW (got {want!r})")
            continue
        bucket = negative if want == "ALLOW" else positive
        bucket[rule_id] = bucket.get(rule_id, 0) + 1
    for entry in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/guardrails/*.md"))):
        rule_id = os.path.basename(entry)[:-3]
        if not positive.get(rule_id):
            errors.append(
                f"guardrail '{rule_id}' has no positive fixture — add a case to "
                ".github/fixtures/guardrails.tsv showing it fires")
        if not negative.get(rule_id):
            errors.append(
                f"guardrail '{rule_id}' has no negative (ALLOW) fixture — add a case "
                "showing what it must NOT match; a rule that matches everything passes "
                "positives just fine")
# Ceiling on the part of a rule body that reaches the model when the rule fires. Issue
# #30 suggested ~600; the well-written redirects actually land between 223 and 829, and
# trimming to 600 would mean deleting things the model needs to act on. 900 sits above
# every current rule and well below where they started (1500–2400), so it cannot be met
# by accident but does catch a slide back to pasting rationale into the payload.
REDIRECT_BUDGET = 900


def redirect_of(body):
    """The block-time payload: everything above the first bare `---` line in the body."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "---":
            return "\n".join(lines[:i]).strip()
    return body.strip()


def check_redirect_budget():
    """A rule's block-time message must stay short enough to read as an instruction.

    `docs/CONCEPTS.md` §2: "a good block doesn't say 'denied,' it says 'don't edit an
    applied migration — create a new one with `db:new`.' Redirect, don't just refuse."
    A redirect buried under design rationale still redirects, technically.
    """
    for path in sorted(glob.glob(os.path.join(ROOT, "kit/catalog/guardrails/*.md"))):
        name = os.path.basename(path)[:-3]
        text = open(path).read()
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue  # frontmatter check reports this separately
        payload = redirect_of(parts[2].strip())
        if not payload:
            errors.append(
                f"guardrail '{name}' has an empty block message — the text above the "
                "`---` separator is what the model is shown"
            )
        elif len(payload) > REDIRECT_BUDGET:
            errors.append(
                f"guardrail '{name}' block message is {len(payload)} chars, over the "
                f"{REDIRECT_BUDGET} budget — move design rationale below a `---` line; "
                "it stays in the file, it just stops being sent on every block"
            )


def check_version():
    vpath = os.path.join(ROOT, "VERSION")
    cpath = os.path.join(ROOT, "CHANGELOG.md")
    if not os.path.exists(vpath):
        errors.append("VERSION file is missing")
        return
    version = open(vpath).read().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append(f"VERSION is not semver: {version!r}")
    text = open(cpath).read() if os.path.exists(cpath) else ""
    headings = re.findall(r"^##\s*\[(\d+\.\d+\.\d+)\]\s*(.*)$", text, re.M)
    top = headings[0][0] if headings else None
    if top != version:
        errors.append(
            f"VERSION ({version}) != top CHANGELOG entry ({top}) — both are written by "
            "`.github/scripts/release.py <version>`; a feature PR should not touch either "
            "(add a changelog.d/ fragment instead)")

    # Release status is a mechanically checkable claim, and it drifted: every heading
    # read "Unreleased" including twelve published versions, which release.yml then
    # copied verbatim into the GitHub Release notes (issue #33).
    tags = git_tags()
    if not tags:
        # None = git could not answer; empty = a shallow or --no-tags clone, or a
        # tarball. Either way release status is unverifiable, and asserting against an
        # empty tag set would report every published version as never released. CI uses
        # fetch-depth: 0 so this path is not how the check passes there.
        print("note: no v* tags in this checkout — skipping the release-status check")
        return
    for index, (ver, suffix) in enumerate(headings):
        suffix = suffix.strip()
        dated = re.fullmatch(r"—\s*\d{4}-\d{2}-\d{2}", suffix)
        pending = re.fullmatch(r"—\s*Unreleased", suffix)
        never = re.fullmatch(r"—\s*not released", suffix)
        if index == 0:
            # The top entry has two legitimate states, because `release.py` writes the
            # section in a PR and `release.yml` creates the tag when that PR merges:
            #   pending  — written, not yet merged, so no tag exists
            #   released — merged and tagged, which is the steady state between releases
            if ver in tags:
                if not dated:
                    errors.append(
                        f"CHANGELOG [{ver}] is tagged as v{ver} but its heading reads "
                        f"{suffix!r} — run `.github/scripts/release.py <next>`, which "
                        "stamps the previous version's date"
                    )
            elif not pending:
                errors.append(
                    f"CHANGELOG [{ver}] has no v{ver} tag yet, so as the top entry it "
                    f"must read '— Unreleased', not {suffix!r}"
                )
            continue
        if ver in tags:
            if not dated:
                errors.append(
                    f"CHANGELOG [{ver}] is tagged as v{ver} but its heading reads {suffix!r} — "
                    "it must carry the release date (YYYY-MM-DD)"
                )
        elif not never:
            errors.append(
                f"CHANGELOG [{ver}] has no v{ver} tag, so it must read '— not released', "
                f"not {suffix!r} — an uncut version must not look pending"
            )



def main():
    check_guardrails()
    check_agents()
    check_skills()
    check_skill_triggers()
    check_stack_vocabulary()
    check_copied_fields()
    check_manifest_flags()
    check_catalog_totals()
    check_catalog_listed()
    check_fixture_coverage()
    check_redirect_budget()
    check_fragments()
    check_version()
    if errors:
        print("❌ validation failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("✅ catalog + version validation passed")


if __name__ == "__main__":
    main()
