"""Game routes implementation concern: session loop bundle evidence.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''


def _session_loop_evidence_for_bundle(
    *,
    created: dict[str, Any] | None,
    state: dict[str, Any],
    runtime_session_id: str,
    module_id: str,
) -> dict[str, Any] | None:
    if isinstance(created, dict) and isinstance(created.get("session_loop"), dict):
        return created["session_loop"]
    if isinstance(state.get("session_loop"), dict):
        return state["session_loop"]

    runtime_world = state.get("runtime_world") if isinstance(state.get("runtime_world"), dict) else {}
    if str(runtime_world.get("status") or "").strip() != "initialized":
        return None
    rooms = runtime_world.get("rooms") if isinstance(runtime_world.get("rooms"), dict) else {}
    props = runtime_world.get("props") if isinstance(runtime_world.get("props"), dict) else {}
    exits = runtime_world.get("exits") if isinstance(runtime_world.get("exits"), dict) else {}
    actors = runtime_world.get("actors") if isinstance(runtime_world.get("actors"), dict) else {}
    return {
        "status": "runtime_engine_initialized",
        "session_id": runtime_session_id,
        "module_id": module_id or runtime_world.get("module_id"),
        "turn_counter": state.get("turn_counter"),
        "current_scene_id": state.get("current_scene_id"),
        "history_len": state.get("history_count"),
        "diagnostics_len": None,
        "runtime_world": {
            "schema_version": runtime_world.get("schema_version"),
            "status": runtime_world.get("status"),
            "mode": runtime_world.get("mode"),
            "current_room_id": runtime_world.get("current_room_id"),
            "room_count": len(rooms),
            "prop_count": len(props),
            "exit_count": len(exits),
            "actor_count": len(actors),
            "diagnostic_summary": runtime_world.get("diagnostic_summary"),
        },
    }


'''
