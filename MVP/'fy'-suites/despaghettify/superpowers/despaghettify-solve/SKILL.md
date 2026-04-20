---
name: despaghettify-solve
description: Routes agents to the Despaghettify implementation task — one DS-ID, sub-waves, pre/post, completion gate. Triggers on run spaghetti-solve-task DS-0xx, despaghettify wave, implement DS row, EXECUTION_GOVERNANCE.
---

# Despaghettify solve (router)

**Do not duplicate procedure here.** The **only** specification for invocation, wave plan, governance cycles, and closure is:

`despaghettify/spaghetti-solve-task.md`

Read that file **in full** and execute it (including **Wave sizing**, **Persist the wave plan**, **`wave_plan.json` + `wave-plan-validate`**, **Resume after interruption**, **External branch updates** — do not improvise elsewhere).

Optional preflight (machine): `python -m despaghettify.tools solve-preflight --ds DS-016` (includes **`wave_sizing`** when open); optional plan check: `python -m despaghettify.tools wave-plan-validate --file …` — see [`../references/CLI.md`](../references/CLI.md).
