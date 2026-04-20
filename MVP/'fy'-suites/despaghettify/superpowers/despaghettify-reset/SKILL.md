---
name: despaghettify-reset
description: Routes agents to the Despaghettify full hub reset — clean workstreams, ephemeral scratch, restore EMPTY input template, then one spaghetti-check pass. Triggers on spaghetti reset, hub clean slate, reset despaghettification input, EMPTY template then check.
---

# Despaghettify reset (router)

**Do not duplicate step order or safety notes here.** The **only** specification for **clean → template → one check** (and how it composes `despaghettify/spaghetti-clean-task.md` with `despaghettify/spaghetti-check-task.md`) is:

`despaghettify/spaghetti-reset-task.md`

Read that file **in full** and execute it. **Reset starts with the clean task** (workstream wipe); then restores `despaghettify/despaghettification_implementation_input.md` from the canonical EMPTY template and runs **one** structure check pass.

**Trigger values** (**C1..C7** bars, **`M7_ref`**) live **only** in `spaghetti-check-task.md` — never copy them into this skill.
