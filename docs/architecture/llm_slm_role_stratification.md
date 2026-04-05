# LLM / SLM role stratification (Tasks 2A / 2B)

## Scope (what exists today)

Task 2A adds a **canonical, model-aware routing core** in the backend runtime:

- **Contracts**: `backend/app/runtime/model_routing_contracts.py` — bounded enums, `AdapterModelSpec`, `RoutingRequest`, `RoutingDecision`.
- **Registry**: `backend/app/runtime/adapter_registry.py` — legacy `register_adapter` / `get_adapter` unchanged; `register_adapter_model` stores both the adapter instance and its spec; `clear_registry()` clears both stores.
- **Policy**: `backend/app/runtime/model_routing.py` — explicit `TASK_ROUTING_MODE` role matrix, deterministic **single-pass** `route_model()` (Task 2E staged policy inside one call), inspectable `RouteReasonCode`, `decision_factors`, `fallback_chain`, and `escalation_applied` / `degradation_applied` flags.

This layer chooses an **adapter name** (and echoes provider/model from the spec). It does **not** call providers itself.

### Task 2B — where routing is wired

- **Canonical runtime AI path** (`execute_turn_with_ai` in `backend/app/runtime/ai_turn_executor.py`): builds a minimal `RoutingRequest` from session/context, calls `route_model(...)` **once** before adapter execution, resolves the executable adapter by name, and falls back to the caller-supplied adapter when no eligible spec-backed adapter exists (e.g. `no_eligible_adapter`). Guard legality, commit semantics, and reject behavior are unchanged. A compact **`model_routing_trace`** is attached to `AIDecisionLog` (full `RoutingRequest` / `RoutingDecision` JSON plus legacy fields). **Task 2C-2** adds a nested **`routing_evidence`** object with a stable cross-surface summary (`requested_workflow_phase`, `requested_task_kind`, selected vs executed adapter, `route_reason_code`, `fallback_chain`, flags, `no_eligible_spec_selection`, runtime-only `passed_adapter_name` / `fallback_to_passed_adapter`). **Task 2D** adds `policy_execution_aligned` and `execution_deviation` where the implementation can know them. This is observability for operators, not a telemetry product.
- **Writers Room** (`backend/app/services/writers_room_service.py`): model choice no longer uses `story_runtime_core.RoutingPolicy`. Specs are built via `backend/app/services/writers_room_model_routing.py` and **two honest routing stages** call `route_model`: **Stage A** (preflight / cheap task kinds) as an optional bounded model call when a routed adapter resolves; **Stage B** (synthesis / generation). `model_generation.task_2a_routing` exposes `preflight` / `synthesis` traces; each stage includes **`routing_evidence`** in the same normalized shape as runtime (bounded-call / skip fields filled where applicable; synthesis uses the provider that actually produced content when known).
- **Improvement** (`backend/app/api/v1/improvement_routes.py` + `backend/app/services/improvement_task2a_routing.py`): after the deterministic recommendation package is built, **two** `route_model` stages (preflight + synthesis, same spec source as Writers Room) attach **`task_2a_routing`** and **`model_assisted_interpretation`** to the persisted recommendation package. Sandbox metrics and threshold-based recommendation labels remain the truth-bearing base; `deterministic_recommendation_base` is set before transcript suffixes. Bounded model calls are optional; traces stay honest when no adapter resolves (`no_eligible_adapter_or_missing_provider_adapter`). Each stage carries **`routing_evidence`** aligned with the shared helper in `backend/app/runtime/model_routing_evidence.py`.

Shared helper: **`backend/app/runtime/model_routing_evidence.py`** — `build_routing_evidence`, `attach_stage_routing_evidence` (Writers Room / Improvement stages).

## Not the same as `role_contract.py`

`backend/app/runtime/role_contract.py` defines **interpreter / director / responder** sections inside **one** structured adapter output. That is an **intra-call** shape contract.

Task 2A routing is **cross-model** stratification: which registered adapter (LLM-class vs SLM-class, tier, cost/latency metadata) should handle a **routing request** described by workflow phase and task kind. Keep the two concepts separate.

## Role matrix (encoded in code)

`TASK_ROUTING_MODE` maps each `TaskKind` to:

- **SLM-first**: `classification`, `trigger_signal_extraction`, `repetition_consistency_check`, `ranking`, `cheap_preflight`
- **LLM-first**: `scene_direction`, `conflict_synthesis`, `narrative_formulation`, `social_narrative_tradeoff`, `revision_synthesis`
- **Escalation-sensitive**: `ambiguity_resolution`, `continuity_judgment`, `high_stakes_narrative_tradeoff` — with optional `EscalationHint` values (including `ambiguity_high`, `conflict_dense`, `continuity_risk`, `social_tradeoff_high`, `unreliable_low_cost_candidate`, plus legacy `prefer_llm` / `high_stakes`) to steer LLM-class pools when both classes are eligible.

## Task 2C status (honest scope)

