"""Game routes implementation concern: player shell state projection.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''

def _player_shell_state_view(
    *,
    state: dict[str, Any],
    run_id: str,
    template_id: str,
    module_id: str,
    runtime_session_id: str,
) -> dict[str, Any]:
    committed = state.get("committed_state") if isinstance(state.get("committed_state"), dict) else {}
    player_shell_context = committed.get("player_shell_context")
    if not isinstance(player_shell_context, dict):
        player_shell_context = state.get("player_shell_context") if isinstance(state.get("player_shell_context"), dict) else {}
    module_scope_truth = committed.get("module_scope_truth")
    if not isinstance(module_scope_truth, dict):
        module_scope_truth = state.get("module_scope_truth") if isinstance(state.get("module_scope_truth"), dict) else {}
    counter_proj = _shell_turn_counter_projection(state)
    view: dict[str, Any] = {
        "run_id": run_id,
        "template_id": template_id,
        "module_id": module_id,
        "runtime_session_id": runtime_session_id,
        "turn_counter": _shell_committed_turn_display_counter(state),
        "opening_committed": counter_proj["opening_committed"],
        "player_committed_turns": counter_proj["player_committed_turns"],
        "total_canonical_turns": counter_proj["total_canonical_turns"],
        "latest_canonical_turn_id": counter_proj["latest_canonical_turn_id"],
        "player_graph_turn_counter": state.get("turn_counter"),
        "current_scene_id": state.get("current_scene_id"),
        "history_count": state.get("history_count"),
        "last_narrative_commit_summary": committed.get("last_narrative_commit_summary"),
        "last_committed_consequences": committed.get("last_committed_consequences") or [],
        "last_open_pressures": committed.get("last_open_pressures") or [],
        "environment_state": committed.get("environment_state") if isinstance(committed.get("environment_state"), dict) else {},
        "player_shell_context": player_shell_context,
        "module_scope_truth": module_scope_truth,
    }
    w5_player_view = state.get("w5_player_view")
    if not isinstance(w5_player_view, dict):
        w5_player_view = committed.get("w5_player_view")
    w5_player_diag = state.get("w5_player_view_diagnostics")
    if not isinstance(w5_player_diag, dict):
        w5_player_diag = committed.get("w5_player_view_diagnostics")
    if isinstance(w5_player_diag, dict):
        runtime_world = state.get("runtime_world") if isinstance(state.get("runtime_world"), dict) else {}
        current_room_id = (
            str(w5_player_diag.get("current_room_fallback_value") or "").strip()
            or str(runtime_world.get("current_room_id") or "").strip()
            or None
        )
        if isinstance(w5_player_view, dict):
            where = w5_player_view.get("where_summary") if isinstance(w5_player_view.get("where_summary"), dict) else {}
            current_room_id = (
                str(where.get("current_visible_location") or "").strip()
                or str(where.get("current_location") or "").strip()
                or current_room_id
            )
            scene_location = where.get("scene_location")
            if isinstance(scene_location, dict):
                current_room_id = str(scene_location.get("value") or "").strip() or current_room_id
        view["w5_player_view_diagnostics"] = w5_player_diag
        if isinstance(w5_player_view, dict):
            view["w5_player_view"] = w5_player_view
        view["current_room_id"] = current_room_id

        view["current_room_source"] = w5_player_diag.get("current_room_source") or "fallback_current_room"
        view["current_room_fallback_value"] = w5_player_diag.get("current_room_fallback_value")
        view["current_room_w5_value"] = w5_player_diag.get("current_room_w5_value")
        view["current_room_mismatch"] = bool(w5_player_diag.get("current_room_mismatch"))
        feature_flags = state.get("feature_flags") if isinstance(state.get("feature_flags"), dict) else {}
        view["feature_flags"] = {
            "W5_AST_FRONTEND_PLAYER_VIEW_ENABLED": bool(
                feature_flags.get("W5_AST_FRONTEND_PLAYER_VIEW_ENABLED")
            )
        }
    return view
'''
