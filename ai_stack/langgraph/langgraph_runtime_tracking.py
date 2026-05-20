"""
``ai_stack/langgraph/langgraph_runtime_tracking.py`` — expand purpose, primary
entrypoints, and invariants for maintainers.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as pkg_version

from ai_stack.langgraph.langgraph_runtime_state import RuntimeTurnState


def _dist_version(name: str) -> str:
    """``_dist_version`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        name: ``name`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    try:
        return pkg_version(name)
    except PackageNotFoundError:
        return "unknown"


def _track(state: RuntimeTurnState, *, node_name: str, outcome: str = "ok") -> RuntimeTurnState:
    """Describe what ``_track`` does in one line (verb-led summary for this
    function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        node_name: ``node_name`` (str); meaning follows the type and call sites.
        outcome: ``outcome`` (str); meaning follows the type and call sites.
    
    Returns:
        RuntimeTurnState:
            Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
    """
    nodes = list(state.get("nodes_executed", []))
    outcomes = dict(state.get("node_outcomes", {}))
    nodes.append(node_name)
    outcomes[node_name] = outcome
    return {"nodes_executed": nodes, "node_outcomes": outcomes}
