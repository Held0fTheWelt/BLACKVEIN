# LLM / SLM role stratification (Tasks 2A / 2B)

## Scope (what exists today)

Task 2A adds a **canonical, model-aware routing core** in the backend runtime:

- **Contracts**: `backend/app/runtime/model_routing_contracts.py` — bounded enums, `AdapterModelSpec`, `RoutingRequest`, `RoutingDecision`.
- **Registry**: `backend/app/runtime/adapter_registry.py` — legacy `register_adapter` / `get_adapter` unchanged; `register_adapter_model` stores both the adapter instance and its spec; `clear_registry()` clears both stores.
- **Policy**: `backend/app/runtime/model_routing.py` — explicit `TASK_ROUTING_MODE` role matrix, deterministic **single-pass** `route_model()` (Task 2E staged policy inside one call), inspectable `RouteReasonCode`, `decision_factors`, `fallback_chain`, and `escalation_applied` / `degradation_applied` flags.

This layer chooses an **adapter name** (and echoes provider/model from the spec). It does **not** call providers itself.

### Task 2 — Operational model inventory (registry maturity)

Frozen seam map (where specs come from vs global registry): [`model_inventory_seam_map.md`](../reference/model_inventory_seam_map.md).

- **Contract**: `backend/app/runtime/model_inventory_contract.py` — required `(workflow_phase, task_kind, requires_structured_output)` tuples per surface (`runtime_staged`, `writers_room`, `improvement_bounded`). Used for coverage checks, not for routing policy.
- **Bootstrap**: `backend/app/runtime/routing_registry_bootstrap.py` — registers the real in-repo **`MockStoryAIAdapter`** with `register_adapter_model` and a broad `AdapterModelSpec` so Runtime paths that call `route_model()` without an explicit `specs=` argument see non-empty `iter_model_specs()` under normal app startup. Invoked from `create_app` in `backend/app/__init__.py`. Toggle with config **`ROUTING_REGISTRY_BOOTSTRAP`** (env `ROUTING_REGISTRY_BOOTSTRAP`, default true in `Config`). No fictional OpenAI/Claude **story** adapters are registered; production operators still register real `StoryAIAdapter` implementations plus matching specs when they add providers.
- **Writers-Room / Improvement shared specs**: `backend/app/services/writers_room_model_routing.py` maps `story_runtime_core` `ModelSpec` rows to `AdapterModelSpec`. LLM entries that already support narrative work **also** declare **`revision_synthesis`** so Improvement’s bounded revision-stage routing is covered. **`openai`** and **`ollama`** specs set **`degrade_targets: ["mock"]`**; the default **`mock`** row declares **all** `TaskKind` values so degrade chains remain eligible under the same phase/task filters. Routing policy (`route_model`) is unchanged; only registration metadata is disciplined.
- **Inventory / validation**: `backend/app/runtime/model_inventory_report.py` — `report_registry_inventory`, `validate_surface_coverage`, `inventory_summary_dict`, and small **setup classifiers** (`classify_no_eligible_setup` when the registry has zero specs vs honest exhaustion, `classify_policy_degradation` when `degradation_applied` is true). Deterministic only; not a telemetry pipeline.

