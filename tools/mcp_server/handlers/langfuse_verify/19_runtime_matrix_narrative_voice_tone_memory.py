"""Langfuse verify source segment: runtime_matrix_narrative_voice_tone_memory.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
            social_pressure_rec,
            relationship_state_rec,
            disclosure_rec,
            expectation_variation_rec,
            narrative_momentum_rec,
            dramatic_irony_rec,
            callback_rec,
            cascade_rec,
            npc_agency_rec,
            cap_rec,
            vis_rec,
            narrative_rec,
            voice_rec,
            tonal_rec,
            memory_rec,
        )
        if r.get("status") == "partial"
    ]
    main_record = failed_records[0] if failed_records else partial_records[0] if partial_records else {}
    reasons = main_record.get("reasons") if isinstance(main_record.get("reasons"), list) else []
    main_failure = str(main_record.get("failure_reason") or (reasons[0] if reasons else "")).strip() or None
    row = {
        "session_id": ledger.get("session_id") or path_summary.get("session_id") or _extract_metadata(raw_trace).get("session_id"),
        "trace_id": str(raw_trace.get("id") or raw_trace.get("trace_id") or "").strip(),
        "canonical_turn_id": ledger.get("canonical_turn_id") or path_summary.get("canonical_turn_id") or _extract_metadata(raw_trace).get("canonical_turn_id"),
        "environment": raw_trace.get("environment") or _extract_metadata(raw_trace).get("environment") or path_summary.get("environment"),
        "turn_number": ledger.get("turn_number") if ledger else path_summary.get("turn_number"),
        "raw_input": input_actual.get("raw_player_input") or action_actual.get("raw_player_input") or path_summary.get("raw_player_input"),
        "input_kind": input_actual.get("player_input_kind") or input_actual.get("input_kind") or action_actual.get("input_kind") or path_summary.get("player_input_kind"),
        "action_kind": action_actual.get("action_kind"),
        "turn_aspect_ledger_present": bool(ledger.get("turn_aspect_ledger")) if ledger else bool(path_summary.get("turn_aspect_ledger_present") or det_scores.get("turn_aspect_ledger_present")),
        "beat_selected": bool(beat_selected.get("selected_beat_id") or beat_selected.get("selected_scene_function")) if beat_selected else det_scores.get("beat_selected"),
        "selected_beat": beat_selected.get("selected_beat_id") or beat_selected.get("selected_scene_function"),
        "beat_realized": beat_actual.get("realized") if "realized" in beat_actual else det_scores.get("beat_realized"),
        "scene_energy_target_present": bool(scene_energy_target) if scene_energy_rec else det_scores.get("scene_energy_target_present"),
        "scene_energy_level": scene_energy_target.get("energy_level"),
        "scene_energy_transition": scene_energy_target.get("target_transition") or scene_energy_transition.get("transition_intent"),
        "scene_energy_contract_pass": (
            scene_energy_actual.get("contract_pass")
            if "contract_pass" in scene_energy_actual
            else det_scores.get("scene_energy_contract_pass")
        ),
        "scene_energy_transition_allowed": (
            scene_energy_actual.get("transition_allowed")
            if "transition_allowed" in scene_energy_actual
            else det_scores.get("scene_energy_transition_allowed")
        ),
        "scene_energy_pressure_realized": (
            "scene_energy_missing_required_pressure" not in scene_energy_failure_codes
            if scene_energy_actual
            else det_scores.get("scene_energy_pressure_realized")
        ),
        "scene_energy_failure_codes": scene_energy_failure_codes,
        "pacing_rhythm_target_present": (
            bool(pacing_rhythm_target)
            if pacing_rhythm_rec
            else det_scores.get("pacing_rhythm_target_present")
        ),
        "pacing_rhythm_cadence": pacing_rhythm_target.get("cadence"),
        "pacing_rhythm_response_shape": pacing_rhythm_target.get("response_shape"),
        "pacing_rhythm_contract_pass": (
            pacing_rhythm_actual.get("contract_pass")
            if "contract_pass" in pacing_rhythm_actual
            else det_scores.get("pacing_rhythm_contract_pass")
        ),
        "pacing_rhythm_density_respected": (
            "pacing_rhythm_visible_density_exceeded" not in pacing_rhythm_failure_codes
            if pacing_rhythm_actual
            else det_scores.get("pacing_rhythm_density_respected")
        ),
        "pacing_rhythm_pause_respected": (
            "pacing_rhythm_pause_obligation_lost" not in pacing_rhythm_failure_codes
'''
