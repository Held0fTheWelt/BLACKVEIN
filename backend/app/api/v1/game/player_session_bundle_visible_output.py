"""Game routes implementation concern: player session bundle visible output.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
def _player_session_bundle(
    *,
    run_id: str,
    template_id: str,
    module_id: str,
    runtime_session_id: str,
    state: dict[str, Any],
    created: dict[str, Any] | None = None,
    turn: dict[str, Any] | None = None,
) -> dict[str, Any]:
    story_window = _story_window_from_state(state)
    latest_turn = turn if isinstance(turn, dict) else None
    opening_turn = created.get("opening_turn") if isinstance(created, dict) and isinstance(created.get("opening_turn"), dict) else None
    session_loop = _session_loop_evidence_for_bundle(
        created=created,
        state=state,
        runtime_session_id=runtime_session_id,
        module_id=module_id,

    )
    if latest_turn is None:
        latest_turn = state.get("last_committed_turn") if isinstance(state.get("last_committed_turn"), dict) else None
    latest_governance = (
        latest_turn.get("runtime_governance_surface")
        if isinstance(latest_turn, dict) and isinstance(latest_turn.get("runtime_governance_surface"), dict)
        else None
    )
    narrator_streaming = None
    latest_turn_kind = str(latest_turn.get("turn_kind") or "") if isinstance(latest_turn, dict) else ""
    if (
        isinstance(latest_turn, dict)
        and latest_turn_kind.strip().lower() != "opening"
        and isinstance(latest_turn.get("narrator_streaming"), dict)
    ):
        narrator_streaming = latest_turn.get("narrator_streaming")
    cumulative_blocks = _cumulative_scene_blocks_from_story_window(story_window)
    used_cumulative = bool(cumulative_blocks)
    if cumulative_blocks:
        scene_blocks = cumulative_blocks
    else:
        scene_blocks = (
            _scene_blocks_from_turn(latest_turn)
            or _scene_blocks_from_turn(opening_turn)
            or _scene_blocks_from_story_window(story_window)
        )
    visible_scene_output: dict[str, Any] | None = None
    if scene_blocks:
        if str(module_id or "").strip() == GOC_MODULE_ID:
            scene_blocks = polish_goc_scene_blocks_for_player_shell(scene_blocks)
        player_cards, shell_diag = build_player_facing_narrative_cards(scene_blocks)
        if used_cumulative and player_cards:
            prior_semantic = _scene_blocks_count_prior_story_entries(story_window)
            tw_start = player_shell_typewriter_start_index(
                player_cards,
                prior_semantic_index=prior_semantic,
                used_cumulative_story_blocks=True,
            )
        else:
            tw_start = _typewriter_slice_start_index_for_bundle(
                story_window=story_window,
                scene_blocks=player_cards,
                used_cumulative_story_blocks=used_cumulative,
            )
        visible_scene_output = {
            "blocks": player_cards,
            "player_shell_narrative_card_diagnostics": shell_diag,
        }
        if tw_start is not None:
            visible_scene_output["typewriter_slice_start_index"] = tw_start
    readiness_created = dict(created) if isinstance(created, dict) else {}
    if session_loop and not isinstance(readiness_created.get("session_loop"), dict):
        readiness_created["session_loop"] = session_loop
    opening_readiness = evaluate_session_opening_readiness(
        story_entries=story_window["entries"],
        visible_scene_output=visible_scene_output,
        created=readiness_created,
    )
    rip = runtime_intelligence_projection_from_turn_aspect_ledger(latest_turn)
    deg = degradation_signals_from_latest_turn(latest_turn)
    readiness_overlay = resolve_runtime_readiness_with_adr0041(
        base_runtime_session_ready=bool(opening_readiness["runtime_session_ready"]),
        base_can_execute=bool(opening_readiness["can_execute"]),
        opening_generation_status=str(opening_readiness.get("opening_generation_status") or ""),
        runtime_intelligence_projection=rip,
        degradation_signals=deg,
        retrieval_payload=latest_turn.get("retrieval") if isinstance(latest_turn, dict) else None,
    )
    retrieval_diag = (
        latest_turn.get("retrieval")
        if isinstance(latest_turn, dict) and isinstance(latest_turn.get("retrieval"), dict)
        else {}

    )
'''
