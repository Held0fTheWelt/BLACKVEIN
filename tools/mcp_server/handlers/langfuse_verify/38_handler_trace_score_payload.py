"""Langfuse verify source segment: handler_trace_score_payload.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
                "structured_narration_summary_kind",
                "opening_narration_normalized",
                "opening_narration_source",
                "opening_narration_beat_count",
                "narration_summary_input_kind",
            )
            if sm.get(k) is not None
        }
        return {
            "ok": True,
            "trace_id": trace_id,
            "is_opening_trace": is_opening,
            "trace_name": raw.get("name"),
            "trace_origin": meta.get("trace_origin"),
            "execution_tier": meta.get("execution_tier"),
            "canonical_player_flow": meta.get("canonical_player_flow"),
            "selected_player_role": meta.get("selected_player_role"),
            "human_actor_id": meta.get("human_actor_id"),
            "deterministic_scores": enriched_det,
            "judge_scores": judge_scores,
            "opening_shape_diagnostics": opening_shape_diagnostics,
            "canonical_live_langfuse_filters": {
                "opening_evaluators": {
                    "trace.name": "world-engine.session.create",
                    "world_engine_generation_observation.name": "story.model.generation",
                    "trace_origin": "live_ui",
                    "execution_tier": "live",
                    "canonical_player_flow": True,
                    "observation_filters": dict(OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS),
                    "alternate_trace_names_for_search": LANGFUSE_OPENING_GENERATION_FILTER_BUNDLE[
                        "alternate_trace_names_for_search"
                    ],
                    "trace_metadata_when_available": dict(
                        LANGFUSE_OPENING_GENERATION_FILTER_BUNDLE["metadata"]
                    ),
                },
                "opening_generation_categorical_evaluators": {
                    "judges": list(_judge_names_for_scope("opening_generation")),
                    "observation_filters": dict(OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS),
                    "alternate_trace_names_for_search": LANGFUSE_OPENING_GENERATION_FILTER_BUNDLE[
                        "alternate_trace_names_for_search"
                    ],
                    "trace_metadata_when_available": dict(
                        LANGFUSE_OPENING_GENERATION_FILTER_BUNDLE["metadata"]
                    ),
                },
                "turn_evaluators": {
                    "primary_trace_name": WORLD_ENGINE_TURN_TRACE_NAME,
                    "alternate_backend_root_trace_name": BACKEND_TURN_ROOT_TRACE_NAME,
                    "distributed_trace_note": (
                        f"Backend opens {BACKEND_TURN_ROOT_TRACE_NAME}; world-engine participates with "
                        f"{WORLD_ENGINE_TURN_TRACE_NAME} on the same Langfuse trace. Prefer GENERATION "
                        "story.model.generation scoped to the world-engine turn span when attaching judges."
                    ),
                    "world_engine_turn_observation_name": WORLD_ENGINE_TURN_TRACE_NAME,
                    "trace_origin": "live_ui",
                    "execution_tier": "live",
                    "canonical_player_flow": True,
                },
                # Langfuse evaluator UI: attach scores to GENERATION on story.model.generation
                # under live turn traces (WoS canonical live metadata when available).
                "turn_generation_categorical_evaluators": {
                    "judges": list(_judge_names_for_scope("turn_generation")),
                    "observation_filters": dict(TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS),
                    "alternate_backend_root_trace_names": list(
                        LANGFUSE_TURN_GENERATION_FILTER_BUNDLE.get("alternate_trace_names") or []
                    ),
                    "trace_metadata_when_available": {
                        "trace_origin": "live_ui",
                        "execution_tier": "live",
                        "canonical_player_flow": True,
                        "opening_turn": False,
'''
