SOURCE = r'''\
        "narrator_path_selected": narrator_path_selected,
        "director_narrator_path_plan": graph_state.get("director_narrator_path_plan")
        if isinstance(graph_state.get("director_narrator_path_plan"), dict)
        else None,
        "narrator_path": graph_state.get("narrator_path")
        if isinstance(graph_state.get("narrator_path"), dict)
        else None,
        "validator_dispatch_mode": (
            _validator_dispatch_report.get("dispatch_mode")
            or _validator_dispatch_report.get("mode")
            or graph_state.get("validator_dispatch_mode")
        ),
        "readiness_policy_input": _readiness_policy_input,
        "validation_status": validation.get("status"),
        "validation_reason": validation.get("reason"),
        "intent_surface_diagnostics": (
            validation.get("intent_surface_diagnostics")
            if isinstance(validation.get("intent_surface_diagnostics"), dict)
            else {}
        ),
        "npc_narrated_player_action_violation": bool(
            (
                validation.get("intent_surface_diagnostics")
                if isinstance(validation.get("intent_surface_diagnostics"), dict)
                else {}
            ).get("npc_narrated_player_action_violation")
        ),
        "actor_lane_validation_status": actor_lane_validation.get("status"),
        "actor_lane_validation_reason": actor_lane_validation.get("reason"),
        "commit_applied": bool(committed.get("commit_applied")),
        "player_input_kind": str(interpreted_input.get("player_input_kind") or "").strip().lower() or None,
        "player_input_kind_family": player_input_kind_family(_player_input_kind) if _player_input_kind else None,
        "intent_contract_version": INTENT_CONTRACT_VERSION,
        "player_action_committed": bool(interpreted_input.get("player_action_committed")),
        "player_speech_committed": bool(interpreted_input.get("player_speech_committed")),
        "narrator_response_expected": bool(interpreted_input.get("narrator_response_expected")),
        "npc_response_expected": bool(interpreted_input.get("npc_response_expected")),
        "player_action_frame_present": bool(
            graph_state.get("player_action_frame")
            if isinstance(graph_state.get("player_action_frame"), dict)
            else False
        ),
        "affordance_resolution_present": bool(
            graph_state.get("affordance_resolution")
            if isinstance(graph_state.get("affordance_resolution"), dict)
            else False
        ),
        "affordance_status": (
            str(
                (
                    graph_state.get("affordance_resolution")
                    if isinstance(graph_state.get("affordance_resolution"), dict)
                    else {}
                ).get("affordance_status")
                or ""
            ).strip()
            or None
        ),
        "action_commit_policy": (
            str(
                (
                    graph_state.get("affordance_resolution")
                    if isinstance(graph_state.get("affordance_resolution"), dict)
                    else {}
                ).get("action_commit_policy")
                or ""
            ).strip()
            or None
        ),
        "action_resolution_branch": routing.get("action_resolution_branch"),
        "action_resolution_short_path": bool(routing.get("action_resolution_short_path")),
        "action_resolution_short_path_reason": routing.get("action_resolution_short_path_reason"),
        "synthetic_short_path": bool(routing.get("action_resolution_short_path")),
        "authoritative_action_resolution_reason": (
            routing.get("action_resolution_short_path_reason")
            if routing.get("action_resolution_short_path")
            else None
        ),
        "generation_required": (
            bool(routing.get("generation_required"))
            if routing.get("generation_required") is not None
            else bool("invoke_model" in nodes or "fallback_model" in nodes)
        ),
        "semantic_move_kind": str(semantic_move_record.get("move_type") or "").strip() or None,
        "subtext_surface_mode": str(_subtext_record.get("surface_mode") or "").strip() or None,
        "subtext_hidden_intent_hypothesis": (
            str(_subtext_record.get("hidden_intent_hypothesis") or "").strip() or None
        ),
        "subtext_function": str(_subtext_record.get("subtext_function") or "").strip() or None,
        "subtext_sincerity_band": str(_subtext_record.get("sincerity_band") or "").strip() or None,
        "subtext_policy_source": str(_subtext_record.get("policy_source") or "").strip() or None,
        "subtext_policy_rule_id": str(_subtext_record.get("policy_rule_id") or "").strip() or None,
        "subtext_evidence_codes": list(_subtext_record.get("evidence_codes") or [])
        if isinstance(_subtext_record.get("evidence_codes"), list)
        else [],
        "scene_director_selection_source": (
            str(multi_pressure_resolution.get("selection_source") or "").strip()
            or str(scene_plan_record.get("selection_source") or "").strip()
            or None
        ),
        "planner_rationale_codes": list(scene_plan_record.get("planner_rationale_codes") or [])
        if isinstance(scene_plan_record.get("planner_rationale_codes"), list)
        else [],
        "scene_energy_target": (
            graph_state.get("scene_energy_target")
            if isinstance(graph_state.get("scene_energy_target"), dict)
            else scene_plan_record.get("scene_energy_target")
            if isinstance(scene_plan_record.get("scene_energy_target"), dict)
            else {}
        ),
        "scene_energy_transition": (
            graph_state.get("scene_energy_transition")
            if isinstance(graph_state.get("scene_energy_transition"), dict)
            else scene_plan_record.get("scene_energy_transition")
            if isinstance(scene_plan_record.get("scene_energy_transition"), dict)
            else {}
        ),
        "scene_energy_validation": (
            graph_state.get("scene_energy_validation")
            if isinstance(graph_state.get("scene_energy_validation"), dict)
            else {}
        ),
        "pacing_rhythm_state": (
            graph_state.get("pacing_rhythm_state")
            if isinstance(graph_state.get("pacing_rhythm_state"), dict)
            else scene_plan_record.get("pacing_rhythm_state")
            if isinstance(scene_plan_record.get("pacing_rhythm_state"), dict)
            else {}
        ),
        "pacing_rhythm_target": (
            graph_state.get("pacing_rhythm_target")
            if isinstance(graph_state.get("pacing_rhythm_target"), dict)
            else scene_plan_record.get("pacing_rhythm_target")
            if isinstance(scene_plan_record.get("pacing_rhythm_target"), dict)
            else {}
        ),
        "pacing_rhythm_validation": (
            graph_state.get("pacing_rhythm_validation")
            if isinstance(graph_state.get("pacing_rhythm_validation"), dict)
            else {}
        ),
        "temporal_control_state": (
            graph_state.get("temporal_control_state")
            if isinstance(graph_state.get("temporal_control_state"), dict)
            else scene_plan_record.get("temporal_control_state")
            if isinstance(scene_plan_record.get("temporal_control_state"), dict)
            else {}
        ),
        "temporal_control_target": (
            graph_state.get("temporal_control_target")
            if isinstance(graph_state.get("temporal_control_target"), dict)
            else scene_plan_record.get("temporal_control_target")
            if isinstance(scene_plan_record.get("temporal_control_target"), dict)
            else {}
        ),
        "temporal_control_validation": (
            graph_state.get("temporal_control_validation")
            if isinstance(graph_state.get("temporal_control_validation"), dict)
            else {}
        ),
        "sensory_context_state": (
            graph_state.get("sensory_context_state")
            if isinstance(graph_state.get("sensory_context_state"), dict)
            else scene_plan_record.get("sensory_context_state")
            if isinstance(scene_plan_record.get("sensory_context_state"), dict)
            else {}
        ),
        "sensory_context_target": (
            graph_state.get("sensory_context_target")
            if isinstance(graph_state.get("sensory_context_target"), dict)
            else scene_plan_record.get("sensory_context_target")
            if isinstance(scene_plan_record.get("sensory_context_target"), dict)
            else {}
        ),
        "sensory_context_validation": (
            graph_state.get("sensory_context_validation")
            if isinstance(graph_state.get("sensory_context_validation"), dict)
            else {}
        ),
        "genre_awareness_state": (
            graph_state.get("genre_awareness_state")
            if isinstance(graph_state.get("genre_awareness_state"), dict)
            else scene_plan_record.get("genre_awareness_state")
            if isinstance(scene_plan_record.get("genre_awareness_state"), dict)
            else {}
        ),
        "genre_awareness_target": (
            graph_state.get("genre_awareness_target")
            if isinstance(graph_state.get("genre_awareness_target"), dict)
            else scene_plan_record.get("genre_awareness_target")
            if isinstance(scene_plan_record.get("genre_awareness_target"), dict)
            else {}
        ),
        "genre_awareness_validation": (
            graph_state.get("genre_awareness_validation")
            if isinstance(graph_state.get("genre_awareness_validation"), dict)
            else {}
        ),
        "symbolic_object_resonance_state": (
            graph_state.get("symbolic_object_resonance_state")
            if isinstance(graph_state.get("symbolic_object_resonance_state"), dict)
            else scene_plan_record.get("symbolic_object_resonance_state")
            if isinstance(scene_plan_record.get("symbolic_object_resonance_state"), dict)
            else {}
        ),
        "symbolic_object_resonance_target": (
            graph_state.get("symbolic_object_resonance_target")
            if isinstance(graph_state.get("symbolic_object_resonance_target"), dict)
            else scene_plan_record.get("symbolic_object_resonance_target")
            if isinstance(scene_plan_record.get("symbolic_object_resonance_target"), dict)
            else {}
        ),
        "symbolic_object_resonance_validation": (
            graph_state.get("symbolic_object_resonance_validation")
            if isinstance(graph_state.get("symbolic_object_resonance_validation"), dict)
            else {}
        ),
        "social_pressure_state": (
            graph_state.get("social_pressure_state")
            if isinstance(graph_state.get("social_pressure_state"), dict)
            else scene_plan_record.get("social_pressure_state")
            if isinstance(scene_plan_record.get("social_pressure_state"), dict)
            else {}
        ),
        "social_pressure_target": (
            graph_state.get("social_pressure_target")
            if isinstance(graph_state.get("social_pressure_target"), dict)
            else scene_plan_record.get("social_pressure_target")
            if isinstance(scene_plan_record.get("social_pressure_target"), dict)
            else {}
        ),
        "social_pressure_validation": (
            graph_state.get("social_pressure_validation")
            if isinstance(graph_state.get("social_pressure_validation"), dict)
            else {}
        ),
        "expectation_variation_state": (
            graph_state.get("expectation_variation_state")
            if isinstance(graph_state.get("expectation_variation_state"), dict)
            else scene_plan_record.get("expectation_variation_state")
'''
