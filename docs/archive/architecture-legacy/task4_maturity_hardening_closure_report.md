# Task 4 — Maturity hardening closure report

## Verdict: **PASS**

Task 4 completed within scope: validation seam map, explicit hardening gates, stronger Runtime/bootstrap/cross-surface/negative-path/drift tests, and aligned architecture documentation. **No routing policy redesign, no `StoryAIAdapter` redesign, and no changes to guard/commit/reject or authoritative runtime mutation rules** were introduced.

## Gate outcomes (see `task4_hardening_gates.md`)

| Gate | Result |
|------|--------|
| G-RUN-01 — Canonical staged success | PASS (existing + cross-surface runtime contract) |
| G-RUN-02 — SLM-only | PASS (`test_runtime_staged_orchestration`) |
| G-RUN-03 — Degraded paths | PASS (`test_runtime_task4_hardening`) |
| G-RUN-04 — Orchestration preempted audit | PASS (`test_agent_orchestration_executes_real_separate_subagents_and_logs_trace` asserts preempted audit schema, `note_deep_traces`, single `orchestration_preempted` timeline row) |
| G-RUN-05 — Legacy single-pass | PASS (`test_runtime_staged_orchestration`) |
| G-RUN-06 — Authority / guard path | PASS (existing staged guard test + success paths unchanged) |
| G-TOOL-01 — Staged synthesis → tool loop → finalize | PASS (`test_staged_synthesis_tool_request_then_tool_loop_finalizes_via_follow_up_generate`) |
| G-WR-01 | PASS (`test_cross_surface_operator_audit_contract`) |
| G-IMP-01 | PASS (same module) |
| G-BOOT-01 | PASS (`test_bootstrap_staged_runtime_integration`) |
| G-BOOT-02 | PASS (existing `test_model_inventory_bootstrap` / `TestingConfig`) |
| G-INV-01 | PASS (`test_model_inventory_bootstrap`) |
| G-XS-01 | PASS (`test_cross_surface_operator_audit_contract`) |
| G-NEG-01 | PASS (empty registry, preflight-only skip, synthesis phase with `no_eligible_spec_selection` + fallback to passed adapter) |
| G-NEG-02 | PASS (`test_improvement_task2a_routing_negative`) |
| G-DRIFT-01 | PASS (`test_runtime_drift_resistance`) |
| G-DOC-01 | PASS (this report + `ai_story_contract.md` + `llm_slm_role_stratification.md` + seam map + gates) |

## Files changed (added or modified)

### Added

- `docs/architecture/task4_validation_seam_map.md`
- `docs/architecture/task4_hardening_gates.md`
- `docs/architecture/task4_maturity_hardening_closure_report.md`
- `backend/tests/runtime/test_runtime_task4_hardening.py`
- `backend/tests/runtime/test_cross_surface_operator_audit_contract.py`
- `backend/tests/runtime/test_runtime_drift_resistance.py`
- `backend/tests/test_bootstrap_staged_runtime_integration.py`
- `backend/tests/services/test_improvement_task2a_routing_negative.py`

### Modified

- `docs/architecture/ai_story_contract.md`
- `docs/architecture/llm_slm_role_stratification.md`
- `backend/tests/runtime/test_ai_turn_executor.py`

## Tests run and results

Command (from `backend/`, coverage disabled for speed):

```bash
python -m pytest tests/runtime/test_runtime_task4_hardening.py tests/runtime/test_runtime_staged_orchestration.py tests/runtime/test_operator_audit.py tests/runtime/test_model_inventory_bootstrap.py tests/runtime/test_runtime_drift_resistance.py tests/runtime/test_cross_surface_operator_audit_contract.py tests/test_bootstrap_staged_runtime_integration.py tests/services/test_improvement_task2a_routing_negative.py tests/runtime/test_ai_turn_executor.py::test_agent_orchestration_executes_real_separate_subagents_and_logs_trace -q --no-cov
```

**Result:** `37 passed` with `--no-cov` (elapsed time varies by machine; one Windows reference run: ~51s).

## Summaries

### Runtime hardening

- End-to-end `execute_turn_with_ai` coverage for `degraded_early_skip_then_synthesis`, `degraded_parse_forced_synthesis`, preflight-only skip with signal+synthesis still routed, empty `iter_model_specs()` with honest synthesis-on-passed-adapter degradation, synthesis routing with no eligible spec (`no_eligible_spec_selection` true) while the bounded call still uses the passed adapter, and staged synthesis emitting a tool request followed by tool-loop finalization via follow-up generation.
- Orchestration-preempted path: `operator_audit` matches the preempted builder contract (`audit_schema_version`, `note_deep_traces`, single `orchestration_preempted` timeline entry).

### Bootstrap / registry hardening

- One integration test uses a real `create_app(BootstrapEnabledTestingConfig)` path with `ROUTING_REGISTRY_BOOTSTRAP=True`, then runs full staged Runtime against the registered `mock` adapter.

### Cross-surface hardening

- Shared assertions for top-level `operator_audit` keys, timeline entry shape, and `routing_evidence` contract keys across Runtime (staged harness), Writers-Room HTTP response, and Improvement recommendation package; `stage_id`/`stage` alias checked for bounded surfaces; deterministic recommendation base vs advisory `model_assisted_interpretation` disclaimer checked on Improvement.

### Failure-mode / negative-path hardening

- Improvement `_run_routed_bounded_call` with an empty adapter map documents `no_eligible_adapter_or_missing_provider_adapter` and attaches routing evidence without pretending a bounded call ran.

### Drift resistance

- `AUDIT_SCHEMA_VERSION` locked to `"1"`; stable key superset on `build_routing_evidence`; stable top-level keys on `build_runtime_operator_audit` for legacy-empty-trace rollup.

## Residual risks (honest)

- **Key-set contract tests** intentionally freeze a **subset** of `routing_evidence` keys; additive fields may grow without failing tests unless they remove or rename contract keys.
- **Cross-surface tests** compare shared shapes; Runtime-only fields (e.g. `final_path` on `audit_summary`) are not required on bounded surfaces — intentional asymmetry remains.
- **God-of-Carnage lifecycle E2E** (`test_e2e_god_of_carnage_full_lifecycle.py`) still does not assert staged audit payloads; Task 4 proof for audit/trace truth is in targeted Runtime and HTTP tests, not that smoke path.
- **Private import** `improvement_task2a_routing._run_routed_bounded_call` in tests is acceptable for white-box honesty but couples tests to the underscore API.

## Semantic stability statement

**Cross-model routing semantics (`route_model` / Task 2E) and authoritative Runtime semantics (guards, commit, reject, engine authority) are unchanged in this task.** No narrowly justified hardening bug fixes were required; changes are tests and documentation only.
