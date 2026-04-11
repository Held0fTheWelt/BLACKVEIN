# Area 2 — Workstream B reproducibility closure report

This report records **Workstream B** closure: named startup profiles and bootstrap behavior are **deterministic** and test-classified; clean-environment install paths are **explicit** (`setup-test-environment` scripts + `backend/requirements*.txt`); test dependencies include the pytest/async stack; dual-closure tests **collect and run** from `backend/` without undocumented provider secrets; documented validation commands **match** [`area2_validation_commands.py`](../../backend/app/runtime/area2_validation_commands.py); and architecture docs stay aligned — enforced by **G-B-01** through **G-B-07**.

**Explicit unchanged semantics:** **`route_model` policy semantics**, **`StoryAIAdapter`**, **guard legality**, **commit semantics**, **reject semantics**, and **authoritative Runtime mutation rules** were **not** changed.

**Binding vocabulary:** [`area2_dual_workstream_binding.md`](./area2_dual_workstream_binding.md)

**Gate table:** [`area2_workstream_b_gates.md`](./area2_workstream_b_gates.md)

**Tests:** `backend/tests/runtime/test_area2_final_closure_gates.py` (G-B-01 … G-B-07)

**Canonical commands (code):** [`backend/app/runtime/area2_validation_commands.py`](../../backend/app/runtime/area2_validation_commands.py)

---

## Gate outcomes (PASS/FAIL)

| Gate | Result |
|------|--------|
| G-B-01 Startup profile determinism | PASS |
| G-B-02 Bootstrap reproducibility | PASS |
| G-B-03 Clean-environment validation | PASS |
| G-B-04 Dependency/setup explicitness | PASS |
| G-B-05 Test-profile stability | PASS |
| G-B-06 Validation-command reality | PASS |
| G-B-07 Documentation truth for reproducibility | PASS |

---

## Reproducibility / environment summary

- **Profiles:** `Area2StartupProfile` facts and `resolve_startup_profile` behave deterministically for production vs pytest × bootstrap flag combinations.
- **Clean install:** Root `setup-test-environment.sh` / `.bat` install `backend/requirements.txt` and `backend/requirements-test.txt`.
- **Pytest model:** Run Area 2 validation with **`cd backend`** so `backend/pytest.ini` applies; use **`--no-cov`** for gate runs because default `addopts` enable coverage.
- **No hidden provider keys:** Dual-closure module collection succeeds with provider-related environment variables stripped (**G-B-05**).

---

## Validation commands and results

Canonical single line (must match docs and `area2_dual_closure_pytest_invocation()`):

```text
python -m pytest tests/runtime/test_area2_task2_closure_gates.py tests/runtime/test_area2_convergence_gates.py tests/runtime/test_area2_final_closure_gates.py tests/runtime/test_cross_surface_operator_audit_contract.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_model_inventory_bootstrap.py -q --tb=short --no-cov
```

Also documented in [`docs/testing-setup.md`](../testing-setup.md) and [`area2_dual_workstream_closure_report.md`](./area2_dual_workstream_closure_report.md).

---

## Residual risks

- **Full backend suite:** The dual-closure list is a **focused** Area 2 regression; `pytest tests/` without selection remains heavier and may require more disk/DB setup than in-memory gate tests.
- **Optional dev tools:** `requirements-dev.txt` is not required for the dual-closure regression path.

---

## Changed files (this workstream)

See [`area2_dual_workstream_closure_report.md`](./area2_dual_workstream_closure_report.md).
