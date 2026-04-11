from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as pkg_version

from ai_stack.langgraph_runtime_state import RuntimeTurnState


def _dist_version(name: str) -> str:
    try:
        return pkg_version(name)
    except PackageNotFoundError:
        return "unknown"


def _track(state: RuntimeTurnState, *, node_name: str, outcome: str = "ok") -> RuntimeTurnState:
    nodes = list(state.get("nodes_executed", []))
    outcomes = dict(state.get("node_outcomes", {}))
    nodes.append(node_name)
    outcomes[node_name] = outcome
    return {"nodes_executed": nodes, "node_outcomes": outcomes}
