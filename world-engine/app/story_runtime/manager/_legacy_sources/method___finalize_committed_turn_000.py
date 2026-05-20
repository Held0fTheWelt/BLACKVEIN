SOURCE = r'''\
    def _finalize_committed_turn(
        self,
        *,
        session: StorySession,
        graph_state: dict[str, Any],
        trace_id: str | None,
        commit_turn_number: int,
        player_input: str,
        turn_kind: str | None,
        prior_scene_id: str,
        history_tail: list,
        graph_threads: list[dict[str, Any]] | None,
        graph_summary: str | None,
        host_experience_template: dict[str, Any] | None,
        prior_ci: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        prior_narrative_threads_for_rollback = copy.deepcopy(session.narrative_threads)
        prior_thread_update_trace_for_rollback = copy.deepcopy(session.last_thread_update_trace)
        prior_continuity_impacts_for_rollback = copy.deepcopy(session.prior_continuity_impacts)
        goc_append_continuity_impacts(session.module_id, session.prior_continuity_impacts, graph_state)
        graph_diag = graph_state.get("graph_diagnostics", {}) if isinstance(graph_state.get("graph_diagnostics"), dict) else {}
        errors = graph_diag.get("errors", []) if isinstance(graph_diag.get("errors"), list) else []
        gen = graph_state.get("generation", {}) if isinstance(graph_state.get("generation"), dict) else {}
        interpreted_input = graph_state.get("interpreted_input", {})
        if not isinstance(interpreted_input, dict):
            interpreted_input = {}
        validation_outcome = (
            graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
        )
        turn_lc = TurnLifecycleChain()
        turn_lc.advance("received")
        turn_lc.advance("interpreted")
        prior_beat = _prior_beat_from_session(session)
        narrative_commit = resolve_narrative_commit(
            turn_number=commit_turn_number,
            prior_scene_id=prior_scene_id,
            player_input=player_input,
            interpreted_input=interpreted_input,
            generation=gen,
            runtime_projection=session.runtime_projection,
            graph_state=graph_state,
            prior_beat_progression=prior_beat,
        )
        model_ok = gen.get("success") is True
        turn_lc.advance("generated_or_resolved")
        turn_lc.advance("validated")
        session.current_scene_id = narrative_commit.committed_scene_id
        if isinstance(graph_state.get("environment_state"), dict):
            session.environment_state = dict(graph_state["environment_state"])
        session.narrative_threads, session.last_thread_update_trace = update_narrative_threads(
            prior=session.narrative_threads,
            latest_commit=narrative_commit,
            history_tail=history_tail,
            committed_scene_id=narrative_commit.committed_scene_id,
            turn_number=commit_turn_number,
        )
        turn_lc.advance("committed")
        outcome = "ok" if model_ok and not errors else "degraded"
        actor_survival_telemetry = (
            graph_state.get("actor_survival_telemetry")
            if isinstance(graph_state.get("actor_survival_telemetry"), dict)
            else {}
        )
        vitality_telemetry_v1 = (
            actor_survival_telemetry.get("vitality_telemetry_v1")
            if isinstance(actor_survival_telemetry.get("vitality_telemetry_v1"), dict)
            else None
        )
        passivity_diagnosis_v1 = (
            actor_survival_telemetry.get("passivity_diagnosis_v1")
            if isinstance(actor_survival_telemetry.get("passivity_diagnosis_v1"), dict)
            else None
        )

        # Build LLM invocation details from graph_state
        routing = graph_state.get("routing") if isinstance(graph_state.get("routing"), dict) else {}
        gen_meta = gen.get("metadata") if isinstance(gen.get("metadata"), dict) else {}
        self_correction = graph_state.get("self_correction") if isinstance(graph_state.get("self_correction"), dict) else {}
        llm_invocation_details = {
            "selected_provider": routing.get("selected_provider"),
            "selected_model": routing.get("selected_model"),
            "adapter_used": gen_meta.get("adapter"),
            "adapter_invocation_mode": gen_meta.get("adapter_invocation_mode"),
            "fallback_stage_reached": routing.get("fallback_stage_reached") or ("graph_fallback_executed" if "fallback_model" in (graph_state.get("nodes_executed") or []) else "primary_only"),
            "fallback_reason": routing.get("fallback_reason"),
            "retry_attempt_count": self_correction.get("attempt_count"),
            "parser_error": gen.get("parser_error"),
            "structured_output_present": gen.get("structured_output") is not None,
            "model_success": model_ok,
        }

        # Build validation details
        validation_details = {
            "status": validation_outcome.get("status"),
            "reason": validation_outcome.get("reason"),
            "dramatic_quality_gate": validation_outcome.get("dramatic_quality_gate"),
        }
        actor_lane_validation = validation_outcome.get("actor_lane_validation") if isinstance(validation_outcome.get("actor_lane_validation"), dict) else {}
        if actor_lane_validation:
            validation_details["actor_lane_validation_status"] = actor_lane_validation.get("status")
            validation_details["actor_lane_validation_reason"] = actor_lane_validation.get("reason")

        # Build commit details
        commit_details = {
            "committed": narrative_commit is not None,
            "degraded": outcome == "degraded",
            "degradation_reason": str(errors[0]) if errors else None,
        }

        # Build retrieval details if available
        retrieval_status = graph_state.get("retrieval") if isinstance(graph_state.get("retrieval"), dict) else {}
        retrieval_details = {
            "status": retrieval_status.get("status"),
            "hit_count": retrieval_status.get("hit_count"),
            "documents_used": retrieval_status.get("documents_used"),
            "retrieval_route": retrieval_status.get("retrieval_route"),
            "profile": retrieval_status.get("profile"),
            "domain": retrieval_status.get("domain"),
            "top_hit_score": retrieval_status.get("top_hit_score"),
            "corpus_fingerprint": retrieval_status.get("corpus_fingerprint"),
            "index_version": retrieval_status.get("index_version"),
        } if retrieval_status else None

        log_story_turn_event(
            trace_id=trace_id,
            story_session_id=session.session_id,
            module_id=session.module_id,
            turn_number=commit_turn_number,
            player_input=player_input,
            outcome=outcome,
            graph_error_count=len(errors),
            quality_class=str(graph_state.get("quality_class") or "") or None,
            degradation_signals=list(graph_state.get("degradation_signals") or []),
            vitality_telemetry=vitality_telemetry_v1,
            passivity_diagnosis=passivity_diagnosis_v1,
            llm_invocation_details=llm_invocation_details,
            validation_details=validation_details,
            commit_details=commit_details,
            retrieval_details=retrieval_details,
        )
        narrative_commit_payload = narrative_commit.model_dump(mode="json")
        beat_payload = (
            narrative_commit_payload.get("beat_progression")
            if isinstance(narrative_commit_payload.get("beat_progression"), dict)
            else {}
        )
        if isinstance(graph_state.get("turn_aspect_ledger"), dict) and beat_payload:
            ledger_for_beat_commit = normalize_runtime_aspect_ledger(graph_state.get("turn_aspect_ledger"))
            aspects_for_beat = ledger_for_beat_commit.get("turn_aspect_ledger")
            beat_record = aspects_for_beat.get(ASPECT_BEAT) if isinstance(aspects_for_beat, dict) else {}
            if isinstance(beat_record, dict):
                graph_state["turn_aspect_ledger"] = set_aspect_record(
                    ledger_for_beat_commit,
                    ASPECT_BEAT,
                    make_aspect_record(
                        applicable=True,
                        status=str(beat_record.get("status") or "partial"),
                        expected=beat_record.get("expected")
                        if isinstance(beat_record.get("expected"), dict)
                        else {},
                        selected=beat_record.get("selected")
                        if isinstance(beat_record.get("selected"), dict)
                        else {"selected_beat_id": beat_payload.get("beat_id")},
                        actual={
                            **(beat_record.get("actual") if isinstance(beat_record.get("actual"), dict) else {}),
                            "committed": True,
                            "committed_beat_id": beat_payload.get("beat_id"),
                            "beat_slot": beat_payload.get("beat_slot"),
                            "advanced": beat_payload.get("advanced"),
                            "advancement_reason": beat_payload.get("advancement_reason"),
                        },
                        reasons=beat_record.get("reasons") if isinstance(beat_record.get("reasons"), list) else [],
                        source="commit",
                        selected_beat=beat_payload.get("beat_id"),
                    ),
                )
        turn_thread_metrics = thread_continuity_metrics(session.narrative_threads)
        dramatic_context_summary = _build_committed_dramatic_context_summary(
            graph_state=graph_state,
            narrative_commit_payload=narrative_commit_payload,
            thread_metrics=turn_thread_metrics,
        )
        committed_turn_authority = _build_committed_turn_authority(
            narrative_commit_payload=narrative_commit_payload,
            graph_state=graph_state,
            committed_scene_id=session.current_scene_id,
            turn_number=commit_turn_number,
            dramatic_context_summary=dramatic_context_summary,
        )
        r_src = str(self._runtime_config_status.get("source") or "")
        governed_active = r_src in {"governed_runtime_config", "governed_runtime_config_with_injected_adapters"} and not bool(
            self._runtime_config_status.get("live_execution_blocked")
        )
        gov: dict[str, Any] = {
            "source": self._runtime_config_status.get("source"),
            "config_version": self._runtime_config_status.get("config_version"),
            "governed_runtime_active": governed_active,
            "legacy_default_registry_path": r_src == "default_registry",
            "live_execution_blocked": bool(self._runtime_config_status.get("live_execution_blocked")),
            # The authority version records which authority binding shaped this
            # committed turn. ``reload_runtime_config`` bumps the version; a
            # turn committed after reload shows the new value, making the live
            # binding auditable rather than inferred.
            "authority_version": self._authority_version,
            "authority_applied_at_iso": self._authority_applied_at_iso,
        }
        routing = graph_state.get("routing") if isinstance(graph_state.get("routing"), dict) else {}
        gov["primary_route_selection"] = {
            "selected_model_id": routing.get("selected_model"),
            "selected_provider_id": routing.get("selected_provider"),
            "route_reason_code": routing.get("route_reason_code"),
            "fallback_chain": routing.get("fallback_chain"),
            "route_id": routing.get("route_id"),
            "route_family": routing.get("route_family"),
            "route_family_expected": routing.get("route_family_expected"),
            "route_substitution_occurred": bool(routing.get("route_substitution_occurred")),
        }
        gov["fallback_stage_reached"] = routing.get("fallback_stage_reached") or (
            "graph_fallback_executed" if "fallback_model" in (graph_state.get("nodes_executed") or []) else "primary_only"
        )
        gen_meta = gen.get("metadata") if isinstance(gen.get("metadata"), dict) else {}
        gov["final_model_invocation"] = {
            "adapter": gen_meta.get("adapter"),
            "api_model": gen_meta.get("model"),
            "adapter_invocation_mode": gen_meta.get("adapter_invocation_mode"),
        }
        gov["route_selected_model"] = routing.get("selected_model")
        gov["route_selected_provider"] = routing.get("selected_provider")
        gov["route_reason_code"] = routing.get("route_reason_code")
        gov["adapter"] = gen_meta.get("adapter")
        gov["api_model"] = gen_meta.get("model")
        if graph_state.get("director_path_mode"):
            gov["director_path_mode"] = graph_state.get("director_path_mode")
            gov["director_narrator_path_plan"] = graph_state.get("director_narrator_path_plan")
            gov["narrator_path"] = graph_state.get("narrator_path")
        self_correction = graph_state.get("self_correction") if isinstance(graph_state.get("self_correction"), dict) else {}
        gov["self_correction_attempt_count"] = self_correction.get("attempt_count")
        val = validation_outcome
        gov["validation_reason"] = val.get("reason")
        gov["mock_output_flag"] = bool(str(gen.get("content") or "").strip().startswith("[mock]"))
'''
