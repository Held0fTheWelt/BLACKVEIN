# Area 2 — Task 2 registry/routing convergence closure report

This report records **Area 2 Closure Task 2**: canonical Runtime, Writers-Room, and Improvement paths converge on one **registry/routing operational truth**, with explicit non-competing layers, startup/bootstrap discipline, healthy-path coverage, no-eligible honesty, and compact operator truth — proven first in **code and tests** ([`area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py), G-CONV/G-FINAL family, **G-T2-01** … **G-T2-08** in [`test_area2_task2_closure_gates.py`](../../backend/tests/runtime/test_area2_task2_closure_gates.py)).

**Explicit unchanged semantics:** Task 2A **`route_model` policy semantics**, **`StoryAIAdapter`**, **guard legality**, **commit semantics**, **reject semantics**, and **authoritative Runtime mutation rules** were **not** changed by this closure work.

---

## Binding interpretation (minimal)

| Rule | Statement |
|------|-----------|
| **Primary authority** | Exactly **one primary operational authority** per canonical path (Runtime, Writers-Room, Improvement bounded): *who applies routing policy* and *where specs come from* on that path. |
| **Non-competing layers** | **Translation**, **compatibility**, and **non-authoritative support** lines may coexist only when **explicit, bounded, and non-competing** — no hidden second routing policy for the same canonical surface. |
| **Importable map** | `AREA2_AUTHORITY_REGISTRY` in [`area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py) classifies every registered seam; operator truth uses `AUTHORITY_SOURCE_RUNTIME`, `AUTHORITY_SOURCE_WRITERS_ROOM`, `AUTHORITY_SOURCE_IMPROVEMENT`. |

---

## Gate outcomes (G-T2-01 .. G-T2-08)

| Gate | Result |
|------|--------|
| G-T2-01 Authority convergence | PASS |
| G-T2-02 Startup/bootstrap truth | PASS |
| G-T2-03 Healthy canonical paths | PASS |
| G-T2-04 No-eligible discipline | PASS |
| G-T2-05 Operator truth | PASS |
| G-T2-06 Inventory/coverage truth | PASS |
| G-T2-07 Legacy compatibility | PASS |
| G-T2-08 Documentation truth | PASS |

Full gate table: [`area2_task2_closure_gates.md`](./area2_task2_closure_gates.md).

---

## Tests run and results

From `backend/` (includes **Workstream A/B** dual closure modules; see [`area2_dual_workstream_closure_report.md`](./area2_dual_workstream_closure_report.md)):

```text
python -m pytest tests/runtime/test_area2_task2_closure_gates.py tests/runtime/test_area2_convergence_gates.py tests/runtime/test_area2_final_closure_gates.py tests/runtime/test_cross_surface_operator_audit_contract.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_model_inventory_bootstrap.py -q --tb=short --no-cov
```

Canonical single-line source: `area2_dual_closure_pytest_invocation()` in [`backend/app/runtime/area2_validation_commands.py`](../../backend/app/runtime/area2_validation_commands.py).

Last verified: **64 passed**, **0 failed** (single run of the command above with `--no-cov`, local).

---

## Summaries

- **Authority:** `route_model` is sole routing policy; Runtime specs from `adapter_registry` when `specs=None`; Writers-Room and Improvement use `build_writers_room_model_route_specs` / `writers_room_model_routing`; LangGraph `RoutingPolicy` remains compatibility-only (see `AREA2_AUTHORITY_REGISTRY`).
- **Startup/bootstrap:** Named profiles in `area2_startup_profiles`; `Area2OperationalState` from explicit facts in `area2_operational_state`.
- **Healthy paths:** Bootstrap-on testing profile + inventory coverage; no routine `no_eligible_adapter` on healthy routed stages (delegated proofs).
- **No-eligible discipline:** `NoEligibleDiscipline` + `legibility.route_status` do not normalize true NEA as healthy.
- **Operator truth:** `area2_operator_truth` / `legibility` derived only from existing traces and config.

---

## Residual risks

- CI does not claim real external story providers without credentials; `testing_isolated` empty registry remains an **expected** profile, not a product defect.
- Full-suite timing: G-T2 tests **delegate** to G-CONV/G-FINAL; a full run executes both layers.

---

## Changed files (Task 2)

Track in version control: `area2_routing_authority.py` (binding docstring), `test_area2_task2_closure_gates.py`, this report, `area2_task2_closure_gates.md`, and architecture cross-reference deltas (`llm_slm_role_stratification.md`, `ai_story_contract.md`, `area2_convergence_gates.md`, `area2_final_closure_gates.md`).
