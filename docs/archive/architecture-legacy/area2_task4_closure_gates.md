# Area 2 Task 4 Closure Gates — Validation Hardening

This document lists the closure gates for Area 2 Task 4 (validation hardening).
Canonical command surface: `area2_validation_commands` in `backend/app/runtime/area2_validation_commands.py`.
Gate table: `area2_task4_closure_gates.md`. Closure report: `area2_validation_hardening_closure_report.md`.

## Gate Table

| Gate | Description |
|------|-------------|
| G-T4-01 | Runtime, Writers-Room, and Improvement each have proven integration contract truth. |
| G-T4-02 | Named profiles, bootstrap on/off, and real create_app bootstrap-on staged path. |
| G-T4-03 | compact_operator_comparison grammar and cross-surface contract regression layers. |
| G-T4-04 | Degraded Runtime paths and Improvement missing-adapter honesty. |
| G-T4-05 | Audit schema and routing-evidence stable key expectations. |
| G-T4-06 | testing-setup.md embeds the exact canonical Task 4 invocation from code. |
| G-T4-07 | Full proof module list passes via subprocess (excludes gate orchestrator). |
| G-T4-08 | Required architecture docs reference every G-T4 gate and the command surface. |

## Command Surface Reference

`area2_validation_commands` (`AREA2_TASK4_FULL_CLOSURE_PYTEST_MODULES`, `area2_task4_full_closure_pytest_invocation`)
in `backend/app/runtime/area2_validation_commands.py`.
