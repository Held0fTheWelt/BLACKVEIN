SOURCE = r'''\
            # authored transition.
            runtime_state = {
                "session_id": session.session_id,
                "current_scene_id": session.current_scene_id,
                "actor_positions": graph_state.get("actor_positions", {}),
                "narrative_threads": [t.model_dump() if hasattr(t, 'model_dump') else t
                                     for t in (session.narrative_threads.active if hasattr(session.narrative_threads, 'active') else [])],
            }
            dramatic_context = (
                graph_state.get("dramatic_context_summary", {})
                if isinstance(graph_state.get("dramatic_context_summary"), dict)
                else {}
            )
            if narrator_path_opening:
                narrator_packet = {
                    "contract": "narrator_packet.v1",
                    "mode": "narrator_path_already_projected",
                    "streaming_required": False,
                    "opening_scene_sequence": graph_state.get("opening_scene_sequence")
                    if isinstance(graph_state.get("opening_scene_sequence"), dict)
                    else None,
                }
            else:
                narrator_packet = build_narrator_packet(
                    opening_scene_sequence=graph_state.get("opening_scene_sequence")
                    if isinstance(graph_state.get("opening_scene_sequence"), dict)
                    else None,
                    hard_forbidden_rules=graph_state.get("hard_forbidden_rules")
                    if isinstance(graph_state.get("hard_forbidden_rules"), dict)
                    else None,
                    actor_lane_context=self._extract_actor_lane_context(session),
                    session_output_language=session.session_output_language,
                    story_runtime_experience=experience_policy.effective,
                )
            runtime_state["narrator_packet"] = narrator_packet
            narrative_threads_list = [t.model_dump() if hasattr(t, 'model_dump') else t
                                     for t in (session.narrative_threads.active if hasattr(session.narrative_threads, 'active') else [])]

            # MVP4: Create child span for Narrator phase
            narrator_span = None
            previous_active_span = None
            adapter = None
            try:
                from app.observability.langfuse_adapter import LangfuseAdapter
                adapter = LangfuseAdapter.get_instance()
                if not narrator_path_opening and adapter and adapter.is_enabled():
                    logger.info(f"[MANAGER] Creating Narrator phase span for session {session.session_id}, turn {commit_turn_number}")
                    narrator_span = adapter.create_child_span(
                        name="story.phase.narrator",
                        input={
                            "session_id": session.session_id,
                            "turn_number": commit_turn_number,
                            "npc_agency_plan": scene_turn_envelope.get("npc_agency_plan") if isinstance(scene_turn_envelope, dict) else None,
                            "narrator_packet": narrator_packet,
                        },
                        metadata={
                            "phase": "narrator",
                            "turn_number": commit_turn_number,
                            "session_id": session.session_id,
                        }
                    )
                    # Set as active span so NarrativeRuntimeAgent can create child spans
                    if narrator_span:
                        logger.info(f"[MANAGER] Narrator phase span created, setting as active context")
                        previous_active_span = adapter.get_active_span()
                        adapter.set_active_span(narrator_span)
                    else:
                        logger.warning(f"[MANAGER] Narrator phase span creation returned None")
            except Exception as e:
                logger.error(f"[MANAGER] Exception creating Narrator phase span: {e}", exc_info=True)

            try:
                if str(turn_kind or "").strip().lower() == "opening":
                    streaming_started = False
                else:
                    streaming_started = _orchestrate_narrative_agent(
                        manager=self,
                        session_id=session.session_id,
                        ldss_output=scene_turn_envelope,
                        runtime_state=runtime_state,
                        dramatic_signature=dramatic_context,
                        narrative_threads=narrative_threads_list,
                        turn_number=commit_turn_number,
                        trace_id=trace_id,
                        narrator_packet=narrator_packet,
                    )

                if streaming_started:
                    narrator_phase_cost = build_deterministic_phase_cost(
                        phase="narrator",
                        provider="world_engine",
                        model="narrative_runtime_agent_scheduled",
                        streaming_started=True,
                    )
                    graph_state.setdefault("phase_costs", {})["narrator"] = narrator_phase_cost

                if streaming_started and narrator_span:
                    narrator_span.update(
                        output={
                            "status": "streaming_started"
                        },
                        metadata={
                            **narrator_phase_cost,
                            "phase_cost": dict(narrator_phase_cost),
                        },
                    )
            finally:
                if narrator_span:
                    logger.info(f"[MANAGER] Ending Narrator phase span")
                    narrator_span.end()
                    logger.info(f"[MANAGER] Narrator phase span ended")
                if adapter is not None and narrator_span is not None:
                    adapter.set_active_span(previous_active_span)

            if streaming_started:
                event["narrative_agent_started"] = True
                event["narrator_streaming"] = {
                    "status": "streaming",
                    "session_id": session.session_id,
                }

        # MVP4: Build DiagnosticsEnvelope from committed state only.
        # Never exposes raw AI proposals as committed truth.
        if session.module_id == GOD_OF_CARNAGE_MODULE_ID:
            try:
                # Phase B: Collect degradation events
                degradation_events = []
                signals = graph_state.get("degradation_signals") or []
                for signal in signals:
                    severity = "critical" if signal in ("execution_error", "graph_error") \
                               else "moderate" if "fallback" in signal \
                               else "minor"
                    degradation_events.append(DegradationEvent(
                        marker=signal.upper(),
                        severity=severity,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        recovery_successful=graph_state.get("committed_result", {}).get("commit_applied", False),
                        context_snapshot={"turn_number": commit_turn_number},
                    ))

                _ensure_model_generation_phase_cost(graph_state)
                cost_summary = aggregate_phase_costs(graph_state.get("phase_costs", {}))

                diag_envelope = build_diagnostics_envelope(
                    session_id=session.session_id,
                    turn_number=commit_turn_number,
                    trace_id=trace_id or "",
                    player_input=player_input,
                    runtime_projection=session.runtime_projection,
                    graph_state=graph_state,
                    scene_turn_envelope=scene_turn_envelope,
                    langfuse_trace_id=get_langfuse_trace_id() or "",
                    langfuse_enabled=self._get_tracing_config(session.session_id),
                    degradation_events=degradation_events,
                )
                # Update cost_summary in the envelope
                diag_envelope.cost_summary = cost_summary
                event["diagnostics_envelope"] = diag_envelope.to_dict()
            except Exception as exc:
                log_story_runtime_failure(
                    trace_id=trace_id or "",
                    story_session_id=session.session_id,
                    operation="diagnostics_envelope",
                    message=str(exc),
                    failure_class="diagnostics_construction_error",
                )
                raise

        # Langfuse path summary and evidence scores must run after live projection
        # populates ``scene_blocks`` (GoC); otherwise ``visible_output_present`` is 0.
        if event.get("turn_status") is None:
            tk_final = str(turn_kind or "").strip().lower()
            if tk_final == "opening":
                event["turn_status"] = "opening_committed"
            else:
                event["turn_status"] = "committed" if outcome == "ok" else "committed_degraded"
        event.setdefault("http_status", 200)
        if session.module_id == GOD_OF_CARNAGE_MODULE_ID:
            human_att = _build_human_input_attribution_record(
                session=session,
                graph_state=graph_state,
                interpreted_input=interpreted_input,
                selected_responder_set=selected_responder_set,
                commit_turn_number=commit_turn_number,
                player_input=player_input,
            )
            graph_state["human_input_attribution"] = human_att
            event["human_input_attribution"] = human_att
        _reconcile_governance_passivity_with_final_projection(event)
        _attach_no_dead_end_recovery_to_event(
            session=session,
            graph_state=graph_state,
            event=event,
            player_input=player_input,
            turn_number=commit_turn_number,
            turn_kind=turn_kind or "player",
            turn_outcome=outcome,
            recoverable_outcome=False,
        )
        memory_source_turn = {
            "canonical_turn_id": event.get("canonical_turn_id"),
            "module_id": session.module_id,
            "runtime_profile_id": _runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
            "turn_number": commit_turn_number,
            "turn_kind": turn_kind or "player",
            "turn_outcome": outcome,
            "narrative_commit": narrative_commit_payload,
            "committed_turn_authority": committed_turn_authority,
            "dramatic_context_summary": dramatic_context_summary,
            "actor_turn_summary": actor_turn_summary,
            "no_dead_end_recovery": event.get("no_dead_end_recovery"),
            "turn_aspect_ledger": event.get("turn_aspect_ledger"),
            "visible_output_bundle": event.get("visible_output_bundle"),
            "committed_state_after": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
                "environment_state": session.environment_state
                if isinstance(session.environment_state, dict)
                else {},
            },
        }
        _record_hierarchical_memory_aspect(
            session=session,
            graph_state=graph_state,
            event=event,
            committed_turn=memory_source_turn,
            allow_write=True,
        )
        turn_lc.advance("projected")

        committed_record = {
            "canonical_turn_id": event.get("canonical_turn_id"),
            "turn_number": commit_turn_number,
            "turn_kind": turn_kind or "player",
            "trace_id": trace_id or "",
            "turn_outcome": outcome,
            "narrative_commit": narrative_commit_payload,
            "committed_turn_authority": committed_turn_authority,
'''
