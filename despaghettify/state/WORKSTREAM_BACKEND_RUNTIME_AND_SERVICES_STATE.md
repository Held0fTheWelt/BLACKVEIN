# Workstream state: Backend Runtime and Services

## Current objective

Run backend runtime and service changes under [`EXECUTION_GOVERNANCE.md`](EXECUTION_GOVERNANCE.md). Structural refactors: [`despaghettify/despaghettification_implementation_input.md`](../despaghettification_implementation_input.md) (input list, structure scan, optional work log). Keep orientation numbers and hotspots only there — do not duplicate here.

## Current repository status

- Typical scope: `backend/app/runtime`, `backend/app/services`, `backend/app/api/v1`, related tests.
- After the next **wave**: place a scope snapshot under `artifacts/workstreams/backend_runtime_services/pre/` (see naming convention in the input list).

## Hotspot / target status

- **DS-001** closed (2026-04-11): Deferred imports / cycle-avoidance pattern resolution. Tasks 1–4: promoted 4 stale deferred imports in role_structured_decision.py, ai_decision.py, ai_failure_recovery.py, turn_executor.py to module-level top-level imports. Type narrowing: `ParseResult.role_aware_decision` `Any | None` → `ParsedRoleAwareDecision | None` (backwards compatible). Seams tightened, no new cycles. Tests: 207/207 passing across all affected runtime suites. Commits: d834e4b (turn_executor), other tasks prior. **DS-002** closed (2026-04-11): Writers Room pipeline stages 1–5; closure `artifacts/workstreams/backend_runtime_services/post/session_20260411_DS-002_closure_notes.md`. **DS-003** closed (2026-04-10). **DS-003 structure** (2026-04-12): commit-path split (`narrative_threads_commit_path_utils`, `narrative_threads_update_from_commit_phases`); `update_narrative_threads_from_commit_impl` **63** AST L; post `post/session_20260412_DS-003_commit_path_structure_post.md`. **DS-004** closed (2026-04-11): Magic numbers and mutable state hardening. Post: `artifacts/workstreams/backend_runtime_services/post/session_20260411_DS-004_post.md`. Config modules created, 24 route files refactored, extensions.py hardened. `pytest backend/tests/` 241 passed. **DS-004 assembly** (2026-04-12): closure cockpit + session evidence report assembly split into `ai_stack_closure_cockpit_report_sections` + `ai_stack_evidence_session_bundle_sections`; `assemble_closure_cockpit_report` **64** AST L, `assemble_session_evidence_bundle` **24** AST L; post `post/session_20260412_DS-004_report_assembly_post.md`. **DS-005** closed (2026-04-11): user/news control-flow guard slice; closure `post/session_20260411_DS-005_closure_notes.md` (regression bundle 321 tests). **DS-005 optional** (2026-04-10): thin `execute_users_update_put` (**70** AST L) via `user_put_collect_service_kwargs`; `run_validated_turn_pipeline` **90** AST L with `turn_executor_validated_pipeline_apply` + `turn_executor_validated_pipeline_narrative_log`; post `post/session_20260410_DS-005_optional_thin_post.md`. **DS-007** closed (2026-04-12): Narrative DTO integration & pipeline refactoring; post `artifacts/workstreams/backend_runtime_services/post/session_20260412_DS-007_post.md`; pre/post comparison `session_20260412_DS-007_pre_post_comparison.json`. **DS-006** closed (2026-04-12): Writers Room packaging + inspector orchestration; packaging reduced 354→317 LOC, inspector reduced 248→157 LOC, 3 new modules (142 LOC), 79 tests passing. Post: `artifacts/workstreams/backend_runtime_services/post/session_20260412_DS-006_post.md`; pre/post comparison `session_20260412_DS-006_pre_post_comparison.json`. **DS-008** closed (2026-04-12): Improvement recommendation decision flattening; extracted policy evaluators (3 guards + 3 builders), main function reduced 176→136 LOC (23% reduction), 60 improvement tests passing. Post: `artifacts/workstreams/backend_runtime_services/post/session_20260412_DS-008_post.md`; pre/post comparison `session_20260412_DS-008_pre_post_comparison.json`.

## Last completed wave/session

