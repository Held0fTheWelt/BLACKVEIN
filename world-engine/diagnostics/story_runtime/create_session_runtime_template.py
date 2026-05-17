from __future__ import annotations

from typing import Any


SESSION_RUNTIME_TEMPLATE_SCHEMA_VERSION = "session_runtime_template.v1"


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


def _status_count(rows: list[dict[str, Any]], status: str) -> int:
    return sum(1 for row in rows if isinstance(row, dict) and row.get("status") == status)


def _source_summary(rows: dict[str, Any]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for row in rows.values():
        if not isinstance(row, dict):
            continue
        source_kind = _clean_id(row.get("source_kind")) or "unknown"
        summary[source_kind] = summary.get(source_kind, 0) + 1
    return summary


def _add_issue(
    issues: list[dict[str, Any]],
    *,
    code: str,
    status: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    issues.append(
        {
            "code": code,
            "status": status,
            "message": message,
            "details": _json_safe(details or {}),
        }
    )


def create_session_runtime_template(
    *,
    session_id: str,
    module_id: str,
    runtime_projection: dict[str, Any],
    runtime_world: dict[str, Any],
    environment_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a diagnostic-only reduction of a newly initialized session state.

    This file is intentionally outside the application runtime tree. The
    function is a reference/debugging aid for reading and comparing session
    birth state; it must not be imported or called by the live session loop.
    """
    projection = _as_dict(runtime_projection)
    world = _as_dict(runtime_world)
    state = _as_dict(environment_state)
    rooms = _as_dict(world.get("rooms"))
    props = _as_dict(world.get("props"))
    exits = _as_dict(world.get("exits"))
    actors = _as_dict(world.get("actors"))
    diagnostics = [row for row in _as_list(world.get("diagnostics")) if isinstance(row, dict)]
    issues: list[dict[str, Any]] = []

    current_room_id = (
        _clean_id(world.get("current_room_id"))
        or _clean_id(state.get("current_room_id"))
        or _clean_id(state.get("current_area"))
        or _clean_id(projection.get("start_room_id"))
        or _clean_id(projection.get("start_location_id"))
        or _clean_id(projection.get("start_scene_id"))
    )
    current_scene_id = (
        _clean_id(world.get("current_scene_id"))
        or _clean_id(projection.get("start_scene_id"))
        or current_room_id
    )

    prop_ids_by_room: dict[str, list[str]] = {}
    for prop_id, raw in props.items():
        if not isinstance(raw, dict):
            continue
        room_id = _clean_id(raw.get("room_id"))
        if room_id:
            prop_ids_by_room.setdefault(room_id, []).append(_clean_id(raw.get("id")) or str(prop_id))

    exit_ids_by_room: dict[str, list[str]] = {}
    for exit_id, raw in exits.items():
        if not isinstance(raw, dict):
            continue
        from_room_id = _clean_id(raw.get("from_room_id"))
        if from_room_id:
            exit_ids_by_room.setdefault(from_room_id, []).append(_clean_id(raw.get("id")) or str(exit_id))

    if world.get("status") != "initialized":
        _add_issue(
            issues,
            code="runtime_world_not_initialized",
            status="error",
            message="Runtime world is not marked as initialized.",
            details={"status": world.get("status")},
        )
    if not rooms:
        _add_issue(
            issues,
            code="no_rooms",
            status="error",
            message="Runtime template has no rooms to anchor the session.",
        )
    if not current_room_id:
        _add_issue(
            issues,
            code="current_room_missing",
            status="warning",
            message="Runtime template has no current room id.",
        )
    elif current_room_id not in rooms:
        _add_issue(
            issues,
            code="current_room_unknown",
            status="error",
            message="Current room id does not exist in runtime rooms.",
            details={"room_id": current_room_id},
        )
    else:
        current_room = _as_dict(rooms.get(current_room_id))
        source_kind = _clean_id(current_room.get("source_kind"))
        if source_kind in {"derived", "inferred"}:
            _add_issue(
                issues,
                code="current_room_not_declared",
                status="warning",
                message="Current room exists only because runtime world derived or inferred it.",
                details={"room_id": current_room_id, "source_kind": source_kind},
            )

    for prop_id, raw in props.items():
        if not isinstance(raw, dict):
            continue
        pid = _clean_id(raw.get("id")) or str(prop_id)
        room_id = _clean_id(raw.get("room_id"))
        if not room_id:
            _add_issue(
                issues,
                code="prop_without_room",
                status="warning",
                message="Prop has no room id.",
                details={"prop_id": pid},
            )
        elif room_id not in rooms:
            _add_issue(
                issues,
                code="prop_room_missing",
                status="error",
                message="Prop references a room that is not present in runtime rooms.",
                details={"prop_id": pid, "room_id": room_id},
            )
        else:
            room = _as_dict(rooms.get(room_id))
            if room.get("source_kind") == "inferred" and room.get("source_ref") == f"runtime_world.props.{pid}.room_id":
                _add_issue(
                    issues,
                    code="prop_room_inferred",
                    status="warning",
                    message="Prop room was admitted only because the prop referenced it.",
                    details={"prop_id": pid, "room_id": room_id},
                )

    for exit_id, raw in exits.items():
        if not isinstance(raw, dict):
            continue
        eid = _clean_id(raw.get("id")) or str(exit_id)
        from_room_id = _clean_id(raw.get("from_room_id"))
        to_room_id = _clean_id(raw.get("to_room_id"))
        if not from_room_id:
            _add_issue(
                issues,
                code="exit_source_missing",
                status="warning",
                message="Exit has no source room id.",
                details={"exit_id": eid},
            )
        elif from_room_id not in rooms:
            _add_issue(
                issues,
                code="exit_source_unknown",
                status="error",
                message="Exit source room is not present in runtime rooms.",
                details={"exit_id": eid, "from_room_id": from_room_id},
            )
        if not to_room_id:
            _add_issue(
                issues,
                code="exit_target_missing",
                status="warning",
                message="Exit has no target room id.",
                details={"exit_id": eid},
            )
        elif to_room_id not in rooms:
            _add_issue(
                issues,
                code="exit_target_unknown",
                status="error",
                message="Exit target room is not present in runtime rooms.",
                details={"exit_id": eid, "to_room_id": to_room_id},
            )

    if not actors:
        _add_issue(
            issues,
            code="no_actors",
            status="warning",
            message="Runtime template has no actors.",
        )
    for actor_id, raw in actors.items():
        if not isinstance(raw, dict):
            continue
        aid = _clean_id(raw.get("id")) or str(actor_id)
        room_id = _clean_id(raw.get("room_id"))
        if not room_id:
            _add_issue(
                issues,
                code="actor_without_room",
                status="warning",
                message="Actor has no room id.",
                details={"actor_id": aid},
            )
        elif room_id not in rooms:
            _add_issue(
                issues,
                code="actor_room_missing",
                status="error",
                message="Actor references a room that is not present in runtime rooms.",
                details={"actor_id": aid, "room_id": room_id},
            )

    room_rows = []
    for room_id, raw in sorted(rooms.items()):
        if not isinstance(raw, dict):
            continue
        rid = _clean_id(raw.get("id")) or str(room_id)
        room_rows.append(
            {
                "id": rid,
                "name": _clean_id(raw.get("name")) or rid,
                "source_kind": _clean_id(raw.get("source_kind")) or "unknown",
                "source_ref": raw.get("source_ref"),
                "access": raw.get("access"),
                "privacy": raw.get("privacy"),
                "adjacent_room_ids": [
                    _clean_id(item) for item in _as_list(raw.get("adjacent_room_ids")) if _clean_id(item)
                ],
                "prop_ids": sorted(prop_ids_by_room.get(rid, [])),
                "exit_ids": sorted(exit_ids_by_room.get(rid, [])),
            }
        )

    prop_rows = []
    for prop_id, raw in sorted(props.items()):
        if not isinstance(raw, dict):
            continue
        pid = _clean_id(raw.get("id")) or str(prop_id)
        prop_rows.append(
            {
                "id": pid,
                "name": _clean_id(raw.get("name")) or pid,
                "room_id": _clean_id(raw.get("room_id")) or None,
                "source_kind": _clean_id(raw.get("source_kind")) or "unknown",
                "source_ref": raw.get("source_ref"),
                "status": _clean_id(raw.get("status")) or "present",
                "affordances": _json_safe(_as_list(raw.get("affordances"))),
            }
        )

    exit_rows = []
    for exit_id, raw in sorted(exits.items()):
        if not isinstance(raw, dict):
            continue
        eid = _clean_id(raw.get("id")) or str(exit_id)
        exit_rows.append(
            {
                "id": eid,
                "from_room_id": _clean_id(raw.get("from_room_id")) or None,
                "to_room_id": _clean_id(raw.get("to_room_id")) or None,
                "kind": _clean_id(raw.get("kind")) or "transition",
                "source_kind": _clean_id(raw.get("source_kind")) or "unknown",
                "source_ref": raw.get("source_ref"),
            }
        )

    actor_rows = []
    for actor_id, raw in sorted(actors.items()):
        if not isinstance(raw, dict):
            continue
        aid = _clean_id(raw.get("id")) or str(actor_id)
        actor_rows.append(
            {
                "id": aid,
                "lane": _clean_id(raw.get("lane")) or "unknown",
                "room_id": _clean_id(raw.get("room_id")) or None,
                "source_ref": raw.get("source_ref"),
            }
        )

    diagnostic_warning_count = _status_count(diagnostics, "warning")
    diagnostic_error_count = _status_count(diagnostics, "error")
    issue_warning_count = _status_count(issues, "warning")
    issue_error_count = _status_count(issues, "error")

    return _json_safe(
        {
            "schema_version": SESSION_RUNTIME_TEMPLATE_SCHEMA_VERSION,
            "contract": SESSION_RUNTIME_TEMPLATE_SCHEMA_VERSION,
            "mode": "session_runtime_diagnostic_template",
            "diagnostic_only": True,
            "not_runtime_path": True,
            "runtime_execution": "none",
            "session_id": _clean_id(session_id),
            "module_id": _clean_id(module_id) or _clean_id(world.get("module_id")),
            "runtime_profile_id": world.get("runtime_profile_id") or projection.get("runtime_profile_id"),
            "current_scene_id": current_scene_id or None,
            "current_room_id": current_room_id or None,
            "counts": {
                "room_count": len(room_rows),
                "prop_count": len(prop_rows),
                "exit_count": len(exit_rows),
                "actor_count": len(actor_rows),
                "diagnostic_count": len(diagnostics),
                "potential_issue_count": len(issues),
                "warning_count": diagnostic_warning_count + issue_warning_count,
                "error_count": diagnostic_error_count + issue_error_count,
                "diagnostic_warning_count": diagnostic_warning_count,
                "diagnostic_error_count": diagnostic_error_count,
                "potential_warning_count": issue_warning_count,
                "potential_error_count": issue_error_count,
            },
            "source_summary": {
                "rooms": _source_summary(rooms),
                "props": _source_summary(props),
                "exits": _source_summary(exits),
            },
            "rooms": room_rows,
            "props": prop_rows,
            "exits": exit_rows,
            "actors": actor_rows,
            "diagnostics": diagnostics,
            "potential_issues": issues,
        }
    )
