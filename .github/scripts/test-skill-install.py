#!/usr/bin/env python3
"""Install the REAL catalog skills into a throwaway workspace and check what lands there.

`validate.py` checks a `SKILL.md` as a source file. What reaches a user is not that file:
`/lodestar-init` copies the workspace-wide skills and `/lodestar-onboard` §5 copies the
stack-scoped ones into `.claude/skills/`, substituting the `REPO` placeholder with the
repo's basename "so its body points at `docs/REPO/…`". Six of the ten shipped skills carry
that placeholder five or six times each, and nothing exercised the substitution — the same
gap `test-catalog.py` closed for the guardrails' `id:` → `name:` transform.

The failure it guards is silent. A skill installed with a literal `REPO` tells the model to
read `docs/REPO/conventions.md`, a path no workspace has; the model reads nothing and
proceeds on general knowledge, which looks exactly like a skill that loaded and had nothing
to add. No error, no log, no output.

Three assertions, against a workspace built from the shipped templates:

  1. the substitution is not vacuous — a skill claiming a placeholder has one to replace
  2. after substitution, no `REPO` token survives in an installed skill
  3. every `docs/…` path an installed skill sends the model to exists in that workspace

Plus the negative direction: the detector must fire on an unsubstituted install and stop
firing once the substitution has run. That is asserted against a literal fixture rather than
a catalog file — picking a real skill *because* the detector matched it and then asserting
the detector matches it is circular, and the first version of this file did exactly that.

`REPO` is a deliberate placeholder in `kit/` (CLAUDE.md, "Code Style"), so nothing here
objects to the token in a source file. What it asserts is that installing resolves it.
"""

import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SKILLS = os.path.join(ROOT, "kit", "catalog", "skills")
TEMPLATES = os.path.join(ROOT, "kit", "templates")

# The basename `/lodestar-onboard` §1 would derive from the repo directory. Deliberately
# unlike "REPO" so a half-done substitution cannot pass by looking similar.
REPO_NAME = "acme-api"

# `docs/…` paths the shipped skills point at, and what puts each one in a workspace. The
# left column is a prefix; the right is the template or the command step that creates it.
PLACED_BY = [
    ("docs/_shared/",   "kit/templates/docs/_shared/ (copied by /lodestar-init)"),
    ("docs/repo-map.md", "kit/templates/repo-map.md (copied by /lodestar-init)"),
    ("docs/%s/conventions.md" % REPO_NAME,
     "kit/templates/docs/repo-conventions.md (copied by /lodestar-onboard §5)"),
    ("docs/%s/architecture/" % REPO_NAME, "/lodestar-onboard §3 (the architecture map)"),
]

# A bare `docs/` in prose names the directory, not a file to read.
IGNORED_PATHS = {"docs", "docs/"}

PLACEHOLDER = re.compile(r"\bREPO\b")
DOC_PATH = re.compile(r"docs/[A-Za-z0-9_./-]*")

# The negative fixture, written out rather than taken from the catalog. A real skill chosen
# *because* the detector matched it cannot then witness that the detector works — that is
# circular, and it is how this check was first written. A literal is independent of the
# predicate, so both a detector that matches nothing and a substitution that is a no-op fail
# against it.
UNSUBSTITUTED_FIXTURE = "Read **`docs/REPO/conventions.md`** before editing REPO.\n"


def substitute(text):
    """The install-time transform: `REPO` → the repo's basename, everywhere in the file.

    Word-bounded, so a longer word that merely contains the token keeps its spelling.
    """
    return PLACEHOLDER.sub(REPO_NAME, text)


def doc_paths(text):
    """The `docs/…` paths a skill body tells the model to read."""
    found = set()
    for raw in DOC_PATH.findall(text):
        path = raw.rstrip(".,;:)")
        if path and path not in IGNORED_PATHS:
            found.add(path)
    return sorted(found)


