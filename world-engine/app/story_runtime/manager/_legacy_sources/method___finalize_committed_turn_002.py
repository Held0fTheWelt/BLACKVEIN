SOURCE = r'''\
                graph_state=graph_state,
            )
        if isinstance(turn_aspect_ledger, dict):
            turn_aspect_ledger = dict(turn_aspect_ledger)
            turn_aspect_ledger["branching_forecast"] = branching_forecast
            turn_aspect_ledger = normalize_runtime_aspect_ledger(turn_aspect_ledger)
            graph_state["turn_aspect_ledger"] = turn_aspect_ledger
        graph_state["branching_forecast"] = branching_forecast
        gov["branching_forecast"] = {
            "status": branching_forecast.get("status"),
            "option_count": branching_forecast.get("option_count"),
            "forecast_only": branching_forecast.get("forecast_only"),
            "inactive_branches_authoritative": branching_forecast.get("inactive_branches_authoritative"),
            "mutates_canonical_state": branching_forecast.get("mutates_canonical_state"),
        }
        event: dict[str, Any] = {
            "turn_number": commit_turn_number,
            "canonical_turn_id": canonical_turn_id,
            "turn_kind": turn_kind or "player",
            "trace_id": trace_id or "",
            "raw_input": player_input,
            "turn_aspect_ledger": turn_aspect_ledger,
            "interpreted_input": interpreted_input,
            "narrative_commit": narrative_commit_payload,
            "retrieval": graph_state.get("retrieval", {}),
            "model_route": {**routing, "generation": gen},
            "graph": graph_diag,
            "visible_output_bundle": packaged_bundle if packaged_bundle is not None else raw_bundle,
            "story_runtime_experience": experience_policy.to_truth_surface(),
            "dramatic_context_summary": dramatic_context_summary,
            "diagnostics_refs": graph_state.get("diagnostics_refs"),
            "experiment_preview": graph_state.get("experiment_preview"),
            "validation_outcome": val,
            "committed_result": graph_state.get("committed_result"),
            "committed_turn_authority": committed_turn_authority,
            "environment_state": session.environment_state
            if isinstance(session.environment_state, dict)
            else {},
            "selected_scene_function": graph_state.get("selected_scene_function"),
            "director_path_mode": graph_state.get("director_path_mode"),
            "director_narrator_path_plan": graph_state.get("director_narrator_path_plan"),
            "narrator_path": graph_state.get("narrator_path"),
            "scene_energy_target": graph_state.get("scene_energy_target"),
            "scene_energy_transition": graph_state.get("scene_energy_transition"),
            "scene_energy_validation": graph_state.get("scene_energy_validation"),
            "temporal_control_state": graph_state.get("temporal_control_state"),
            "temporal_control_target": graph_state.get("temporal_control_target"),
            "temporal_control_validation": graph_state.get("temporal_control_validation"),
            "social_pressure_state": graph_state.get("social_pressure_state"),
            "social_pressure_target": graph_state.get("social_pressure_target"),
            "social_pressure_validation": graph_state.get("social_pressure_validation"),
            "tonal_consistency_target": graph_state.get("tonal_consistency_target"),
            "tonal_consistency_validation": graph_state.get("tonal_consistency_validation"),
            "expectation_variation_state": graph_state.get("expectation_variation_state"),
            "expectation_variation_target": graph_state.get("expectation_variation_target"),
            "expectation_variation_validation": graph_state.get("expectation_variation_validation"),
            "narrative_momentum_state": graph_state.get("narrative_momentum_state"),
            "narrative_momentum_target": graph_state.get("narrative_momentum_target"),
            "narrative_momentum_validation": graph_state.get("narrative_momentum_validation"),
            "dramatic_irony_record": graph_state.get("dramatic_irony_record"),
            "dramatic_irony_validation": graph_state.get("dramatic_irony_validation"),
            "selected_responder_set": selected_responder_set,
            "visibility_class_markers": graph_state.get("visibility_class_markers"),
            "failure_markers": graph_state.get("failure_markers"),
            "self_correction": self_correction,
            "branching_forecast": branching_forecast,
            "actor_survival_telemetry": actor_survival_telemetry,
            "actor_turn_summary": actor_turn_summary,
            "runtime_governance_surface": gov,
        }
        projection_aspect_recorded = False

        def _recover_if_projection_gate_blocks_commit() -> dict[str, Any] | None:
            failure = _runtime_aspect_commit_blocking_failure(
                event.get("turn_aspect_ledger")
                if isinstance(event.get("turn_aspect_ledger"), dict)
                else graph_state.get("turn_aspect_ledger")
                if isinstance(graph_state.get("turn_aspect_ledger"), dict)
                else None
            )
            if not failure:
                return None
            reason = str(failure.get("failure_reason") or "runtime_aspect_projection_failure")
            session.current_scene_id = prior_scene_id
            session.narrative_threads = copy.deepcopy(prior_narrative_threads_for_rollback)
            session.last_thread_update_trace = copy.deepcopy(prior_thread_update_trace_for_rollback)
            session.prior_continuity_impacts = copy.deepcopy(prior_continuity_impacts_for_rollback)
            if str(turn_kind or "").strip().lower() == "opening":
                raise RuntimeError(f"Opening projection contract failure: {reason}")

            message = _recoverable_turn_message(session=session, reason=reason)
            turn_aspect_ledger = _recoverable_runtime_aspect_ledger(
                session_id=session.session_id,
                module_id=session.module_id,
                turn_number=commit_turn_number,
                turn_kind="player_projection_rejected_recoverable",
                player_input=player_input,
                trace_id=trace_id,
                reason=reason,
                validation_status="rejected",
                existing_ledger=event.get("turn_aspect_ledger")
                if isinstance(event.get("turn_aspect_ledger"), dict)
                else graph_state.get("turn_aspect_ledger")
                if isinstance(graph_state.get("turn_aspect_ledger"), dict)
                else None,
                visible_output_present=True,
            )
            val_projection: dict[str, Any] = {
                "status": "rejected",
                "reason": reason,
                "validator_lane": "runtime_aspect_projection_gate_v1",
                "recoverable_rejection": True,
                "hard_boundary_failure": False,
                "runtime_aspect_failure": failure,
            }
            recoverable_event = _recoverable_playable_turn_envelope(
                session=session,
                commit_turn_number=commit_turn_number,
                player_input=player_input,
                trace_id=trace_id,
                turn_kind="player_projection_rejected_recoverable",
                interpreted_input=interpreted_input,
                narrative_commit={
                    "situation_status": "continue",
                    "allowed": False,
                    "commit_reason_code": "runtime_aspect_projection_gate",
                    "committed_scene_id": prior_scene_id,
                    "proposed_scene_id": prior_scene_id,
                    "selected_candidate_source": "runtime_aspect_projection_gate",
                    "is_terminal": False,
                },
                validation_outcome=val_projection,
                message=message,
                turn_aspect_ledger=turn_aspect_ledger,
                reason=reason,
                diagnostics_extras={
                    "failure_class": failure.get("failure_class"),
                    "runtime_aspect_failure": failure,
                },
            )
            graph_state["turn_aspect_ledger"] = recoverable_event.get("turn_aspect_ledger")
            graph_state["validation_outcome"] = val_projection
            graph_state["visible_output_bundle"] = recoverable_event["visible_output_bundle"]
            graph_state["committed_result"] = {
                "commit_applied": False,
                "committed_effects": [],
                "reason": reason,
                "runtime_aspect_failure": failure,
            }
            return self._persist_player_visible_turn_event(
                session=session,
                graph_state=graph_state,
                event=recoverable_event,
                trace_id=trace_id,
                commit_turn_number=commit_turn_number,
                player_input=player_input,
                turn_outcome="recoverable_projection_failure",
            )
        if session.module_id != GOD_OF_CARNAGE_MODULE_ID:
            generic_scene_blocks = _scene_blocks_from_visible_bundle(
                event.get("visible_output_bundle")
                if isinstance(event.get("visible_output_bundle"), dict)
                else None
            )
            if generic_scene_blocks:
                event["turn_aspect_ledger"] = _record_visible_projection_aspect(
                    ledger=event.get("turn_aspect_ledger")
                    if isinstance(event.get("turn_aspect_ledger"), dict)
                    else graph_state.get("turn_aspect_ledger")
                    if isinstance(graph_state.get("turn_aspect_ledger"), dict)
                    else None,
                    session_id=session.session_id,
                    module_id=session.module_id,
                    turn_number=commit_turn_number,
                    turn_kind=turn_kind or "player",
                    raw_player_input=player_input,
                    trace_id=trace_id,
                    scene_blocks=generic_scene_blocks,
                )
                projection_aspect_recorded = True
                graph_state["turn_aspect_ledger"] = event["turn_aspect_ledger"]
                blocked_projection_event = _recover_if_projection_gate_blocks_commit()
                if blocked_projection_event is not None:
                    return blocked_projection_event
        # Build SceneTurnEnvelope.v2 for God of Carnage solo sessions.
        # Live graph/model output is primary. LDSS is reserved as the final
        # deterministic fallback when the live path cannot produce scene blocks.
        scene_turn_envelope: dict[str, Any] | None = None
        if session.module_id == GOD_OF_CARNAGE_MODULE_ID:
            live_scene_blocks = []
            if gen.get("success") is True and not graph_state.get("force_ldss_scene_fallback"):
                gen_meta_for_blocks = gen.get("metadata") if isinstance(gen.get("metadata"), dict) else {}
                structured_for_projection = (
                    gen_meta_for_blocks.get("structured_output")
                    if isinstance(gen_meta_for_blocks.get("structured_output"), dict)
                    else None
                )
                if structured_for_projection is None and isinstance(gen.get("structured_output"), dict):
                    structured_for_projection = gen["structured_output"]
                live_scene_blocks = _live_scene_blocks_from_visible_bundle(
                    event.get("visible_output_bundle")
                    if isinstance(event.get("visible_output_bundle"), dict)
                    else {},
                    turn_number=commit_turn_number,
                    structured_output=structured_for_projection,
                    runtime_projection=session.runtime_projection
                    if isinstance(session.runtime_projection, dict)
                    else None,
                    graph_state=graph_state,
                    session_output_language=session.session_output_language,
                    player_input=player_input,
                    story_runtime_experience=experience_policy.effective,
                )
                live_scene_blocks = _maybe_split_goc_opening_into_two_movements(
                    live_scene_blocks,
                    commit_turn_number=commit_turn_number,
                )
            if live_scene_blocks:
                event_bundle = (
                    event.get("visible_output_bundle")
                    if isinstance(event.get("visible_output_bundle"), dict)
                    else {}
                )
                event["visible_output_bundle"] = {
                    **event_bundle,
                    "scene_blocks": [dict(block) for block in live_scene_blocks],
                }
                event["turn_aspect_ledger"] = _record_visible_projection_aspect(
                    ledger=event.get("turn_aspect_ledger")
                    if isinstance(event.get("turn_aspect_ledger"), dict)
                    else graph_state.get("turn_aspect_ledger")
                    if isinstance(graph_state.get("turn_aspect_ledger"), dict)
                    else None,
                    session_id=session.session_id,
                    module_id=session.module_id,
                    turn_number=commit_turn_number,
                    turn_kind=turn_kind or "player",
                    raw_player_input=player_input,
                    trace_id=trace_id,
                    scene_blocks=[dict(block) for block in live_scene_blocks if isinstance(block, dict)],
'''
