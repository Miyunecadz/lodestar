---
id: protect-generated-files
title: Protect generated and binary artifacts
category: generated
severity: block
recommended: true
stacks: [all]
event: file
pattern: '(dump\.rdb$|graph\.(json|html)$|GRAPH_REPORT\.md$|/(android|ios)/.*/build/)'
emits: hookify
---

These paths are generated or binary artifacts — the redis `dump.rdb`, Graphify output (`graph.json` / `graph.html` / `GRAPH_REPORT.md`), and native `android`/`ios` build output. Editing them is meaningless or actively harmful; regenerate from their source instead (rerun graphify, rebuild the app, etc.).