- **2C-1**: Improvement HTTP path uses Task-2A routing as **bounded enrichment** around the deterministic evaluation core (no model override of governance or threshold semantics).
- **2C-2**: **Normalized `routing_evidence`** is shared across Runtime (`model_routing_trace`), Writers Room (`task_2a_routing` stages), and Improvement (`task_2a_routing` stages). This does **not** add new dashboards, product-wide telemetry, or deeper `RouteReasonCode` semantics than `route_model` actually emits.
- **Still not claimed**: multi-stage narrative pipelines in runtime (still **route once, execute one adapter** per turn), or “full stack” observability beyond these JSON surfaces.

## Task 2E (escalation policy — single evaluation, honest semantics)

Task 2E **does not** add a second routing pipeline or Runtime multi-stage orchestration. `route_model` still runs **once** per routing decision; stages are **internal** ordering for exclusions, constraints, ranking, and reason assignment.

### Stages inside `route_model` (deterministic)

1. **Hard exclusions** — drop unsupported phase/task specs; optionally drop low structured-output reliability when `requires_structured_output`. If nothing remains → `no_eligible_adapter` (terminates).
2. **Mandatory escalation constraints** — may narrow to LLM-class specs when: task kind is high-stakes (`ambiguity_resolution`, `continuity_judgment`, `high_stakes_narrative_tradeoff`); or escalation-sensitive task with non-empty `escalation_hints`; or `complexity=high` on a synthesis-heavy path (`revision_synthesis`, `conflict_synthesis`, `narrative_formulation`, `social_narrative_tradeoff`, or `ranking` **only** when `workflow_phase` is `generation` or `revision`) while an LLM-class spec exists in the eligible set.
3. **Role-family preference** — apply `TASK_ROUTING_MODE` (`slm_first` / `llm_first` / `escalation_sensitive`) on the working set.
4. **Quality ranking** — deterministic `_pick_primary` / tier and cost/latency alignment keys (same spirit as Task 2A).
5. **Cost / latency optimization** — reflected in the pick keys; **primary** `latency_constraint` / `cost_constraint` only when counterfactual re-picks on the **same final pool** with neutral budget/sensitivity would change the winner.
6. **Widening / fallback** — `fallback_chain` from `degrade_targets`; `fallback_only` when the preferred role-family pool was empty **without** mandatory LLM narrowing forcing the widen. `degradation_applied` is true when the preferred pool was widened **or** when structured-output rules materially change the deterministic primary versus the same staged policy run on the full pre-structured candidate set (Task 2E-R1 — not merely because some ineligible-for-structure specs disappeared from the global set).

### Task 2E-R1 (narrow structured-output gap)

The primary code `escalation_due_to_structured_output_gap` fires only when `requires_structured_output` is true **and** structured-output filtering changes the **selected primary adapter** compared to a counterfactual evaluation on the full pre-structured eligible set (`eligible_all` through the same stages). Global shrinkage of the eligible list alone is **not** sufficient. The staged Task 2E ordering inside `route_model` is unchanged; deep Runtime multi-stage orchestration remains out of scope.

### Hard vs soft escalation signals

- **Hard (can force primary escalation codes or mandatory LLM pool)**: **material** structured-output gap (strict primary differs from the pre-structured counterfactual primary); high-stakes task kinds with SLM still eligible and LLM selected; non-empty hints on escalation-sensitive tasks with SLM still eligible and LLM selected; high complexity on synthesis-heavy generation/revision when the medium-complexity counterfactual would pick a different adapter.
- **Soft (informational `decision_factors` only)**: e.g. `soft_preferred_reliability_pressure`, `soft_synthesis_heavy_context`, `soft_widened_or_degraded_pool` — they do **not** add extra primary reason codes.

### Primary `RouteReasonCode` precedence (exactly one primary)

1. `no_eligible_adapter`
2. `escalation_due_to_structured_output_gap`
3. `escalation_due_to_explicit_hint`
4. `escalation_due_to_high_stakes_task`
5. `escalation_due_to_complexity`
6. `fallback_only` (preferred pool empty **without** mandatory LLM narrowing)
7. `latency_constraint` then `cost_constraint` (counterfactual must prove the winner changed; latency wins if both would change)
8. `role_matrix_primary`

Legacy enum values `structured_output_required` and `escalation_applied` remain for **ingesting old traces**; current `route_model` emits the Task 2E codes above.

`decision_factors` may include: `escalation_trigger`, `structured_output_gap` (material gap only; mirrors the primary structured-output escalation branch), `explicit_hint_present`, `preferred_pool_empty`, `mandatory_llm_pool_applied`, `selected_outside_preferred_role_family` (when true), `counterfactual_latency_changed`, `counterfactual_cost_changed`, plus soft keys listed in code.

### `routing_overview` (derived summary, not independent reasoning)

`build_routing_evidence` adds `routing_overview`: `{ title, summary, severity }` from a **fixed table** keyed by the emitted `route_reason_code` (and `no_eligible_spec_selection`). It is a human-readable index over policy output — not a second model or narrative generator. Optional `routing_diagnostics` echoes a small allowlist of `decision_factors` keys when present.

