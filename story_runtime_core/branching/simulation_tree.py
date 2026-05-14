"""Bounded multi-turn branching simulation tree helpers.

The tree is operator/diagnostic evidence only. It expands forecast options by
running future turns on isolated session clones; it must never become canonical
history or mutate the active story session.
"""

from __future__ import annotations

import hashlib
from typing import Any


BRANCHING_SIMULATION_TREE_SCHEMA_VERSION = "branching_simulation_tree.v1"
BRANCHING_SIMULATION_TREE_SOURCE = "world_engine_isolated_session_clone"
MAX_SIMULATION_DEPTH = 3
MAX_SIMULATION_BRANCHING = 3
MAX_SIMULATION_NODES = 40
MAX_SIMULATION_TEXT = 180


def _short(value: Any, limit: int = MAX_SIMULATION_TEXT) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, set):
        return sorted(_json_safe(v) for v in value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def clamp_simulation_limits(
    *,
    max_depth: int | None,
    max_branching: int | None,
) -> tuple[int, int, int]:
    """Return safe depth/branch/node limits for simulation expansion."""

    depth = max(0, min(MAX_SIMULATION_DEPTH, int(max_depth if max_depth is not None else 2)))
    branching = max(0, min(MAX_SIMULATION_BRANCHING, int(max_branching if max_branching is not None else 2)))
    if depth <= 0 or branching <= 0:
        return depth, branching, 1
    estimated_nodes = 1
    level_width = 1
    for _ in range(depth):
        level_width *= branching
        estimated_nodes += level_width
    return depth, branching, min(MAX_SIMULATION_NODES, estimated_nodes)


def stable_simulation_id(prefix: str, *parts: Any) -> str:
    seed = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def simulated_input_for_branch_option(option: dict[str, Any], *, depth: int) -> str:
    """Build deterministic simulated player input for a forecast option."""

    family = _short(option.get("family"), 64) or "branch"
    label = _short(option.get("label"), 96) or family
    consequence = _short(option.get("forecasted_consequence"), 120)
    readable = label.replace("_", " ")
    if consequence:
        return f"Simulate branch depth {depth}: {readable}. {consequence}"
    return f"Simulate branch depth {depth}: {readable}."


def forecast_has_options(forecast: dict[str, Any]) -> bool:
    return (
        isinstance(forecast, dict)
        and str(forecast.get("status") or "").strip() == "forecasted"
        and int(forecast.get("option_count") or 0) > 0
        and isinstance(forecast.get("options"), list)
    )


def _simulation_truth_flags() -> dict[str, bool]:
    return {
        "simulation_only": True,
        "authoritative": False,
        "mutates_canonical_state": False,
        "mutates_active_session": False,
        "persists_simulated_turns": False,
        "selection_required_to_commit": True,
    }


def make_simulation_tree(
    *,
    story_session_id: str,
    module_id: str | None,
    runtime_profile_id: str | None,
    root_canonical_turn_id: str | None,
    root_turn_number: int | None,
    root_branching_forecast: dict[str, Any] | None,
    max_depth: int,
    max_branching: int,
    max_nodes: int,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Create an empty simulation tree with a root committed-turn node."""

    root_forecast = _as_dict(root_branching_forecast)
    root_node_id = stable_simulation_id(
        "branch_sim_root",
        story_session_id,
        root_canonical_turn_id,
        root_turn_number,
    )
    root_node = {
        "node_id": root_node_id,
        "node_kind": "root_committed_turn",
        "parent_node_id": None,
        "child_node_ids": [],
        "depth": 0,
        "story_session_id": story_session_id,
        "source_canonical_turn_id": root_canonical_turn_id,
        "source_turn_number": root_turn_number,
        "branching_forecast": _json_safe(root_forecast),
        "stop_reason": None if forecast_has_options(root_forecast) and max_depth > 0 else "no_expandable_root_forecast",
    }
    return {
        "schema_version": BRANCHING_SIMULATION_TREE_SCHEMA_VERSION,
        "source": BRANCHING_SIMULATION_TREE_SOURCE,
        "status": "simulated" if root_node["stop_reason"] is None else "not_applicable",
        "story_session_id": story_session_id,
        "module_id": module_id,
        "runtime_profile_id": runtime_profile_id,
        "root_canonical_turn_id": root_canonical_turn_id,
        "root_turn_number": root_turn_number,
        "trace_id": trace_id,
        "max_depth": max_depth,
        "max_branching": max_branching,
        "max_nodes": max_nodes,
        **_simulation_truth_flags(),
        "nodes": [root_node],
        "root_node_id": root_node_id,
        "truncated": False,
        "truncation_reason": None,
        "summary": {},
    }


def make_simulated_turn_node(
    *,
    tree: dict[str, Any],
    parent_node_id: str,
    depth: int,
    option: dict[str, Any],
    option_index: int,
    path_option_ids: list[str],
    simulated_input: str,
    simulated_event: dict[str, Any] | None,
    stop_reason: str | None,
    error: str | None = None,
) -> dict[str, Any]:
    """Build a compact JSON-safe node from a simulated turn event."""

    event = _as_dict(simulated_event)
    forecast = _as_dict(event.get("branching_forecast"))
    narrative_commit = _as_dict(event.get("narrative_commit"))
    validation = _as_dict(event.get("validation_outcome"))
    committed = _as_dict(event.get("committed_result"))
    ledger = _as_dict(event.get("turn_aspect_ledger"))
    projection = _as_dict(ledger.get("runtime_intelligence_projection"))
    node_id = stable_simulation_id(
        "branch_sim_node",
        tree.get("root_canonical_turn_id"),
        parent_node_id,
        depth,
        option.get("option_id"),
        option_index,
        "|".join(path_option_ids),
    )
    commit_applied = committed.get("commit_applied")
    return {
        "node_id": node_id,
        "node_kind": "simulated_turn",
        "parent_node_id": parent_node_id,
        "child_node_ids": [],
        "depth": depth,
        "option_index": option_index,
        "source_forecast_option_id": option.get("option_id"),
        "source_forecast_family": option.get("family"),
        "source_forecast_label": option.get("label"),
        "path_option_ids": list(path_option_ids),
        "path_signature": stable_simulation_id("branch_sim_path", *path_option_ids),
        "simulated_input": _short(simulated_input),
        "simulated_turn_id": event.get("canonical_turn_id"),
        "simulated_turn_number": event.get("turn_number"),
        "simulated_turn_kind": event.get("turn_kind"),
        "validation_status": validation.get("status"),
        "commit_applied_in_clone": bool(commit_applied),
        "narrative_commit_preview": _json_safe(narrative_commit),
        "committed_state_after_preview": _json_safe(
            _as_dict(event.get("committed_state_after"))
            or {"turn_number": event.get("turn_number")}
        ),
        "turn_aspect_projection": _json_safe(projection),
        "branching_forecast": _json_safe(forecast),
        "branching_forecast_status": forecast.get("status"),
        "branch_option_count": int(forecast.get("option_count") or 0) if forecast else 0,
        "visible_output_present": isinstance(event.get("visible_output_bundle"), dict),
        "simulation_error": _short(error) if error else None,
        "stop_reason": stop_reason,
        **_simulation_truth_flags(),
    }


def append_simulation_node(tree: dict[str, Any], node: dict[str, Any]) -> None:
    """Append a node and register it as child of its parent."""

    parent_id = node.get("parent_node_id")
    for existing in tree.get("nodes", []):
        if existing.get("node_id") == parent_id:
            children = existing.setdefault("child_node_ids", [])
            if isinstance(children, list) and node.get("node_id") not in children:
                children.append(node.get("node_id"))
            break
    tree.setdefault("nodes", []).append(_json_safe(node))


def finalize_simulation_tree(tree: dict[str, Any]) -> dict[str, Any]:
    """Attach derived summary fields and return a JSON-safe tree."""

    nodes = [n for n in tree.get("nodes", []) if isinstance(n, dict)]
    simulated_nodes = [n for n in nodes if n.get("node_kind") == "simulated_turn"]
    leaf_nodes = [n for n in nodes if not n.get("child_node_ids")]
    errors = [n for n in simulated_nodes if n.get("simulation_error")]
    max_depth_observed = max((int(n.get("depth") or 0) for n in nodes), default=0)
    tree["node_count"] = len(nodes)
    tree["simulated_turn_count"] = len(simulated_nodes)
    tree["leaf_count"] = len(leaf_nodes)
    tree["max_depth_observed"] = max_depth_observed
    if errors and tree.get("status") == "simulated":
        tree["status"] = "partial"
    tree["summary"] = {
        "node_count": len(nodes),
        "simulated_turn_count": len(simulated_nodes),
        "leaf_count": len(leaf_nodes),
        "max_depth_observed": max_depth_observed,
        "simulation_error_count": len(errors),
        "root_had_expandable_forecast": tree.get("status") != "not_applicable",
        **_simulation_truth_flags(),
    }
    return _json_safe(tree)
