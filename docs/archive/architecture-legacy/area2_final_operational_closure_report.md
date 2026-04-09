# Area 2 — Final operational closure report

This report records **final** Area 2 operational closure: named startup profiles, healthy canonical-path proofs under `testing_bootstrap_on`, practical authority convergence in `AREA2_AUTHORITY_REGISTRY` and `canonical_authority_summary`, no-eligible non-normalization via `legibility.route_status`, operator legibility block, cross-surface key coherence, legacy test isolation, and documentation gates **G-FINAL-01** through **G-FINAL-08**.

**Explicit unchanged semantics:** Task 2A **`route_model` policy semantics**, **`StoryAIAdapter`**, **guard legality**, **commit semantics**, **reject semantics**, and **authoritative Runtime mutation rules** were **not** changed by this closure work — only classification, startup-profile documentation, operator-truth derivation, registry entries for documentation parity, tests, and architecture text were extended.

---

## Binding 10/10 interpretation (final target for this task)

| Dimension | Satisfied when |
|-----------|----------------|
| **Reproducible bootstrap truth** | Named profiles (`production_default`, `testing_isolated`, `testing_bootstrap_on`, and `production_bootstrap_disabled` where honest) each have frozen **expected facts** in code (`area2_startup_profiles`) and tests prove `create_app` + `ROUTING_REGISTRY_BOOTSTRAP` ↔ `iter_model_specs()` ↔ `Area2OperationalState` alignment. |
| **Coherent canonical path behavior** | Under **`testing_bootstrap_on`**, staged Runtime, Writers-Room HTTP, and Improvement HTTP show **eligible** `route_model` outcomes (not routine `no_eligible_adapter`), **selected adapter names**, and preflight **bounded_model_call** when adapters resolve — without relying on undocumented skip-only success. |
| **Practical authority convergence** | `AREA2_AUTHORITY_REGISTRY` lists `area2_operator_truth` and `area2_startup_profiles`; every response’s `canonical_authority_summary` states **`route_model`** authority and bounded vs runtime spec sources. LangGraph remains **compatibility-only** (unchanged). |
| **Operator-grade legibility** | `area2_operator_truth.legibility` compactly exposes **`authority_source`**, **`operational_state`**, **`route_status`**, **`selected_vs_executed`**, **`primary_operational_concern`**, **`startup_profile`** — all **derived** from existing traces and config (no new telemetry). |
| **Cross-surface operational truth** | Same **top-level** `area2_operator_truth` keys on Runtime, Writers-Room, and Improvement under the same profile. |
| **Honest residual boundaries** | CI does not claim real OpenAI/Ollama **story** coverage without credentials; empty global registry under **`testing_isolated`** is **expected**; bounded synthesis may use LangChain bridges without duplicating `bounded_model_call` on every trace field — routing eligibility and adapter resolution remain the gate. |

---

## Gate outcomes (PASS/FAIL)

| Gate | Result |
|------|--------|
| G-FINAL-01 Reproducible bootstrap | PASS |
| G-FINAL-02 Healthy canonical paths | PASS |
| G-FINAL-03 Practical authority convergence | PASS |
| G-FINAL-04 No-eligible non-normalization | PASS |
| G-FINAL-05 Operator legibility | PASS |
| G-FINAL-06 Cross-surface coherence | PASS |
| G-FINAL-07 Legacy compatibility | PASS |
| G-FINAL-08 Documentation and closure truth | PASS |

Prior evolution gates (**G-CONV-01** … **G-CONV-08**) remain enforced by existing tests; see [`area2_convergence_gates.md`](./area2_convergence_gates.md).

---

## Tests run and results

From repository root (or `backend/` as cwd):

```text
python -m pytest tests/runtime/test_area2_final_closure_gates.py tests/runtime/test_area2_convergence_gates.py tests/runtime/test_cross_surface_operator_audit_contract.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_model_inventory_bootstrap.py -q --tb=short --no-cov
```

Last verified: **40 passed** in ~38.5s, **0 failed** (local run, `--no-cov`).

---

## Startup-profile truth summary

