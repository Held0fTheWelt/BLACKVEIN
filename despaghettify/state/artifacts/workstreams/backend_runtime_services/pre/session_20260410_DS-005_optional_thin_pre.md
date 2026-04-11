# Pre — DS-005 optional wave (thin PUT + validated pipeline modules)

**Date:** 2026-04-10  
**Workstream:** `backend_runtime_services`  
**Scope:** Optional goals from input list row DS-005 — thin `execute_users_update_put`; companion modules for `run_validated_turn_pipeline` early stages + narrative logging.

**Baseline (from prior scan / input list):**

- `user_routes_users_update.py` — `execute_users_update_put` ~152 AST lines (inline validation + role branches).
- `turn_executor_validated_pipeline.py` — `run_validated_turn_pipeline` ~143 AST lines (monolithic stages 1–6 + `_log_narrative_outcomes`).

**Gates planned:** `python tools/ds005_runtime_import_check.py`; `pytest` user `users_update` selection; `test_turn_executor.py::test_execute_turn_system_error_path` (monkeypatch target moves with code).
