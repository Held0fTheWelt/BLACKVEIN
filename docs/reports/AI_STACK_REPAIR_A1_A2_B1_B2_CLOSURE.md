# AI Stack Repair Closure — A1 + A2 + B1 + B2

Date: 2026-04-04

## Summary of repairs

- **A1:** Replaced queue-only frontend shell action flow with real runtime turn dispatch path to backend session turn execution and World-Engine runtime.
- **A2:** Added authoritative narrative progression commit logic in World-Engine runtime using runtime projection legality checks.
- **B1:** Introduced and wired a real LangChain integration layer for runtime-adjacent model invocation plus writers-room retriever/tool bridges.
- **B2:** Hardened LangGraph dependency declaration and runtime import behavior with explicit degraded-mode failure semantics.

## Milestone verdict table

| Milestone | Verdict | Gate report |
|-----------|---------|-------------|
| A1 | Pass | `docs/reports/ai_stack_gates/A1_REPAIR_GATE_REPORT.md` |
| A2 | Pass | `docs/reports/ai_stack_gates/A2_REPAIR_GATE_REPORT.md` |
| B1 | Pass | `docs/reports/ai_stack_gates/B1_REPAIR_GATE_REPORT.md` |
| B2 | Pass | `docs/reports/ai_stack_gates/B2_REPAIR_GATE_REPORT.md` |

## Exact runtime paths repaired

### Primary free-input runtime path (A1)

1. Frontend `/play/<run_id>/execute` accepts free natural text.
2. Frontend dispatches `player_input` to backend `POST /api/v1/sessions/<session_id>/turns`.
3. Backend session route invokes shared interpreter preview and proxies execution to World-Engine story runtime turn endpoint.
4. World-Engine executes turn through `RuntimeTurnGraphExecutor`.

### Authoritative narrative commit path (A2)

1. Turn graph execution returns interpreted input and runtime diagnostics.
2. `StoryRuntimeManager.execute_turn` performs legality checks against runtime projection (`scenes`, `transition_hints`).
3. Legal proposals commit `current_scene_id`; illegal proposals are rejected safely with explicit reason.
4. Committed progression and diagnostics are emitted together (`progression_commit` + committed state snapshots).

### LangChain active integration paths (B1)

- Runtime-adjacent:
  - `wos_ai_stack/langgraph_runtime.py` uses `invoke_runtime_adapter_with_langchain` (prompt abstraction + structured parse metadata).
- Writers-room:
  - `backend/app/services/writers_room_service.py` uses LangChain retriever bridge and capability tool bridge.

### LangGraph hardening path (B2)

- `wos_ai_stack/langgraph_runtime.py` now gates graph construction via `ensure_langgraph_available`.
- Missing dependency path raises explicit runtime error instead of ambiguous import failure.
- Dependency declaration includes `langgraph` in backend/world-engine requirements.

## What remains out of scope

- Full RAG maturity expansion beyond current runtime/writers-room usage.
- MCP stack completion claims.
- Writers-room feature depth beyond B1 integration-layer wiring.
- Broad migration of all historical/legacy AI paths to LangChain/LangGraph patterns.

## Next-block readiness (RAG / MCP / Writers-Room / Improvement depth)

Repository status after this repair block: **ready to proceed**.

Rationale:

- primary player input path is now executable and truthful,
- runtime authority has explicit commit semantics,
- LangChain is real and exercised,
- LangGraph dependency/runtime behavior is hardened and test-covered.
