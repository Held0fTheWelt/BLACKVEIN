from __future__ import annotations

LANGGRAPH_IMPORT_ERROR: Exception | None = None
try:  # pragma: no cover - exercised by dedicated missing-dependency test via sentinel override
    from langgraph.graph import END, StateGraph
except Exception as exc:  # pragma: no cover
    END = None
    StateGraph = None
    LANGGRAPH_IMPORT_ERROR = exc


def ensure_langgraph_available() -> None:
    if LANGGRAPH_IMPORT_ERROR is not None:
        raise RuntimeError(
            "LangGraph runtime dependency is unavailable. Install 'langgraph' in the runtime environment "
            "and verify requirements are up to date."
        ) from LANGGRAPH_IMPORT_ERROR


from ai_stack.langgraph_runtime_executor import RuntimeTurnGraphExecutor
from ai_stack.langgraph_runtime_seed_graphs import (
    build_seed_improvement_graph,
    build_seed_writers_room_graph,
)
from ai_stack.langgraph_runtime_state import (
    STORY_RUNTIME_ROUTING_POLICY_ID,
    STORY_RUNTIME_ROUTING_POLICY_VERSION,
    RuntimeTurnState,
)
