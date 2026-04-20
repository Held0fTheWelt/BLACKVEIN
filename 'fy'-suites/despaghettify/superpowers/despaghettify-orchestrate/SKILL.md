---
name: despaghettify-orchestrate
description: Routes agents to the correct Despaghettify task markdown — check vs solve vs add-task vs autonomous loop vs clean vs reset. Triggers on despaghettify orchestration, spaghetti pipeline, M7 scan then implement, run spaghetti-autonomous-agent-task, which DS next, wipe artefacts only or full hub reset.
---

# Despaghettify orchestrate (router)

**Do not duplicate policy or checklists here.** Pick **one** track and follow **only** that task file end-to-end:

| Intent | Open and follow (single source) |
|--------|----------------------------------|
| Retune **C1..C7** bars, **M7** weights, or **`M7_ref`** | `despaghettify/spaghetti-setup.md` |
| Structure scan / **M7** / hotspots / DS table when triggers fire | `despaghettify/spaghetti-check-task.md` |
| Implement one **DS-*** (with `run spaghetti-solve-task DS-nnn`) | `despaghettify/spaghetti-solve-task.md` |
| **Autonomous loop:** solve **open** input-list **DS-*** backlog **first**, then check → solve → check until **setup** conditions clear or hard stop | `despaghettify/spaghetti-autonomous-agent-task.md` |
| Plan new **DS-*** rows for one **C1–C7** category | `despaghettify/spaghetti-add-task-to-meet-trigger.md` |
| Wipe **only** workstream `pre`/`post` artefacts (+ optional ephemeral cleanup) | `despaghettify/spaghetti-clean-task.md` |
| Full hub reset (clean + EMPTY template + **one** check pass) | `despaghettify/spaghetti-reset-task.md` |

**Trigger values** (**C1..C7** bars, **weights**, **`M7_ref`**) live **only** in `spaghetti-setup.md` — never copy them into this skill.

Optional CLI helpers (metrics / listing / preflight): [`references/CLI.md`](../references/CLI.md) — helpers only, not a second policy.

Input list: `despaghettify/despaghettification_implementation_input.md`.
