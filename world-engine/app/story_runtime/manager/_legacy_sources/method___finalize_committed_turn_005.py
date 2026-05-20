SOURCE = r'''\
            "dramatic_context_summary": dramatic_context_summary,
            "actor_turn_summary": actor_turn_summary,
            "branching_forecast": event.get("branching_forecast"),
            "no_dead_end_recovery": event.get("no_dead_end_recovery"),
            "turn_aspect_ledger": event.get("turn_aspect_ledger"),
            "visible_output_bundle": event.get("visible_output_bundle"),
            "scene_energy_target": event.get("scene_energy_target"),
            "scene_energy_transition": event.get("scene_energy_transition"),
            "scene_energy_validation": event.get("scene_energy_validation"),
            "temporal_control_state": event.get("temporal_control_state"),
            "temporal_control_target": event.get("temporal_control_target"),
            "temporal_control_validation": event.get("temporal_control_validation"),
            "social_pressure_state": event.get("social_pressure_state"),
            "social_pressure_target": event.get("social_pressure_target"),
            "social_pressure_validation": event.get("social_pressure_validation"),
            "expectation_variation_state": event.get("expectation_variation_state"),
            "expectation_variation_target": event.get("expectation_variation_target"),
            "expectation_variation_validation": event.get("expectation_variation_validation"),
            "narrative_momentum_state": event.get("narrative_momentum_state"),
            "narrative_momentum_target": event.get("narrative_momentum_target"),
            "narrative_momentum_validation": event.get("narrative_momentum_validation"),
            "human_input_attribution": event.get("human_input_attribution"),
            "hierarchical_memory_update": event.get("hierarchical_memory"),
            "committed_state_after": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
                "environment_state": session.environment_state
                if isinstance(session.environment_state, dict)
                else {},
            },
        }
        if isinstance(event.get("narrator_streaming"), dict):
            committed_record["narrator_streaming"] = event["narrator_streaming"]
        turn_lc.advance("persisted")
        committed_record["lifecycle_state"] = "observed"
        event["lifecycle_state"] = "observed"
        session.history.append(committed_record)
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
        # ADR-0063: W5 Actor Situation Tracker shadow extraction (Phase 1).
        # Best-effort; never fails the turn. No consumer reads w5_history yet.
        self._w5_shadow_extract_after_commit(
            session=session,
            graph_state=graph_state if isinstance(graph_state, dict) else {},
            event=event,
        )
        self._persist_session(session)
        return event
'''
