# Area 2 — Dual workstream closure report (Workstream A + Workstream B)

This report records **combined** closure for Area 2 **final weakness** work: **Workstream A** (practical convergence) and **Workstream B** (reproducibility and environment discipline), each with its own gate set (**G-A-01** … **G-A-07**, **G-B-01** … **G-B-07**). Prior suites (**G-CONV-**, **G-FINAL-**, **G-T2-**) remain in force and are included in the regression command list below.

**Explicit unchanged semantics:** Task 2A **`route_model` policy semantics and precedence**, **`StoryAIAdapter`**, **guard legality**, **commit semantics**, **reject semantics**, and **authoritative Runtime mutation rules** were **not** changed by this dual closure — only explicit authority registry entries, derived operator truth, startup-profile facts, validation command surfacing, tests, and architecture documentation were extended.

**Minimal binding interpretation:** [`area2_dual_workstream_binding.md`](./area2_dual_workstream_binding.md)

**Workstream A gates:** [`area2_workstream_a_gates.md`](./area2_workstream_a_gates.md) — tests `backend/tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py` (G-A-01 … G-A-07)

**Workstream B gates:** [`area2_workstream_b_gates.md`](./area2_workstream_b_gates.md) — tests `backend/tests/runtime/test_runtime_startup_profiles_operator_truth.py` (G-B-01 … G-B-07)

**Importable authority map:** [`backend/app/runtime/area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py) (`AREA2_AUTHORITY_REGISTRY`)

**Canonical pytest argv (code):** [`backend/app/runtime/area2_validation_commands.py`](../../backend/app/runtime/area2_validation_commands.py) (`AREA2_DUAL_CLOSURE_PYTEST_MODULES`, `area2_dual_closure_pytest_invocation`)

---

## Workstream A — gate-by-gate results

| Gate | Result |
|------|--------|
| G-A-01 Primary authority convergence | PASS |
| G-A-02 Non-competing auxiliary layer | PASS |
| G-A-03 Canonical path coherence | PASS |
| G-A-04 Healthy canonical path confidence | PASS |
| G-A-05 No-eligible non-normalization | PASS |
| G-A-06 Operator-grade convergence readability | PASS |
| G-A-07 Documentation truth for convergence | PASS |

Detail: [`area2_practical_convergence_closure_report.md`](./area2_practical_convergence_closure_report.md)

---

## Workstream B — gate-by-gate results

| Gate | Result |
|------|--------|
| G-B-01 Startup profile determinism | PASS |
| G-B-02 Bootstrap reproducibility | PASS |
| G-B-03 Clean-environment validation | PASS |
| G-B-04 Dependency/setup explicitness | PASS |
| G-B-05 Test-profile stability | PASS |
| G-B-06 Validation-command reality | PASS |
| G-B-07 Documentation truth for reproducibility | PASS |

Detail: [`area2_reproducibility_closure_report.md`](./area2_reproducibility_closure_report.md)

---

## Practical convergence summary (Workstream A)

Canonical Runtime, Writers-Room, and Improvement paths each have **one** primary Task 2A routing policy authority (`route_model`) with **bounded** translation (WR/Improvement spec builders + `story_runtime_core` rows), **compatibility-only** parallel LangGraph lines (empty canonical surface claim), and **support** modules that do not replace policy. Healthy bootstrap-on paths remain route-eligible without routine `no_eligible_adapter`; operator truth stays readable from derived fields.

---

## Reproducibility / environment summary (Workstream B)

Named profiles in `area2_startup_profiles` align deterministically with bootstrap and registry expectations. Setup scripts at repository root install declared requirements. Area 2 dual-closure validation runs from **`backend/`** with **`--no-cov`** to override default coverage `addopts`. Module list and invocation string are defined once in **`area2_validation_commands`** and mirrored here and in [`docs/testing-setup.md`](../testing-setup.md).

---

## Healthy-path confidence summary

Under **`testing_bootstrap_on`**, staged Runtime execution, Writers-Room review creation, and Improvement experiment routing demonstrate eligible adapters and consistent `area2_operator_truth` top-level keys across surfaces where tested (**G-A-04**, **G-FINAL-06** lineage).

---

## No-eligible discipline summary

`no_eligible_adapter` on routed stages is **not** normalized as healthy canonical success; `route_status` and `NoEligibleDiscipline` preserve honest distinctions (**G-A-05**).

---

## Operator-readability summary

`legibility` exposes authority source, operational state, route status, selected-vs-executed rollup, primary operational concern, and startup profile without new telemetry (**G-A-06**).

---

## Validation commands and results

**Working directory:** `backend/` (so `backend/pytest.ini` applies: `pythonpath`, `testpaths`, asyncio mode).

**Exact invocation line** (must match `area2_dual_closure_pytest_invocation()` in code):

```text
python -m pytest tests/runtime/test_runtime_routing_registry_composed_proofs.py tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py tests/runtime/test_runtime_startup_profiles_operator_truth.py tests/runtime/test_cross_surface_operator_audit_contract.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_model_inventory_bootstrap.py -q --tb=short --no-cov
```

**Modules covered:** `tests/runtime/test_runtime_routing_registry_composed_proofs.py`, `tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py`, `tests/runtime/test_runtime_startup_profiles_operator_truth.py`, `tests/runtime/test_cross_surface_operator_audit_contract.py`, `tests/test_bootstrap_staged_runtime_integration.py`, `tests/runtime/test_model_inventory_bootstrap.py`.

Run the command after `./setup-test-environment.sh` or `setup-test-environment.bat` (or manual `pip install -r backend/requirements.txt -r backend/requirements-test.txt`).

---

## Residual risks

- **Flask context gaps:** Some legibility fields may be `null` off hot paths without app context.
- **Global registry:** Process-global adapter registry still requires disciplined `clear_registry()` in isolated tests.
- **Scope:** Dual-closure regression does not replace the full `backend/tests/` tree; optional providers remain outside mock-based proofs.

---

## Changed files (implementation)

- `backend/app/runtime/area2_validation_commands.py` (new)
- `backend/tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py` (Workstream A gate tests merged here)
- `backend/tests/runtime/test_runtime_startup_profiles_operator_truth.py` (Workstream B gate tests merged here)
- `docs/architecture/area2_dual_workstream_binding.md` (new)
- `docs/architecture/area2_workstream_a_gates.md` (new)
- `docs/architecture/area2_workstream_b_gates.md` (new)
- `docs/architecture/area2_practical_convergence_closure_report.md` (new)
- `docs/architecture/area2_reproducibility_closure_report.md` (new)
- `docs/architecture/area2_dual_workstream_closure_report.md` (this file)
- `docs/architecture/area2_registry_routing_convergence_closure_report.md` (regression command aligned with dual suite)
- `docs/architecture/llm_slm_role_stratification.md` (cross-references)
- `docs/architecture/ai_story_contract.md` (cross-references)
- `docs/testing-setup.md` (Area 2 dual validation section; smoke accuracy)
