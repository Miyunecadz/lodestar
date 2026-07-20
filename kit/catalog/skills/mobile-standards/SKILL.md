---
name: mobile-standards
description: Use when editing the mobile repo (REPO) — React Native screens, navigation, NativeWind, or push/Firebase.
stacks: [react-native]
---

# Mobile standards (REPO)

Conventions live in the docs, not here. Read **`docs/REPO/conventions.md`** and **`docs/REPO/architecture/`** before editing.

**Key reminders:**

- **Env tiers:** environments are configured via **react-native-config** — use it rather than hard-coding per-environment values.
- **Native deps:** patch native-dependency changes with **patch-package** (never hand-edit inside `node_modules` without capturing it as a patch).
- Screens/navigation are React Native, styled with NativeWind; push notifications go through Firebase.

Details and the actual screen/navigation layout are in `docs/REPO/` — go there.
