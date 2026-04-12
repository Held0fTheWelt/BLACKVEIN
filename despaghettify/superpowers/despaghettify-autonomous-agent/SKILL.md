---
name: despaghettify-autonomous-agent
description: Routes agents to the Despaghettify autonomous loop — drain open DS backlog from the input list first (solve only), then repeated check then solve until setup trigger clears or hard stop. Triggers on run spaghetti-autonomous-agent-task, autonomous despag loop, backlog then check implement check until M7 conditions.
---

# Despaghettify autonomous agent (router)

**Do not duplicate the loop or policy here.** The **only** specification for the **check → solve → check** macro loop, success conditions, error scope, and anti-stall rules is:

`despaghettify/spaghetti-autonomous-agent-task.md`

Read that file **in full** and execute it. Each **check** pass must follow `despaghettify/spaghetti-check-task.md` (after reading numeric policy in `despaghettify/spaghetti-setup.md`). Each **solve** pass must follow `despaghettify/spaghetti-solve-task.md` for **one** **DS-*** at a time.

**Machine guards (must):** `autonomous-init` at session start; after each documented macro step `autonomous-advance` (exit **2** → **HARD_STOP**); run `autonomous-verify` between waves as in the task doc. Regenerate **`despaghettify/spaghetti-setup.json`** with **`setup-sync`** after edits to **`spaghetti-setup.md`** (JSON is derived only, not hand-maintained).

Optional CLI: `python -m despaghettify.tools check` | `open-ds` | `solve-preflight --ds DS-0xx` — see [`../references/CLI.md`](../references/CLI.md).
