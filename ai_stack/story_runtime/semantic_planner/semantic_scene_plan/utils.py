"""Shared value cleaning and content lookup helpers."""

from __future__ import annotations

from typing import Any


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _append_unique(out: list[str], value: str) -> None:
    text = _clean(value)
    if text and text not in out:
        out.append(text)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique_clean(values: list[Any] | tuple[Any, ...]) -> list[str]:
    out: list[str] = []
    for value in values:
        _append_unique(out, str(value))
    return out


def _actor_id_index(character_documents: dict[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, row in _as_dict(character_documents).items():
        if not isinstance(row, dict):
            continue
        actor_id = _clean(row.get("actor_id") or row.get("runtime_actor_id"))


        if not actor_id:
            continue
        for ref in (
            key,
            row.get("id"),
            row.get("canonical_id"),
            row.get("character_id"),
            actor_id,
            row.get("runtime_actor_id"),
        ):
            cleaned = _clean(ref)
            if cleaned:
                out.setdefault(cleaned, actor_id)
    return out


def _resolve_actor_id(actor_ref_or_id: Any, actor_id_by_ref: dict[str, str]) -> str:
    value = _clean(actor_ref_or_id)
    if not value:
        return ""
    return actor_id_by_ref.get(value, value if value in actor_id_by_ref.values() else "")


def _ai_forbidden_actor_ids(actor_lane_context: dict[str, Any] | None) -> set[str]:
    ctx = _as_dict(actor_lane_context)
    forbidden = {_clean(ctx.get("human_actor_id"))}
    for actor_id in _as_list(ctx.get("ai_forbidden_actor_ids")):
        forbidden.add(_clean(actor_id))
    return {actor_id for actor_id in forbidden if actor_id}


def _step_rows(canonical_path: dict[str, Any] | None) -> list[dict[str, Any]]:
    path = _as_dict(canonical_path)
    return [dict(row) for row in _as_list(path.get("steps")) if isinstance(row, dict)]


def _step_by_id(canonical_path: dict[str, Any] | None, step_id: str) -> dict[str, Any]:
    sid = _clean(step_id)
    if not sid:
        return {}
    for step in _step_rows(canonical_path):
        if _clean(step.get("id")) == sid:
            return step
    return {}


def _scene_nodes(scene_graph: dict[str, Any] | None) -> list[dict[str, Any]]:
    graph = _as_dict(scene_graph)
    return [dict(row) for row in _as_list(graph.get("nodes")) if isinstance(row, dict)]


def _scene_node_by_id(scene_graph: dict[str, Any] | None, node_id: str) -> dict[str, Any]:
    nid = _clean(node_id)
    if not nid:
        return {}
    for node in _scene_nodes(scene_graph):
        if _clean(node.get("id")) == nid:
            return node
    return {}


def _location_rows(locations: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    locs = _as_dict(locations)
    places = locs.get("places")
    if isinstance(locs.get("locations"), dict):
        places = locs["locations"].get("places")
    out: dict[str, dict[str, Any]] = {}
    for row in _as_list(places):
        if not isinstance(row, dict):
            continue
        loc_id = _clean(row.get("id"))
        if loc_id:


            out[loc_id] = dict(row)
    return out


def _object_rows(objects: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    objs = _as_dict(objects)
    docs = objs.get("object_documents")
    if isinstance(objs.get("objects"), dict):
        docs = objs["objects"].get("object_documents")
    if isinstance(docs, dict):
        return {str(k): dict(v) for k, v in docs.items() if isinstance(v, dict)}
    return {}


def _access_rows(content_access_policy: dict[str, Any] | None) -> list[dict[str, Any]]:
    policy = _as_dict(content_access_policy)
    rows: list[dict[str, Any]] = []
    for key in ("blocked_entities", "gated_entities"):
        for row in _as_list(policy.get(key)):
            if isinstance(row, dict):
                rows.append({**row, "policy_bucket": key})
    return rows


def _access_decisions_for_targets(
    *,
    content_access_policy: dict[str, Any] | None,
    target_ids: list[str],
) -> list[dict[str, Any]]:
    targets = {target_id for target_id in target_ids if target_id}
    out: list[dict[str, Any]] = []
    for row in _access_rows(content_access_policy):
        if _clean(row.get("target_id")) in targets:
            out.append(
                {
                    "id": row.get("id"),
                    "scope": row.get("scope"),
                    "target_id": row.get("target_id"),
                    "decision": row.get("decision"),
                    "requirements": list(row.get("requirements") or [])
                    if isinstance(row.get("requirements"), list)
                    else [],
                    "reason_ref": row.get("reason_ref"),
                    "policy_bucket": row.get("policy_bucket"),
                }
            )
    return out


def _active_canonical_step(
    *,
    canonical_path: dict[str, Any] | None,
    scene_graph: dict[str, Any] | None,
    scene_assessment: dict[str, Any] | None,
    current_scene_id: str,
    narrative_scene_function: str,
    selection_source: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    scene = _as_dict(scene_assessment)
    for key in (
        "canonical_path_step_id",
        "active_canonical_path_step_id",
        "current_canonical_path_step_id",
    ):
        step = _step_by_id(canonical_path, _clean(scene.get(key)))
        if step:
            return step, {}
    for key in ("canonical_path_step_ids", "active_canonical_path_step_ids"):
        for step_id in _as_list(scene.get(key)):
            step = _step_by_id(canonical_path, _clean(step_id))
            if step:
                return step, {}



    scene_id = _clean(scene.get("scene_node_id") or scene.get("current_scene_node_id") or current_scene_id)
    node = _scene_node_by_id(scene_graph, scene_id)
    if node:
        step = _step_by_id(canonical_path, _clean(node.get("canonical_path_step_id")))
        if step:
            return step, node
        for step_id in _as_list(node.get("canonical_path_step_ids")):
            step = _step_by_id(canonical_path, _clean(step_id))
            if step:
                return step, node

    step = _step_by_id(canonical_path, scene_id)
    if step:
        return step, node

    if "opening" in _clean(selection_source).lower() or _clean(scene.get("scene_phase")).lower() == "opening":
        path = _as_dict(canonical_path)
        first_playable = _clean(
            _as_dict(_as_dict(path.get("paths")).get("opening")).get("first_playable_step_id")
        )
        if narrative_scene_function == "arrange_scene":
            first_playable = "opening_007_living_room_arrangement"
        step = _step_by_id(canonical_path, first_playable)
        if step:
            return step, node

    return {}, node
