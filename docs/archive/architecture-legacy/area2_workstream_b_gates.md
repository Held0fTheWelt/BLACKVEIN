# Area 2 Workstream B Gates — Reproducibility

This document lists the Workstream B reproducibility gates for Area 2.
Canonical command surface: `area2_validation_commands` in `backend/app/runtime/area2_validation_commands.py`.

## Gate Table

| Gate | Description |
|------|-------------|
| G-B-01 | Named profiles map deterministically to bootstrap and registry expectations. |
| G-B-02 | Bootstrap-off vs healthy bootstrap-on behaviors are both testable. |
| G-B-03 | Explicit setup scripts and requirements paths exist for clean installs. |
| G-B-04 | Test requirements explicitly include pytest stack; static file graph is valid. |
| G-B-05 | Test-profile stability under various configurations. |
| G-B-06 | Validation-command reality: documented invocations match code. |
| G-B-07 | Listed docs reference every G-B id and area2_validation_commands. |

## Command Reference

`area2_validation_commands` — `AREA2_DUAL_CLOSURE_PYTEST_MODULES`, `area2_dual_closure_pytest_invocation`.
