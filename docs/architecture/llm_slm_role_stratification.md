# LLM / SLM role stratification (Tasks 2A / 2B)

## Scope (what exists today)

Task 2A adds a **canonical, model-aware routing core** in the backend runtime:

- **Contracts**: `backend/app/runtime/model_routing_contracts.py` — bounded enums, `AdapterModelSpec`, `RoutingRequest`, `RoutingDecision`.
- **Registry**: `backend/app/runtime/adapter_registry.py` — legacy `register_adapter` / `get_adapter` unchanged; `register_adapter_model` stores both the adapter instance and its spec; `clear_registry()` clears both stores.
- **Policy**: `backend/app/runtime/model_routing.py` — explicit `TASK_ROUTING_MODE` role matrix, deterministic `route_model()`, inspectable `RouteReasonCode`, `decision_factors`, `fallback_chain`, and `escalation_applied` / `degradation_applied` flags.

This layer chooses an **adapter name** (and echoes provider/model from the spec). It does **not** call providers itself.

### Task 2B — where routing is wired

- **Canonical runtime AI path** (`execute_turn_with_ai` in `backend/app/runtime/ai_turn_executor.py`): builds a minimal `RoutingRequest` from session/context, calls `route_model(...)` **once** before adapter execution, resolves the executable adapter by name, and falls back to the caller-supplied adapter when no eligible spec-backed adapter exists (e.g. `no_eligible_adapter`). Guard legality, commit semantics, and reject behavior are unchanged. A compact **`model_routing_trace`** is attached to `AIDecisionLog` for minimal routing evidence (invocation, phase/task kind, selected vs executed adapter, fallback when applicable, escalation/degradation flags when present on the decision).
- **Writers Room** (`backend/app/services/writers_room_service.py`): model choice no longer uses `story_runtime_core.RoutingPolicy`. Specs are built via `backend/app/services/writers_room_model_routing.py` and **two honest routing stages** call `route_model`: **Stage A** (preflight / cheap task kinds) as an optional bounded model call when a routed adapter resolves; **Stage B** (synthesis / generation). Payload/report fields expose `task_2a_routing` and related digest flags so the path is inspectable. This is **not** full observability closure across the stack.

Improvement flows and other world-engine paths remain **outside** Task 2B scope.

## Not the same as `role_contract.py`

`backend/app/runtime/role_contract.py` defines **interpreter / director / responder** sections inside **one** structured adapter output. That is an **intra-call** shape contract.

Task 2A routing is **cross-model** stratification: which registered adapter (LLM-class vs SLM-class, tier, cost/latency metadata) should handle a **routing request** described by workflow phase and task kind. Keep the two concepts separate.

## Role matrix (encoded in code)

`TASK_ROUTING_MODE` maps each `TaskKind` to:

- **SLM-first**: `classification`, `trigger_signal_extraction`, `repetition_consistency_check`, `ranking`, `cheap_preflight`
- **LLM-first**: `scene_direction`, `conflict_synthesis`, `narrative_formulation`, `social_narrative_tradeoff`, `revision_synthesis`
- **Escalation-sensitive**: `ambiguity_resolution`, `continuity_judgment`, `high_stakes_narrative_tradeoff` — with optional `EscalationHint` values to prefer LLM-class adapters when both classes are eligible.

## Deferred work (Task 2C)

- **Full observability closure** (unified traces, governance dashboards, improvement-loop integration) and broader routing consumers remain deferred.
- Task 2B deliberately adds only **minimum routing evidence** on the runtime log and Writers Room payload; it does not redefine guards, commits, or authoritative state mutation.

## Honest limits

- **Tier and alignment scores** are deterministic heuristics until production telemetry informs tuning.
- **`RouteReasonCode`**: the contract enumerates rich reason codes; **not every code is actively produced as the primary policy output** in all paths — do not overclaim finer-grained routing narratives than the current `route_model` implementation returns.
- **Registry consistency**: `register_adapter(name, ...)` does not update or remove an existing spec for the same name; mixed use of legacy and spec registration for one name can leave stale metadata — prefer `register_adapter_model` when specs are in play.
- **Environments without `register_adapter_model`**: routing often yields `no_eligible_adapter`; runtime integration **must** keep the honest fallback to the already supplied executable adapter.