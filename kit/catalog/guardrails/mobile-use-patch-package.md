---
id: mobile-use-patch-package
title: Persist node_modules edits with patch-package
category: dependencies
severity: block
recommended: false
stacks: [react-native]
event: file
pattern: '(^|/)node_modules/'
emits: rule
---

Direct edits to `node_modules` vanish on the next reinstall. This repo uses patch-package — make the change, then run `npx patch-package <pkg>` to persist it into `patches/`, which is reapplied automatically on postinstall.