- **`production_default`:** `Config` default `ROUTING_REGISTRY_BOOTSTRAP=True`; after `create_app`, `iter_model_specs()` is non-empty.
- **`testing_isolated`:** `TestingConfig` default bootstrap **off**; empty global registry expected; `Area2OperationalState.test_isolated` when classifying under pytest with empty registry.
- **`testing_bootstrap_on`:** pytest config subclass with bootstrap **on**; non-empty global registry after `create_app`; used for G-FINAL-02/G-FINAL-06 HTTP and Runtime proofs.
- **`production_bootstrap_disabled`:** non-test process with bootstrap **off**; `Area2OperationalState.intentionally_degraded` from classification rules.

Module: [`backend/app/runtime/area2_startup_profiles.py`](../../backend/app/runtime/area2_startup_profiles.py).

---

## Healthy canonical-path summary

- **Runtime:** `create_app` with bootstrap-on testing config + `execute_turn_with_ai` — routed stages do not routine-hit `no_eligible_adapter`.
- **Writers-Room / Improvement:** HTTP tests with `client_bootstrap_on` — `preflight` and `synthesis` decisions are not `no_eligible_adapter`, carry `selected_adapter_name`, and preflight sets `bounded_model_call` when the adapter resolves.

---

## Authority convergence summary

- Registry entries **`area2_operator_truth`** and **`area2_startup_profiles`** added to `AREA2_AUTHORITY_REGISTRY`.
- **`canonical_authority_summary`** on every `area2_operator_truth` payload documents `route_model`, `adapter_registry` vs `writers_room_model_routing`, and LangGraph non-canonical role.

---

## Operator-legibility summary

- Nested **`legibility`** object with deterministic **`route_status`** (e.g. `canonical_route_eligible`, `no_eligible_on_routed_stage_not_normalized_as_healthy`, `test_isolated_expected_empty_registry`, `misconfigured_registry_or_inventory`, `bootstrap_disabled_intentional_posture`).
- **`startup_profile`** inferred from `ROUTING_REGISTRY_BOOTSTRAP` + `pytest_session_active()` when config is known.

---

## Changed files (implementation)

- `backend/app/runtime/area2_startup_profiles.py` (new)
- `backend/app/runtime/area2_operator_truth.py` (legibility, route_status, canonical_authority_summary)
- `backend/app/runtime/area2_routing_authority.py` (registry entries)
- `backend/tests/conftest.py` (`TestingConfigWithRoutingBootstrap`, `app_bootstrap_on`, `client_bootstrap_on`, `auth_headers_bootstrap_on`)
- `backend/tests/runtime/test_area2_final_closure_gates.py` (new)
- `backend/tests/runtime/test_area2_convergence_gates.py` (truth shape + legibility keys)
- `docs/architecture/area2_final_closure_gates.md` (new)
- `docs/architecture/area2_final_operational_closure_report.md` (this file)
- `docs/architecture/llm_slm_role_stratification.md`
- `docs/architecture/ai_story_contract.md`

---

## Residual risks

- **Flask context:** `bootstrap_enabled` / `startup_profile` in legibility may be `null` when no app context exists on code paths that skip enrichment.
- **Global registry:** Tests must keep calling `clear_registry()` where isolation matters; bootstrap-on fixtures re-seed via `create_app` or `bootstrap_routing_registry_from_config`.
- **Parallel stacks:** Operators must still distinguish LangGraph `RoutingPolicy` from Task 2A evidence on canonical HTTP paths — documented in `canonical_authority_summary` and `AREA2_AUTHORITY_REGISTRY`.

---

## G-FINAL cross-reference (documentation gate)

This document explicitly references **G-FINAL-01**, **G-FINAL-02**, **G-FINAL-03**, **G-FINAL-04**, **G-FINAL-05**, **G-FINAL-06**, **G-FINAL-07**, **G-FINAL-08** and **`area2_routing_authority`** for **G-FINAL-08**. Prior gates **G-CONV-01** … **G-CONV-08** remain documented in [`area2_final_closure_gates.md`](./area2_final_closure_gates.md) and [`area2_convergence_gates.md`](./area2_convergence_gates.md).
