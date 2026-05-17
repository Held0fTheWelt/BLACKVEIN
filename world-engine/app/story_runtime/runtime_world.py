from __future__ import annotations

from typing import Any


RUNTIME_WORLD_SCHEMA_VERSION = "story_runtime_world.v1"
RUNTIME_WORLD_DIAGNOSTIC_SCHEMA_VERSION = "story_runtime_world_diagnostic.v1"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _clean_id(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _row_id(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        candidate = _clean_id(row.get(key))
        if candidate:
            return candidate
    return ""


def _room_label(room_id: str, row: dict[str, Any]) -> str:
    return _clean_id(row.get("name") or row.get("display_name") or row.get("title")) or room_id


def _add_diag(
    diagnostics: list[dict[str, Any]],
    *,
    code: str,
    status: str = "info",
    message: str = "",
    details: dict[str, Any] | None = None,
) -> None:
    diagnostics.append(
        {
            "schema_version": RUNTIME_WORLD_DIAGNOSTIC_SCHEMA_VERSION,
            "code": code,
            "status": status,
            "message": message,
            "details": _json_safe(details or {}),
        }
    )


def _rooms_from_environment_model(environment_model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rooms: dict[str, dict[str, Any]] = {}
    for room_id, raw in _as_dict(environment_model.get("locations")).items():
        if not isinstance(raw, dict):
            continue
        rid = _clean_id(raw.get("id") or room_id)
        if not rid:
            continue
        rooms[rid] = {
            "id": rid,
            "name": _room_label(rid, raw),
            "kind": "room",
            "source_kind": "declared",
            "source_ref": "environment_model.locations",
            "access": raw.get("access") or raw.get("playable_access"),
            "privacy": raw.get("privacy"),
            "aliases": _json_safe(_as_list(raw.get("aliases"))),
            "adjacent_room_ids": [
                _clean_id(x) for x in _as_list(raw.get("adjacent_room_ids")) if _clean_id(x)
            ],
            "visibility_from_room": _json_safe(_as_dict(raw.get("visibility_from_room"))),
            "raw": _json_safe(raw),
        }
    return rooms


def _merge_runtime_projection_rooms(
    rooms: dict[str, dict[str, Any]],
    runtime_projection: dict[str, Any],
    diagnostics: list[dict[str, Any]],
) -> None:
    for collection_key in ("rooms", "locations", "places", "scenes"):
        for raw in _as_list(runtime_projection.get(collection_key)):
            if not isinstance(raw, dict):
                continue
            rid = _row_id(raw, "id", "room_id", "location_id", "place_id", "scene_id")
            if not rid:
                continue
            source_ref = f"runtime_projection.{collection_key}"
            if rid not in rooms:
                rooms[rid] = {
                    "id": rid,
                    "name": _room_label(rid, raw),
                    "kind": "scene" if collection_key == "scenes" else "room",
                    "source_kind": "projection",
                    "source_ref": source_ref,
                    "access": raw.get("access") or raw.get("playable_access"),
                    "privacy": raw.get("privacy"),
                    "aliases": _json_safe(_as_list(raw.get("aliases"))),
                    "adjacent_room_ids": [
                        _clean_id(x) for x in _as_list(raw.get("adjacent_room_ids")) if _clean_id(x)
                    ],
                    "visibility_from_room": _json_safe(_as_dict(raw.get("visibility_from_room"))),
                    "raw": _json_safe(raw),
                }
                _add_diag(
                    diagnostics,
                    code="room_from_runtime_projection",
                    message="Runtime projection supplied a room/location/scene not present in the environment model.",
                    details={"room_id": rid, "source_ref": source_ref},
                )
            else:
                rooms[rid]["raw"] = {**_as_dict(rooms[rid].get("raw")), **_json_safe(raw)}
                rooms[rid].setdefault("projection_refs", [])
                if isinstance(rooms[rid]["projection_refs"], list):
                    rooms[rid]["projection_refs"].append(source_ref)


def _props_from_environment_model(environment_model: dict[str, Any], fallback_room_id: str) -> dict[str, dict[str, Any]]:
    props: dict[str, dict[str, Any]] = {}
    for object_id, raw in _as_dict(environment_model.get("objects")).items():
        if not isinstance(raw, dict):
            continue
        oid = _clean_id(raw.get("id") or object_id)
        if not oid:
            continue
        room_id = _clean_id(raw.get("placement_room_id") or raw.get("room_id") or fallback_room_id)
        props[oid] = {
            "id": oid,
            "name": _room_label(oid, raw),
            "room_id": room_id or None,
            "source_kind": "declared",
            "source_ref": "environment_model.objects",
            "status": "present",
            "affordances": _json_safe(_as_list(raw.get("affordances"))),
            "aliases": _json_safe(_as_list(raw.get("aliases"))),
            "risk_tags": _json_safe(_as_list(raw.get("risk_tags"))),
            "symbolic_roles": _json_safe(_as_list(raw.get("symbolic_roles"))),
            "raw": _json_safe(raw),
        }
    return props


def _merge_runtime_projection_props(
    props: dict[str, dict[str, Any]],
    runtime_projection: dict[str, Any],
    fallback_room_id: str,
    diagnostics: list[dict[str, Any]],
) -> None:
    for collection_key in ("props", "objects", "items"):
        for raw in _as_list(runtime_projection.get(collection_key)):
            if not isinstance(raw, dict):
                continue
            oid = _row_id(raw, "id", "prop_id", "object_id", "item_id")
            if not oid:
                continue
            source_ref = f"runtime_projection.{collection_key}"
            if oid not in props:
                props[oid] = {
                    "id": oid,
                    "name": _room_label(oid, raw),
                    "room_id": _clean_id(raw.get("placement_room_id") or raw.get("room_id")) or fallback_room_id or None,
                    "source_kind": "projection",
                    "source_ref": source_ref,
                    "status": "present",
                    "affordances": _json_safe(_as_list(raw.get("affordances"))),
                    "aliases": _json_safe(_as_list(raw.get("aliases"))),
                    "risk_tags": _json_safe(_as_list(raw.get("risk_tags"))),
                    "symbolic_roles": _json_safe(_as_list(raw.get("symbolic_roles"))),
                    "raw": _json_safe(raw),
                }
                _add_diag(
                    diagnostics,
                    code="prop_from_runtime_projection",
                    message="Runtime projection supplied a prop/object not present in the environment model.",
                    details={"prop_id": oid, "source_ref": source_ref},
                )
            else:
                props[oid]["raw"] = {**_as_dict(props[oid].get("raw")), **_json_safe(raw)}


def _exits_from_environment_model(
    environment_model: dict[str, Any],
    rooms: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    exits: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(_as_list(environment_model.get("transitions"))):
        if not isinstance(raw, dict):
            continue
        from_id = _clean_id(raw.get("from_area_id") or raw.get("from_room_id") or raw.get("from_location_id"))
        to_id = _clean_id(raw.get("to_area_id") or raw.get("to_room_id") or raw.get("to_location_id"))
        if not from_id or not to_id:
            continue
        kind = _clean_id(raw.get("kind")) or "transition"
        exit_id = _clean_id(raw.get("id")) or f"{from_id}->{to_id}:{kind}:{index}"
        exits[exit_id] = {
            "id": exit_id,
            "from_room_id": from_id,
            "to_room_id": to_id,
            "kind": kind,
            "source_kind": "declared",
            "source_ref": "environment_model.transitions",
            "raw": _json_safe(raw),
        }
    for room_id, room in rooms.items():
        for to_id in _as_list(room.get("adjacent_room_ids")):
            target = _clean_id(to_id)
            if not target:
                continue
            exit_id = f"{room_id}->{target}:adjacent"
            exits.setdefault(
                exit_id,
                {
                    "id": exit_id,
                    "from_room_id": room_id,
                    "to_room_id": target,
                    "kind": "adjacent",
                    "source_kind": "declared",
                    "source_ref": "runtime_world.rooms.adjacent_room_ids",
                },
            )
    return exits


def _actors_from_projection(
    runtime_projection: dict[str, Any],
    current_room_id: str,
) -> dict[str, dict[str, Any]]:
    actors: dict[str, dict[str, Any]] = {}
    lanes = _as_dict(runtime_projection.get("actor_lanes"))

    def add(actor_id: Any, lane: str | None = None) -> None:
        aid = _clean_id(actor_id)
        if not aid:
            return
        actors.setdefault(
            aid,
            {
                "id": aid,
                "lane": lane or _clean_id(lanes.get(aid)) or "unknown",
                "room_id": current_room_id or None,
                "source_ref": "runtime_projection.actor_lanes",
            },
        )

    add(runtime_projection.get("human_actor_id"), "human")
    add(runtime_projection.get("selected_player_role"), "human")
    for actor_id in _as_list(runtime_projection.get("npc_actor_ids")):
        add(actor_id, "npc")
    for actor_id, lane in lanes.items():
        add(actor_id, _clean_id(lane) or None)
    return actors


def initialize_runtime_world(
    *,
    module_id: str,
    runtime_projection: dict[str, Any],
    environment_model: dict[str, Any] | None = None,
    environment_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the mechanical runtime world used by the story session loop.

    This is intentionally not the legacy ``RuntimeInstance`` path. It keeps
    story sessions in one authority lane while still giving the loop rooms,
    props, exits, actor IDs, and diagnostics.
    """
    projection = _as_dict(runtime_projection)
    model = _as_dict(environment_model)
    state = _as_dict(environment_state)
    diagnostics: list[dict[str, Any]] = []
    current_room_id = (
        _clean_id(state.get("current_room_id"))
        or _clean_id(state.get("current_area"))
        or _clean_id(projection.get("start_room_id"))
        or _clean_id(projection.get("start_location_id"))
        or _clean_id(projection.get("start_scene_id"))
        or _clean_id(model.get("anchor_room_id"))
    )

    rooms = _rooms_from_environment_model(model)
    _merge_runtime_projection_rooms(rooms, projection, diagnostics)
    if current_room_id and current_room_id not in rooms:
        rooms[current_room_id] = {
            "id": current_room_id,
            "name": current_room_id,
            "kind": "room",
            "source_kind": "derived",
            "source_ref": "runtime_projection.start_scene_id",
            "access": "active",
            "privacy": None,
            "aliases": [],
            "adjacent_room_ids": [],
            "visibility_from_room": {},
            "raw": {"id": current_room_id},
        }
        _add_diag(
            diagnostics,
            code="start_room_derived",
            status="warning",
            message="Start room id was not present in canonical room/location sources and was derived from the runtime projection.",
            details={"room_id": current_room_id},
        )
    elif not current_room_id:
        _add_diag(
            diagnostics,
            code="start_room_missing",
            status="warning",
            message="No start room/location/scene id was available for runtime world initialization.",
        )

    props = _props_from_environment_model(model, current_room_id)
    _merge_runtime_projection_props(props, projection, current_room_id, diagnostics)
    exits = _exits_from_environment_model(model, rooms)
    actors = _actors_from_projection(projection, current_room_id)

    for prop_id, prop in props.items():
        room_id = _clean_id(prop.get("room_id"))
        if room_id and room_id not in rooms:
            rooms[room_id] = {
                "id": room_id,
                "name": room_id,
                "kind": "room",
                "source_kind": "inferred",
                "source_ref": f"runtime_world.props.{prop_id}.room_id",
                "access": None,
                "privacy": None,
                "aliases": [],
                "adjacent_room_ids": [],
                "visibility_from_room": {},
                "raw": {"id": room_id},
            }
            _add_diag(
                diagnostics,
                code="room_inferred_from_prop",
                message="A prop referenced a room not otherwise present; runtime world admitted it as inferred.",
                details={"room_id": room_id, "prop_id": prop_id},
            )

    _add_diag(
        diagnostics,
        code="runtime_world_initialized",
        message="Runtime world initialized from runtime projection and canonical environment model.",
        details={
            "room_count": len(rooms),
            "prop_count": len(props),
            "exit_count": len(exits),
            "actor_count": len(actors),
            "current_room_id": current_room_id or None,
        },
    )

    warning_count = sum(1 for d in diagnostics if d.get("status") == "warning")
    return _json_safe(
        {
            "schema_version": RUNTIME_WORLD_SCHEMA_VERSION,
            "contract": RUNTIME_WORLD_SCHEMA_VERSION,
            "status": "initialized",
            "mode": "story_runtime_projection",
            "module_id": _clean_id(module_id) or _clean_id(projection.get("module_id")),
            "runtime_profile_id": projection.get("runtime_profile_id") or model.get("runtime_profile_id"),
            "current_room_id": current_room_id or None,
            "current_scene_id": _clean_id(projection.get("start_scene_id")) or current_room_id or None,
            "commands_enabled": False,
            "narration_arrangement_enabled": False,
            "rooms": rooms,
            "props": props,
            "exits": exits,
            "actors": actors,
            "diagnostics": diagnostics,
            "diagnostic_summary": {
                "diagnostic_count": len(diagnostics),
                "warning_count": warning_count,
                "error_count": sum(1 for d in diagnostics if d.get("status") == "error"),
            },
        }
    )


def runtime_world_session_diagnostic(runtime_world: dict[str, Any], *, session_id: str) -> dict[str, Any]:
    summary = _as_dict(runtime_world.get("diagnostic_summary"))
    return _json_safe(
        {
            "schema_version": RUNTIME_WORLD_DIAGNOSTIC_SCHEMA_VERSION,
            "event_type": "runtime_world_initialized",
            "turn_kind": "runtime_engine_init",
            "session_id": session_id,
            "module_id": runtime_world.get("module_id"),
            "current_room_id": runtime_world.get("current_room_id"),
            "status": runtime_world.get("status") or "initialized",
            "runtime_world": {
                "schema_version": runtime_world.get("schema_version"),
                "mode": runtime_world.get("mode"),
                "commands_enabled": bool(runtime_world.get("commands_enabled")),
                "narration_arrangement_enabled": bool(runtime_world.get("narration_arrangement_enabled")),
                "room_count": len(_as_dict(runtime_world.get("rooms"))),
                "prop_count": len(_as_dict(runtime_world.get("props"))),
                "exit_count": len(_as_dict(runtime_world.get("exits"))),
                "actor_count": len(_as_dict(runtime_world.get("actors"))),
                "diagnostic_count": int(summary.get("diagnostic_count") or 0),
                "warning_count": int(summary.get("warning_count") or 0),
                "error_count": int(summary.get("error_count") or 0),
            },
            "diagnostics": _as_list(runtime_world.get("diagnostics")),
        }
    )
