# Gate G10 Baseline: End-to-End Closure

## Gate

- Gate name: G10 End-to-End Closure  
- Gate class: operational (roadmap taxonomy; `docs/GoC_Gate_Baseline_Audit_Plan.md` G10 §A)  
- Audit subject: the full eleven-step end-to-end chain in `docs/MVPs/MVP_VSL_And_GoC_Contracts/ROADMAP_MVP_GoC.md` §6.11, evidenced as **one integrated system**, not isolated green layers.

## Prerequisites Consumed (Tasks 1–3)

This baseline is assembled **only after** per-gate reports for G1–G9 and G9B exist:

- `docs/audit/gate_G1_semantic_contract_baseline.md` through `docs/audit/gate_G8_improvement_operating_baseline.md`  
- `docs/audit/gate_G9_experience_acceptance_baseline.md`  
- `docs/audit/gate_G9B_evaluator_independence_baseline.md`  
- Mapping/index: `docs/audit/canonical_to_repo_mapping_table.md`, `docs/audit/repo_evidence_index.md`

## Repository Inspection Targets (Audit Plan G10 §C)

- Runtime executors: `ai_stack/langgraph_runtime.py`, `backend/app/runtime/ai_turn_executor.py`, `backend/app/runtime/turn_dispatcher.py`  
- Module load: `content/modules/god_of_carnage/`, `backend/app/content/builtins.py`, `world-engine/app/content/builtins.py` (as applicable)  
- Routing / observation / evidence: `backend/app/runtime/model_routing_evidence.py`, `backend/app/services/ai_stack_evidence_service.py`  
- End-to-end tests: `backend/tests/test_e2e_god_of_carnage_full_lifecycle.py`, `backend/tests/test_bootstrap_staged_runtime_integration.py`, `backend/tests/runtime/test_area2_task4_closure_gates.py`  
- Smoke: `run-smoke-tests.bat`, `run-smoke-tests.sh`, `tests/smoke/`  

## Eleven-Step Chain — Evidence Mapping

Integrated witness for steps **1–10**: backend pytest trio run `g10_backend_e2e_20260409` — `tests/reports/evidence/g10_backend_e2e_20260409/pytest_g10_backend_trio.txt` (**15 passed**, `exit_code: 0`), metadata `run_metadata.json`. Step **11** remains anchored on authoritative G9 only (same run as G9/G9B baselines).

| # | Roadmap requirement (`docs/MVPs/MVP_VSL_And_GoC_Contracts/ROADMAP_MVP_GoC.md` §6.11) | Evidence basis for this baseline | Upstream gate / note |
|---|--------------------------------------------------------|-----------------------------------|----------------------|
| 1 | Module load from canonical package | E2E: `create_session("god_of_carnage")`, module registered in runtime store (`test_e2e_god_of_carnage_full_lifecycle.py`); bootstrap uses real `ContentModule` (`test_bootstrap_staged_runtime_integration.py`). | G1, G3, G5, G10 |
| 2 | Runtime turn execution | E2E: `dispatch_turn` single and multi-turn (`test_e2e_*`); bootstrap: `execute_turn_with_ai` under `create_app` with `ROUTING_REGISTRY_BOOTSTRAP` (`test_bootstrap_*`); area2 closure gates re-invoke staged path (`test_area2_task4_closure_gates.py`). | G3, G4 |
| 3 | Bounded retrieval when appropriate | Staged runtime and graph-backed paths exercised through backend integration tests; lane-level proof remains aligned with G5/G9 retrieval scenarios — trio proves backend/runtime wiring, not a substitute for G5 structural `green`. | G5, G9 |
| 4 | Task-aware routing | Area2 closure: routing/registry/bootstrap matrices (`test_g_t4_02`, `test_g_t4_03`, related gates in `test_area2_task4_closure_gates.py`); registry-backed adapter resolution in bootstrap test. | G2, G7, G8 |
| 5 | Structured model output | `execute_turn_with_ai` / dispatcher turn results with `execution_status` and session metadata (`ai_decision_logs` in bootstrap test). | G3, G9 |
| 6 | Validation and commit | Turn pipeline completes with committed session/canonical state updates across sequential E2E turns (`updated_canonical_state` handoff). | G3, G9 |
| 7 | Dramatic turn record emission | Turn results and runtime session/module invariants through dispatcher path (E2E + staged AI executor). | G3 |
| 8 | Operator-visible routing truth | Area2 **G-T4-01**: runtime vs Writers' Room vs Improvement operator-audit contract alignment (`test_g_t4_01_end_to_end_truth_three_surfaces_gate`). | G2, G3 |
| 9 | Fallback correctness when primary path fails | E2E error/empty-input resilience (`test_error_input_doesnt_crash_session`); **primary-model failure + graph fallback** remains evidenced on authoritative G9 S5 (`g9_level_a_fullsix_20260410`) per `gate_G9_experience_acceptance_baseline.md` — not re-run inside this trio. | G9 |
| 10 | Writers' Room semantic compatibility intact | Area2 **G-T4-01**: `test_writers_room_operator_audit_and_routing_evidence_contract` invoked from closure gate module. | G1, G7 |
| 11 | Experience acceptance threshold remains green | **Authoritative G9 repo evidence only:** `g9_level_a_fullsix_20260410` — full six-scenario pytest witness, structured capture, complete 6×5 matrix, validator `complete: true`, `pass_all: true` (`docs/audit/gate_G9_experience_acceptance_baseline.md`). | G9, G9B |

