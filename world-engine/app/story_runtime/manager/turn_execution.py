"""Turn execution orchestration.

Coordinates the core manager turn execution flow from input through runtime graph, commit, persistence, and output packaging.
"""
from __future__ import annotations

from ._deps import *

class _TurnExecutionMixin:
    def _execute_turn_locked(self, *, session_id: str, player_input: str, trace_id: str | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        self._assert_live_player_governance()
        session.turn_counter += 1
        session.updated_at = datetime.now(timezone.utc)
        commit_turn_number = session.turn_counter
        prior_scene_id = session.current_scene_id
        history_tail = session.history[-(NARRATIVE_COMMIT_HISTORY_TAIL - 1) :]
        graph_threads, graph_summary = build_graph_thread_export(session.narrative_threads)
        host_experience_template = (
            goc_host_experience_template(session.runtime_projection)
            if session.module_id == GOD_OF_CARNAGE_MODULE_ID
            else None
        )
        try:
            prior_ci = goc_prior_continuity_for_graph(session.module_id, session.prior_continuity_impacts)
            # Feed the prior committed beat back into the graph so the director
            # can key pacing and responder decisions off a stable continuity
            # identity rather than the loose prior_continuity_impacts list.
            prior_beat = _prior_beat_from_session(session)
            prior_signature = _beat_to_dramatic_signature(prior_beat)
            prior_social_state_record = _prior_social_state_record_from_session(session)
            prior_planner_truth = _prior_planner_truth_from_session(session)
            prior_narrative_thread_state = _prior_narrative_thread_state_from_session(
                session,
                graph_threads=graph_threads,
                graph_summary=graph_summary,
            )
            prior_callback_web_state = self._prior_callback_web_state_for_graph(session)
            prior_consequence_cascade_state = self._prior_consequence_cascade_state_for_graph(session)
            prior_temporal_control_state = _prior_temporal_control_state_from_session(session)
            prior_pacing_rhythm_state = _prior_pacing_rhythm_state_from_session(session)
            prior_social_pressure_state = _prior_social_pressure_state_from_session(session)
            prior_expectation_variation_state = _prior_expectation_variation_state_from_session(session)
            prior_narrative_momentum_state = _prior_narrative_momentum_state_from_session(session)
            prior_symbolic_object_resonance_state = _prior_symbolic_object_resonance_state_from_session(session)
            prior_relationship_state_record = _prior_relationship_state_record_from_session(session)
            phase1_canonical_context = _phase1_canonical_context_for_session(session)
            prior_director_gathering_state = _prior_director_gathering_state_from_session(session)
            _, prior_memory_policy = _load_module_memory_policy(
                module_id=session.module_id,
                runtime_profile_id=_runtime_profile_id_from_projection(
                    session.runtime_projection if isinstance(session.runtime_projection, dict) else None
                ),
            )
            hierarchical_memory_context = project_hierarchical_memory_context(
                snapshot=session.hierarchical_memory
                if isinstance(session.hierarchical_memory, dict)
                else None,
                memory_policy=prior_memory_policy,
            )
            graph_state = self.turn_graph.run(
                session_id=session.session_id,
                module_id=session.module_id,
                current_scene_id=session.current_scene_id,
                player_input=player_input,
                trace_id=trace_id,
                host_versions={"world_engine_app_version": APP_VERSION},
                active_narrative_threads=graph_threads or None,
                thread_pressure_summary=graph_summary,
                host_experience_template=host_experience_template,
                prior_continuity_impacts=prior_ci if prior_ci else None,
                prior_dramatic_signature=prior_signature,
                prior_social_state_record=prior_social_state_record,
                prior_narrative_thread_state=prior_narrative_thread_state,
                prior_callback_web_state=prior_callback_web_state,
                prior_consequence_cascade_state=prior_consequence_cascade_state,
                prior_temporal_control_state=prior_temporal_control_state,
                prior_expectation_variation_state=prior_expectation_variation_state,
                prior_narrative_momentum_state=prior_narrative_momentum_state,
                prior_symbolic_object_resonance_state=prior_symbolic_object_resonance_state,
                prior_pacing_rhythm_state=prior_pacing_rhythm_state,
                prior_social_pressure_state=prior_social_pressure_state,
                prior_relationship_state_record=prior_relationship_state_record,
                prior_planner_truth=prior_planner_truth,
                hierarchical_memory_context=hierarchical_memory_context,
                turn_number=commit_turn_number,
                turn_initiator_type="player",
                live_player_truth_surface=True,
                actor_lane_context=self._extract_actor_lane_context(session),
                session_input_language=session.session_input_language,
                session_output_language=session.session_output_language,
                story_runtime_experience=self._story_runtime_experience_policy().effective,
                validation_execution_mode=self._validation_execution_mode(),
                environment_state=session.environment_state
                if isinstance(session.environment_state, dict)
                else None,
                canonical_step_id=phase1_canonical_context.get("canonical_step_id"),
                canonical_path=phase1_canonical_context.get("canonical_path"),
                current_step_scene_id=phase1_canonical_context.get("current_step_scene_id"),
                current_step_named_characters=phase1_canonical_context.get("current_step_named_characters"),
                prior_director_gathering_state=prior_director_gathering_state,
                w5_latest_snapshot=session.w5_latest_snapshot
                if isinstance(session.w5_latest_snapshot, dict)
                else None,
                )
        except Exception as exc:
            if not _is_recoverable_graph_execution_exception(exc):
                session.turn_counter -= 1
                log_story_runtime_failure(
                    trace_id=trace_id,
                    story_session_id=session_id,
                    operation="execute_turn",
                    message=str(exc),
                    failure_class="turn_execution_unrecoverable_exception",
                )
                raise
            log_story_runtime_failure(
                trace_id=trace_id,
                story_session_id=session_id,
                operation="execute_turn",
                message=str(exc),
                failure_class="graph_execution_exception",
            )
            gmsg = _recoverable_turn_message(session=session, reason="graph_execution_exception")
            turn_aspect_ledger = _recoverable_runtime_aspect_ledger(
                session_id=session.session_id,
                module_id=session.module_id,
                turn_number=commit_turn_number,
                turn_kind="player_graph_exception_playable",
                player_input=player_input,
                trace_id=trace_id,
                reason="graph_execution_exception",
                validation_status="rejected",
                visible_output_present=True,
            )
            val_graph_exc: dict[str, Any] = {
                "status": "rejected",
                "reason": "graph_execution_exception",
                "recoverable_rejection": True,
                "hard_boundary_failure": False,
                "parser_or_model_failure": True,
            }
            event = _recoverable_playable_turn_envelope(
                session=session,
                commit_turn_number=commit_turn_number,
                player_input=player_input,
                trace_id=trace_id,
                turn_kind="player_graph_exception_playable",
                interpreted_input={},
                narrative_commit={
                    "situation_status": "continue",
                    "allowed": False,
                    "commit_reason_code": "graph_execution_exception",
                    "committed_scene_id": prior_scene_id,
                    "proposed_scene_id": prior_scene_id,
                    "selected_candidate_source": "runtime_exception_gate",
                    "is_terminal": False,
                },
                validation_outcome=val_graph_exc,
                message=gmsg,
                turn_aspect_ledger=turn_aspect_ledger,
                reason="graph_execution_exception",
                diagnostics_extras={
                    "failure_class": "graph_execution_exception",
                    "exception_type": type(exc).__name__,
                },
            )
            graph_state_recoverable = {
                "session_id": session.session_id,
                "module_id": session.module_id,
                "turn_number": commit_turn_number,
                "turn_kind": "player_graph_exception_playable",
                "player_input": player_input,
                "trace_id": trace_id,
                "interpreted_input": {},
                "generation": {
                    "success": False,
                    "error": str(exc),
                    "metadata": {"error": str(exc), "exception_type": type(exc).__name__},
                },
                "graph_errors": ["graph_execution_exception"],
                "validation_outcome": val_graph_exc,
                "visible_output_bundle": event["visible_output_bundle"],
                "turn_aspect_ledger": event.get("turn_aspect_ledger"),
            }
            return self._persist_player_visible_turn_event(
                session=session,
                graph_state=graph_state_recoverable,
                event=event,
                trace_id=trace_id,
                commit_turn_number=commit_turn_number,
                player_input=player_input,
                turn_outcome="recoverable_graph_exception",
            )

        val = graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
        if val.get("status") != "approved":
            if is_hard_boundary_failure(val):
                session.turn_counter -= 1
                raise RuntimeError(f"Hard narrative boundary: {val.get('reason') or 'rejected'}")
            return self._build_recoverable_rejection_turn(
                session=session,
                graph_state=graph_state,
                trace_id=trace_id,
                attempted_turn_number=commit_turn_number,
                player_input=player_input,
                prior_scene_id=prior_scene_id,
                validation_outcome=val,
            )
        return self._finalize_committed_turn(
            session=session,
            graph_state=graph_state,
            trace_id=trace_id,
            commit_turn_number=commit_turn_number,
            player_input=player_input,
            turn_kind="player",
            prior_scene_id=prior_scene_id,
            history_tail=history_tail,
            graph_threads=graph_threads,
            graph_summary=graph_summary,
            host_experience_template=host_experience_template,
            prior_ci=prior_ci,
        )


__all__ = ["_TurnExecutionMixin"]
