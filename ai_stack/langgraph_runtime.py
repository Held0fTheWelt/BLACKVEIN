"""
``ai_stack/langgraph_runtime.py`` — public surface of this module; see exports and call sites for contracts.
"""
from __future__ import annotations

from ai_stack.langgraph_imports import END, LANGGRAPH_IMPORT_ERROR, StateGraph


def ensure_langgraph_available() -> None:
    """Describe what ``ensure_langgraph_available`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    """
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
