---
name: despaghettify-check
description: Routes agents to the Despaghettify structure / spaghetti analysis task — M7 triggers, scan rules, Open hotspots, input list updates. Triggers on spaghetti check, M7 scan, structure scan refresh, despaghettify analysis track, update open hotspots.
---

# Despaghettify check (router)

**Do not duplicate numeric policy here.** **Bars**, **M7 weights**, and **`M7_ref`** are **only** in:

`despaghettify/spaghetti-setup.md`

**Procedure** (scan steps, **Open hotspots**, DS rules, Mermaid) is **only** in:

`despaghettify/spaghetti-check-task.md`

Read **both** in full and execute the check task. Optional machine input first (does not replace the task docs):

```bash
python -m despaghettify.tools check
```

CLI reference: [`../references/CLI.md`](../references/CLI.md).
