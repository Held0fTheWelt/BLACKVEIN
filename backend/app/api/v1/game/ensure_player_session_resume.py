"""Game routes implementation concern: ensure player session resume.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''


def _ensure_player_session(
    user: User,

    *,
    run_id: str | None = None,
    template_id: str | None = None,
    run_payload: dict[str, Any] | None = None,
    trace_id: str | None = None,
    langfuse_trace_id: str | None = None,
    selected_player_role: str | None = None,
    session_input_language: str | None = None,
    session_output_language: str = _DEFAULT_OUTPUT_LANGUAGE,
    skip_graph_opening_on_create: bool = False,
) -> dict[str, Any]:
    clean_run_id = (run_id or "").strip()
    created: dict[str, Any] | None = None

    if not clean_run_id:
        if not isinstance(run_payload, dict):
            raise ValidationError("run_id is required.")
        clean_run_id = _run_id(run_payload)

    slot = _find_player_session_slot(user.id, clean_run_id)
    if slot is not None:
        metadata = slot.metadata_json if isinstance(slot.metadata_json, dict) else {}
        runtime_session_id = str(
            metadata.get("runtime_session_id") or metadata.get("world_engine_story_session_id") or ""
        ).strip()
        module_id = str(metadata.get("module_id") or "").strip()
        slot_template_id = str(slot.template_id or template_id or "").strip()
        if runtime_session_id and module_id and slot_template_id:
            try:
                state = get_story_state(runtime_session_id, trace_id=g.get("trace_id"))
                return _player_session_bundle(
                    run_id=clean_run_id,
                    template_id=slot_template_id,
                    module_id=module_id,
                    runtime_session_id=runtime_session_id,
                    state=state,
                )
            except GameServiceError as exc:
                if exc.status_code != route_status_codes.not_found:
                    raise
                raise GameServiceError(
                    "World-Engine story session is no longer available; restart is required.",
                    status_code=route_status_codes.conflict,
                    code="session_lost",
                    payload={
                        "resume_status": "needs_restart",
                        "runtime_session_id": runtime_session_id,
                        "run_id": clean_run_id,
                    },
                ) from exc
'''
