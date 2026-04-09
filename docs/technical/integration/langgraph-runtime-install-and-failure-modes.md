# LangGraph Runtime Install and Failure Modes

Status: hardened runtime contract (B2 repair).

## Required dependency

LangGraph is a required runtime dependency for canonical orchestration paths in this repository.

Declared in:

- `world-engine/requirements.txt`
- `backend/requirements.txt`

## Runtime guard behavior

`ai_stack/langgraph_runtime.py` now protects import and startup paths with explicit checks:

- module import captures LangGraph import exceptions in `LANGGRAPH_IMPORT_ERROR`
- `ensure_langgraph_available()` raises a clear runtime error when dependency is unavailable
- graph constructors call `ensure_langgraph_available()` before building executable graphs:
  - `RuntimeTurnGraphExecutor`
  - `build_seed_writers_room_graph`
  - `build_seed_improvement_graph`

## Healthy mode expectations

- LangGraph-dependent modules import successfully.
- Runtime turn graph executes and emits diagnostics.
- Writers-room/improvement seed graphs compile and execute.

## Degraded mode expectations

When LangGraph is missing or broken, callers receive an explicit runtime error:

- message starts with: `LangGraph runtime dependency is unavailable`
- action hint directs operators to install/update `langgraph` requirements
- failure is explicit and non-silent (no fake "working" fallback)
