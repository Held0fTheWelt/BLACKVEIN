# Despaghettify automation workflow (reference)

```text
                    ┌─────────────────────┐
                    │ despaghettify-      │
                    │ orchestrate         │
                    └──────────┬──────────┘
    ┌────────┬────────┬────────┬────────┬────────┬────────┐
    ▼        ▼        ▼        ▼        ▼        ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ check  │ │ solve  │ │add-task│ │ auto   │ │ clean  │ │ reset  │
│ skill  │ │ skill  │ │ skill  │ │ agent  │ │ skill  │ │ skill  │
└───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
    │          │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼          ▼
spaghetti-  spaghetti-  spaghetti- spaghetti- spaghetti- spaghetti-
check-task  solve-task  add-task-  autonomous clean-task reset-task
.md         .md         to-meet-   -agent-
                        trigger.md task.md
```

- **check** → updates `despaghettification_implementation_input.md` scan always; DS/phases only when trigger policy fires.
- **solve** → requires `run spaghetti-solve-task DS-0xx`; autonomous sub-waves until that DS is CLOSED.
- **add-task** → one target category **C1–C7**; markdown-only planning pass on the input list.
- **autonomous-agent** → `run spaghetti-autonomous-agent-task`; **Step 0:** closes **open** input-list **DS-*** with **solve** before the first full **check**; then chains **check** and **solve** until **setup** conditions clear and no open DS rows remain, or hard stop / advisory anti-stall.
- **clean** → wipes all `state/artifacts/workstreams/**/pre|post` session files (per slug) and optional ephemeral dirs; **does not** reset the input list or run a check.
- **reset** → runs **clean** (at least workstream wipe), restores the input list from the EMPTY template, then **one** **check** pass.

After a **solve** closes a large DS, optionally run **check** again to refresh metrics and hotspots.
