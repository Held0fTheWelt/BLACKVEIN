"""Durable selectable branch-tree record helpers.

The branch-tree record wraps an on-demand simulation tree in lifecycle metadata:
it may be persisted and later selected, but it is still not canonical story truth
until the selected path is replayed through the normal runtime commit path.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any


BRANCHING_TREE_RECORD_SCHEMA_VERSION = "branching_tree_record.v1"
BRANCHING_TREE_RECORD_SOURCE = "world_engine_branching_tree_store"
BRANCHING_TREE_STATUS_SIMULATED = "simulated"
BRANCHING_TREE_STATUS_NOT_APPLICABLE = "not_applicable"
BRANCHING_TREE_STATUS_STALE = "stale"
BRANCHING_TREE_STATUS_EXPIRED = "expired"
BRANCHING_TREE_STATUS_COMMITTED = "committed"
BRANCHING_TREE_SCOPE_ACTIVE = "active"
BRANCHING_TREE_SCOPE_PREVIEW = "preview"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def stable_branch_tree_id(
    *,
    story_session_id: str,
    root_canonical_turn_id: str | None,
    root_turn_number: int | None,
    root_session_fingerprint: dict[str, Any] | None,
    trace_id: str | None = None,
) -> str:
    seed = "|".join(
        [
            story_session_id,
            str(root_canonical_turn_id or ""),
            str(root_turn_number if root_turn_number is not None else ""),
            str((root_session_fingerprint or {}).get("fingerprint") or ""),
            str(trace_id or ""),
        ]
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"branch_tree_{digest}"


def selectable_simulation_nodes(simulation_tree: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = simulation_tree.get("nodes") if isinstance(simulation_tree, dict) else []
    out: list[dict[str, Any]] = []
    if not isinstance(nodes, list):
        return out
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("node_kind") != "simulated_turn":
            continue
        if node.get("simulation_error"):
            continue
        if node.get("commit_applied_in_clone") is not True:
            continue
        if not str(node.get("simulated_input") or "").strip():
            continue
        out.append(node)
    return out


def make_branch_tree_record(
    *,
    simulation_tree: dict[str, Any],
    root_session_fingerprint: dict[str, Any],
    current_session_fingerprint: dict[str, Any],
    trace_id: str | None = None,
    scope: str = BRANCHING_TREE_SCOPE_ACTIVE,
    preview: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Wrap a simulation tree in a durable, selectable record."""

    sim = _json_safe(simulation_tree if isinstance(simulation_tree, dict) else {})
    created = created_at or _now_iso()
    root_canonical_turn_id = (
        sim.get("root_canonical_turn_id") if isinstance(sim.get("root_canonical_turn_id"), str) else None
    )
    root_turn_number = sim.get("root_turn_number")
    if root_turn_number is not None:
        try:
            root_turn_number = int(root_turn_number)
        except (TypeError, ValueError):
            root_turn_number = None
    tree_id = stable_branch_tree_id(
        story_session_id=str(sim.get("story_session_id") or ""),
        root_canonical_turn_id=root_canonical_turn_id,
        root_turn_number=root_turn_number,
        root_session_fingerprint=root_session_fingerprint,
        trace_id=trace_id or (str(sim.get("trace_id")) if sim.get("trace_id") else None),
    )
    selectable = selectable_simulation_nodes(sim)
    sim_status = str(sim.get("status") or "").strip()
    status = (
        BRANCHING_TREE_STATUS_NOT_APPLICABLE
        if sim_status == "not_applicable" or not selectable
        else BRANCHING_TREE_STATUS_SIMULATED
    )
    return {
        "schema_version": BRANCHING_TREE_RECORD_SCHEMA_VERSION,
        "source": BRANCHING_TREE_RECORD_SOURCE,
        "tree_id": tree_id,
        "status": status,
        "scope": scope if scope in {BRANCHING_TREE_SCOPE_ACTIVE, BRANCHING_TREE_SCOPE_PREVIEW} else BRANCHING_TREE_SCOPE_ACTIVE,
        "story_session_id": sim.get("story_session_id"),
        "module_id": sim.get("module_id"),
        "runtime_profile_id": sim.get("runtime_profile_id"),
        "root_canonical_turn_id": root_canonical_turn_id,
        "root_turn_number": root_turn_number,
        "root_session_fingerprint": _json_safe(root_session_fingerprint),
        "current_session_fingerprint": _json_safe(current_session_fingerprint),
        "preview": _json_safe(preview or {}),
        "trace_id": trace_id or sim.get("trace_id"),
        "created_at": created,
        "updated_at": created,
        "expires_at": None,
        "authoritative": False,
        "mutates_canonical_state": False,
        "selection_required_to_commit": True,
        "selection_replays_normal_commit_path": True,
        "adopts_simulated_snapshot": False,
        "simulation_tree": sim,
        "selectable_node_ids": [str(node.get("node_id")) for node in selectable if node.get("node_id")],
        "selected_node_id": None,
        "selection": None,
        "stale_reason": None,
        "summary": branch_tree_summary_from_simulation(sim, selectable),
    }


