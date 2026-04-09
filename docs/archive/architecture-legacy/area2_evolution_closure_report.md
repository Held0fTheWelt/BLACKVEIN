# Area 2 — Evolution closure report

This report records the **Area 2 operational routing/registry convergence** closure: explicit authority layers, deterministic operational state, no-eligible discipline, additive operator truth, and enforced G-CONV gates. **Task 2A `route_model` policy semantics, `StoryAIAdapter`, and guard/commit/reject / authoritative Runtime mutation rules were not redesigned** — only observability, classification, documentation, and tests were extended.

## Gate outcomes (PASS/FAIL)

| Gate | Result |
|------|--------|
| G-CONV-01 Single authority | PASS |
| G-CONV-02 Healthy bootstrap | PASS |
| G-CONV-03 State classification | PASS |
| G-CONV-04 No-eligible discipline | PASS |
| G-CONV-05 Operator truth | PASS |
| G-CONV-06 Legacy compatibility | PASS |
| G-CONV-07 Documentation truth | PASS |
| G-CONV-08 Cross-surface coherence | PASS |

## Final authority model

- **Authoritative (Task 2A):** `app.runtime.model_routing.route_model`, `app.runtime.adapter_registry` (spec store for Runtime when `specs=None`), `app.runtime.model_routing_contracts`.
- **Translation:** `app.services.writers_room_model_routing` (ModelSpec → AdapterModelSpec); `story_runtime_core.model_registry` ModelSpec source rows.
- **Compatibility (not canonical for HTTP Task 2A paths):** `ai_stack.langgraph_runtime` + `story_runtime_core.RoutingPolicy.choose()`.
- **Non-authoritative support:** bootstrap, inventory/validation, routing evidence, operator audit builders, runtime staged orchestration wiring, WR/Improvement services that call `route_model` with explicit specs.

Full registry: `backend/app/runtime/area2_routing_authority.py` (`AREA2_AUTHORITY_REGISTRY`).

## Final operational state model

- **`Area2OperationalState`:** `healthy`, `intentionally_degraded`, `misconfigured`, `test_isolated` — derived from bootstrap flag (when known), registry spec count, and canonical surface coverage satisfaction (`validate_surface_coverage`). **Task 2E `degradation_applied` on an otherwise healthy route does not map to this enum**; use `NoEligibleDiscipline` for routing-level semantics.
- **`NoEligibleDiscipline`:** `not_applicable`, `missing_registration_or_specs`, `true_no_eligible_adapter`, `intentional_degraded_route`, `test_isolated_empty_registry`, `bounded_executor_mismatch`.

Module: `backend/app/runtime/area2_operational_state.py`.

## Healthy-path coverage summary

- **Runtime:** `routing_registry_bootstrap` + `register_adapter_model` yields non-empty `iter_model_specs()` under default `Config`; staged preflight/signal/synthesis `RoutingRequest` shapes route without `no_eligible_adapter` when specs cover tuples (see `model_inventory_contract` and `test_model_inventory_bootstrap.py`, `test_area2_convergence_gates.py`).
- **Writers-Room / Improvement:** `build_writers_room_model_route_specs()` satisfies `writers_room` and `improvement_bounded` required tuples; default `build_default_model_adapters()` aligns with provider keys for bounded calls under normal fixtures.

## No-eligible discipline summary

- Empty registry under pytest + `no_eligible_adapter` → `test_isolated_empty_registry`.
- Empty registry outside pytest → `missing_registration_or_specs`.
- Non-empty specs + `no_eligible_adapter` without degradation flag on decision → `true_no_eligible_adapter`.
- Non-empty specs + `no_eligible_adapter` + `degradation_applied` on decision → `intentional_degraded_route`.
- Routed name present but bounded executor missing → `bounded_executor_mismatch` (skip reason containing `missing_provider`).

Rollup: `rollup_no_eligible_discipline_for_bounded_traces` in `area2_operational_state.py`; exposed under `operator_audit.area2_operator_truth.no_eligible_discipline`.

## Operator-truth summary

`operator_audit.area2_operator_truth` (additive) includes at minimum: `surface`, `authority_source`, `bootstrap_enabled`, `registry_model_spec_count` (count of specs used for `route_model` on that surface), `route_coverage_state`, `canonical_surfaces_all_satisfied`, `selected_vs_executed`, `primary_operational_concern`, `operational_state`, `no_eligible_discipline`, `stages_with_no_eligible_adapter`. Populated by `enrich_operator_audit_with_area2_truth` in Runtime (`ai_turn_executor`), Writers-Room (`writers_room_service`), Improvement (`improvement_task2a_routing`).

## Tests run and results

Run from repository root:

```text
python -m pytest backend/tests/runtime/test_area2_convergence_gates.py backend/tests/runtime/test_cross_surface_operator_audit_contract.py -q
```

Last verified run: **14 passed** (9 gate tests + 5 cross-surface tests, including Runtime vs bounded key alignment).

## Residual risks

- **Flask context:** `bootstrap_enabled` in `area2_operator_truth` is `null` when no app context exists (e.g. some unit tests calling `build_runtime_operator_audit` directly without enrichment — enrichment only on canonical paths).
- **Parallel stacks:** Operators must not confuse LangGraph `RoutingPolicy` outcomes with Task 2A `route_model` evidence on canonical HTTP paths; documentation and `AREA2_AUTHORITY_REGISTRY` state this explicitly.
- **Global registry:** Process-wide `adapter_registry` remains sensitive to test ordering if `clear_registry()` is omitted; existing hygiene preserved.

## Changed files (implementation)

- `backend/app/runtime/area2_routing_authority.py` (new)
- `backend/app/runtime/area2_operational_state.py` (new)
- `backend/app/runtime/area2_operator_truth.py` (new)
- `backend/app/runtime/ai_turn_executor.py` (enrich operator audit)
- `backend/app/services/writers_room_service.py` (enrich operator audit)
- `backend/app/services/improvement_task2a_routing.py` (enrich operator audit)
- `backend/tests/runtime/test_area2_convergence_gates.py` (new)
- `backend/tests/runtime/test_cross_surface_operator_audit_contract.py` (G-CONV-05, G-CONV-08, including Runtime vs Writers-Room key parity)
- `docs/architecture/area2_convergence_gates.md` (new)
- `docs/architecture/area2_evolution_closure_report.md` (this file)
- `docs/architecture/llm_slm_role_stratification.md`
- `docs/architecture/ai_story_contract.md`
- `docs/architecture/model_inventory_seam_map.md`

## Explicit unchanged semantics

**Routing semantics** (`route_model` / Task 2E precedence) and **authoritative Runtime semantics** (guards, commit, reject, engine authority) were **not** changed by this closure work.
