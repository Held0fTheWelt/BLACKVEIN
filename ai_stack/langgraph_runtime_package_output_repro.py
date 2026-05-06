"""Repro metadata and graph-path summary for package_output (DS-037)."""

from __future__ import annotations

from typing import Any

from ai_stack.goc_turn_seams import repro_metadata_complete
from ai_stack.langgraph_runtime_state import RuntimeTurnState
from ai_stack.langgraph_runtime_tracking import _dist_version
from ai_stack.runtime_turn_contracts import (
    ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK,
    ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
    EXECUTION_HEALTH_DEGRADED_GENERATION,
    EXECUTION_HEALTH_GRAPH_ERROR,
    EXECUTION_HEALTH_HEALTHY,
    EXECUTION_HEALTH_MODEL_FALLBACK,
)
from ai_stack.version import AI_STACK_SEMANTIC_VERSION


def build_repro_metadata_and_health(
    state: RuntimeTurnState,
    *,
    graph_name: str,
    graph_version: str,
    fallback_taken: bool,
) -> tuple[dict[str, Any], str, bool]:
    """Return repro_metadata (incl. graph_path_summary, repro_complete),
    execution_health, repro_ok.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        graph_name: ``graph_name`` (str); meaning follows the type and call sites.
        graph_version: ``graph_version`` (str); meaning follows the type and call sites.
        fallback_taken: ``fallback_taken`` (bool); meaning follows the type and call sites.
    
    Returns:
        tuple[dict[str, Any], str, bool]:
            Returns a value of type ``tuple[dict[str, Any], str, bool]``; see the function body for structure, error paths, and sentinels.
    """
    routing = state.get("routing") or {}
    retrieval = state.get("retrieval") or {}
    generation = state.get("generation") or {}
    host_versions = dict(state.get("host_versions") or {})
    # P1-5: Separate planned route from actual invocation for clarity
    repro_metadata: dict[str, Any] = {
        "ai_stack_semantic_version": AI_STACK_SEMANTIC_VERSION,
        "runtime_turn_graph_version": graph_version,
        "graph_name": graph_name,
        "trace_id": state.get("trace_id") or "",
        "story_runtime_core_version": _dist_version("story_runtime_core"),
        "routing_policy": "story_runtime_core.RoutingPolicy",
        "routing_policy_version": "registry_default_v1",
        # Planned route (what the governance/routing policy selected)
        "planned_route": {
            "selected_model": routing.get("selected_model"),
            "selected_provider": routing.get("selected_provider"),
            "route_reason": routing.get("route_reason"),
            "fallback_chain": routing.get("fallback_chain"),
        },
        "selected_model": routing.get("selected_model"),
        "selected_provider": routing.get("selected_provider"),
        "route_reason": routing.get("route_reason") or routing.get("reason"),
        "fallback_chain": routing.get("fallback_chain"),
        # Actual invocation (what was actually called)
        "actual_invocation": {
            "attempted": generation.get("attempted"),
            "success": generation.get("success"),
            "fallback_used": generation.get("fallback_used"),
        },
        "model_attempted": generation.get("attempted"),
        "model_success": generation.get("success"),
        "model_fallback_used": generation.get("fallback_used"),
        "retrieval_domain": retrieval.get("domain"),
        "retrieval_profile": retrieval.get("profile"),
        "retrieval_status": retrieval.get("status"),
        "retrieval_hit_count": retrieval.get("hit_count"),
        "module_id": state.get("module_id"),
        "session_id": state.get("session_id"),
        "host_versions": host_versions,
    }
    graph_errors = list(state.get("graph_errors", []))
    execution_health = EXECUTION_HEALTH_HEALTHY
    if graph_errors:
        execution_health = EXECUTION_HEALTH_GRAPH_ERROR
    elif fallback_taken:
        execution_health = EXECUTION_HEALTH_MODEL_FALLBACK
    elif generation.get("success") is False:
        execution_health = EXECUTION_HEALTH_DEGRADED_GENERATION

    gen_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    adapter_mode = gen_meta.get("adapter_invocation_mode")
    if fallback_taken and adapter_mode == ADAPTER_INVOCATION_LANGCHAIN_PRIMARY:
        graph_path_summary = "used_fallback_model_node_langchain_adapter"
    elif fallback_taken:
        graph_path_summary = "used_fallback_model_node_raw_adapter"
    elif adapter_mode == ADAPTER_INVOCATION_LANGCHAIN_PRIMARY:
        graph_path_summary = "primary_invoke_langchain_only"
    elif adapter_mode == ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK:
        graph_path_summary = "degraded_adapter_or_fallback_missing"
    else:
        graph_path_summary = "primary_path_unknown_adapter_mode"

    repro_metadata["adapter_invocation_mode"] = adapter_mode
    repro_metadata["graph_path_summary"] = graph_path_summary
    repro_ok = repro_metadata_complete(repro_metadata)
    repro_metadata["repro_complete"] = repro_ok

    return repro_metadata, execution_health, repro_ok
