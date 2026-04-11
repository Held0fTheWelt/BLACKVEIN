from __future__ import annotations

from typing_extensions import TypedDict

try:  # pragma: no cover - mirror facade; seed module must not import langgraph_runtime at load time
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover
    END = None
    StateGraph = None


def build_seed_writers_room_graph():
    from ai_stack.langgraph_runtime import ensure_langgraph_available

    ensure_langgraph_available()

    class WritersRoomSeedState(TypedDict, total=False):
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
    from ai_stack.langgraph_runtime import ensure_langgraph_available

    ensure_langgraph_available()

    class ImprovementSeedState(TypedDict, total=False):
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