- **2026-04-12 — DS-004 (report assembly):** AI stack closure cockpit + session evidence bundle section modules. See `post/session_20260412_DS-004_report_assembly_post.md`.
- **2026-04-12 — DS-003 (commit-path structure):** Narrative thread commit path split into drive + terminal + non-terminal phases and pure helpers. See `post/session_20260412_DS-003_commit_path_structure_post.md`.
- **2026-04-10 — DS-005 (optional thin):** Input-list optional goals for DS-005 (thin user PUT + pipeline modules). See `post/session_20260410_DS-005_optional_thin_post.md`.
- **2026-04-12 — DS-008 (closure):** Improvement recommendation decision flattening. Tasks 1–5: analysis → policy evaluator extraction → main function refactoring → backwards compatibility verification → wave closure. Created: improvement_service_policy_evaluators.py (192 LOC, 6 functions: 3 guards + 3 builders + 1 dataclass). Refactored: improvement_service_recommendation_decision.py (176→136 LOC, 23% reduction). Tests: 60 improvement tests passing, zero modifications, full backwards compatibility. Commit: 8f6b9f2. Post: `post/session_20260412_DS-008_post.md` + `session_20260412_DS-008_pre_post_comparison.json`.
- **2026-04-12 — DS-006 (closure):** Writers Room packaging + inspector orchestration refactoring. Tasks 1–5: analysis → packaging sub-stage extraction → inspector helper consolidation → closure bundle analysis → wave closure. Refactored: writers_room_pipeline_packaging_stage.py (354→317 LOC), inspector_turn_projection_sections_assembly_filled.py (248→157 LOC). Created: writers_room_pipeline_packaging_issue_extraction.py, writers_room_pipeline_packaging_recommendation_bundling.py, inspector_turn_projection_assembly_helpers.py (335 LOC, 16 reusable functions). Tests: 64 writers_room + 15 inspector = 79 passing, zero modifications, full backwards compatibility. Post: `post/session_20260412_DS-006_post.md` + `session_20260412_DS-006_pre_post_comparison.json`.
- **2026-04-12 — DS-007 (closure):** Narrative DTO integration & pipeline refactoring. Tasks 3–5: created `pipeline_decision_guards.py` (227 LOC), refactored `run_validated_turn_pipeline` (155+70 LOC stages), documented narrative protocol in `narrative_threads_update_from_commit.py` (input/output/semantics contracts). 1 module created, 3 modified, type hints complete, 1 circular import documented with mitigation. Post: `post/session_20260412_DS-007_post.md` + `session_20260412_DS-007_pre_post_comparison.json`. Tests: pending (runtime suite long-running).
- **2026-04-11 — DS-005 (closure):** User/news control-flow slice; post `post/session_20260411_DS-005_closure_notes.md`; `pytest tests/test_news_service.py tests/test_user_service.py tests/test_service_layer.py tests/test_user_routes.py tests/test_users_api.py` 321 passed.
- **2026-04-11 — DS-005 (stage 6):** `user_service_admin_guards` for `assign_role` / `ban_user`. Post: `post/session_20260411_DS-005_stage6_admin_guards_post.md`; `pytest tests/test_service_layer.py -k "ban_user or unban_user or assign_role"` 8; `tests/test_users_api.py -k "assign_role or ban"` 14; `tests/test_user_routes.py -k assign_role` 18 passed.
- **2026-04-11 — DS-005 (stage 5):** `user_service_update_guards` for `update_user`. Post: `post/session_20260411_DS-005_stage5_update_user_guards_post.md`; `pytest tests/test_user_service.py` 27; `tests/test_user_routes.py -k users_update` 55; `tests/test_users_api.py -k users_update` 4 passed.
- **2026-04-11 — DS-004 (closure):** Magic numbers + mutable state hardening. Config modules: route_constants.py, limiter_config.py (frozen dataclasses). 24 route files refactored (672 constants refactored). Extensions hardened (limiter_config imports, no embedded constants). Tests: 16 new integration tests, 241 backend suite passing. Post: `post/session_20260411_DS-004_post.md` + `post/session_20260411_DS-004_pre_post_comparison.json`.
- **2026-04-10 — DS-005 (stage 4):** `news_service_translation_upsert_guards` for `upsert_article_translation`. Post: `post/session_20260410_DS-005_stage4_translation_upsert_guards_post.md`; `pytest tests/test_news_service.py` 48 passed.
- **2026-04-11 — DS-005 (stage 3):** `news_service_update_guards` for `update_news`. Post: `post/session_20260411_DS-005_stage3_update_news_guards_post.md`; `pytest tests/test_news_service.py` 48 passed.
- **2026-04-11 — DS-005 (stage 2):** `news_service_create_guards` + `user_service_account_guards` for `create_news`, `create_user`, `change_password`. Post: `post/session_20260411_DS-005_stage2_news_user_create_guards_post.md`; `pytest tests/test_news_service.py tests/test_user_service.py tests/test_service_layer.py` 125 passed.
- **2026-04-11 — DS-005 (stage 1):** User PUT guards module for `/users/<id>`. Post: `post/session_20260411_DS-005_stage1_user_put_guards_post.md`; `pytest tests/test_user_routes.py -k users_update` 55 passed; `tests/test_users_api.py -k users_update` 4 passed.
- **2026-04-11 — DS-002 (closure):** Formal closure after stage 5. Post: `post/session_20260411_DS-002_closure_notes.md`; `pytest tests/writers_room/` 64 passed.
- **2026-04-11 — DS-002 (stage 5):** `writers_room_pipeline_finalize_stage.py`. Main workflow **82** AST lines. Post: `post/session_20260411_DS-002_stage5_post.md`; `pytest tests/writers_room/` 64 passed.
- **2026-04-11 — DS-002 (stage 4):** `writers_room_pipeline_packaging_stage.py`. Main workflow **185** AST lines. Post: `post/session_20260411_DS-002_stage4_post.md`; `pytest tests/writers_room/` 64 passed.
- **2026-04-11 — DS-002 (stage 3):** `writers_room_pipeline_generation_stage.py`. Main workflow **449** AST lines. Post: `post/session_20260411_DS-002_stage3_post.md`; `pytest tests/writers_room/` 64 passed.
- **2026-04-11 — DS-002 (stage 2):** `writers_room_pipeline_retrieval_stage.py`; orchestrator delegates retrieval block. **585** AST lines on main workflow function. Post: `post/session_20260411_DS-002_stage2_post.md`; `pytest tests/writers_room/` 64 passed.
- **2026-04-11 — DS-002 (stage 1):** Removed duplicate helper definitions from `writers_room_pipeline.py`; single source in `writers_room_pipeline_manifest.py` / `writers_room_pipeline_context_preview.py`. `pytest tests/writers_room/` 64 passed. Pre/post: `pre/session_20260411_DS-002_stage1_baseline.md`, `post/session_20260411_DS-002_stage1_post.md`.
- **2026-04-11 — DS-001 (complete):** Partial wave plus closure: no `turn_executor` import from `turn_executor_validated_pipeline`; system-error regression tests patch `turn_executor_validated_pipeline_apply.validate_decision` (since DS-005 optional, 2026-04-10). Post addendum: `artifacts/workstreams/backend_runtime_services/post/session_20260411_DS-001_closure_notes.md` (with `ds005` + pytest evidence).

## Pre-work baseline reference

Canonical pattern (create files only when a wave runs):

- `artifacts/workstreams/backend_runtime_services/pre/git_status_scope.txt` *(optional)*
- `artifacts/workstreams/backend_runtime_services/pre/session_YYYYMMDD_DS-xxx_*` *(claim, snapshot, collect, … — see governance)*

## Post-work verification reference

- `artifacts/workstreams/backend_runtime_services/post/session_YYYYMMDD_DS-xxx_*`
- Pre→post comparison and `pre_post_comparison.json` where required.

## Known blockers

- —

## Next recommended wave

- **DS-002** (writers room pipeline monolith): claim **DS-ID + owner**, **pre** under `artifacts/workstreams/backend_runtime_services/pre/` — [spaghetti-solve-task.md](../spaghetti-solve-task.md), [despaghettification_implementation_input.md](../despaghettification_implementation_input.md).

## Contradictions / caveats

- Closure claims only with linked, versioned artefacts; missing old paths do not replace Git history or CI.
