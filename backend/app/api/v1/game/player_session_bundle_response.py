"""Game routes implementation concern: player session bundle response.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
    return {
        "contract": "game_player_session_v1",
        "run_id": run_id,
        "template_id": template_id,
        "module_id": module_id,
        "ticket_id": None,
        "backend_session_id": None,
        "runtime_session_id": runtime_session_id,
        "world_engine_story_session_id": runtime_session_id,
        "runtime_session_ready": readiness_overlay["runtime_ready"],
        "can_execute": readiness_overlay["can_execute"],
        "opening_generation_status": opening_readiness["opening_generation_status"],
        "opening_present": opening_readiness["opening_present"],
        "story_window": story_window,
        "story_entries": story_window["entries"],
        "visible_scene_output": visible_scene_output,
        "narrator_streaming": narrator_streaming,
        "shell_state_view": _player_shell_state_view(
            state=state,
            run_id=run_id,
            template_id=template_id,
            module_id=module_id,
            runtime_session_id=runtime_session_id,
        ),
        "authoritative_state": state,
        "turn": latest_turn,
        "opening_turn": opening_turn,
        "session_loop": session_loop,
        "governance": {
            "runtime_governance_surface": latest_governance,
            "runtime_config_status": created.get("runtime_config_status") if isinstance(created, dict) else None,
            "adr0041_readiness_projection_echo": build_adr0041_readiness_projection_echo(rip),
            "adr0041_runtime_readiness_consumer": readiness_overlay,
            "retrieval_diagnostic_context": {
                "source": "latest_turn.retrieval",
                "present": bool(retrieval_diag),
                "diagnostic_only": True,
                "not_readiness_authority": True,
                "retrieval_authority": retrieval_diag.get("retrieval_authority")
                if isinstance(retrieval_diag.get("retrieval_authority"), dict)
                else {},
                "boundary_guard": retrieval_diag.get("boundary_guard")
                if isinstance(retrieval_diag.get("boundary_guard"), dict)
                else {},
            },
            "content_publication_gate": "published_game_content_required_for_template_module_binding",
            "player_path_governed_by": [
                "game content publication lifecycle",
                "world-engine governed runtime config",
                "runtime validation and guardrails",
            ],
        },
        "identifier_model": {
            "template_id": "launcher/content template selection",
            "module_id": "compiled runtime module for story execution",
            "run_id": "player launch and continuity handle",
            "ticket_id": "not used by canonical HTTP story player path",
            "backend_session_id": "not used by canonical player path",
            "runtime_session_id": "world-engine story session id",
        },
    }


_ALLOWED_OUTPUT_LANGUAGES = frozenset({"de", "en"})
_DEFAULT_OUTPUT_LANGUAGE = "de"


'''
