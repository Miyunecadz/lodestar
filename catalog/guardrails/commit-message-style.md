---
id: commit-message-style
title: One-line commit messages, no co-author trailer
category: quality
severity: warn
recommended: false
stacks: [all]
event: bash
pattern: 'git commit'
emits: rule
---

Keep commit messages to a **single line** — a concise subject, no body — and do **not** append a `Co-Authored-By:` trailer (or other trailers). If a `-m` message spans multiple lines or adds a co-author, rewrite it as one line before committing.

This encodes an opinionated style; adjust to taste. Set `severity: block` to hard-reject instead of remind. Note a `bash` rule only sees `git commit -m "…"` — for enforcement across *all* commits (including editor/manual ones), pair it with a native `commit-msg` git hook that reads the message file.
