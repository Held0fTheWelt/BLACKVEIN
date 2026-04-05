# Model inventory seam map (Task 2 — frozen audit)

This document freezes the routing/registry seam map used for Task 2. It is the working truth unless code review finds a hard contradiction.

**Area 2 authority classification (machine-readable):** each component is classified exactly once in [`backend/app/runtime/area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py) (`AREA2_AUTHORITY_REGISTRY`). Canonical Runtime / Writers-Room / Improvement Task 2A paths do **not** treat `ai_stack` LangGraph `RoutingPolicy` as authoritative; that stack is **compatibility-only** relative to `route_model`.

## Registry stores ([`adapter_registry.py`](../../backend/app/runtime/adapter_registry.py))

- **Legacy map**: adapter name → `StoryAIAdapter` (`register_adapter`, `get_adapter`).
- **Model spec map**: adapter name → `AdapterModelSpec` (`register_adapter_model`, `iter_model_specs`, `get_model_spec`).
- **Stale-spec risk**: `register_adapter` after `register_adapter_model` replaces the instance only; the spec row is unchanged.

## Where specs are supplied

| Surface | `route_model` specs source | Executable adapter resolution |
|--------|----------------------------|------------------------------|
| Runtime staged ([`runtime_ai_stages.py`](../../backend/app/runtime/runtime_ai_stages.py)) | `specs=None` → `iter_model_specs()` | `get_adapter(selected_name)` else passed adapter |
| Runtime legacy single-pass ([`ai_turn_executor.py`](../../backend/app/runtime/ai_turn_executor.py)) | `iter_model_specs()` | Same |
| Writers-Room ([`writers_room_service.py`](../../backend/app/services/writers_room_service.py)) | `build_writers_room_model_route_specs()` | `workflow.adapters` keyed by provider / `selected_adapter_name` |
| Improvement ([`improvement_task2a_routing.py`](../../backend/app/services/improvement_task2a_routing.py)) | Same builder as Writers-Room | `build_default_model_adapters()` |

## Pre–Task 2 gap (resolved in Task 2)

- **Application code** did not call `register_adapter_model`; only tests did. Runtime therefore often saw an **empty** spec list and honest `no_eligible_adapter` while still executing via the passed adapter.
- **Improvement synthesis** used `WorkflowPhase.revision` + `TaskKind.revision_synthesis` while the shared `ModelSpec` → `AdapterModelSpec` mapping did not declare `revision_synthesis` for typical LLM registry entries, causing systematic under-coverage for that stage.

## Non-goals (unchanged)

- Cross-model routing policy semantics in [`model_routing.py`](../../backend/app/runtime/model_routing.py).
- `StoryAIAdapter` contract and guard/commit/reject authority in `execute_turn`.
- Conflation with [`role_contract.py`](../../backend/app/runtime/role_contract.py) (intra-call shape, not cross-model routing).
