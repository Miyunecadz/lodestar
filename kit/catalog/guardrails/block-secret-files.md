---
id: block-secret-files
title: Block reads and writes of key and credential files
category: secrets
severity: block
recommended: true
stacks: [all]
event: file
pattern: '(\.pem$|\.key$|\.p12$|\.pfx$|(^|/)id_(rsa|ed25519|ecdsa|dsa)$|(^|/)\.?(credentials|service-account.*|gcloud-key.*)\.json$)'
emits: rule
---

These are private keys and credential files — TLS/SSH private keys (`*.pem`, `*.key`, `id_rsa`, `id_ed25519`), PKCS#12 bundles (`*.p12`, `*.pfx`), and cloud credential files (`credentials.json`, service-account keys). The assistant must never read or write them; their contents are live secrets that must not enter context or the repo. If you need to know the expected shape, use a committed `*.example` template or the project's documented variable list instead. Sibling of [[block-env-files]] — that rule covers `.env*`, this one covers keys and certs.