This field is **unchanged** for backward compatibility. It keeps the Task 2E long-form `summary` sentence per reason code.

### Task 2F — compact operator diagnostics (readability only)

Task 2F adds **additive** keys on the same `routing_evidence` object. It does **not** change `route_model`, guard/commit/reject semantics, or Runtime orchestration (still route once, execute one adapter per canonical turn).

- **`diagnostics_overview`**: `{ title, summary, severity, operator_hint, short_explanation }`.
  - **`summary`** uses a **small fixed vocabulary** (e.g. `Primary route`, `Escalated route`, `Fallback route`, `No eligible spec`, `Execution deviation`, `Degraded route`) so operators can scan outcomes quickly.
  - When **`execution_deviation`** is present, the compact layer **prioritizes** `Execution deviation` so policy-vs-execution mismatch is obvious; `short_explanation` appends adapter names and any real `note` only.
  - **`operator_hint`** is chosen from a **fixed allowlist** using deterministic priority rules over existing evidence (e.g. registration gaps, structured-output gap, passed-adapter fallback). It is not free-form advice.
  - **`short_explanation`** reuses the honest long-form text from `routing_overview["summary"]` and may append a bounded clause when execution deviated.
- **`diagnostics_flags`**: compact booleans mirroring evidence already on the payload (`escalation_applied`, `degradation_applied`, `no_eligible_spec_selection`, `policy_execution_aligned`, `fallback_to_passed_adapter`, `bounded_model_call`, `has_execution_deviation`).
- **`diagnostics_causes`**: ordered `{ code, detail }` entries built only from allowlisted `decision_factors`, `skip_reason`, `no_eligible_spec` / `failure`, and `execution_deviation`. It does **not** infer causes the policy did not record.

**Compact vs deep evidence**: The **deep** truth remains `route_reason_code`, `decision_factors` (full, on `RoutingDecision` / trace `decision`), `fallback_chain`, `routing_diagnostics`, alignment/deviation fields, and bounded-call metadata. The Task 2F layer is a **deterministic index** over that truth — clearer for operators, not smarter than routing.

**Honesty limits**: Diagnostics cannot claim telemetry, counterfactuals, or registration state that is not reflected in the evidence dict. They do not replace reading `decision` or specs when debugging.

### `routing_evidence` (shared shape)

Built by `build_routing_evidence` in `backend/app/runtime/model_routing_evidence.py`:

- **Requested route**: `requested_workflow_phase`, `requested_task_kind` (from `RoutingRequest`).
- **Selected route**: `selected_adapter_name`, `selected_provider`, `selected_model`, plus `route_reason_code`, `routing_overview`, **Task 2F** `diagnostics_overview` / `diagnostics_flags` / `diagnostics_causes`, `fallback_chain`, `escalation_applied`, `degradation_applied`, optional `routing_diagnostics`.
- **Executed adapter**: `executed_adapter_name` when the caller knows what actually ran.
- **`policy_execution_aligned`**: `True` / `False` when knowable; `null` when there is no policy selection or execution is unknown (e.g. `no_eligible_spec_selection`, or stage did not run a bounded call). Runtime uses `resolved_via_get_adapter`; Writers Room / Improvement compare normalized names when registry flags are absent.
- **`execution_deviation`**: object only when selected and executed names differ; optional `note` from real paths (e.g. Writers Room `raw_fallback_reason`). No fabricated explanations.
- **Bounded skip path**: `bounded_model_call` false with `skip_reason` (e.g. `no_eligible_adapter_or_missing_provider_adapter`).

### Registry helpers (Task 2D)

- `has_model_spec(name)` — spec registered for routing.
- `legacy_adapter_without_model_spec(name)` — instance without spec (routing ignores that name for `iter_model_specs`).
- Calling `register_adapter` after `register_adapter_model` **replaces only the adapter instance**; the **spec entry is unchanged** (stale-metadata risk). Prefer `register_adapter_model` when specs matter; see tests.

### Still out of scope

Deep **multi-stage Runtime orchestration** (chained SLM→LLM narrative pipelines inside `execute_turn_with_ai`) remains **out of scope**. Runtime stays **route once, execute one adapter** per canonical turn. **Authoritative truth** for governance and engine state does not move into model output; routing traces are observability only.

## Honest limits

- **Tier and alignment scores** are deterministic heuristics until production telemetry informs tuning.
- **`RouteReasonCode`**: the enum is fixed; **Task 2E** documents the precedence above. Do not attribute a reason code unless that branch fired; counterfactual reasons (`latency_constraint`, `cost_constraint`) require the internal neutral-budget / neutral-sensitivity re-pick to differ on the same final candidate pool.
- **Registry consistency**: `register_adapter(name, ...)` does not update or remove an existing spec for the same name; mixed use of legacy and spec registration for one name can leave stale metadata — prefer `register_adapter_model` when specs are in play.
- **Environments without `register_adapter_model`**: routing often yields `no_eligible_adapter`; runtime integration **must** keep the honest fallback to the already supplied executable adapter.