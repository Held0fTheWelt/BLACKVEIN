# Area 2 — Task 4 closure gates (G-T4)

Minimal **binding interpretation** for Area 2 Task 4 (final validation, drift resistance, end-to-end truth). This document does not change product semantics; it defines what **must be proven** for closure.

## Binding terms

- **Hard validation (Area 2):** Claims about canonical Runtime, Writers-Room, and Improvement paths, bootstrap/profile truth, cross-surface contracts, negative paths, and drift are backed by **named automated tests** or **explicit documented limits**. Narrative is not a substitute for executable proof.
- **E2E truth (Area 2):** Proof through **integration** or **focused end-to-end paths** (`execute_turn_with_ai`, real `create_app` bootstrap where applicable, HTTP surfaces for bounded paths), not solely through isolated unit tests of helpers.
- **Drift resistance:** Stable **`grammar_version` / schema tags** and **bounded key expectations** for `routing_evidence`, `operator_audit`, and `compact_operator_comparison`; silent shape/key regressions should fail tests unless intentionally updated.
- **Negative / failure honesty:** Degraded, no-eligible, missing-provider, test-isolated, and misconfigured states remain **classifiable** and must not upgrade degraded paths to “healthy success” semantics in operator truth or compact surfaces.
- **Cross-surface contract truth:** Runtime, Writers-Room, and Improvement share **proven** common keys and versions where the contract requires them; documented asymmetries (e.g. Runtime-only `null` slots) stay explicit and bounded.
- **Startup / bootstrap truths:** Named profiles (`production_default`, `testing_isolated`, `testing_bootstrap_on`, etc.) and bootstrap on/off behaviors are **explicitly validated** in code/tests, not only described in prose.
- **Acceptable environment sensitivity:** Wall-clock timing and locale may vary; the closure suite must **not** require provider API keys or undocumented secrets (aligned with Workstream B collect-only discipline).

## Gate table

| Gate ID | Pass condition | Proof | Failure meaning |
|--------|----------------|-------|-----------------|
| **G-T4-01** | Canonical **Runtime**, **Writers-Room**, and **Improvement** integration truth for operator audit + routing evidence contracts is exercised. | `backend/tests/runtime/test_area2_task4_closure_gates.py::test_g_t4_01_end_to_end_truth_three_surfaces_gate` (delegates to cross-surface contract tests). | One or more surfaces lack proven staged/HTTP integration shape or contract keys. |
| **G-T4-02** | Bootstrap-on, test-isolated, and profile-implied states are validated on canonical Area 2 paths. | Delegation to final/convergence/bootstrap integration tests in `test_g_t4_02_bootstrap_validation_gate`. | Bootstrap or profile classification is not enforced by tests. |
| **G-T4-03** | Cross-surface **compact_operator_comparison** and shared audit contracts remain consistent and regression-protected. | Delegation to Task 3 closure gates + cross-surface contract tests in `test_g_t4_03_cross_surface_contract_gate`. | Compact grammar or cross-surface key contract drifts without test failure. |
| **G-T4-04** | Negative, degraded, and missing-adapter paths are honest (no false success). | Delegation to Task 4 hardening, Improvement negative routing, and related paths in `test_g_t4_04_negative_degraded_honesty_gate`. | Degraded truth is under-proven vs healthy paths or overclaims success. |
| **G-T4-05** | Schema/version and bounded routing-evidence key expectations are guarded. | Delegation to `test_task4_drift_resistance.py` in `test_g_t4_05_drift_resistance_gate`. | Silent drift of audit or evidence shapes. |
| **G-T4-06** | Documented validation commands match the **canonical** Task 4 module list and flags from code (exact string). | `test_g_t4_06_validation_command_reality_gate` reads `docs/testing-setup.md` and compares to `area2_task4_full_closure_pytest_invocation()`. | Docs and `area2_validation_commands.py` diverge. |
| **G-T4-07** | Full **proof** module list (canonical Task 4 list **excluding** the gate orchestrator module) passes under pytest. | `test_g_t4_07_required_suite_stability_gate` subprocess from `backend/`. | Any proof module regresses; closure suite not green. |
| **G-T4-08** | Architecture docs reference every **G-T4-0x** gate and the closure report + command surface. | `test_g_t4_08_documentation_and_closure_truth_gate`. | Documentation truth for Task 4 gates is incomplete or inconsistent. |

## Hard boundaries (unchanged)

No redesign of `route_model` semantics or precedence, no `StoryAIAdapter` redesign, no changes to guard legality, commit/reject semantics, or authoritative runtime mutation rules.

## Related artifacts

- Canonical command list: [`backend/app/runtime/area2_validation_commands.py`](../../backend/app/runtime/area2_validation_commands.py) — `AREA2_TASK4_FULL_CLOSURE_PYTEST_MODULES`, `area2_task4_full_closure_pytest_invocation`.
- Closure report: [`area2_validation_hardening_closure_report.md`](./area2_validation_hardening_closure_report.md).
- Prior hardening gate IDs (G-RUN-*, G-XS-01, …): [`task4_hardening_gates.md`](./task4_hardening_gates.md).