**Area 2 — Task 2 registry/routing convergence (G-T2-01, G-T2-02, G-T2-03, G-T2-04, G-T2-05, G-T2-06, G-T2-07, G-T2-08):** Composes evolution/final proofs into one named suite; gate table [`area2_task2_closure_gates.md`](../../archive/architecture-legacy/area2_task2_closure_gates.md), PASS/FAIL report [`area2_registry_routing_convergence_closure_report.md`](../../archive/architecture-legacy/area2_registry_routing_convergence_closure_report.md), tests `backend/tests/runtime/test_runtime_routing_registry_composed_proofs.py`. Importable authority: [`area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py) (`AREA2_AUTHORITY_REGISTRY`). **One primary operational authority per canonical path**; translation/compatibility/support layers only when **explicit, bounded, and non-competing**.

**Area 2 — Dual workstream final closure (G-A-01, G-A-02, G-A-03, G-A-04, G-A-05, G-A-06, G-A-07, G-B-01, G-B-02, G-B-03, G-B-04, G-B-05, G-B-06, G-B-07):** Splits **practical convergence** (Workstream A) from **reproducibility / environment discipline** (Workstream B). Gate tables [`area2_workstream_a_gates.md`](../../archive/architecture-legacy/area2_workstream_a_gates.md), [`area2_workstream_b_gates.md`](../../archive/architecture-legacy/area2_workstream_b_gates.md); combined report [`area2_dual_workstream_closure_report.md`](../../archive/architecture-legacy/area2_dual_workstream_closure_report.md); binding terms [`area2_dual_workstream_binding.md`](../../archive/architecture-legacy/area2_dual_workstream_binding.md). Tests: `backend/tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py` (G-A), `backend/tests/runtime/test_runtime_startup_profiles_operator_truth.py` (G-B). **Authority:** `area2_routing_authority`. **Canonical validation commands:** `area2_validation_commands` (`backend/app/runtime/area2_validation_commands.py`). **Routing policy and authoritative Runtime semantics remain unchanged.**
- **Registry keys helper**: `adapter_registry.snapshot_registry_keys()` for sorted legacy vs spec name lists.

**Healthy coverage**: `validate_surface_coverage` passes for all three surfaces when `iter_model_specs()` is populated (after `bootstrap_routing_registry_from_config` or non-test `create_app` with bootstrap enabled) and when using `build_writers_room_model_route_specs()` for bounded HTTP paths. **`TestingConfig` sets `ROUTING_REGISTRY_BOOTSTRAP = False`** so pytest does not pollute the process-global registry; opt-in subclasses or explicit bootstrap calls cover wiring tests.

**Still out of scope after Task 2**: multi-provider **story** adapter packs beyond what the repo registers; distributed routing control planes; any change to `route_model` precedence or Task 1 Runtime authority.

### Task 2B — where routing is wired

- **Canonical runtime AI path** (`execute_turn_with_ai` in `backend/app/runtime/ai_turn_executor.py`): **Task 1** adds **multi-stage Runtime orchestration** in `backend/app/runtime/runtime_ai_stages.py` when `runtime_staged_orchestration` is not disabled in session metadata (default: enabled). The pipeline runs **preflight** (`WorkflowPhase.preflight`, `TaskKind.cheap_preflight`), **signal / consistency** (`WorkflowPhase.interpretation`, `TaskKind.repetition_consistency_check`), then **ranking** (`WorkflowPhase.interpretation`, `TaskKind.ranking`) as separate `RoutingRequest` shapes. When the signal base gate already allows **SLM-only** (`needs_llm_synthesis` false), **ranking** is still traced with the **intended** ranking request, **`decision: null`**, **no `route_model` call**, **no bounded call**, and `skip_reason: ranking_not_required_signal_allows_slm_only` (binding). When the base gate **requires or allows** synthesis, **ranking** runs **`route_model` + bounded `generate`** when eligible; its **bounded `RankingStageOutput`** feeds **`compute_synthesis_gate_after_ranking`** (ranked-skip, ranked-then-synthesis, or explicit degraded reasons). **LLM-heavy synthesis** (`WorkflowPhase.generation`, session-configured task kind, default `narrative_formulation`) runs when the **merged** gate requires it. Otherwise deterministic **SLM-only packaging** builds canonical structured story JSON — still advisory; **guards, commit, and reject semantics in `execute_turn` are unchanged**. When stages have **no eligible adapter**, traces record honest `skip_reason` values and the pipeline **degrades** as implemented (including ranking no-eligible fallback to the signal gate). **`model_routing_trace`** remains a **legacy-shaped rollup** with additive **`ranking_context`** and optional **`slm_only_after_ranking_skip`** when ranking drove a synthesis skip; per-stage detail lives in **`runtime_stage_traces`** and **`runtime_orchestration_summary`**. Each routed stage record may embed **`routing_evidence`** via `attach_stage_routing_evidence` when a routing decision exists. **Supervisor `agent_orchestration`** **preempts** the staged pipeline; `runtime_orchestration_summary` records `staged_pipeline_preempted: agent_orchestration`. Set **`runtime_staged_orchestration: false`** to restore the legacy single `route_model` + single generate path (used for regression tests). **Task 2C-2** `routing_evidence` on the rollup trace behaves as before where applicable. **Task 2D** alignment/deviation fields apply per nested stage evidence when populated. Closure: [`area2_runtime_ranking_closure_report.md`](../../archive/architecture-legacy/area2_runtime_ranking_closure_report.md). **Task 1B (canonical ranking closure)** additionally mirrors `runtime_orchestration_summary` ranking fields into **`operator_audit.audit_summary`** and **`area2_operator_truth.legibility.runtime_ranking_summary`** on the default staged Runtime path (no new telemetry; values copied from existing summary facts). Gates: **G-CANON-RANK-01 .. G-CANON-RANK-08** in `backend/tests/runtime/test_runtime_ranking_closure_gates.py`.
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
- **Runtime Task 1 (implemented)**: chained **preflight → signal → ranking → conditional synthesis** (with honest suppressed-ranking trace on SLM-only) and inspectable traces; not “full stack” observability beyond the documented JSON surfaces.

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

The primary code `escalation_due_to_structured_output_gap` fires only when `requires_structured_output` is true **and** structured-output filtering changes the **selected primary adapter** compared to a counterfactual evaluation on the full pre-structured eligible set (`eligible_all` through the same stages). Global shrinkage of the eligible list alone is **not** sufficient. The staged Task 2E ordering inside **each** `route_model` call is unchanged. **Task 1** composes multiple such calls across Runtime stages; it does not change Task 2E’s internal precedence.

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

Task 2F adds **additive** keys on the same `routing_evidence` object. It does **not** change `route_model`, guard/commit/reject semantics, or **authoritative** Runtime execution. **Task 1** may attach Task 2F diagnostics **per stage** inside `runtime_stage_traces` entries where `routing_evidence` is present.

- **`diagnostics_overview`**: `{ title, summary, severity, operator_hint, short_explanation }`.
  - **`summary`** uses a **small fixed vocabulary** (e.g. `Primary route`, `Escalated route`, `Fallback route`, `No eligible spec`, `Execution deviation`, `Degraded route`) so operators can scan outcomes quickly.
  - When **`execution_deviation`** is present, the compact layer **prioritizes** `Execution deviation` so policy-vs-execution mismatch is obvious; `short_explanation` appends adapter names and any real `note` only.
  - **`operator_hint`** is chosen from a **fixed allowlist** using deterministic priority rules over existing evidence (e.g. registration gaps, structured-output gap, passed-adapter fallback). It is not free-form advice.
  - **`short_explanation`** reuses the honest long-form text from `routing_overview["summary"]` and may append a bounded clause when execution deviated.
- **`diagnostics_flags`**: compact booleans mirroring evidence already on the payload (`escalation_applied`, `degradation_applied`, `no_eligible_spec_selection`, `policy_execution_aligned`, `fallback_to_passed_adapter`, `bounded_model_call`, `has_execution_deviation`).
- **`diagnostics_causes`**: ordered `{ code, detail }` entries built only from allowlisted `decision_factors`, `skip_reason`, `no_eligible_spec` / `failure`, and `execution_deviation`. It does **not** infer causes the policy did not record.

**Compact vs deep evidence**: The **deep** truth remains `route_reason_code`, `decision_factors` (full, on `RoutingDecision` / trace `decision`), `fallback_chain`, `routing_diagnostics`, alignment/deviation fields, and bounded-call metadata. The Task 2F layer is a **deterministic index** over that truth — clearer for operators, not smarter than routing.

**Honesty limits**: Diagnostics cannot claim telemetry, counterfactuals, or registration state that is not reflected in the evidence dict. They do not replace reading `decision` or specs when debugging.

### Task 3 — operator audit surface (derived-only)

Task 3 adds **`operator_audit`** payloads computed in `backend/app/runtime/operator_audit.py`. Every field is **deterministically derived** from evidence the pipeline already produced (`routing_evidence`, Task 2F `diagnostics_*`, stage traces, orchestration summary keys). It does **not** add routing policy, adapter behavior, guard/commit/reject rules, extra Runtime stages, or a distributed immutable audit log.

**Diagnostics vs operator audit**

- **Diagnostics (Task 2F)** remain on **`routing_evidence`**: per routing decision, compact `diagnostics_overview` / `diagnostics_flags` / `diagnostics_causes`.
- **Operator audit** is an **additional** cross-cut: ordered **`audit_timeline`** (stage key, bounded-call/skip, route reason echo, diagnostics route class / severity, error count), rollup **`audit_flags`** and **`audit_deviations`**, **`audit_summary`** (surface name, Runtime `final_path` and synthesis gate reason when present, max diagnostics severity, deterministic **`primary_concern_code`** from merged cause codes), and **`audit_review_fingerprint`** for diff-friendly stable rows. Deep truth stays in full traces and `decision` / `routing_evidence`.

**Runtime**

- **`AIDecisionLog.operator_audit`** is populated for staged, legacy single-route, and orchestration-preempted paths (preempted uses a single synthetic timeline row tied to the rollup `routing_evidence` when present).
- Additive **`runtime_orchestration_summary`** keys (legacy `stages_skipped` unchanged): **`stages_without_bounded_model_call_by_design`** lists stages such as **`packaging`** that never invoke a model by design; **`stages_skipped_no_eligible_adapter`** lists stages where `bounded_model_call` is false and the `skip_reason` indicates no eligible adapter. This separates packaging from “routing skipped the call.”
- **SLM-only** orchestration summary exposes **`synthesis_gate_reason`** as well as **`synthesis_skip_reason`** (same value) for a consistent gate-reason field.
- Model stages in traces include **`stage_kind`**: `routed_model_stage`; packaging stages use **`stage_kind`**: `packaging` and **`orchestration_role`**.

**Writers-Room and Improvement**

- Workflow / recommendation payloads include top-level **`operator_audit`** with the same **`audit_schema_version`** and shape as Runtime where meanings align.
- Bounded traces keep **`stage`**; Task 3 adds **`stage_id`** as an **alias** equal to **`stage`** for comparison with Runtime’s `stage_id`.

**Honesty limits (audit)**

- No new causal claims: `primary_concern_code` is chosen from a fixed priority table over **`diagnostics_causes`** codes already emitted.
- Audit does not certify external systems, storage durability, or tamper evidence.

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

**Task 1** implements **bounded** multi-stage Runtime orchestration; it does **not** add new guard rules, autonomous multi-turn editorial agents, or product-wide telemetry. **Authoritative truth** for governance and engine state remains outside model output; stage outputs and traces are **observability and advisory packaging** only. Optional **legacy** single-pass behavior remains available via `runtime_staged_orchestration: false`.

### Task 4 — Validation surface (no semantic redesign)

Task 4 tightens **proof** and **drift resistance** without changing Task 2E routing precedence, Task 1 stage contracts, or Task 3 derivation rules.

**Area 2 Task 4 closure gates (G-T4-01 … G-T4-08):** [`area2_task4_closure_gates.md`](../../archive/architecture-legacy/area2_task4_closure_gates.md). **Validation hardening closure report:** [`area2_validation_hardening_closure_report.md`](../../archive/architecture-legacy/area2_validation_hardening_closure_report.md). **Canonical pytest list:** [`backend/app/runtime/area2_validation_commands.py`](../../backend/app/runtime/area2_validation_commands.py) — `AREA2_TASK4_FULL_CLOSURE_PYTEST_MODULES`, `area2_task4_full_closure_pytest_invocation`. **Gate enforcement:** `backend/tests/runtime/test_runtime_validation_commands_orchestration.py`. **G-T4-01** three-surface E2E contract truth; **G-T4-02** bootstrap validation; **G-T4-03** cross-surface compact contract; **G-T4-04** negative/degraded honesty; **G-T4-05** drift resistance; **G-T4-06** validation-command reality; **G-T4-07** proof-suite subprocess stability; **G-T4-08** documentation truth. Setup reference: [`docs/testing-setup.md`](../../testing-setup.md).

- **Seam map:** [`task4_validation_seam_map.md`](../../archive/architecture-legacy/task4_validation_seam_map.md) — baseline coverage vs gaps closed by tests.
- **Hardening gates:** [`task4_hardening_gates.md`](../../archive/architecture-legacy/task4_hardening_gates.md) — explicit gate IDs (G-RUN-*, G-BOOT-*, G-XS-*, G-NEG-*, G-DRIFT-01, G-DOC-01).
- **Closure:** [`task4_maturity_hardening_closure_report.md`](../../archive/architecture-legacy/task4_maturity_hardening_closure_report.md).

**E2E truths actually established in tests (honest scope):** multi-stage Runtime paths including degraded `final_path` values, preempted supervisor path `operator_audit`, tool-loop ordering after staged synthesis emits a tool request, registry bootstrap via real `create_app`, Improvement bounded-call skip when adapters are missing, and cross-surface operator-audit / routing-evidence key alignment where surfaces share shapes. **Not** a claim of full production E2E audit on every session smoke test.

### Area 2 — Operational routing/registry convergence (G-CONV)

**Authority (frozen, importable):** [`backend/app/runtime/area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py) — `AREA2_AUTHORITY_REGISTRY` classifies each seam as exactly one of `authoritative`, `translation_layer`, `compatibility_layer`, or `non_authoritative_support`. Task 2A **policy** remains solely `route_model`; `ai_stack` LangGraph uses `story_runtime_core.RoutingPolicy` for a **parallel compatibility** graph path and is **not** authoritative for canonical Runtime / Writers-Room / Improvement HTTP paths.

