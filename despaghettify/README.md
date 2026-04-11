# Despaghettify

Central place for the **despaghettification** and **structure / spaghetti-check cycle**, including the **execution-governance state hub** under [`state/`](state/README.md).

| File | Role |
|------|------|
| [`despaghettification_implementation_input.md`](despaghettification_implementation_input.md) | Canonical **input list**, coordination of structural IDs, structure-scan table, implementation order, work log (templates). |
| [`spaghetti-check-task.md`](spaghetti-check-task.md) | **Analysis track:** AST + architecture spaghetti check; **always** maintain § *Latest structure scan* (including **M7** and category breakdown); when the trigger policy fires, maintain **Information input list**, **Recommended implementation order** (phase table **+ mandatory Mermaid** `flowchart` per §3), and **DS-ID → workstream** (no code changes). |
| [`spaghetti-solve-task.md`](spaghetti-solve-task.md) | **Implementation track:** review or revise order, then implement **wave by wave** until a factual **success** message is justified (pre/post, completion gate); **open hotspots** in the input list are cleared or updated when waves fix those known structure issues. |
| [`spaghetti-clean-task.md`](spaghetti-clean-task.md) | **Deep clean:** delete **all** session files under `state/artifacts/workstreams/<slug>/pre|post/` (every slug), recreate empty folders per [`WORKSTREAM_INDEX.md`](state/WORKSTREAM_INDEX.md); optional same-pass ephemeral cleanup as reset. **Run before** a full reset when workstream evidence should be cleared. |
| [`spaghetti-reset-task.md`](spaghetti-reset-task.md) | **Reset track:** runs **`spaghetti-clean-task.md`** first (workstream wipe), then listed ephemeral dirs (MkDocs/pytest/coverage scratch, **despag-adjacent** `backend/var/*` and `world-engine/app/var/runs`, hub `*.tmp`/`*.bak` under `despaghettify/` except `state/` and `templates/` if not already done in clean), reset the input list from [`templates/despaghettification_implementation_input.EMPTY.md`](templates/despaghettification_implementation_input.EMPTY.md), then run **`spaghetti-check-task.md` once** to refill the scan (and DS/phases only if the trigger policy is met). |
| [`spaghetti-add-task-to-meet-trigger.md`](spaghetti-add-task-to-meet-trigger.md) | **Targeted planning:** pick **one** of **C1..C7**, add or extend **DS-*** rows in the input list to bring that category **under** its trigger once implemented, then **re-sort the whole** § *Recommended implementation order* (dependencies, parallelism, Mermaid). Markdown-only; does not replace a full spaghetti-check for fresh metrics. |

**Tools** (remain under `tools/`): `spaghetti_ast_scan.py`, `ds005_runtime_import_check.py`.

**Governance / pre–post:** [`state/README.md`](state/README.md), [`state/EXECUTION_GOVERNANCE.md`](state/EXECUTION_GOVERNANCE.md).

**Language:** All documents under `despaghettify/` are maintained in **English**, consistent with project documentation policy.
