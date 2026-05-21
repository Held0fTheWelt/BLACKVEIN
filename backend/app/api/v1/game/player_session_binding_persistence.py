"""Game routes implementation concern: player session binding persistence.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
def _persist_player_session_binding(
    user: User,
    *,

    run_id: str,
    template_id: str,
    template_title: str | None,
    module_id: str,
    runtime_session_id: str,
    session_input_language: str = _DEFAULT_OUTPUT_LANGUAGE,
    session_output_language: str = _DEFAULT_OUTPUT_LANGUAGE,
) -> GameSaveSlot:
    return upsert_save_slot_for_user(
        user.id,
        slot_key=_player_session_slot_key(run_id),
        title=template_title or f"Play session {run_id}",
        template_id=template_id,
        template_title=template_title,
        run_id=run_id,
        kind="canonical_player_session",
        status="active",
        metadata={
            "contract": "game_player_session_v1",
            "module_id": module_id,
            "runtime_session_id": runtime_session_id,
            "world_engine_story_session_id": runtime_session_id,
            "continuity_owner": "backend_game_player_session_bridge",
            "session_input_language": session_input_language,
            "session_output_language": session_output_language,
        },
    )

'''
