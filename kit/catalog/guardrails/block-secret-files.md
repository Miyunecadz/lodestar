---
id: block-secret-files
title: Block reads and writes of key and credential files
category: secrets
severity: block
recommended: true
stacks: [all]
event: file
pattern: '(\.pem$|\.key$|\.p12$|\.pfx$|(^|/)id_(rsa|ed25519|ecdsa|dsa)$|(^|/)\.?(credentials|service-account.*|gcloud-key.*)\.json$)'
surface: [agent, commit, permission]
permission_rules: [Read(./**/*.pem), Read(./**/*.key), Read(./**/*.p12), Read(./**/*.pfx), Read(./**/id_rsa), Read(./**/id_ed25519), Read(./**/id_ecdsa), Read(./**/id_dsa), Read(./**/credentials.json), Read(./*.pem), Read(./*.key), Read(./*.p12), Read(./*.pfx), Read(./id_rsa), Read(./id_ed25519), Read(./id_ecdsa), Read(./id_dsa), Read(./credentials.json)]
emits: rule
---

These are private keys and credential files — TLS/SSH private keys (`*.pem`, `*.key`, `id_rsa`, `id_ed25519`), PKCS#12 bundles (`*.p12`, `*.pfx`), and cloud credential files (`credentials.json`, service-account keys). The assistant must never read or write them; their contents are live secrets that must not enter context or the repo. If you need to know the expected shape, use a committed `*.example` template or the project's documented variable list instead. Sibling of [[block-env-files]] — that rule covers `.env*`, this one covers keys and certs.

**Surfaces: `agent`, `commit`, `permission`.** "Never read" used to be guidance rather than an enforced stop, because the PreToolUse engine is registered for `Bash|Edit|Write|MultiEdit` and cannot intercept a `Read`. The `permission` surface closes that: the `permission_rules` above become `permissions.deny` entries in `.claude/settings.json`, which Claude Code applies to every tool, merges across settings scopes, and has no interpreter that could fail open. The hook still covers Edit/Write with the precise regex, and a staged key or credential file blocks the commit for every committer.

Unlike [[block-env-files]], these patterns port cleanly to globs — a private key has no committed `*.example` counterpart to carve out — so the deny list mirrors the regex rather than a safe subset of it.
