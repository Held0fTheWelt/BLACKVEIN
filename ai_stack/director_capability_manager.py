"""Bounded dispatch audit for director-selected dramatic capabilities.

The scene director uses dramatic capabilities as a selective runtime gate. This
module keeps that gate finite: each selected capability gets one individual
terminal path, paths are cycle-checked, and the dispatcher is not allowed to
expand the queue while walking a path.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ai_stack.dramatic_capability_contracts import (
    NPC_ACTION_GESTURE_OPTIONAL,
    NPC_DIRECT_ANSWER_ALLOWED,
    NPC_SOCIAL_REACTION_OPTIONAL,
    NARRATOR_ACTION_CONSEQUENCE_DESCRIBE,
    NARRATOR_OBJECT_STATE_DESCRIBE,
    NARRATOR_OPENING_EVENT_REALIZE,
    NARRATOR_PERCEPTION_RESULT_DESCRIBE,
    NARRATOR_SCENE_CONTEXT_ESTABLISH,
    default_capability_policy,
)


DIRECTOR_CAPABILITY_MANAGER_PLAN_SCHEMA_VERSION = "director_capability_manager_plan.v1"
DIRECTOR_CAPABILITY_DISPATCH_AUDIT_SCHEMA_VERSION = "director_capability_dispatch_audit.v1"
DEFAULT_MAX_CAPABILITY_PATHS = 12
DEFAULT_MAX_CAPABILITY_PATH_DEPTH = 4
CAPABILITY_TERMINAL_NODE = "terminal"


DRAMATIC_CAPABILITY_DISPATCH_PATHS: dict[str, tuple[str, ...]] = {
    NARRATOR_SCENE_CONTEXT_ESTABLISH: (
        "director_tick",
        "narrator.scene_context",
        "visible_output.narrator",
        CAPABILITY_TERMINAL_NODE,
    ),
    NARRATOR_OPENING_EVENT_REALIZE: (
        "director_tick",
        "canonical_path.opening_event",
        "visible_output.narrator",
        CAPABILITY_TERMINAL_NODE,
    ),
    NARRATOR_PERCEPTION_RESULT_DESCRIBE: (
        "director_tick",
        "narrator.perception_result",
        "visible_output.narrator",
        CAPABILITY_TERMINAL_NODE,
    ),
    NARRATOR_OBJECT_STATE_DESCRIBE: (
        "director_tick",
        "narrator.object_state",
        "visible_output.narrator",
        CAPABILITY_TERMINAL_NODE,
    ),
    NARRATOR_ACTION_CONSEQUENCE_DESCRIBE: (
        "director_tick",
        "narrator.action_consequence",
        "visible_output.narrator",
        CAPABILITY_TERMINAL_NODE,
    ),
    NPC_SOCIAL_REACTION_OPTIONAL: (
        "director_tick",
        "npc.presence_or_reaction",
        "visible_output.npc",
        CAPABILITY_TERMINAL_NODE,
    ),
    NPC_DIRECT_ANSWER_ALLOWED: (
        "director_tick",
        "speech_policy.direct_answer",
        "visible_output.npc_speech",
        CAPABILITY_TERMINAL_NODE,
    ),
    NPC_ACTION_GESTURE_OPTIONAL: (
        "director_tick",
        "actor_directive.visible_gesture",
        "visible_output.npc_action",
        CAPABILITY_TERMINAL_NODE,
    ),
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _unique_clean(values: Iterable[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        text = _clean(value)
        if text and text not in out:
            out.append(text)
    return out


def _allowed_dramatic_capabilities() -> set[str]:
    enabled = default_capability_policy().get("enabled")
    if not isinstance(enabled, list):
        return set(DRAMATIC_CAPABILITY_DISPATCH_PATHS)
    return {_clean(item) for item in enabled if _clean(item)}


def _steps_by_capability(capability_steps: Iterable[Mapping[str, Any]] | None) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for step in capability_steps or []:
        capability = _clean(step.get("capability") if isinstance(step, Mapping) else "")
        if capability and capability not in out and isinstance(step, Mapping):
            out[capability] = step
    return out


def _path_nodes_for(
    capability: str,
    *,
    path_registry: Mapping[str, Iterable[Any]] | None,
) -> list[str]:
    registry = path_registry or DRAMATIC_CAPABILITY_DISPATCH_PATHS
    raw_nodes = registry.get(capability) if isinstance(registry, Mapping) else None
    if not raw_nodes:
        return []
    return _unique_node_payload(raw_nodes)


def _unique_node_payload(nodes: Iterable[Any]) -> list[str]:
    out: list[str] = []
    for node in nodes:
        node_id = _clean(node.get("node_id")) if isinstance(node, Mapping) else _clean(node)
        if node_id:
            out.append(node_id)
    return out


def _has_cycle(nodes: list[str]) -> bool:
    seen: set[str] = set()
    for node in nodes:
        if node in seen:
            return True
        seen.add(node)
    return False


def audit_director_capability_paths(
    *,
    selected_capabilities: Iterable[Any],
    capability_steps: Iterable[Mapping[str, Any]] | None = None,
    suppressed_capabilities: Iterable[Any] | None = None,
    allowed_capabilities: Iterable[Any] | None = None,
    path_registry: Mapping[str, Iterable[Any]] | None = None,
    max_path_count: int = DEFAULT_MAX_CAPABILITY_PATHS,
    max_path_depth: int = DEFAULT_MAX_CAPABILITY_PATH_DEPTH,
) -> dict[str, Any]:
    """Return a finite per-capability dispatch audit for one director plan."""

    selected = _unique_clean(selected_capabilities)
    suppressed = set(_unique_clean(suppressed_capabilities or ()))
    allowed = set(_unique_clean(allowed_capabilities or _allowed_dramatic_capabilities()))
    steps = _steps_by_capability(capability_steps)
    safe_max_paths = max(0, int(max_path_count))
    safe_max_depth = max(1, int(max_path_depth))
    paths: list[dict[str, Any]] = []
    executable: list[str] = []
    rejected: list[str] = []

    for index, capability in enumerate(selected):
        step = steps.get(capability, {})
        nodes = _path_nodes_for(capability, path_registry=path_registry)
        cycle_detected = _has_cycle(nodes)
        depth = len(nodes)
        reasons: list[str] = []
        if index >= safe_max_paths:
            reasons.append("path_count_limit_exceeded")
        if capability not in allowed:
            reasons.append("capability_not_enabled")
        if capability in suppressed:
            reasons.append("suppressed_capability_selected")
        if not nodes:
            reasons.append("missing_dispatch_path")
        if cycle_detected:
            reasons.append("cycle_detected")
        if depth > safe_max_depth:
            reasons.append("path_depth_limit_exceeded")
        if nodes and nodes[-1] != CAPABILITY_TERMINAL_NODE:
            reasons.append("path_not_terminal")

        status = "rejected" if reasons else "passed"
        if status == "passed":
            executable.append(capability)
        else:
            rejected.append(capability)

        paths.append(
            {
                "path_id": f"director_capability_path:{capability}",
                "run_order": index + 1,
                "capability": capability,
                "mode": _clean(step.get("mode")) or "selected",
                "source": _clean(step.get("source")) or "capability_manager",
                "nodes": [
                    {"visit_order": node_index + 1, "node_id": node}
                    for node_index, node in enumerate(nodes)
                ],
                "depth": depth,
                "max_depth": safe_max_depth,
                "terminal_node": nodes[-1] if nodes else None,
                "cycle_detected": cycle_detected,
                "status": status,
                "reason_codes": reasons or ["bounded_individual_path"],
                "activates_beat_orders": list(step.get("activates_beat_orders") or [])
                if isinstance(step.get("activates_beat_orders"), list)
                else [],
            }
        )

    return {
        "schema_version": DIRECTOR_CAPABILITY_DISPATCH_AUDIT_SCHEMA_VERSION,
        "dispatch_strategy": "bounded_individual_capability_paths",
        "status": "failed" if rejected else "passed",
        "path_count": len(paths),
        "max_path_count": safe_max_paths,
        "max_path_depth": safe_max_depth,
        "max_observed_path_depth": max((path["depth"] for path in paths), default=0),
        "loop_guard": {
            "recursive_dispatch_allowed": False,
            "queue_expansion_allowed": False,
            "cycle_detection": "per_path_unique_node_visit",
            "terminal_node_required": CAPABILITY_TERMINAL_NODE,
        },
        "paths": paths,
        "dispatch_queue": list(executable),
        "executable_capabilities": list(executable),
        "rejected_capabilities": list(rejected),
    }


def executable_capabilities_from_manager_plan(plan: Mapping[str, Any] | None) -> list[str]:
    """Return audited executable capabilities, falling back for older plans."""

    if not isinstance(plan, Mapping):
        return []
    audit = plan.get("capability_dispatch_audit")
    if isinstance(audit, Mapping):
        for key in ("executable_capabilities", "dispatch_queue"):
            values = audit.get(key)
            if isinstance(values, list):
                return _unique_clean(values)
    for key in ("requested_visible_functions", "selected_capabilities"):
        values = plan.get(key)
        if isinstance(values, list):
            return _unique_clean(values)
    return []
