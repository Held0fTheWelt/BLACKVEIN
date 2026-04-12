---
name: despaghettify-autonomous-agent
description: Routes agents to the Despaghettify autonomous loop — Step 0 backlog drain uses slice → check --out → autonomous-advance backlog-implement (--check-json repo-relative); only after the DS row is closed in the input list, backlog-solve; then main check→solve until trigger clears or hard stop.
---

# Despaghettify autonomous agent (router)

**Do not duplicate the loop or policy here.** The **only** specification for the **check → solve → check** macro loop, success conditions, error scope, and anti-stall rules is:

`despaghettify/spaghetti-autonomous-agent-task.md`

Read that file **in full** and execute it. Each **check** pass must follow `despaghettify/spaghetti-check-task.md` (after reading numeric policy in `despaghettify/spaghetti-setup.md`). Each **solve** pass must follow `despaghettify/spaghetti-solve-task.md` for **one** **DS-*** at a time.

**Machine guards (must):** `autonomous-init` at session start (repo root: `python -m despaghettify.tools …`). **Step 0 — while a backlog DS row is open:** after each implementation slice, run hub **`check … --out <file>`**, then **`autonomous-advance --kind backlog-implement --ds DS-0xx --check-json <path>`** where `<path>` is **relative to the repository root**. **Only after** the DS goal is met and the row is **closed** in `despaghettification_implementation_input.md`: **`autonomous-advance --kind backlog-solve --ds DS-0xx`** (that advance **exit 2** if the row is still open — **HARD_STOP**). For all other macro steps, `autonomous-advance` as in the task doc (**exit 2** → **HARD_STOP**). Run **`autonomous-verify`** between waves as in the task doc. Regenerate **`despaghettify/spaghetti-setup.json`** with **`setup-sync`** after edits to **`spaghetti-setup.md`** (JSON is derived only, not hand-maintained).

Optional CLI: `python -m despaghettify.tools check` | `open-ds` | `solve-preflight --ds DS-0xx` — see [`../references/CLI.md`](../references/CLI.md).