def build_workspace(work):
    """A workspace with the docs `/lodestar-init` and `/lodestar-onboard` would have made.

    Built from the shipped templates rather than by hand: a skill pointing at a
    `docs/_shared/` file that has no template must fail here, and it only can if this
    workspace is populated from the templates that actually ship.
    """
    shutil.copytree(os.path.join(TEMPLATES, "docs", "_shared"),
                    os.path.join(work, "docs", "_shared"))
    shutil.copy(os.path.join(TEMPLATES, "repo-map.md"),
                os.path.join(work, "docs", "repo-map.md"))
    repo_docs = os.path.join(work, "docs", REPO_NAME)
    os.makedirs(os.path.join(repo_docs, "architecture"))
    shutil.copy(os.path.join(TEMPLATES, "docs", "repo-conventions.md"),
                os.path.join(repo_docs, "conventions.md"))
    os.makedirs(os.path.join(work, ".claude", "skills"))


def install_skill(name, source_text, work):
    """Copy a catalog skill into `.claude/skills/<name>/SKILL.md`, substituted."""
    target = os.path.join(work, ".claude", "skills", name)
    os.makedirs(target, exist_ok=True)
    installed = substitute(source_text)
    with open(os.path.join(target, "SKILL.md"), "w") as f:
        f.write(installed)
    return installed


def main():
    entries = sorted(
        (os.path.basename(os.path.dirname(p)), p)
        for p in (os.path.join(SKILLS, d, "SKILL.md") for d in os.listdir(SKILLS))
        if os.path.isfile(p)
    )
    if not entries:
        print("❌ no skills found under kit/catalog/skills — this harness asserts nothing")
        return 1

    failures = []
    checks = 0
    placeholder_bearing = 0
    work = tempfile.mkdtemp(prefix="lodestar-skill-install-")
    try:
        build_workspace(work)
        for name, path in entries:
            source = open(path).read()
            in_source = len(PLACEHOLDER.findall(source))
            if in_source:
                placeholder_bearing += 1
            installed = install_skill(name, source, work)

            # (2) the substitution resolved every placeholder
            surviving = len(PLACEHOLDER.findall(installed))
            checks += 1
            if surviving:
                failures.append(
                    "%s: %d literal REPO token(s) survived installation — the model would "
                    "be sent to docs/REPO/…, a path no workspace has" % (name, surviving))

            # (3) every doc path the installed skill names exists in the workspace
            for doc in doc_paths(installed):
                checks += 1
                if os.path.exists(os.path.join(work, doc)):
                    continue
                hint = next((why for prefix, why in PLACED_BY if doc.startswith(prefix)),
                            "nothing in kit/templates/ creates it and no command step "
                            "generates it")
                failures.append(
                    "%s: points the model at %r, which no workspace has — %s"
                    % (name, doc, hint))

        # (1) the substitution is not vacuous. If no shipped skill carries a placeholder,
        # every assertion above passes for the wrong reason.
        checks += 1
        if not placeholder_bearing:
            failures.append(
                "no shipped skill contains a REPO placeholder — assertion (2) passes "
                "trivially, so this harness has stopped testing the substitution")

        # The negative direction, in the shape test-catalog.py's ALLOW fixtures take: the
        # detector must fire on text a skipped substitution would leave behind, and must
        # stop firing once `substitute()` has run over that same text. Asserted against the
        # literal fixture so neither half can pass by circularity.
        checks += 1
        if not PLACEHOLDER.findall(UNSUBSTITUTED_FIXTURE):
            failures.append(
                "the placeholder detector does not match the unsubstituted fixture — it "
                "cannot catch a skipped substitution, which makes assertion (2) decorative")
        checks += 1
        if PLACEHOLDER.findall(substitute(UNSUBSTITUTED_FIXTURE)):
            failures.append(
                "substitute() left a REPO token in the unsubstituted fixture — the "
                "install-time transform this harness models does not resolve the placeholder")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if failures:
        print("❌ skill install: %d problem(s) across %d skills\n" % (len(failures), len(entries)))
        for f in failures:
            print("  - " + f)
        return 1
    print("✅ skill install: %d checks across %d skills (%d carry a REPO placeholder)"
          % (checks, len(entries), placeholder_bearing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
