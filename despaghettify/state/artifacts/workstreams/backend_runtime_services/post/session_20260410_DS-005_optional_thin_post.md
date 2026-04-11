# Post — DS-005 optional wave (thin PUT + validated pipeline modules)

**Date:** 2026-04-10  
**Workstream:** `backend_runtime_services`

## Code changes

1. **`user_routes_users_update_guards.py`** — New `user_put_collect_service_kwargs`: merges username/email, format-only validation, `preferred_language`, admin-other and self `role` / `role_level` branches (same semantics as inlined route).
2. **`user_routes_users_update.py`** — `execute_users_update_put` delegates auth, password rejection, and kwargs collection to guards; handler focuses on service call, activity log, privilege log, response.
3. **`turn_executor_validated_pipeline_apply.py`** — New: `validated_turn_validate_construct_and_apply` (validate → construct deltas → apply + matching `event_log` entries).
4. **`turn_executor_validated_pipeline_narrative_log.py`** — New: `log_narrative_outcomes_after_commit` (formerly `_log_narrative_outcomes`).
5. **`turn_executor_validated_pipeline.py`** — Orchestrates apply module, `resolve_narrative_commit`, narrative log helper, completion log, `TurnExecutionResult`.
6. **`package_classification.py`** — Register new runtime root modules.
7. **`tools/ds005_runtime_import_check.py`** — Import new modules before main pipeline in frozen order.
8. **`backend/tests/runtime/test_turn_executor.py`** — Monkeypatch `turn_executor_validated_pipeline_apply.validate_decision` (patch site moved with extraction).

## AST (post)

- `execute_users_update_put`: **70** AST lines (`ast` count).
- `run_validated_turn_pipeline`: **90** AST lines.

## Verification

- `python tools/ds005_runtime_import_check.py` — exit **0** (all `import_ok`).
- `python -m pytest backend/tests/test_user_routes.py -k users_update backend/tests/test_users_api.py -k users_update -q` — **59** passed.
- `python -m pytest backend/tests/runtime/test_turn_executor.py::test_execute_turn_system_error_path -q` — passed.

See `session_20260410_DS-005_optional_thin_pre_post_comparison.json` for pre→post summary.
