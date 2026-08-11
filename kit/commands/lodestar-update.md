---
description: Update the installed Lodestar kit in this workspace — fetch a released version and re-sync catalog, templates, commands, and the guardrail engine, without touching anything you generated.
argument-hint: "[version] — e.g. /lodestar-update 0.6.0 to pin or roll back; omit for the latest release"
allowed-tools: Bash, Read, AskUserQuestion
effort: low   # mechanical: resolve a tag, fetch it, re-run install.sh, diff versions, report
---

You update the Lodestar **kit** installed in this workspace. This refreshes the reusable catalog/templates/commands/engine only — it must **never** touch what the user generated (their manifest, `.claude/guardrails/*`, `.claude/agents/*`, `.claude/settings.json`, `CLAUDE.md`, or `docs/`). Narrate each step.

Updates move between **released tags**, not to the tip of `main`, so an update is a deliberate step from one version to another and is reversible.

## 1. Locate the install
- Confirm `.lodestar/` exists here. If not, this workspace has no Lodestar install — point the user at the install command in the README and stop.
- Read `.lodestar/VERSION` (what's installed now) and `.lodestar/source.json`:
  ```json
  { "kind": "remote|local", "origin": "<url or path>", "ref": "v0.6.0", "version": "0.6.0" }
  ```
- **Fallbacks, in order** — older installs predate `source.json`:
  1. No `source.json` but `.lodestar/SOURCE` exists → treat its contents as the origin. If it looks like a URL (`http`, `git@`, `ssh://`) treat it as `kind: remote`, otherwise as `kind: local`.
  2. Neither file → ask the user (AskUserQuestion / free text) for the repo URL or the path to their clone.
  Either way the next `install.sh` run writes `source.json`, so this only happens once.

## 2. Pick the target version
- `$ARGUMENTS` given → that's the target. Accept `0.6.0` or `v0.6.0`; normalize to the `v`-prefixed tag. This is how a user **pins or rolls back**.
- No argument → resolve the newest release tag from the origin:
  ```
  git ls-remote --tags --refs <origin> | awk -F/ '{print $NF}' \
    | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1
  ```
- If the target equals `.lodestar/VERSION`, say they're already current and ask whether to re-sync anyway (repairs edited/missing kit files). If the target is **older**, say plainly that this is a rollback and confirm.
- Tags before **v0.5.0** use the pre-`kit/` layout and cannot be installed this way; the installer refuses with instructions. Don't offer them as a target.

## 3. Fetch and re-sync (non-destructive)
Run the installer for the target version. Never hand-copy files yourself — `install.sh` owns that behavior.

- **`kind: remote`** — fetch the tag into a temp dir, install from it, remove the temp dir:
  ```bash
  tmp="$(mktemp -d)"
  git clone --quiet --depth 1 --branch <tag> <origin> "$tmp/lodestar" \
    && "$tmp/lodestar/install.sh" "$PWD"
  rm -rf "$tmp"
  ```
  Nothing is left behind — the workspace never owns a clone.
- **`kind: local`** (contributor or offline install, `origin` is a path) — keep today's behavior:
  ```bash
  git -C "<origin>" pull --ff-only && "<origin>/install.sh" "$PWD"
  ```
  If the pull fails (local changes, detached HEAD, no network), report the error and ask whether to re-sync from the clone as-is or abort. If `<origin>` isn't a git repo (a copied folder), skip the pull and re-sync from it directly.
  - **With an explicit version on a local install**, don't mutate the user's clone. Read its remote and let the installer fetch that tag instead:
    ```bash
    url="$(git -C "<origin>" remote get-url origin)"
    LODESTAR_REPO="$url" "<origin>/install.sh" "$PWD" --ref <tag>
    ```
- If the installer exits non-zero, report its output verbatim and stop — the workspace is unchanged apart from files it already copied.

## 4. Report what changed and what to do next
- Show old → new version (and say "rollback" if it went backwards).
- Summarize notable changes for the new version from the fetched `CHANGELOG.md`. If a section has an **Upgrading** note, surface it — that's where "re-run this command to adopt the fix" lives.
- Compare the refreshed catalog against the manifest's enabled ids: list any **new catalog entries** (guardrails / agents / skills) now available that the workspace hasn't adopted. This is the key value — the user won't see new rules/agents until they opt in.
- **Then report the rules the workspace already adopted whose catalog source has since changed.** New entries are only half of it: an installed rule in `.claude/guardrails/` was copied once and is never reconciled, so a corrected pattern sits in the refreshed catalog while the file that actually enforces stays as it was. Do not eyeball this — run the shipped checker, which reads both sides:
  ```bash
  python3 .lodestar/templates/hooks/lodestar-rule-check.py
  ```
  It prints each drifted rule with the field, the installed value, and the catalog value. Relay that verbatim rather than summarising it — which field moved is the whole content of the report. **Never edit an installed rule to "fix" the drift**: the checker cannot tell a stale copy from a deliberate local edit (adding an env tier to `permission_rules` is documented practice), and neither can you. Adoption is re-running `/lodestar-guardrails` and re-ticking that rule, which is the user's call.
- Recommend the follow-ups only where relevant:
  - New or changed **guardrails** → re-run `/lodestar-guardrails` and tick them.
  - New or changed **agents** → re-run `/lodestar-agents`.
  - New **stack skills** → re-run `/lodestar-onboard ./<repo>` for the affected repo.
  - **Freshness** available but not enabled (no `freshness` key in the manifest) → suggest `/lodestar-freshness` to keep architecture maps in sync with the code.
- Remind the user their existing rules/agents/docs were left exactly as they were; updating the catalog never regenerates them silently — adoption is always an explicit re-run. Mention `/lodestar-update <old-version>` as the way back if a new version misbehaves.
