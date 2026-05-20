SOURCE = r'''\
        gov["transition_pattern"] = graph_state.get("transition_pattern")
        gov["dramatic_quality_gate"] = val.get("dramatic_quality_gate")
        gate_outcome = val.get("dramatic_effect_gate_outcome") if isinstance(val.get("dramatic_effect_gate_outcome"), dict) else {}
        gov["dramatic_effect_rationale_codes"] = (
            list(gate_outcome.get("effect_rationale_codes") or [])
            if isinstance(gate_outcome, dict)
            else []
        )
        actor_lane_validation = val.get("actor_lane_validation") if isinstance(val.get("actor_lane_validation"), dict) else {}
        gov["actor_lane_validation_status"] = actor_lane_validation.get("status")
        gov["actor_lane_validation_reason"] = actor_lane_validation.get("reason")
        gov["quality_class"] = graph_state.get("quality_class")
        gov["degradation_signals"] = list(graph_state.get("degradation_signals") or [])
        gov["degradation_summary"] = graph_state.get("degradation_summary")
        # The live player-turn path always routes through ``run_validation_seam``
        # inside the graph, which populates ``validator_lane``. Publishing it
        # here makes the "which validator ran" question auditable per turn and
        # distinguishes the canonical live lane from the operator endpoint at
        # /api/internal/narrative/runtime/validate-and-recover.
        gov["validator_lane"] = val.get("validator_lane")
        gov["validator_layers_used"] = narrative_commit.planner_truth.validator_layers_used
        reconciliation = graph_state.get("responder_reconciliation")
        if isinstance(reconciliation, dict):
            gov["responder_reconciliation"] = reconciliation
        social_summary = narrative_commit.planner_truth.social_state_summary
        if social_summary:
            gov["social_state_truth"] = {
                "committed": True,
                "fingerprint": social_summary.get("fingerprint"),
                "validated": social_summary.get("validated"),
                "social_risk_band": social_summary.get("social_risk_band"),
                "responder_asymmetry_code": social_summary.get("responder_asymmetry_code"),
                "social_continuity_status": social_summary.get("social_continuity_status"),
                "prior_social_state_fingerprint": social_summary.get("prior_social_state_fingerprint"),
            }
        # Publish the committed beat identity and the advancement decision on
        # the per-turn governance surface so continuity is observable turn by
        # turn, alongside authority, routing, and validator truth.
        if narrative_commit.beat_progression is not None:
            bp = narrative_commit.beat_progression
            gov["beat_progression"] = {
                "beat_id": bp.beat_id,
                "beat_slot": bp.beat_slot,
                "advanced": bp.advanced,
                "advancement_reason": bp.advancement_reason,
                "continuity_carry_forward_reason": bp.continuity_carry_forward_reason,
                "prior_beat_id": bp.prior_beat_id,
                "pressure_state": bp.pressure_state,
            }
        gov["dramatic_context_summary"] = dramatic_context_summary
        if isinstance(graph_state.get("scene_energy_target"), dict):
            gov["scene_energy_target"] = graph_state.get("scene_energy_target")
        if isinstance(graph_state.get("scene_energy_transition"), dict):
            gov["scene_energy_transition"] = graph_state.get("scene_energy_transition")
        if isinstance(graph_state.get("scene_energy_validation"), dict):
            gov["scene_energy_validation"] = graph_state.get("scene_energy_validation")
        if isinstance(graph_state.get("pacing_rhythm_state"), dict):
            gov["pacing_rhythm_state"] = graph_state.get("pacing_rhythm_state")
        if isinstance(graph_state.get("pacing_rhythm_target"), dict):
            gov["pacing_rhythm_target"] = graph_state.get("pacing_rhythm_target")
        if isinstance(graph_state.get("pacing_rhythm_validation"), dict):
            gov["pacing_rhythm_validation"] = graph_state.get("pacing_rhythm_validation")
        if isinstance(graph_state.get("temporal_control_state"), dict):
            gov["temporal_control_state"] = graph_state.get("temporal_control_state")
        if isinstance(graph_state.get("temporal_control_target"), dict):
            gov["temporal_control_target"] = graph_state.get("temporal_control_target")
        if isinstance(graph_state.get("temporal_control_validation"), dict):
            gov["temporal_control_validation"] = graph_state.get("temporal_control_validation")
        if isinstance(graph_state.get("sensory_context_state"), dict):
            gov["sensory_context_state"] = graph_state.get("sensory_context_state")
        if isinstance(graph_state.get("sensory_context_target"), dict):
            gov["sensory_context_target"] = graph_state.get("sensory_context_target")
        if isinstance(graph_state.get("sensory_context_validation"), dict):
            gov["sensory_context_validation"] = graph_state.get("sensory_context_validation")
        if isinstance(graph_state.get("genre_awareness_state"), dict):
            gov["genre_awareness_state"] = graph_state.get("genre_awareness_state")
        if isinstance(graph_state.get("genre_awareness_target"), dict):
            gov["genre_awareness_target"] = graph_state.get("genre_awareness_target")
        if isinstance(graph_state.get("genre_awareness_validation"), dict):
            gov["genre_awareness_validation"] = graph_state.get("genre_awareness_validation")
        if isinstance(graph_state.get("tonal_consistency_target"), dict):
            gov["tonal_consistency_target"] = graph_state.get("tonal_consistency_target")
        if isinstance(graph_state.get("tonal_consistency_validation"), dict):
            gov["tonal_consistency_validation"] = graph_state.get("tonal_consistency_validation")
        if isinstance(graph_state.get("narrative_momentum_state"), dict):
            gov["narrative_momentum_state"] = graph_state.get("narrative_momentum_state")
        if isinstance(graph_state.get("narrative_momentum_target"), dict):
            gov["narrative_momentum_target"] = graph_state.get("narrative_momentum_target")
        if isinstance(graph_state.get("narrative_momentum_validation"), dict):
            gov["narrative_momentum_validation"] = graph_state.get(
                "narrative_momentum_validation"
            )
        if isinstance(graph_state.get("symbolic_object_resonance_state"), dict):
            gov["symbolic_object_resonance_state"] = graph_state.get(
                "symbolic_object_resonance_state"
            )
        if isinstance(graph_state.get("symbolic_object_resonance_target"), dict):
            gov["symbolic_object_resonance_target"] = graph_state.get(
                "symbolic_object_resonance_target"
            )
        if isinstance(graph_state.get("symbolic_object_resonance_validation"), dict):
            gov["symbolic_object_resonance_validation"] = graph_state.get(
                "symbolic_object_resonance_validation"
            )
        if isinstance(graph_state.get("social_pressure_state"), dict):
            gov["social_pressure_state"] = graph_state.get("social_pressure_state")
        if isinstance(graph_state.get("social_pressure_target"), dict):
            gov["social_pressure_target"] = graph_state.get("social_pressure_target")
        if isinstance(graph_state.get("social_pressure_validation"), dict):
            gov["social_pressure_validation"] = graph_state.get("social_pressure_validation")
        if isinstance(graph_state.get("expectation_variation_state"), dict):
            gov["expectation_variation_state"] = graph_state.get("expectation_variation_state")
        if isinstance(graph_state.get("expectation_variation_target"), dict):
            gov["expectation_variation_target"] = graph_state.get("expectation_variation_target")
        if isinstance(graph_state.get("expectation_variation_validation"), dict):
            gov["expectation_variation_validation"] = graph_state.get("expectation_variation_validation")
        if isinstance(session.environment_state, dict) and session.environment_state:
            gov["environment_state"] = session.environment_state
        # Story Runtime Experience packaging: re-pack the visible bundle
        # according to the governed experience policy. The policy is a real
        # first-class runtime value pulled from the resolved config, so
        # recap / dramatic_turn / live modes differ in packaging truth, not
        # only in prompt wording.
        raw_bundle = graph_state.get("visible_output_bundle")
        experience_policy = self._story_runtime_experience_policy()
        packaged_bundle = self._apply_experience_packaging(raw_bundle, experience_policy)
        packaged_bundle = _finalize_visible_bundle_opening_gm_narration(
            session=session,
            graph_state=graph_state,
            packaged_bundle=packaged_bundle,
            commit_turn_number=commit_turn_number,
        )
        visible_bundle_for_summary = (
            packaged_bundle if isinstance(packaged_bundle, dict) else raw_bundle if isinstance(raw_bundle, dict) else {}
        )
        actor_turn_summary = _build_actor_turn_summary(
            graph_state=graph_state,
            visible_output_bundle=visible_bundle_for_summary,
            dramatic_context_summary=dramatic_context_summary,
        )
        selected_responder_set = (
            graph_state.get("selected_responder_set")
            if isinstance(graph_state.get("selected_responder_set"), list)
            else []
        )
        if selected_responder_set:
            gov["selected_responder_set"] = selected_responder_set
            gov["selected_responder_ids"] = [
                str(row.get("actor_id") or row.get("responder_id") or "").strip()
                for row in selected_responder_set
                if isinstance(row, dict)
                and str(row.get("actor_id") or row.get("responder_id") or "").strip()
            ]
        if vitality_telemetry_v1:
            gov["vitality_telemetry_v1"] = vitality_telemetry_v1
            gov["realized_actor_ids"] = list(vitality_telemetry_v1.get("realized_actor_ids") or [])
            gov["rendered_actor_ids"] = list(vitality_telemetry_v1.get("rendered_actor_ids") or [])
            passivity_diagnosis = (
                actor_survival_telemetry.get("passivity_diagnosis_v1")
                if isinstance(actor_survival_telemetry.get("passivity_diagnosis_v1"), dict)
                else {}
            )
            operator_hints = (
                actor_survival_telemetry.get("operator_diagnostic_hints")
                if isinstance(actor_survival_telemetry.get("operator_diagnostic_hints"), dict)
                else {}
            )
            canonical_diagnosis = passivity_diagnosis if passivity_diagnosis else operator_hints
            if passivity_diagnosis:
                gov["passivity_diagnosis_v1"] = passivity_diagnosis
            gov["why_turn_felt_passive"] = list(canonical_diagnosis.get("why_turn_felt_passive") or [])
            gov["primary_passivity_factors"] = list(canonical_diagnosis.get("primary_passivity_factors") or [])
        quality_class, degradation_signals, degradation_summary = _canonical_quality_fields_from_surfaces(
            runtime_governance_surface=gov,
            authority_summary={
                "validation_status": val.get("status"),
                "commit_applied": bool((graph_state.get("committed_result") or {}).get("commit_applied")),
            },
        )
        gov["quality_class"] = quality_class
        gov["degradation_signals"] = degradation_signals
        gov["degradation_summary"] = degradation_summary
        turn_aspect_ledger = (
            normalize_runtime_aspect_ledger(graph_state.get("turn_aspect_ledger"))
            if isinstance(graph_state.get("turn_aspect_ledger"), dict)
            else None
        )
        turn_aspect_ledger = ensure_runtime_aspect_ledger(
            turn_aspect_ledger,
            session_id=session.session_id,
            module_id=session.module_id,
            turn_number=commit_turn_number,
            turn_kind=turn_kind or "player",
            raw_player_input=player_input,
            input_kind=interpreted_input.get("player_input_kind") or interpreted_input.get("kind"),
            trace_id=trace_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        turn_aspect_ledger = _stamp_turn_aspect_ledger_identity(
            turn_aspect_ledger,
            session=session,
            commit_turn_number=commit_turn_number,
            turn_kind=turn_kind or "player",
        )
        canonical_turn_id = _canonical_turn_id(session.session_id, commit_turn_number)
        runtime_profile_id = _runtime_profile_id_from_projection(
            session.runtime_projection if isinstance(session.runtime_projection, dict) else None
        )
        narrator_path_opening = (
            str(turn_kind or "").strip().lower() == "opening"
            and str(graph_state.get("director_path_mode") or "").strip() == "narrator_path"
        )
        if narrator_path_opening:
            branching_forecast = {
                "schema_version": "branching_forecast.v1",
                "status": "not_applicable",
                "forecast_only": True,
                "authoritative": False,
                "inactive_branches_authoritative": False,
                "mutates_canonical_state": False,
                "option_count": 0,
                "reason": "narrator_path_opening_no_player_branch",
            }
        else:
            branching_forecast = build_branching_forecast(
                story_session_id=session.session_id,
                module_id=session.module_id,
                runtime_profile_id=runtime_profile_id,
                canonical_turn_id=canonical_turn_id,
                turn_number=commit_turn_number,
                turn_kind=turn_kind or "player",
                narrative_commit=narrative_commit_payload,
                narrative_threads=session.narrative_threads.model_dump(mode="json")
                if hasattr(session.narrative_threads, "model_dump")
                else session.narrative_threads,
                thread_metrics=turn_thread_metrics,
                selected_responder_set=selected_responder_set,
                actor_turn_summary=actor_turn_summary,
'''
