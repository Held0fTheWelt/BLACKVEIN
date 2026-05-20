from __future__ import annotations

from ._deps import *

def _story_window_dramatic_context(dramatic_context: dict[str, Any] | None) -> dict[str, Any]:
    """Project committed dramatic context into the story-window surface."""
    if not isinstance(dramatic_context, dict):
        return {}
    responder = dramatic_context.get("responder") if isinstance(dramatic_context.get("responder"), dict) else {}
    pacing = dramatic_context.get("pacing") if isinstance(dramatic_context.get("pacing"), dict) else {}
    scene_energy = (
        dramatic_context.get("scene_energy")
        if isinstance(dramatic_context.get("scene_energy"), dict)
        else {}
    )
    pacing_rhythm = (
        dramatic_context.get("pacing_rhythm")
        if isinstance(dramatic_context.get("pacing_rhythm"), dict)
        else {}
    )
    social_pressure = (
        dramatic_context.get("social_pressure")
        if isinstance(dramatic_context.get("social_pressure"), dict)
        else {}
    )
    scene_energy_target = (
        scene_energy.get("target") if isinstance(scene_energy.get("target"), dict) else {}
    )
    pacing_rhythm_target = (
        pacing_rhythm.get("target") if isinstance(pacing_rhythm.get("target"), dict) else {}
    )
    social_pressure_target = (
        social_pressure.get("target") if isinstance(social_pressure.get("target"), dict) else {}
    )
    scene = dramatic_context.get("scene_assessment") if isinstance(dramatic_context.get("scene_assessment"), dict) else {}
    social = dramatic_context.get("social_state") if isinstance(dramatic_context.get("social_state"), dict) else {}
    outcome = dramatic_context.get("dramatic_outcome") if isinstance(dramatic_context.get("dramatic_outcome"), dict) else {}
    beat = dramatic_context.get("beat") if isinstance(dramatic_context.get("beat"), dict) else {}
    threads = dramatic_context.get("narrative_threads") if isinstance(dramatic_context.get("narrative_threads"), dict) else {}
    return {
        "contract": "story_window_dramatic_context.v1",
        "selected_scene_function": dramatic_context.get("selected_scene_function"),
        "function_type": dramatic_context.get("function_type"),
        "responder_id": responder.get("responder_id"),
        "secondary_responder_ids": _compact_context_list(
            responder.get("secondary_responder_ids"), limit=4
        ),
        "pacing_mode": pacing.get("pacing_mode"),
        "pacing_rhythm_cadence": pacing_rhythm_target.get("cadence"),
        "pacing_rhythm_response_shape": pacing_rhythm_target.get("response_shape"),
        "social_pressure_score": social_pressure_target.get("target_score"),
        "social_pressure_band": social_pressure_target.get("target_band"),
        "social_pressure_trend": social_pressure_target.get("trend"),
        "scene_energy_level": scene_energy_target.get("energy_level"),
        "scene_energy_transition": scene_energy_target.get("target_transition"),
        "pressure_state": scene.get("pressure_state"),
        "thread_pressure_state": scene.get("thread_pressure_state"),
        "social_risk_band": social.get("social_risk_band"),
        "social_outcome": outcome.get("social_outcome"),
        "dramatic_direction": outcome.get("dramatic_direction"),
        "spoken_line_count": outcome.get("spoken_line_count"),
        "action_line_count": outcome.get("action_line_count"),
        "initiative_summary": outcome.get("initiative_summary")
        if isinstance(outcome.get("initiative_summary"), dict)
        else {},
        "last_actor_outcome_summary": outcome.get("last_actor_outcome_summary"),
        "continuity_classes": _compact_context_list(outcome.get("continuity_classes"), limit=4),
        "beat_id": beat.get("beat_id"),
        "thread_pressure_level": threads.get("thread_pressure_level"),
        "player_visible": False,
    }

def _player_shell_context_from_dramatic_context(
    dramatic_context: dict[str, Any] | None,
    *,
    session: "StorySession" | None = None,
) -> dict[str, Any]:
    """Project a small player-shell slice from committed dramatic context plus session identity."""
    out: dict[str, Any] = {}
    if isinstance(dramatic_context, dict):
        story_context = _story_window_dramatic_context(dramatic_context)
        if story_context:
            out = {
                "contract": "player_shell_dramatic_context.v1",
                "selected_scene_function": story_context.get("selected_scene_function"),
                "responder_id": story_context.get("responder_id"),
                "secondary_responder_ids": story_context.get("secondary_responder_ids") or [],
                "pacing_mode": story_context.get("pacing_mode"),
                "pacing_rhythm_cadence": story_context.get("pacing_rhythm_cadence"),
                "pressure_state": story_context.get("pressure_state"),
                "thread_pressure_state": story_context.get("thread_pressure_state"),
                "social_risk_band": story_context.get("social_risk_band"),
                "social_outcome": story_context.get("social_outcome"),
                "spoken_line_count": story_context.get("spoken_line_count"),
                "action_line_count": story_context.get("action_line_count"),
                "initiative_summary": story_context.get("initiative_summary") or {},
                "last_actor_outcome_summary": story_context.get("last_actor_outcome_summary"),
                "continuity_classes": story_context.get("continuity_classes") or [],
                "thread_pressure_level": story_context.get("thread_pressure_level"),
                "surface_note": "bounded_player_shell_context_not_operator_diagnostics",
            }
    if session is not None:
        proj = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
        role = str(proj.get("selected_player_role") or "").strip()
        out["session_output_language"] = getattr(session, "session_output_language", None) or DEFAULT_SESSION_LANGUAGE
        if role:
            out["selected_player_role"] = role
        pdn = goc_player_role_display_name(role)
        if pdn:
            out["player_role_display_name"] = pdn
        lang = str(out.get("session_output_language") or DEFAULT_SESSION_LANGUAGE).strip().lower()[:2]
        mid = str(getattr(session, "module_id", None) or GOD_OF_CARNAGE_MODULE_ID).strip() or GOD_OF_CARNAGE_MODULE_ID
        root = _goc_content_modules_root()
        out["npc_responder_label"] = resolve_string(
            mid, "player_shell.npc_responder_label", lang, content_modules_root=root
        )
        if pdn:
            out["player_identity_line"] = resolve_string(
                mid, "player_shell.player_identity_line", lang, content_modules_root=root, role=pdn
            )
        else:
            out["player_identity_line"] = None
        rid = str(out.get("responder_id") or "").strip()
        if rid:
            out["npc_responder_display_name"] = _goc_npc_shell_legal_name(rid)
    return out

