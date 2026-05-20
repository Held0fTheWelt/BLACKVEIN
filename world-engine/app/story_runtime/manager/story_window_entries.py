from __future__ import annotations

from ._deps import *

def _story_window_entries_for_session(session: StorySession) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for event in session.diagnostics:
        if not isinstance(event, dict):
            continue
        turn_number = event.get("turn_number")
        turn_kind = str(event.get("turn_kind") or "player").strip() or "player"
        commit = event.get("narrative_commit") if isinstance(event.get("narrative_commit"), dict) else {}
        consequences = commit.get("committed_consequences")
        consequence_lines = [str(item) for item in consequences] if isinstance(consequences, list) else []
        bundle = event.get("visible_output_bundle") if isinstance(event.get("visible_output_bundle"), dict) else {}
        spoken_lines = _coerce_visible_text_lines(bundle.get("spoken_lines"))
        action_lines = _coerce_visible_text_lines(bundle.get("action_lines"))
        render_support = bundle.get("render_support") if isinstance(bundle.get("render_support"), dict) else None
        authority = event.get("committed_turn_authority") if isinstance(event.get("committed_turn_authority"), dict) else {}
        validation = event.get("validation_outcome") if isinstance(event.get("validation_outcome"), dict) else {}
        runtime_governance_surface = (
            event.get("runtime_governance_surface")
            if isinstance(event.get("runtime_governance_surface"), dict)
            else {}
        )
        planner = commit.get("planner_truth") if isinstance(commit.get("planner_truth"), dict) else {}
        social_summary = (
            planner.get("social_state_summary")
            if isinstance(planner.get("social_state_summary"), dict)
            else {}
        )
        dramatic_context = (
            event.get("dramatic_context_summary")
            if isinstance(event.get("dramatic_context_summary"), dict)
            else {}
        )
        story_dramatic_context = _story_window_dramatic_context(dramatic_context)
        actor_turn_summary = (
            event.get("actor_turn_summary")
            if isinstance(event.get("actor_turn_summary"), dict)
            else {}
        )
        if not actor_turn_summary and story_dramatic_context:
            actor_turn_summary = {
                "contract": "actor_turn_summary.v1",
                "primary_responder_id": story_dramatic_context.get("responder_id"),
                "secondary_responder_ids": story_dramatic_context.get("secondary_responder_ids") or [],
                "spoken_line_count": story_dramatic_context.get("spoken_line_count") or len(spoken_lines),
                "action_line_count": story_dramatic_context.get("action_line_count") or len(action_lines),
                "initiative_summary": story_dramatic_context.get("initiative_summary") or {},
                "last_actor_outcome_summary": story_dramatic_context.get("last_actor_outcome_summary"),
            }
        authority_summary = {
            "authority_record_version": authority.get("authority_record_version"),
            "committed_scene_id": authority.get("committed_scene_id") or commit.get("committed_scene_id"),
            "validation_status": authority.get("validation_status") or validation.get("status"),
            "commit_applied": authority.get("commit_applied"),
            "quality_class": authority.get("quality_class"),
            "degradation_signals": authority.get("degradation_signals") or [],
            "degradation_summary": authority.get("degradation_summary"),
            "selected_scene_function": event.get("selected_scene_function"),
            "experiment_preview": event.get("experiment_preview"),
            "visibility_class_markers": event.get("visibility_class_markers") or [],
            "failure_markers": event.get("failure_markers") or [],
            "social_state_fingerprint": social_summary.get("fingerprint"),
            "social_risk_band": social_summary.get("social_risk_band"),
            "social_continuity_status": social_summary.get("social_continuity_status"),
            "dramatic_context": story_dramatic_context,
        }

        # Thin-path narrator fold: when realize_via_capabilities produced a single
        # narrator block (and no actor_line / actor_action), the narrator's prose IS
        # the outcome of the player's input. Fold it into the player_input_outcome
        # card and suppress the duplicate runtime_response entry below.
        thin_path_narrator_text: str | None = None
        thin_path_fold = False
        _event_scene_blocks_preview = _scene_blocks_from_turn_event(event)
        _event_realization_plan = (
            event.get("realization_plan")
            if isinstance(event.get("realization_plan"), dict)
            else None
        )
        _path_summary_for_event = (
            event.get("observability_path_summary")
            if isinstance(event.get("observability_path_summary"), dict)
            else event.get("path_summary")
            if isinstance(event.get("path_summary"), dict)
            else None
        )
        _realize_capability = None
        if _path_summary_for_event:
            _realize_capability = _path_summary_for_event.get(
                "realize_via_capabilities_used_capability"
            )
        if not _realize_capability and _event_realization_plan:
            _caps = _event_realization_plan.get("capabilities_selected") or []
            _realize_capability = _caps[0] if _caps else None
        _is_narrator_capability = isinstance(_realize_capability, str) and _realize_capability.startswith("narrator.")
        if _event_scene_blocks_preview:
            _narr_blocks = [
                b
                for b in _event_scene_blocks_preview
                if str(b.get("block_type") or "").strip().lower() == "narrator"
            ]
            _actor_blocks = [
                b
                for b in _event_scene_blocks_preview
                if str(b.get("block_type") or "").strip().lower()
                in ("actor_line", "actor_action")
            ]
            if _is_narrator_capability and len(_narr_blocks) == 1 and not _actor_blocks:
                _candidate_text = str(_narr_blocks[0].get("text") or "").strip()
                if _candidate_text:
                    thin_path_narrator_text = _candidate_text
                    thin_path_fold = True

        if turn_kind != "opening":
            raw_input = str(event.get("raw_input") or "").strip()
            if raw_input:
                proj_sw = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
                hid_sw = str(proj_sw.get("human_actor_id") or "").strip()
                interp_sw = event.get("interpreted_input") if isinstance(event.get("interpreted_input"), dict) else {}
                role_sw = str(proj_sw.get("selected_player_role") or "").strip()
                pdn = goc_player_role_display_name(role_sw) if role_sw else None
                player_blocks = _player_input_scene_blocks_for_story_window(
                    session_id=session.session_id,
                    turn_number=turn_number,
                    raw_input=raw_input,
                    session_output_language=session.session_output_language,
                    human_actor_id=hid_sw or None,
                    interpreted_input=interp_sw,
                    module_id=session.module_id,
                )
                if thin_path_fold and thin_path_narrator_text and player_blocks:
                    for _pb in player_blocks:
                        if str(_pb.get("block_type") or "") == "player_input_outcome":
                            _pb["text"] = thin_path_narrator_text
                            _pb["source"] = "narrator_realization_fold"
                            break
                _mid_sw = str(session.module_id or GOD_OF_CARNAGE_MODULE_ID).strip() or GOD_OF_CARNAGE_MODULE_ID
                _lang_sw = str(session.session_output_language or DEFAULT_SESSION_LANGUAGE).strip().lower()[:2] or DEFAULT_SESSION_LANGUAGE
                _second = resolve_string(
                    _mid_sw,
                    "player_shell.second_person",
                    _lang_sw,
                    content_modules_root=_goc_content_modules_root(),
                )
                player_entry: dict[str, Any] = {
                    "entry_id": f"{session.session_id}:{turn_number}:player",
                    "kind": "player_turn",
                    "role": "player",
                    "speaker": pdn if pdn else _second,
                    "turn_number": turn_number,
                    "text": raw_input,
                    "source": "player_input",
                }
                if player_blocks:
                    player_entry["scene_blocks"] = player_blocks
                    player_entry["text"] = str(player_blocks[0].get("text") or raw_input).strip() or raw_input
                entries.append(player_entry)

        visible_lines = _visible_lines_from_turn_event(event)
        scene_blocks = _scene_blocks_from_turn_event(event)
        if thin_path_fold:
            scene_blocks = [
                b
                for b in scene_blocks
                if str(b.get("block_type") or "").strip().lower() != "narrator"
            ]
            visible_lines = []
        quality_class, degradation_signals, degradation_summary = _canonical_quality_fields_from_surfaces(
            runtime_governance_surface=runtime_governance_surface,
            authority_summary=authority_summary,
        )
        degraded = quality_class in {QUALITY_CLASS_DEGRADED, QUALITY_CLASS_FAILED}
        degraded_reasons = list(degradation_signals)
        actor_survival_telemetry = (
            event.get("actor_survival_telemetry")
            if isinstance(event.get("actor_survival_telemetry"), dict)
            else {}
        )
        vitality = (
            actor_survival_telemetry.get("vitality_telemetry_v1")
            if isinstance(actor_survival_telemetry.get("vitality_telemetry_v1"), dict)
            else {}
        )
        operator_hints = (
            actor_survival_telemetry.get("operator_diagnostic_hints")
            if isinstance(actor_survival_telemetry.get("operator_diagnostic_hints"), dict)
            else {}
        )
        passivity_diagnosis = (
            actor_survival_telemetry.get("passivity_diagnosis_v1")
            if isinstance(actor_survival_telemetry.get("passivity_diagnosis_v1"), dict)
            else operator_hints
        )
        vitality_summary = {
            "response_present": bool(vitality.get("response_present")),
            "initiative_present": bool(vitality.get("initiative_present")),
            "multi_actor_realized": bool(vitality.get("multi_actor_realized")),
            "sparse_input_recovery_applied": bool(vitality.get("sparse_input_recovery_applied")),
            "realized_actor_ids": list(vitality.get("realized_actor_ids") or []),
            "rendered_actor_ids": list(vitality.get("rendered_actor_ids") or []),
        }

        if not visible_lines and not spoken_lines and not action_lines and not consequence_lines:
            continue
        runtime_entry = {
            "entry_id": f"{session.session_id}:{turn_number}:{turn_kind}",
            "kind": "opening" if turn_kind == "opening" else "runtime_response",
            "role": "runtime",
            "speaker": "World of Shadows",
            "turn_number": turn_number,
            "text": "\n\n".join(visible_lines),
            "spoken_lines": spoken_lines,
            "action_lines": action_lines,
            "committed_consequences": consequence_lines,
            "responder_id": story_dramatic_context.get("responder_id"),
            "validation_status": authority_summary.get("validation_status"),
            "quality_class": quality_class,
            "degradation_signals": degradation_signals,
            "degradation_summary": degradation_summary,
            "degraded": degraded,
            "degraded_reasons": degraded_reasons,
            "actor_turn_summary": actor_turn_summary,
            "actor_survival_telemetry": actor_survival_telemetry,
            "vitality_summary": vitality_summary,
            "why_turn_felt_passive": list(passivity_diagnosis.get("why_turn_felt_passive") or []),
            "primary_passivity_factors": list(passivity_diagnosis.get("primary_passivity_factors") or []),
            "source": "authoritative_story_runtime",
            "runtime_governance_surface": runtime_governance_surface,
            "authority_summary": authority_summary,
        }
        if scene_blocks:
            runtime_entry["scene_blocks"] = scene_blocks
        if render_support:
            runtime_entry["render_support"] = render_support
        if story_dramatic_context:
            runtime_entry["dramatic_context_summary"] = story_dramatic_context
        entries.append(runtime_entry)
    return entries

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
