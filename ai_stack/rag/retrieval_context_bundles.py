"""Role-scoped retrieval context bundles for narrator/NPC/runtime diagnostics."""

from __future__ import annotations

from typing import Any


RETRIEVAL_CONTEXT_BUNDLE_SCHEMA_VERSION = "runtime_context_bundle.v1"


def _trim_text(value: Any, *, max_len: int = 500) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def build_narrator_context_bundle(
    *,
    state: dict[str, Any],
    context_text: str,
    retrieval_plan: dict[str, Any] | None,
    memory_indexes: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build narrator-safe prompt bundle without private NPC memory by default."""
    rel_index = (memory_indexes or {}).get("relationship_memory_index")
    callback_index = (memory_indexes or {}).get("callback_web_index")
    scene_events = ((memory_indexes or {}).get("scene_event_log_index") or {}).get("entries") or []
    allowed_lanes = list((retrieval_plan or {}).get("allowed_memory_lanes") or [])
    blocked_lanes = list((retrieval_plan or {}).get("blocked_memory_lanes") or [])
    return {
        "schema_version": RETRIEVAL_CONTEXT_BUNDLE_SCHEMA_VERSION,
        "role": "narrator",
        "retrieval_plan": retrieval_plan or {},
        "allowed_memory_lanes": allowed_lanes,
        "blocked_memory_lanes": blocked_lanes,
        "canonical_scene_facts": {
            "module_id": state.get("module_id"),
            "scene_id": state.get("current_scene_id"),
            "turn_number": state.get("turn_number"),
            "pacing_mode": state.get("pacing_mode"),
        },
        "sensory_and_environment": {
            "sensory_context_target": state.get("sensory_context_target")
            if isinstance(state.get("sensory_context_target"), dict)
            else {},
            "environment_state": state.get("environment_state")
            if isinstance(state.get("environment_state"), dict)
            else {},
        },
        "relationship_pressure": rel_index if isinstance(rel_index, dict) else {},
        "callback_candidates": callback_index if isinstance(callback_index, dict) else {},
        "scene_memory": {"recent_scene_events": scene_events[:8]},
        "retrieved_context_excerpt": _trim_text(context_text, max_len=1600),
        "disclosure_policy": {
            "private_npc_memory_excluded": "agent_private_memory" in blocked_lanes,
            "knowledge_boundary_required": "knowledge_boundary" in allowed_lanes,
        },
    }


def build_npc_context_bundle(
    *,
    actor_id: str,
    state: dict[str, Any],
    retrieval_plan: dict[str, Any] | None,
    memory_indexes: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build NPC-facing bundle with private memory lane for the active NPC actor."""
    private_index = (memory_indexes or {}).get("agent_private_memory_index")
    relationship = (memory_indexes or {}).get("relationship_memory_index")
    knowledge = (memory_indexes or {}).get("knowledge_boundary_index")
    return {
        "schema_version": RETRIEVAL_CONTEXT_BUNDLE_SCHEMA_VERSION,
        "role": "npc",
        "actor_id": actor_id,
        "retrieval_plan": retrieval_plan or {},
        "private_memory": private_index if isinstance(private_index, dict) else {},
        "relationship_memory": relationship if isinstance(relationship, dict) else {},
        "knowledge_boundary": knowledge if isinstance(knowledge, dict) else {},
        "scene_function": state.get("selected_scene_function"),
        "continuity_constraints": state.get("prior_continuity_impacts")
        if isinstance(state.get("prior_continuity_impacts"), list)
        else [],
    }