def _build_committed_turn_authority(
    *,
    narrative_commit_payload: dict[str, Any],
    graph_state: dict[str, Any],
    committed_scene_id: str,
    turn_number: int,
    dramatic_context_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the bounded single authority record for one committed story turn."""
    graph_commit = graph_state.get("committed_result") if isinstance(graph_state.get("committed_result"), dict) else {}
    validation = graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
    continuity = graph_state.get("continuity_impacts") if isinstance(graph_state.get("continuity_impacts"), list) else []
    record = {
        "authority_record_version": "committed_turn_authority.v1",
        "authority": "world_engine_story_runtime",
        "turn_number": turn_number,
        "committed_scene_id": committed_scene_id,
        "validation_status": validation.get("status"),
        "commit_applied": bool(graph_commit.get("commit_applied")),
        "quality_class": graph_state.get("quality_class"),
        "degradation_signals": list(graph_state.get("degradation_signals") or []),
        "degradation_summary": graph_state.get("degradation_summary"),
        "graph_commit": graph_commit,
        "narrative_commit": narrative_commit_payload,
        "continuity_impacts": continuity,
        "truth_sources": {
            "scene_progression": "narrative_commit",
            "dramatic_effects": "graph_commit",
            "social_state": "narrative_commit.planner_truth.social_state_summary",
            "dramatic_context": "dramatic_context_summary",
            "player_visibility": "visible_output_bundle",
        },
    }
    if isinstance(dramatic_context_summary, dict) and dramatic_context_summary:
        record["dramatic_context_summary"] = dramatic_context_summary
    return record

def _resolve_canonical_path_for_session(session: "StorySession") -> Any | None:
    """Resolve the canonical_path bundle for the session's content module.

    Returns None when the module has no canonical_path/ directory or yaml is
    unavailable. The resolver caches by module_root so repeated calls are cheap.
    """
    try:
        from ai_stack.canonical_path.canonical_path_resolver import (
            load_canonical_path,
            CanonicalPathResolveError,
        )
    except ImportError:
        return None
    try:
        module_root = _goc_content_modules_root() / session.module_id
    except Exception:
        return None
    if not module_root.is_dir():
        return None
    try:
        return load_canonical_path(module_root, content_module_id=session.module_id)
    except CanonicalPathResolveError:
        return None
    except Exception:
        return None

def _phase1_canonical_context_for_session(session: "StorySession") -> dict[str, Any]:
    """Build graph context for Director-Pause from the current canonical step."""
    step_id = str(getattr(session, "canonical_step_id", None) or "").strip()
    if not step_id:
        return {}
    canonical_path = _resolve_canonical_path_for_session(session)
    if canonical_path is None:
        return {"canonical_step_id": step_id}
    step = canonical_path.get_step(step_id)
    if step is None:
        return {"canonical_step_id": step_id}
    present = step.present if isinstance(step.present, dict) else {}
    named = [
        str(actor_id).strip()
        for actor_id in (present.get("named_characters") or [])
        if str(actor_id).strip()
    ]
    loc_ref = step.location_ref if isinstance(step.location_ref, dict) else {}
    live_scene = (
        (session.environment_state or {}).get("current_room_id")
        if isinstance(session.environment_state, dict)
        else None
    ) or getattr(session, "current_scene_id", None)
    scene_id = str(live_scene or loc_ref.get("location_id") or "").strip() or None
    return {
        "canonical_step_id": step_id,
        "current_step_named_characters": named,
        "current_step_scene_id": scene_id,
        "canonical_path": {
            "steps": {
                step_id: {
                    "present": dict(present),
                    "location_ref": dict(loc_ref),
                }
            }
        },
    }

def _turn_holds_canonical_path_for_free_player_action(graph_state: dict[str, Any]) -> bool:
    frame = graph_state.get("player_action_frame") if isinstance(graph_state.get("player_action_frame"), dict) else {}
    if not frame:
        return False
    return str(frame.get("canonical_path_effect") or "").strip() == "hold_current_step"

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
