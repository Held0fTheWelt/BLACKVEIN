"""Committed-turn finalization source chunk 003.

Contributes ordered source lines for the legacy manager method that finalizes committed turns. This chunk is intentionally small and ordered by the legacy manifest.
"""
SOURCE = r'''\
                )
                projection_aspect_recorded = True
                graph_state["turn_aspect_ledger"] = event["turn_aspect_ledger"]
                scene_turn_envelope = _build_live_scene_turn_envelope(
                    session=session,
                    graph_state=graph_state,
                    scene_blocks=live_scene_blocks,
                    turn_number=commit_turn_number,
                )
                graph_state.setdefault("phase_costs", {})["live_scene_projection"] = build_deterministic_phase_cost(
                    phase="live_scene_projection",
                    provider="world_engine",
                    model="live_runtime_graph_projection",
                    scene_block_count=len(live_scene_blocks),
                    visible_actor_response_present=bool(
                        scene_turn_envelope.get("diagnostics", {})
                        .get("npc_agency", {})
                        .get("visible_actor_response_present")
                    ),
                )
            else:
                ldss_span = None
                try:
                    from app.observability.langfuse_adapter import LangfuseAdapter
                    adapter = LangfuseAdapter.get_instance()
                    if adapter and adapter.is_enabled():
                        logger.info(f"[MANAGER] Creating LDSS fallback span for session {session.session_id}, turn {commit_turn_number}")
                        ldss_span = adapter.create_child_span(
                            name="story.phase.ldss_fallback",
                            input={
                                "session_id": session.session_id,
                                "turn_number": commit_turn_number,
                                "player_input_length": len(player_input) if player_input else 0,
                                "fallback_reason": "live_scene_blocks_missing",
                            },
                            metadata={
                                "phase": "ldss_fallback",
                                "turn_number": commit_turn_number,
                                "session_id": session.session_id,
                            }
                        )
                except Exception as e:
                    logger.error(f"[MANAGER] Exception creating LDSS fallback span: {e}", exc_info=True)

                try:
                    scene_turn_envelope = _build_ldss_scene_envelope(
                        session=session,
                        graph_state=graph_state,
                        player_input=player_input,
                        turn_number=commit_turn_number,
                    )
                    if scene_turn_envelope and ldss_span:
                        ldss_phase_cost = {}
                        if isinstance(scene_turn_envelope, dict):
                            diagnostics = scene_turn_envelope.get("diagnostics")
                            if isinstance(diagnostics, dict) and isinstance(diagnostics.get("phase_cost"), dict):
                                ldss_phase_cost = diagnostics["phase_cost"]
                        if not ldss_phase_cost:
                            raw_costs = graph_state.get("phase_costs")
                            if isinstance(raw_costs, dict) and isinstance(raw_costs.get("ldss"), dict):
                                ldss_phase_cost = raw_costs["ldss"]
                        ldss_span.update(
                            output={
                                "block_count": len(scene_turn_envelope.get("visible_scene_output", {}).get("blocks", [])) if isinstance(scene_turn_envelope.get("visible_scene_output"), dict) else 0,
                                "decision_count": scene_turn_envelope.get("decision_count", 0) if isinstance(scene_turn_envelope, dict) else 0,
                                "status": "approved"
                            },
                            metadata={
                                **ldss_phase_cost,
                                "phase_cost": dict(ldss_phase_cost),
                            }
                        )
                finally:
                    if ldss_span:
                        logger.info(f"[MANAGER] Ending LDSS fallback span")
                        ldss_span.end()

            if scene_turn_envelope:
                # Phase 2 Stage B/C — Dual Mode Block Stream (ADR-0058).
                # Augment envelope with parallel block_stream_events when the
                # feature flag is on. Real capability outputs from graph_state
                # are extracted and passed so NPC motivation scores use actual
                # runtime signals rather than defaults where available.
                # Bundle path and all existing keys are preserved unchanged.
                try:
                    from ai_stack.story_runtime.block_stream_dual_mode import (
                        augment_envelope_with_block_stream,
                        is_dual_mode_enabled,
                        is_primary_enabled,
                    )
                    from ai_stack.story_runtime.stream_readiness import (
                        compute_primary_selection,
                        compute_stream_readiness,
                        extract_capability_outputs_from_graph_state,
                        extract_module_policies_for_director,
                    )
                    if is_dual_mode_enabled():
                        cap_outputs = extract_capability_outputs_from_graph_state(graph_state)
                        # Stage F: pull Director policies from graph_state / module config.
                        module_policy_dict = (
                            graph_state.get("module_runtime_policy")
                            if isinstance(graph_state.get("module_runtime_policy"), dict)
                            else None
                        )
                        director_policies = extract_module_policies_for_director(
                            graph_state, module_policy_dict
                        )
                        off_stage_updates_policy = (
                            module_policy_dict.get("runtime_governance_policy", {}).get("off_stage_updates")
                            if isinstance(module_policy_dict, dict)
                            and isinstance(module_policy_dict.get("runtime_governance_policy"), dict)
                            else None
                        )
                        scene_turn_envelope = augment_envelope_with_block_stream(
                            scene_turn_envelope,
                            npc_ids=list(scene_turn_envelope.get("npc_actor_ids") or []),
                            scene_energy_output=cap_outputs["scene_energy_output"],
                            social_pressure_output=cap_outputs["social_pressure_output"],
                            relationship_state_output=cap_outputs["relationship_state_output"],
                            narrative_momentum_output=cap_outputs["narrative_momentum_output"],
                            actor_pressure_profiles=director_policies["actor_pressure_profiles"],
                            npc_motivation_score_policy=director_policies["npc_motivation_score_policy"],
                            pacing_rhythm_policy=director_policies["pacing_rhythm_policy"],
                            off_stage_updates_policy=off_stage_updates_policy,
                        )
                        # Stage C: readiness + primary selection — read-only, additive.
                        # Bundle path and all existing keys are never mutated.
                        readiness = compute_stream_readiness(
                            scene_turn_envelope,
                            graph_state=graph_state,
                            ws_session_loop_supported=False,
                            frontend_event_adapter_deployed=True,
                        )
                        primary_selection = compute_primary_selection(readiness)
                        primary_selection["primary_flag_enabled"] = is_primary_enabled()
                        existing_diag = scene_turn_envelope.get("diagnostics") or {}
                        scene_turn_envelope = {
                            **scene_turn_envelope,
                            "diagnostics": {
                                **existing_diag,
                                "phase2_event_stream_readiness": readiness,
                                "phase2_primary_selection": primary_selection,
                            },
                        }
                except Exception:
                    pass  # Dual-mode failure must never break the bundle path.

                event["scene_turn_envelope"] = scene_turn_envelope
                visible_scene_output = (
                    scene_turn_envelope.get("visible_scene_output")
                    if isinstance(scene_turn_envelope.get("visible_scene_output"), dict)
                    else {}
                )
                blocks = visible_scene_output.get("blocks")
                if isinstance(blocks, list) and blocks:
                    raw_scene_blocks = [dict(block) for block in blocks if isinstance(block, dict)]
                    projected_scene_blocks = _live_scene_blocks_from_visible_bundle(
                        {"scene_blocks": raw_scene_blocks},
                        turn_number=commit_turn_number,
                        structured_output=None,
                        runtime_projection=session.runtime_projection
                        if isinstance(session.runtime_projection, dict)
                        else None,
                        graph_state=graph_state,
                        session_output_language=session.session_output_language,
                        player_input=player_input,
                        story_runtime_experience=experience_policy.effective,
                    )
                    if not projected_scene_blocks:
                        projected_scene_blocks = raw_scene_blocks
                    visible_scene_output["blocks"] = [
                        dict(block) for block in projected_scene_blocks if isinstance(block, dict)
                    ]
                    event_bundle = (
                        event.get("visible_output_bundle")
                        if isinstance(event.get("visible_output_bundle"), dict)
                        else {}
                    )
                    event["visible_output_bundle"] = _ensure_gm_narration_from_narrator_scene_blocks(
                        {
                            **event_bundle,
                            "scene_blocks": [
                                dict(block)
                                for block in projected_scene_blocks
                                if isinstance(block, dict)
                            ],
                        }
                    )
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
                        scene_blocks=[
                            dict(block)
                            for block in projected_scene_blocks
                            if isinstance(block, dict)
                        ],
                    )
                    projection_aspect_recorded = True
                    graph_state["turn_aspect_ledger"] = event["turn_aspect_ledger"]

            if not projection_aspect_recorded:
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

            # MVP3: Orchestrate NarrativeRuntimeAgent streaming (after LDSS produces NPCAgencyPlan).
            # Opening turns already own the first visible narrative through the canonical opening
            # contract; streaming ambience here would prepend generic narrator cards before that
'''
