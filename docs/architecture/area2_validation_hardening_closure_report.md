# Area 2 — Task 4 validation hardening closure report

## Verdict

**PASS** — All **G-T4-01** … **G-T4-08** gates pass when the canonical command below is run from `backend/` with `--no-cov`. Results in this section are tied to that executable proof.

## Binding Task 4 interpretation (summary)

See [`area2_task4_closure_gates.md`](./area2_task4_closure_gates.md) for the authoritative minimal definitions of hard validation, E2E truth, drift resistance, negative/failure honesty, cross-surface contract truth, and bootstrap truths.

## Gate results (G-T4-01 … G-T4-08)

| Gate | Result | Proof |
|------|--------|--------|
| **G-T4-01** | PASS | `test_area2_task4_closure_gates.py::test_g_t4_01_end_to_end_truth_three_surfaces_gate` delegates to cross-surface Runtime, Writers-Room, and Improvement contract tests. |
| **G-T4-02** | PASS | `test_g_t4_02_bootstrap_validation_gate` — final/convergence bootstrap gates + real `create_app` bootstrap-on staged integration. |
| **G-T4-03** | PASS | `test_g_t4_03_cross_surface_contract_gate` — Task 3 compact grammar + G-CONV-08 coherence. |
| **G-T4-04** | PASS | `test_g_t4_04_negative_degraded_honesty_gate` — degraded Runtime hardening + Improvement missing-adapter skip. |
| **G-T4-05** | PASS | `test_g_t4_05_drift_resistance_gate` — audit schema and stable routing-evidence keys. |
| **G-T4-06** | PASS | `test_g_t4_06_validation_command_reality_gate` — `docs/testing-setup.md` and this report embed the exact `area2_task4_full_closure_pytest_invocation()` string and list every module. |
| **G-T4-07** | PASS | `test_g_t4_07_required_suite_stability_gate` — subprocess pytest over `AREA2_TASK4_PROOF_PYTEST_MODULES` from `backend/`. |
| **G-T4-08** | PASS | `test_g_t4_08_documentation_and_closure_truth_gate` — required docs reference every G-T4 id and `area2_validation_commands`. |

## End-to-end truth summary

Runtime in-process staged execution, Writers-Room HTTP review, and Improvement experiment package are each exercised with shared `operator_audit` / `routing_evidence` contract checks (**G-T4-01**), backed by `test_cross_surface_operator_audit_contract.py` and the Task 4 proof suite.

## Bootstrap validation summary

Named startup profiles, bootstrap on/off expectations, healthy registry coverage, and a real `create_app(BootstrapEnabledTestingConfig)` staged Runtime path are enforced (**G-T4-02**).

## Cross-surface contract summary

`compact_operator_comparison` grammar version and mandatory keys are proven on all three surfaces via Task 3 gates; bounded HTTP surfaces share `area2_operator_truth` key coherence (**G-T4-03**).

## Negative / degraded honesty summary

Degraded Runtime `final_path` traces and empty-registry honesty are covered via Task 4 Runtime hardening; Improvement `_run_routed_bounded_call` documents skip when adapters are missing (**G-T4-04**).

## Drift-resistance summary

`AUDIT_SCHEMA_VERSION` and bounded stable subsets for `build_routing_evidence` and legacy rollup operator audit top-level keys are regression-locked (**G-T4-05**).

## Validation commands and results

**Canonical command** (single source: `area2_task4_full_closure_pytest_invocation()` in [`backend/app/runtime/area2_validation_commands.py`](../../backend/app/runtime/area2_validation_commands.py)):

```bash
cd backend
python -m pytest tests/runtime/test_area2_workstream_a_closure_gates.py tests/runtime/test_area2_workstream_b_closure_gates.py tests/runtime/test_area2_task2_closure_gates.py tests/runtime/test_area2_convergence_gates.py tests/runtime/test_area2_final_closure_gates.py tests/runtime/test_cross_surface_operator_audit_contract.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_model_inventory_bootstrap.py tests/runtime/test_area2_task3_closure_gates.py tests/runtime/test_runtime_task4_hardening.py tests/runtime/test_task4_drift_resistance.py tests/runtime/test_runtime_staged_orchestration.py tests/runtime/test_runtime_ranking_closure_gates.py tests/improvement/test_improvement_task2a_routing_negative.py tests/runtime/test_ai_turn_executor.py::test_agent_orchestration_executes_real_separate_subagents_and_logs_trace tests/runtime/test_area2_task4_closure_gates.py -q --tb=short --no-cov
```

**G-T4-07 proof-only subprocess** uses `AREA2_TASK4_PROOF_PYTEST_MODULES` (same modules as above except `tests/runtime/test_area2_task4_closure_gates.py`) to avoid recursive self-invocation.

**Reference run (Windows, Python 3.13):** `107 passed` in ~131s for the full canonical command above (includes Task 4 gate module). **G-T4-07** proof-only subprocess run: same modules except `tests/runtime/test_area2_task4_closure_gates.py`, green in ~64s on the same machine class.

Run the canonical command after checkout; all tests must pass for closure.

## Residual risks (honest)

- **Subset key contracts** may allow additive JSON fields without failure until explicit drift tests are extended.
- **G-T4-07** subprocess timeout is bounded (900s); extremely slow hosts may need a local rerun or environment tuning — the proof expectation remains a full green run.
- **White-box tests** that call private helpers (e.g. Improvement routing) remain coupled to internal module layout.

## Semantic stability

**Cross-model routing semantics (`route_model` / Task 2E) and authoritative Runtime semantics (guards, commit, reject, engine authority) were not changed** for this closure task; changes are tests, validation command constants, and documentation alignment.

## Files changed (Task 4 closure)

- `docs/architecture/area2_task4_closure_gates.md` (new)
- `docs/architecture/area2_validation_hardening_closure_report.md` (new)
- `docs/testing-setup.md` (Area 2 Task 4 section)
- `docs/architecture/ai_story_contract.md` (G-T4 references)
- `docs/architecture/llm_slm_role_stratification.md` (G-T4 references)
- `backend/app/runtime/area2_validation_commands.py` (Task 4 module tuples + helpers)
- `backend/tests/runtime/test_area2_task4_closure_gates.py` (new)
