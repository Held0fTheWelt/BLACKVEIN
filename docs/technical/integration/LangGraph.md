# LangGraph integration

LangGraph owns **runtime-supporting turn orchestration** inside the AI stack while **world-engine** remains the authority that **commits** session history and diagnostics.

## Runtime turn graph

Implementation: `ai_stack/langgraph_runtime.py` — `RuntimeTurnGraphExecutor`.

**Nodes:** `interpret_input` → `retrieve_context` → `route_model` → `invoke_model` → (conditional) `fallback_model` → `package_output`.

## Authority boundary

- Graph output is **proposal and diagnostic** data.
- Session mutation (`turn_counter`, history append, diagnostics append) is performed by `StoryRuntimeManager` in world-engine.

## Fallback and retries

On model invocation failure, the graph branches to `fallback_model` (often **mock** adapter) to keep the flow operational. If no fallback exists, diagnostics record explicit error markers. Checkpoint persistence is deferred; traces and deterministic fallback come first.

## State

Typed `RuntimeTurnState` carries session/input identifiers, interpreted input, retrieval metadata, routing details, generation payload, graph trace (`nodes_executed`, `node_outcomes`, `errors`), and health markers.

## Diagnostics

Each run emits `graph_name`, `graph_version`, `node_outcomes`, `fallback_path_taken`, `execution_health` (`healthy` | `model_fallback` | `degraded_generation` | `graph_error`), and `repro_metadata` fields (`adapter_invocation_mode`, `graph_path_summary`) aligned with `ai_stack/runtime_turn_contracts.py`.

## Seed graphs

- `build_seed_writers_room_graph()` — Writers’ Room workflow seed
- `build_seed_improvement_graph()` — improvement workflow seed

Minimal but executable; expandable without a second orchestration stack.

## Related

- [`LangChain.md`](LangChain.md) — structured invocation inside `invoke_model`
- [`../ai/RAG.md`](../ai/RAG.md) — `retrieve_context`
- [`docs/VERTICAL_SLICE_CONTRACT_GOC.md`](../../VERTICAL_SLICE_CONTRACT_GOC.md) — GoC graph checklist
