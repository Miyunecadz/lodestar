---
id: design-guidance-on-ui-edits
title: Warn on UI edits when no design guidance is installed
category: quality
severity: warn
recommended: true
stacks: [has-frontend]
event: file
pattern: '\.(tsx|jsx|vue|svelte)$|(^|/)(components?|ui|views|screens|pages|styles)/.*\.(ts|js|css|scss)$'
requires_manifest_missing: designGuidance.installed
surface: agent
emits: rule
---

This workspace has a frontend but **no design guidance installed**, so UI is being generated against framework defaults — the shortest path to output that reads as templated: default type scale, default spacing, default component chrome, a palette nobody chose.

Install it once and this reminder goes away:

```
/lodestar-agents          # tick "UI designer", which resolves the frontend-design skill
/plugin install frontend-design@claude-plugins-official
```

Then delegate UI work to the `ui-designer` agent rather than editing components directly — that agent loads the design skill first, which is the point.

**Why this fires at all:** a `PreToolUse` hook cannot see which skills are loaded in the current session, so it does not try to. It checks the workspace's recorded state instead — `designGuidance.installed` in `.claude/lodestar.manifest.json` — via `requires_manifest_missing`. That makes it **self-silencing**: once guidance is installed and recorded it never fires again, and if you decline the plugin it keeps reminding you rather than going quiet forever. A no-manifest workspace gets the reminder too, since failing toward visible is the whole point of the rule.

Severity is `warn`, not `block`: design quality is a judgement, and a hook that refused UI edits over an unproven aesthetic claim would be wrong. **Surface: `agent`** — it is guidance for the assistant, not a property of a commit.
