---
id: block-env-files
title: Block reads and writes of .env files
category: secrets
severity: block
recommended: true
stacks: [all]
event: file
pattern: '(^|/)\.env($|\.[^/]+$)'
emits: hookify
---

Real `.env` files hold live credentials and must never be read or written by the assistant. Use the committed `.env.example` to learn the expected variable shape instead — it is deliberately excluded from this pattern (only `.env` and `.env.<suffix>` match, not `.env.example`).
