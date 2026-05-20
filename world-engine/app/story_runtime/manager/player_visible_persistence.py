from __future__ import annotations

from ._deps import *

class _PlayerVisiblePersistenceMixin:
    def _persist_player_visible_turn_event(
        self,
        *,
        session: StorySession,
        graph_state: dict[str, Any],
        event: dict[str, Any],
        trace_id: str | None,
        commit_turn_number: int,
        player_input: str,
        turn_outcome: str,
    ) -> dict[str, Any]:
        """Persist a player-visible non-approved outcome as a canonical turn."""
        event.setdefault("canonical_turn_id", _canonical_turn_id(session.session_id, commit_turn_number))
        event.setdefault("http_status", 200)
        event.setdefault("turn_status", "rejected_recoverable")
        event.setdefault("trace_id", trace_id or "")
        event.setdefault("raw_input", player_input)
        if isinstance(event.get("turn_aspect_ledger"), dict):
            event["turn_aspect_ledger"] = _stamp_turn_aspect_ledger_identity(
                event.get("turn_aspect_ledger"),
                session=session,
                commit_turn_number=commit_turn_number,
                turn_kind=str(event.get("turn_kind") or "player_rejected_recoverable"),
            )
        interpreted_input = (
            event.get("interpreted_input")
            if isinstance(event.get("interpreted_input"), dict)
            else graph_state.get("interpreted_input")
            if isinstance(graph_state.get("interpreted_input"), dict)
            else {}
        )
        selected_responder_set = (
            event.get("selected_responder_set")
            if isinstance(event.get("selected_responder_set"), list)
            else graph_state.get("selected_responder_set")
            if isinstance(graph_state.get("selected_responder_set"), list)
            else []
        )
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
        retrieval = (
            graph_state.get("retrieval")
            if isinstance(graph_state.get("retrieval"), dict)
            else {}
        )
        routing = (
            graph_state.get("routing")
            if isinstance(graph_state.get("routing"), dict)
            else {}
        )
        generation = (
            graph_state.get("generation")
            if isinstance(graph_state.get("generation"), dict)
            else {}
        )
        graph_diag = (
            graph_state.get("graph_diagnostics")
            if isinstance(graph_state.get("graph_diagnostics"), dict)
            else {}
        )
        if retrieval:
            event.setdefault("retrieval", retrieval)
        if routing or generation:
            event.setdefault("model_route", {**routing, "generation": generation})
        if graph_diag:
            event.setdefault("graph", graph_diag)
        if graph_state.get("selected_scene_function") is not None:
            event.setdefault("selected_scene_function", graph_state.get("selected_scene_function"))
        if isinstance(graph_state.get("scene_energy_target"), dict):
            event.setdefault("scene_energy_target", graph_state.get("scene_energy_target"))
        if isinstance(graph_state.get("scene_energy_transition"), dict):
            event.setdefault("scene_energy_transition", graph_state.get("scene_energy_transition"))
        if isinstance(graph_state.get("scene_energy_validation"), dict):
            event.setdefault("scene_energy_validation", graph_state.get("scene_energy_validation"))
        if isinstance(graph_state.get("pacing_rhythm_state"), dict):
            event.setdefault("pacing_rhythm_state", graph_state.get("pacing_rhythm_state"))
        if isinstance(graph_state.get("pacing_rhythm_target"), dict):
            event.setdefault("pacing_rhythm_target", graph_state.get("pacing_rhythm_target"))
        if isinstance(graph_state.get("pacing_rhythm_validation"), dict):
            event.setdefault("pacing_rhythm_validation", graph_state.get("pacing_rhythm_validation"))
        if isinstance(graph_state.get("temporal_control_state"), dict):
            event.setdefault("temporal_control_state", graph_state.get("temporal_control_state"))
        if isinstance(graph_state.get("temporal_control_target"), dict):
            event.setdefault("temporal_control_target", graph_state.get("temporal_control_target"))
        if isinstance(graph_state.get("temporal_control_validation"), dict):
            event.setdefault("temporal_control_validation", graph_state.get("temporal_control_validation"))
        if isinstance(graph_state.get("sensory_context_state"), dict):
            event.setdefault("sensory_context_state", graph_state.get("sensory_context_state"))
        if isinstance(graph_state.get("sensory_context_target"), dict):
            event.setdefault("sensory_context_target", graph_state.get("sensory_context_target"))
        if isinstance(graph_state.get("sensory_context_validation"), dict):
            event.setdefault("sensory_context_validation", graph_state.get("sensory_context_validation"))
        if isinstance(graph_state.get("symbolic_object_resonance_state"), dict):
            event.setdefault(
                "symbolic_object_resonance_state",
                graph_state.get("symbolic_object_resonance_state"),
            )
        if isinstance(graph_state.get("symbolic_object_resonance_target"), dict):
            event.setdefault(
                "symbolic_object_resonance_target",
                graph_state.get("symbolic_object_resonance_target"),
            )
        if isinstance(graph_state.get("symbolic_object_resonance_validation"), dict):
            event.setdefault(
                "symbolic_object_resonance_validation",
                graph_state.get("symbolic_object_resonance_validation"),
            )
        if isinstance(graph_state.get("social_pressure_state"), dict):
            event.setdefault("social_pressure_state", graph_state.get("social_pressure_state"))
        if isinstance(graph_state.get("social_pressure_target"), dict):
            event.setdefault("social_pressure_target", graph_state.get("social_pressure_target"))
        if isinstance(graph_state.get("social_pressure_validation"), dict):
            event.setdefault("social_pressure_validation", graph_state.get("social_pressure_validation"))
        if isinstance(graph_state.get("tonal_consistency_target"), dict):
            event.setdefault("tonal_consistency_target", graph_state.get("tonal_consistency_target"))
        if isinstance(graph_state.get("tonal_consistency_validation"), dict):
            event.setdefault(
                "tonal_consistency_validation",
                graph_state.get("tonal_consistency_validation"),
            )
        if isinstance(graph_state.get("expectation_variation_state"), dict):
            event.setdefault("expectation_variation_state", graph_state.get("expectation_variation_state"))
        if isinstance(graph_state.get("expectation_variation_target"), dict):
            event.setdefault("expectation_variation_target", graph_state.get("expectation_variation_target"))
        if isinstance(graph_state.get("expectation_variation_validation"), dict):
            event.setdefault("expectation_variation_validation", graph_state.get("expectation_variation_validation"))
        if isinstance(graph_state.get("narrative_momentum_state"), dict):
            event.setdefault("narrative_momentum_state", graph_state.get("narrative_momentum_state"))
        if isinstance(graph_state.get("narrative_momentum_target"), dict):
            event.setdefault("narrative_momentum_target", graph_state.get("narrative_momentum_target"))
        if isinstance(graph_state.get("narrative_momentum_validation"), dict):
            event.setdefault("narrative_momentum_validation", graph_state.get("narrative_momentum_validation"))
        if selected_responder_set:
            event.setdefault("selected_responder_set", selected_responder_set)
        actor_survival_telemetry = (
            graph_state.get("actor_survival_telemetry")
            if isinstance(graph_state.get("actor_survival_telemetry"), dict)
            else {}
        )
        if actor_survival_telemetry:
            event.setdefault("actor_survival_telemetry", actor_survival_telemetry)
        graph_state.setdefault("turn_aspect_ledger", event.get("turn_aspect_ledger"))
        graph_state.setdefault("validation_outcome", event.get("validation_outcome"))
        graph_state.setdefault("visible_output_bundle", event.get("visible_output_bundle"))
        graph_state.setdefault("interpreted_input", interpreted_input)
        if isinstance(event.get("no_dead_end_recovery"), dict):
            graph_state["no_dead_end_recovery"] = event["no_dead_end_recovery"]
        _record_hierarchical_memory_aspect(
            session=session,
            graph_state=graph_state,
            event=event,
            committed_turn={
                "canonical_turn_id": event.get("canonical_turn_id"),
                "module_id": session.module_id,
                "runtime_profile_id": _runtime_profile_id_from_projection(
                    session.runtime_projection if isinstance(session.runtime_projection, dict) else None
                ),
                "turn_number": commit_turn_number,
                "turn_kind": event.get("turn_kind") or "player_rejected_recoverable",
                "turn_outcome": turn_outcome,
                "recoverable_outcome": True,
                "no_dead_end_recovery": event.get("no_dead_end_recovery"),
                "narrative_commit": event.get("narrative_commit"),
                "turn_aspect_ledger": event.get("turn_aspect_ledger"),
                "visible_output_bundle": event.get("visible_output_bundle"),
            },
            allow_write=False,
        )
        if isinstance(event.get("diagnostics"), dict):
            event["diagnostics"]["turn_aspect_ledger"] = event.get("turn_aspect_ledger")
            event["diagnostics"]["hierarchical_memory"] = event.get("hierarchical_memory")
        turn_lc = TurnLifecycleChain()
        turn_lc.advance("received")
        turn_lc.advance("interpreted")
        turn_lc.advance("generated_or_resolved")
        turn_lc.advance("validated")
        turn_lc.advance("committed")
        turn_lc.advance("projected")

        canonical_record = {
            "canonical_turn_id": event["canonical_turn_id"],
            "turn_number": commit_turn_number,
            "turn_kind": event.get("turn_kind") or "player_rejected_recoverable",
            "trace_id": trace_id or "",
            "turn_outcome": turn_outcome,
            "narrative_commit": event.get("narrative_commit"),
            "validation_outcome": event.get("validation_outcome"),
            "committed_result": event.get("committed_result")
            if isinstance(event.get("committed_result"), dict)
            else graph_state.get("committed_result"),
            "no_dead_end_recovery": event.get("no_dead_end_recovery"),
            "turn_aspect_ledger": event.get("turn_aspect_ledger"),
            "visible_output_bundle": event.get("visible_output_bundle"),
            "scene_energy_target": event.get("scene_energy_target"),
            "scene_energy_transition": event.get("scene_energy_transition"),
            "scene_energy_validation": event.get("scene_energy_validation"),
            "pacing_rhythm_state": event.get("pacing_rhythm_state"),
            "pacing_rhythm_target": event.get("pacing_rhythm_target"),
            "pacing_rhythm_validation": event.get("pacing_rhythm_validation"),
            "temporal_control_state": event.get("temporal_control_state"),
            "temporal_control_target": event.get("temporal_control_target"),
            "temporal_control_validation": event.get("temporal_control_validation"),
            "sensory_context_state": event.get("sensory_context_state"),
            "sensory_context_target": event.get("sensory_context_target"),
            "sensory_context_validation": event.get("sensory_context_validation"),
            "social_pressure_state": event.get("social_pressure_state"),
            "social_pressure_target": event.get("social_pressure_target"),
            "social_pressure_validation": event.get("social_pressure_validation"),
            "tonal_consistency_target": event.get("tonal_consistency_target"),
            "tonal_consistency_validation": event.get("tonal_consistency_validation"),
            "expectation_variation_state": event.get("expectation_variation_state"),
            "expectation_variation_target": event.get("expectation_variation_target"),
            "expectation_variation_validation": event.get("expectation_variation_validation"),
            "narrative_momentum_state": event.get("narrative_momentum_state"),
            "narrative_momentum_target": event.get("narrative_momentum_target"),
            "narrative_momentum_validation": event.get("narrative_momentum_validation"),
            "human_input_attribution": human_att,
            "hierarchical_memory_update": event.get("hierarchical_memory"),
            "recoverable_outcome": True,
            "committed_state_after": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
                "environment_state": session.environment_state
                if isinstance(session.environment_state, dict)
                else {},
            },
        }
        turn_lc.advance("persisted")
        canonical_record["lifecycle_state"] = "observed"
        event["lifecycle_state"] = "observed"
        session.history.append(canonical_record)
        self._refresh_callback_web_after_commit(
            session=session,
            event=event,
            graph_state=graph_state,
        )
        self._refresh_consequence_cascade_after_commit(
            session=session,
            event=event,
            graph_state=graph_state,
        )
        self._emit_observability_path_for_event(session=session, graph_state=graph_state, event=event)
        session.diagnostics.append(event)
        turn_lc.advance("observed")
        session.updated_at = datetime.now(timezone.utc)
        self._persist_session(session)
        return event


__all__ = ["_PlayerVisiblePersistenceMixin"]