def branch_tree_summary_from_simulation(
    simulation_tree: dict[str, Any],
    selectable_nodes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    selectable = selectable_nodes if selectable_nodes is not None else selectable_simulation_nodes(simulation_tree)
    return {
        "node_count": int(simulation_tree.get("node_count") or len(simulation_tree.get("nodes") or [])),
        "simulated_turn_count": int(simulation_tree.get("simulated_turn_count") or 0),
        "selectable_node_count": len(selectable),
        "max_depth_observed": int(simulation_tree.get("max_depth_observed") or 0),
        "truncated": bool(simulation_tree.get("truncated")),
        "truncation_reason": simulation_tree.get("truncation_reason"),
    }


def find_branch_tree_node(record: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    tree = record.get("simulation_tree") if isinstance(record, dict) else {}
    nodes = tree.get("nodes") if isinstance(tree, dict) else []
    if not isinstance(nodes, list):
        return None
    for node in nodes:
        if isinstance(node, dict) and node.get("node_id") == node_id:
            return node
    return None


def branch_tree_path_nodes(record: dict[str, Any], node_id: str) -> list[dict[str, Any]]:
    """Return simulated nodes from root child to selected node."""

    tree = record.get("simulation_tree") if isinstance(record, dict) else {}
    nodes = tree.get("nodes") if isinstance(tree, dict) else []
    if not isinstance(nodes, list):
        return []
    by_id = {str(node.get("node_id")): node for node in nodes if isinstance(node, dict) and node.get("node_id")}
    path: list[dict[str, Any]] = []
    cursor = by_id.get(node_id)
    while isinstance(cursor, dict) and cursor.get("node_kind") == "simulated_turn":
        path.append(cursor)
        parent = cursor.get("parent_node_id")
        cursor = by_id.get(str(parent)) if parent else None
    path.reverse()
    return path


def branch_tree_is_fresh(record: dict[str, Any], current_session_fingerprint: dict[str, Any]) -> bool:
    root = record.get("root_session_fingerprint") if isinstance(record, dict) else {}
    if not isinstance(root, dict):
        return False
    return str(root.get("fingerprint") or "") == str(current_session_fingerprint.get("fingerprint") or "")


def mark_branch_tree_stale(
    record: dict[str, Any],
    *,
    reason: str,
    current_session_fingerprint: dict[str, Any],
) -> dict[str, Any]:
    out = dict(record)
    out["status"] = BRANCHING_TREE_STATUS_STALE
    out["stale_reason"] = reason
    out["current_session_fingerprint"] = _json_safe(current_session_fingerprint)
    out["updated_at"] = _now_iso()
    return _json_safe(out)


def mark_branch_tree_expired(record: dict[str, Any], *, reason: str = "operator_expired") -> dict[str, Any]:
    out = dict(record)
    out["status"] = BRANCHING_TREE_STATUS_EXPIRED
    out["stale_reason"] = reason
    out["expires_at"] = _now_iso()
    out["updated_at"] = out["expires_at"]
    return _json_safe(out)


def mark_branch_tree_committed(
    record: dict[str, Any],
    *,
    node_id: str,
    selection: dict[str, Any],
    current_session_fingerprint: dict[str, Any],
) -> dict[str, Any]:
    out = dict(record)
    out["status"] = BRANCHING_TREE_STATUS_COMMITTED
    out["selected_node_id"] = node_id
    out["selection"] = _json_safe(selection)
    out["current_session_fingerprint"] = _json_safe(current_session_fingerprint)
    out["mutates_canonical_state"] = True
    out["updated_at"] = _now_iso()
    return _json_safe(out)
