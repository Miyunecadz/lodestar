---
id: block-env-files
title: Block reads and writes of .env files
category: secrets
severity: block
recommended: true
stacks: [all]
event: file
pattern: '(^|/)\.env(\.(?!example|sample|template|dist|defaults)[^/]+)?$'
emits: rule
---

Real `.env` files hold live credentials and must never be read or written by the assistant. Use a committed template (`.env.example`, `.env.sample`, `.env.template`, `.env.dist`, `.env.defaults`) to learn the expected variable shape instead — those template suffixes are excluded by the negative lookahead, while `.env` and real per-tier files like `.env.local` / `.env.production` are blocked.