**Operational state:** [`backend/app/runtime/area2_operational_state.py`](../../backend/app/runtime/area2_operational_state.py) — `Area2OperationalState` (`healthy`, `intentionally_degraded`, `misconfigured`, `test_isolated`) describes bootstrap/process health. **`NoEligibleDiscipline`** (same module) classifies no-eligible and adjacent skip outcomes separately from that enum (true no-eligible vs empty registry vs test isolation vs bounded executor mismatch).

**Operator truth (additive):** [`backend/app/runtime/area2_operator_truth.py`](../../backend/app/runtime/area2_operator_truth.py) attaches `area2_operator_truth` to `operator_audit` on Runtime, Writers-Room, and Improvement — authority source, bootstrap flag when known, spec counts used for routing on that surface, coverage snapshot, selected vs executed summary, primary concern, operational state, and no-eligible discipline rollup. **No new telemetry**; values are derived from existing traces and explicit counts.

**Convergence gates:** [`area2_convergence_gates.md`](../../archive/architecture-legacy/area2_convergence_gates.md) — **G-CONV-01**, **G-CONV-02**, **G-CONV-03**, **G-CONV-04**, **G-CONV-05**, **G-CONV-06**, **G-CONV-07**, **G-CONV-08** (single authority, healthy bootstrap, state classification, no-eligible discipline, operator truth, legacy compatibility, documentation truth, cross-surface coherence). **Closure:** [`area2_evolution_closure_report.md`](../../archive/architecture-legacy/area2_evolution_closure_report.md).

