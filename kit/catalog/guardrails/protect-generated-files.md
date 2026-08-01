---
id: protect-generated-files
title: Protect generated and binary artifacts
category: generated
severity: block
recommended: true
stacks: [all]
event: file
pattern: '(dump\.rdb$|graph\.(json|html)$|GRAPH_REPORT\.md$|/(android|ios)/.*/build/)'
surface: agent
emits: rule
---

These paths are generated or binary artifacts — the redis `dump.rdb`, Graphify output (`graph.json` / `graph.html` / `GRAPH_REPORT.md`), and native `android`/`ios` build output. Editing them is meaningless or actively harmful; regenerate from their source instead (rerun graphify, rebuild the app, etc.).

---

**Surface: `agent` only, deliberately.** A commit-time version of this rule would fight [[lodestar-freshness]]: the graph-refresh hook *intentionally* rebuilds and stages `graph.json` / `GRAPH_REPORT.md` into the same commit, so blocking those paths at commit time would break the lockstep map. Keeping generated artifacts out of history is `.gitignore`'s job, not this rule's.