## Command Strategy (Audit Plan G10 §F)

| command | status | basis | execution evidence (this baseline) |
|--------|--------|-------|-----------------------------------|
| `python -m pytest tests/smoke/ -v --tb=short` (repo root) | not_run | Optional smoke pass; not executed in this G10 assembly slice. | — |
| `run-smoke-tests.bat` / `./run-smoke-tests.sh` | not_run | Optional; not executed in this slice. | — |
| `cd backend && python -m pytest tests/test_e2e_god_of_carnage_full_lifecycle.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_area2_task4_closure_gates.py -q --tb=short --no-cov` | **passed** | Same invocation as `.github/workflows/backend-tests.yml` job `g10-backend-e2e-evidence-path`; install `backend/requirements-dev.txt` from repo root. First capture used `PYTHONPATH` = repository root; **re-verified** with cwd-only from `backend/` (no `PYTHONPATH`) — 15 passed on the same host (`run_metadata.json` note). | `tests/reports/evidence/g10_backend_e2e_20260409/pytest_g10_backend_trio.txt` (`exit_code: 0`); `run_metadata.json` |
| `cd backend && python -m pytest tests/test_e2e_god_of_carnage_full_lifecycle.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_area2_task4_closure_gates.py -q --tb=short --no-cov` (closure rerun) | **passed** | All-gates closure rerun to verify preserved authoritative G10 evidence still matches current repo truth. | `tests/reports/evidence/all_gates_closure_20260409/g10_backend_trio_rerun.txt` (15 passed) |

**CI note:** A green `g10-backend-e2e-evidence-path` job is **the same pytest surface**; it does not, by itself, assert roadmap program closure. Step 11 remains tied to the **authoritative** G9/G9B bundle `g9_level_a_fullsix_20260410`, not to older or partial G9 runs.

**Historical baseline session:** An earlier assembly recorded `failed_to_start` (`ModuleNotFoundError: flask`) when backend dependencies were not installed in the active interpreter — **superseded** by this run’s transcript for command-truth.

## Baseline Findings

1. **Integrated backend chain (steps 1–10):** The audit-plan pytest trio **passed** (15 tests) with archived witness `g10_backend_e2e_20260409`. Together with step 11 on `g9_level_a_fullsix_20260410`, the **§6.11 chain is evidenced as one integrated backend-facing system** for this snapshot (audit plan G10 §G `green` criterion for end-to-end chain stages **as exercised by these tests**).  
2. **Structural gates G1–G8:** Closure rerun evidence now supports G1–G8 as structural `green` on their canonical paths (`tests/reports/evidence/all_gates_closure_20260409/`), so the prior prerequisite-health blocker on G10 closure-level promotion is removed.  
3. **Closure-level vs structural (§7A discipline):** With G1–G8 structural health now green and G9/G9B authoritative evaluative evidence intact, G10 can truthfully carry `closure_level_status: level_a_capable` for this baseline snapshot while preserving strict non-claim discipline for Level B.  
4. **Isolated-layer rule:** Satisfied for this update: integrative proof is **not** claimed from ai_stack-only or single-layer tests alone; the trio + authoritative G9 bundle are both cited.  
5. **Environment parity:** Local witness used Python **3.13.12**; CI merge bar for this repo is **Python 3.10** (`docs/testing-setup.md`). Reproduce CI-identical results using Actions or a 3.10 env if parity is required for a given claim.

## Status Baseline

- structural_status: `green`  
- closure_level_status: `level_a_capable`  

**Rationale:** Audit plan G10 §G — all eleven roadmap steps are mapped to executed evidence: steps 1–10 via the passing backend trio (`g10_backend_e2e_20260409`, revalidated by `all_gates_closure_20260409/g10_backend_trio_rerun.txt`), step 11 via authoritative G9/G9B on `g9_level_a_fullsix_20260410`. With G1–G8 now structurally green on canonical reruns, §7A prerequisite-health gating no longer forces G10 closure-level to `none`; this baseline sets G10 to `level_a_capable` without asserting unsupported Level B or MVP completion claims.

## Evidence Quality

- evidence_quality: `high`  
- justification: Direct pytest transcript with exit code, run metadata, and explicit cross-surface closure tests (Area2 G-T4-01/02/…); step 11 anchored on archived G9 validator output (`pass_all: true`). Residual uncertainty is **environment version skew** (local 3.13 vs CI 3.10), explicitly recorded — not a substitute for running the same job on ubuntu-latest + 3.10 when CI parity is the claim under test.

## Execution Risks Carried Forward

- Re-run the trio under **Python 3.10** (CI image or local) and attach transcript if merge-bar parity must match Actions exactly.  
- Maintain prerequisite-gate rerun discipline if future regressions move any of G1–G8 back below structural `green`.
