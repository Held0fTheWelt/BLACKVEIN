"""
``ai_stack/langgraph_runtime_seed_graphs.py`` — expand purpose, primary
entrypoints, and invariants for maintainers.
"""
from __future__ import annotations

from typing_extensions import TypedDict

try:  # pragma: no cover - mirror facade; seed module must not import langgraph_runtime at load time
    from ai_stack.langgraph_imports import END, StateGraph
except Exception:  # pragma: no cover
    END = None
    StateGraph = None


def build_seed_writers_room_graph():
    """Describe what ``build_seed_writers_room_graph`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    """
    from ai_stack.langgraph_runtime import ensure_langgraph_available

    ensure_langgraph_available()

    class WritersRoomSeedState(TypedDict, total=False):
        """``WritersRoomSeedState`` groups related behaviour; callers should read members for contracts and threading assumptions.
        """
        module_id: str
        workflow: str
        status: str

    graph = StateGraph(WritersRoomSeedState)

    def seed_node(state: WritersRoomSeedState) -> WritersRoomSeedState:
        return {"module_id": state.get("module_id", ""), "workflow": "writers_room_review_seed", "status": "ready"}

    graph.add_node("seed_node", seed_node)
    graph.set_entry_point("seed_node")
    graph.add_edge("seed_node", END)
    return graph.compile()


def build_seed_improvement_graph():
    """Describe what ``build_seed_improvement_graph`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    """
    from ai_stack.langgraph_runtime import ensure_langgraph_available

    ensure_langgraph_available()

    class ImprovementSeedState(TypedDict, total=False):
        """``ImprovementSeedState`` groups related behaviour; callers should read members for contracts and threading assumptions.
        """
        baseline_id: str
        workflow: str
        status: str

    graph = StateGraph(ImprovementSeedState)

    def seed_node(state: ImprovementSeedState) -> ImprovementSeedState:
        return {"baseline_id": state.get("baseline_id", ""), "workflow": "improvement_eval_seed", "status": "ready"}

    graph.add_node("seed_node", seed_node)
    graph.set_entry_point("seed_node")
    graph.add_edge("seed_node", END)
    return graph.compile()
