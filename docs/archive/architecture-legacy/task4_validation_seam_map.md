# Task 4 — Validation seam map (baseline vs hardened)

This document is the **working validation seam map** for Task 4 maturity hardening. It records what was already strong before Task 4 additions, what was weak, and where end-to-end truth was intentionally extended. It does **not** change product semantics; it describes test and documentation coverage.

## Strong pre-Task-4 coverage

- **Staged Runtime (selected happy paths):** `backend/tests/runtime/test_runtime_staged_orchestration.py` — canonical `slm_then_llm`, `slm_only` (synthesis skipped), legacy opt-out (`runtime_staged_orchestration: false`), presence of `runtime_stage_traces`, `routing_evidence`, `operator_audit`, and one guard/success check on SLM-only.
- **Operator audit builders (unit-level):** `backend/tests/runtime/test_operator_audit.py` — packaging vs `no_eligible` skip disambiguation, timeline ordering, bounded-surface audit construction.
- **Routing evidence / Task 2F diagnostics:** `backend/tests/runtime/test_model_routing_evidence.py`, `backend/tests/runtime/test_ai_turn_executor_routing.py` — including `no_eligible_spec_selection` and execution alignment fields.
- **Stage gate logic (pure functions):** `backend/tests/runtime/test_runtime_ai_stages_contracts.py` — `compute_needs_llm_synthesis` for parse-failure forcing vs `slm_sufficient`.
- **Bootstrap and inventory:** `backend/tests/runtime/test_model_inventory_bootstrap.py` — `create_app` with bootstrap on/off subclasses, staged routing requests after bootstrap, surface coverage validation, stale-spec risk on legacy-only registration, no-eligible setup classification, Writers-Room spec shape (`revision_synthesis`, `degrade_targets`).
- **Writers-Room / Improvement HTTP surfaces:** `backend/tests/test_writers_room_routes.py`, `backend/tests/test_improvement_routes.py` — `task_2a_routing`, per-stage `routing_evidence`, `operator_audit` with correct `surface`, deterministic recommendation base vs model-assisted interpretation on Improvement.
- **Agent orchestration (supervisor path):** `backend/tests/runtime/test_ai_turn_executor.py` — multi-subagent execution and priority over tool loop; **operator audit shape for staged preemption was not previously asserted.**
- **Tool loop (non-staged narrative):** `backend/tests/runtime/test_tool_loop.py` — ordering, limits, policy rejection, with staged prelude adapter support for early stages.

## Weak or missing pre-Task-4 coverage (addressed by Task 4)

- **Degraded orchestration paths in full `execute_turn_with_ai`:** `degraded_early_skip_then_synthesis` and `degraded_parse_forced_synthesis` (`final_path` + honest trace/summary) were not integrated end-to-end.
- **Preempted staged pipeline audit:** `staged_pipeline_preempted: agent_orchestration` → `build_runtime_operator_audit_preempted` was not asserted on `AIDecisionLog.operator_audit`.
- **Staged path + tool loop continuation:** No test that a **synthesis** stage returns a tool request, then the host tool runs, then `_generate_with_runtime_policy` finalizes (post-staged tool loop ordering).
- **Cross-surface contract:** No single place comparing stable `operator_audit` / `routing_evidence` key semantics across Runtime, Writers-Room, and Improvement.
- **Improvement missing provider adapter:** `_run_routed_bounded_call` skip path was not directly covered at module level.
- **E2E session lifecycle (`test_e2e_god_of_carnage_full_lifecycle.py`):** Exercises `dispatch_turn` without asserting Task 1–3 trace/audit fields (session default is not a staged-audit proof). Task 4 **does not** claim full God-of-Carnage E2E audit truth; staged proof remains in dedicated runtime tests and HTTP tests above.

## Cross-surface drift risks (mitigation strategy)

- Shared **meaning** for `audit_schema_version`, top-level `operator_audit` keys, timeline entry shape, and core `routing_evidence` fields is enforced by **contract tests** (see `task4_hardening_gates.md`).
- Intentional differences remain: Runtime `audit_summary` includes `final_path` / synthesis gate fields; bounded surfaces include `interpretation_layer` instead. Contract tests **require** shared keys only where all surfaces actually emit them.

## Documentation alignment

- Architecture truth for routing and runtime authority remains in `llm_slm_role_stratification.md` and `ai_story_contract.md`, updated in Task 4 to reference gates and limits.
- **No claim** of distributed immutable audit or platform-grade telemetry beyond derived, bounded JSON surfaces.
