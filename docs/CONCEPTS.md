# Lodestar — Core Concepts

Four mental models. Internalize these and the rest of Lodestar is obvious.

---

## 1. When-to-load is a first-class field

Most setups answer "*what* should the AI know?" Lodestar also answers "*when* should it know it?"

Every skill's `description` and every doc's header states the task it belongs to. The AI reads a tiny index of these triggers at startup and pulls the body only when the current task matches. Consequences:

- Planning a feature? The **planning** skill loads. Coding standards do **not**.
- Writing a resolver? The **backend** skill loads. The mobile navigation guide does **not**.

Write triggers as *tasks*, not topics:

> ✅ `description: Use when scoping or spec'ing a feature, BEFORE any code is written.`
> ❌ `description: Documentation about planning.`

A vague trigger is the #1 cause of the wrong thing loading (or nothing). Triggers are the interface; treat them as carefully as an API.

---

## 2. Advisory vs enforced

There are two ways to make the AI behave, and they are not interchangeable.

- **Advisory** (docs, skills): the AI *reads* guidance and *chooses* to follow it. Probabilistic. Perfect for judgment, style, and context — things with no single right answer.
- **Enforced** (hooks, permissions): a rule that *runs or blocks* regardless of what the model remembered. Absolute. Required for anything where a mistake has real, hard-to-undo cost.

> **Docs make the AI *informed*. Guardrails make it *trustworthy*.**

Rule of thumb: if a violation would corrupt data, leak a secret, or break a build, it must be **enforced** — a doc is not enough. If it's about how clean or idiomatic the code is, **advisory** is right, and enforcing it would just add friction.

And enforcement should *teach*: a good block doesn't say "denied," it says "don't edit an applied migration — create a new one with `db:new`." Redirect, don't just refuse.

---

## 3. Map at the top, hands at the bottom

A cross-repo task needs a wide view to plan and a narrow focus to execute. Put each where it belongs:

- **Breadth lives at the top** — in the orchestrator (the main session) and the docs/graph it consults. This is where the whole-system map belongs.
- **Depth lives in the workers** — delegated agents are *narrow roles* with a crisp done-condition and a minimal tool profile.

Why not a broad "backend agent"? Because "do backend work" has no done-condition; unbounded scope is what invites hallucination — not the domain knowledge itself. A role ("write a migration", "review this diff") is bounded, so it stays reliable.

The one exception is the `implementer` role: deliberately broad, but bounded by *one feature's files* — never "the whole repo." Bounded breadth is fine; unbounded breadth is the problem.

---

## 4. The catalog is the product

Lodestar's value isn't the commands — it's the **catalog** of guardrails, agents, and skills, and the discipline of loading them on demand.

- The commands are generic machinery (detect → filter → pick → write → record).
- The catalog is the content, and it's all plain files.

So "publishing Lodestar" means publishing a catalog other people fork. They delete what they dislike, add their own entries, and re-run the pickers. The **manifest** (`.claude/lodestar.manifest.json`) makes a chosen configuration reproducible — it's the lockfile that lets someone copy your exact setup.

Design every catalog entry as if a stranger will read, judge, and adapt it. Because they will.