**Final operational closure gates:** [`area2_final_closure_gates.md`](../../archive/architecture-legacy/area2_final_closure_gates.md) — **G-FINAL-01**, **G-FINAL-02**, **G-FINAL-03**, **G-FINAL-04**, **G-FINAL-05**, **G-FINAL-06**, **G-FINAL-07**, **G-FINAL-08** (reproducible bootstrap, healthy canonical paths, practical authority convergence, no-eligible non-normalization, operator legibility, cross-surface coherence, legacy compatibility, documentation truth). Named startup profiles: [`backend/app/runtime/area2_startup_profiles.py`](../../backend/app/runtime/area2_startup_profiles.py). **Final report:** [`area2_final_operational_closure_report.md`](../../archive/architecture-legacy/area2_final_operational_closure_report.md).

**Task 3 operator comparison (Area 2 closure):** **G-T3-01**, **G-T3-02**, **G-T3-03**, **G-T3-04**, **G-T3-05**, **G-T3-06**, **G-T3-07**, **G-T3-08** — explicit cross-surface **`compact_operator_comparison`** on `operator_audit.area2_operator_truth` with grammar version **`area2_operator_comparison_v1`** (see [`area2_operator_truth.py`](../../backend/app/runtime/area2_operator_truth.py)). Bounded surfaces use the same mandatory keys with explicit `null` for Runtime-only slots (e.g. `runtime_path_summary`). Gate table: [`area2_task3_closure_gates.md`](../../archive/architecture-legacy/area2_task3_closure_gates.md). Closure report: [`area2_operator_comparison_closure_report.md`](../../archive/architecture-legacy/area2_operator_comparison_closure_report.md). Tests: `backend/tests/runtime/test_runtime_operator_comparison_cross_surface.py`.

**Unchanged:** `route_model` precedence and semantics, `StoryAIAdapter`, guard/commit/reject authority, and authoritative Runtime mutation rules.

## Honest limits

- **Tier and alignment scores** are deterministic heuristics until production telemetry informs tuning.
- **`RouteReasonCode`**: the enum is fixed; **Task 2E** documents the precedence above. Do not attribute a reason code unless that branch fired; counterfactual reasons (`latency_constraint`, `cost_constraint`) require the internal neutral-budget / neutral-sensitivity re-pick to differ on the same final candidate pool.
- **Registry consistency**: `register_adapter(name, ...)` does not update or remove an existing spec for the same name; mixed use of legacy and spec registration for one name can leave stale metadata — prefer `register_adapter_model` when specs are in play.
- **Empty spec store**: if bootstrap is disabled and nothing called `register_adapter_model`, `iter_model_specs()` is empty and routing yields `no_eligible_adapter`; Runtime integration **still** falls back to the passed executable adapter. Use `classify_no_eligible_setup(registry_spec_count=0)` to distinguish that **setup gap** from **true** no-eligible when specs exist but no row matches phase/task/structure filters.