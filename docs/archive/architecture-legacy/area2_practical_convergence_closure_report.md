# Area 2 — Workstream A practical convergence closure report

This report records **Workstream A** closure: canonical Runtime, Writers-Room, and Improvement paths converge on **one primary Task 2A operational authority** per surface, with **explicit, bounded, non-competing** translation, compatibility, and support layers; no practical split-brain with parallel LangGraph routing; healthy-path coherence under `testing_bootstrap_on`; honest no-eligible discipline; and operator-readable `area2_operator_truth` — enforced by **G-A-01** through **G-A-07**.

**Explicit unchanged semantics:** **`route_model` policy semantics**, **`StoryAIAdapter`**, **guard legality**, **commit semantics**, **reject semantics**, and **authoritative Runtime mutation rules** were **not** changed — only tests, registry documentation parity, operator-truth derivation, and architecture text were extended.

**Binding vocabulary:** [`area2_dual_workstream_binding.md`](./area2_dual_workstream_binding.md)

**Gate table:** [`area2_workstream_a_gates.md`](./area2_workstream_a_gates.md)

**Tests:** `backend/tests/runtime/test_area2_convergence_gates.py` (G-A-01 … G-A-07)

**Authority map:** [`backend/app/runtime/area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py) (`AREA2_AUTHORITY_REGISTRY`)

---

## Gate outcomes (PASS/FAIL)

| Gate | Result |
|------|--------|
| G-A-01 Primary authority convergence | PASS |
| G-A-02 Non-competing auxiliary layer | PASS |
| G-A-03 Canonical path coherence | PASS |
| G-A-04 Healthy canonical path confidence | PASS |
| G-A-05 No-eligible non-normalization | PASS |
| G-A-06 Operator-grade convergence readability | PASS |
| G-A-07 Documentation truth for convergence | PASS |

---

## Practical convergence summary

- **Primary authority:** `task2a_route_model` is the sole routing policy; `adapter_registry` and `model_routing_contracts` are authoritative supporting lines scoped per [`area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py).
- **Auxiliary layers:** Translation (`writers_room_model_routing`, `story_runtime_core.model_registry`), compatibility (LangGraph / legacy `RoutingPolicy` with **empty** canonical Task 2A surface sets), and support modules are registry-classified and non-competing.
- **Split-brain guard:** LangGraph lines do not claim canonical HTTP Task 2A surfaces; `canonical_authority_summary` names LangGraph as compatibility-only.
- **Healthy paths:** Under bootstrap-on testing, Runtime staged execution, Writers-Room reviews, and Improvement experiment routes avoid routine `no_eligible_adapter` and retain `area2_operator_truth` shape on bounded HTTP.

---

## Healthy-path confidence summary

Runtime `execute_turn_with_ai`, Writers-Room `POST /api/v1/writers-room/reviews`, and Improvement variant + experiment flow each demonstrate eligible routing with selected adapter names under `testing_bootstrap_on` (see **G-A-04** tests).

---

## No-eligible discipline summary

True `no_eligible_adapter` remains classified via `NoEligibleDiscipline` and `legibility.route_status` so it is not read as ordinary healthy success (**G-A-05**).

---

## Operator-readability summary

`area2_operator_truth.legibility` exposes `authority_source`, `operational_state`, `route_status`, `selected_vs_executed`, `primary_operational_concern`, and `startup_profile` from existing facts; bounded HTTP contracts retain full truth shape (**G-A-06**).

---

## Validation commands

Workstream A gates run as part of the canonical dual-workstream regression (from `backend/`, with `--no-cov`):

```text
python -m pytest tests/runtime/test_area2_task2_closure_gates.py tests/runtime/test_area2_convergence_gates.py tests/runtime/test_area2_final_closure_gates.py tests/runtime/test_cross_surface_operator_audit_contract.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_model_inventory_bootstrap.py -q --tb=short --no-cov
```

Single-line source of truth: `area2_dual_closure_pytest_invocation()` in [`backend/app/runtime/area2_validation_commands.py`](../../backend/app/runtime/area2_validation_commands.py).

---

## Residual risks

- **Flask context:** `startup_profile` in legibility may be `null` when no app context exists on paths that skip enrichment.
- **Global registry:** Tests must continue calling `clear_registry()` where isolation matters; bootstrap-on fixtures re-seed via `create_app` or `bootstrap_routing_registry_from_config`.

---

## Changed files (this workstream)

See combined report [`area2_dual_workstream_closure_report.md`](./area2_dual_workstream_closure_report.md) for the full list.
