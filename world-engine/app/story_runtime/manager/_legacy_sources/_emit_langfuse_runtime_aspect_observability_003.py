"""Runtime-aspect observability source chunk 003.

Contributes ordered source lines for legacy Langfuse runtime-aspect observability emission. This chunk is intentionally small and ordered by the legacy manifest.
"""
SOURCE = r'''\
            ),
        ),
        (
            "pacing_rhythm_density_respected",
            ASPECT_PACING_RHYTHM,
            _runtime_aspect_score_value(
                "pacing_rhythm_visible_density_exceeded" not in pacing_rhythm_failure_codes
            ),
        ),
        (
            "pacing_rhythm_pause_respected",
            ASPECT_PACING_RHYTHM,
            _runtime_aspect_score_value(
                "pacing_rhythm_pause_obligation_lost" not in pacing_rhythm_failure_codes
                and "pacing_rhythm_forced_speech_violation" not in pacing_rhythm_failure_codes
            ),
        ),
        (
            "temporal_control_policy_present",
            ASPECT_TEMPORAL_CONTROL,
            _runtime_aspect_score_value(
                bool(_expected(ASPECT_TEMPORAL_CONTROL).get("policy_present"))
            ),
        ),
        (
            "temporal_control_target_selected",
            ASPECT_TEMPORAL_CONTROL,
            _runtime_aspect_score_value(bool(temporal_control_target.get("operation"))),
        ),
        (
            "temporal_control_operation_allowed",
            ASPECT_TEMPORAL_CONTROL,
            _runtime_aspect_score_value(
                "temporal_control_operation_not_allowed"
                not in temporal_control_failure_codes
            ),
        ),
        (
            "temporal_control_committed_sources_bounded",
            ASPECT_TEMPORAL_CONTROL,
            _runtime_aspect_score_value(
                "temporal_control_uncommitted_source"
                not in temporal_control_failure_codes
                and "temporal_control_unbounded_jump"
                not in temporal_control_failure_codes
            ),
        ),
        (
            "temporal_control_history_rewrite_absent",
            ASPECT_TEMPORAL_CONTROL,
            _runtime_aspect_score_value(
                "temporal_control_history_rewrite_attempt"
                not in temporal_control_failure_codes
                and "temporal_control_branch_state_adoption"
                not in temporal_control_failure_codes
            ),
        ),
        (
            "temporal_control_contract_pass",
            ASPECT_TEMPORAL_CONTROL,
            _runtime_aspect_score_value(
                _rec(ASPECT_TEMPORAL_CONTROL).get("status")
                in {"passed", "not_applicable"}
                and temporal_control_actual.get("contract_pass") is not False
                and not temporal_control_failure_codes
            ),
        ),
        (
            "sensory_context_target_present",
            ASPECT_SENSORY_CONTEXT,
            _runtime_aspect_score_value(bool(sensory_context_target)),
        ),
        (
            "sensory_context_contract_pass",
            ASPECT_SENSORY_CONTEXT,
            _runtime_aspect_score_value(
                _rec(ASPECT_SENSORY_CONTEXT).get("status") in {"passed", "not_applicable"}
            ),
        ),
        (
            "sensory_context_required_layers_realized",
            ASPECT_SENSORY_CONTEXT,
            _runtime_aspect_score_value(
                "sensory_context_missing_required_layer" not in sensory_context_failure_codes
                and "sensory_context_structured_event_missing" not in sensory_context_failure_codes
            ),
        ),
        (
            "sensory_context_source_refs_valid",
            ASPECT_SENSORY_CONTEXT,
            _runtime_aspect_score_value(
                "sensory_context_source_ref_mismatch" not in sensory_context_failure_codes
                and "sensory_context_unselected_layer" not in sensory_context_failure_codes
            ),
        ),
        (
            "genre_awareness_policy_present",
            ASPECT_GENRE_AWARENESS,
            _runtime_aspect_score_value(
                bool(_expected(ASPECT_GENRE_AWARENESS).get("policy_present"))
            ),
        ),
        (
            "genre_awareness_target_selected",
            ASPECT_GENRE_AWARENESS,
            _runtime_aspect_score_value(bool(genre_awareness_target.get("genre_profile_id"))),
        ),
        (
            "genre_awareness_registers_valid",
            ASPECT_GENRE_AWARENESS,
            _runtime_aspect_score_value(
                "genre_awareness_register_not_allowed" not in genre_awareness_failure_codes
            ),
        ),
        (
            "genre_awareness_required_conventions_realized",
            ASPECT_GENRE_AWARENESS,
            _runtime_aspect_score_value(
                "genre_awareness_missing_required_convention"
                not in genre_awareness_failure_codes
                and "genre_awareness_missing_required_event"
                not in genre_awareness_failure_codes
            ),
        ),
        (
            "genre_awareness_forbidden_markers_absent",
            ASPECT_GENRE_AWARENESS,
            _runtime_aspect_score_value(
                "genre_awareness_forbidden_marker" not in genre_awareness_failure_codes
            ),
        ),
        (
            "genre_awareness_contract_pass",
            ASPECT_GENRE_AWARENESS,
            _runtime_aspect_score_value(
                _rec(ASPECT_GENRE_AWARENESS).get("status") in {"passed", "not_applicable"}
                and genre_awareness_actual.get("contract_pass") is not False
            ),
        ),
        (
            "tonal_consistency_policy_present",
            ASPECT_TONAL_CONSISTENCY,
            _runtime_aspect_score_value(
                bool(_expected(ASPECT_TONAL_CONSISTENCY).get("policy_present"))
            ),
        ),
        (
            "tonal_consistency_target_selected",
            ASPECT_TONAL_CONSISTENCY,
            _runtime_aspect_score_value(bool(tonal_consistency_target.get("profile_id"))),
        ),
        (
            "tonal_consistency_independent_classification_present",
            ASPECT_TONAL_CONSISTENCY,
            _runtime_aspect_score_value(
                bool(tonal_consistency_actual.get("structured_classification_present"))
                and tonal_consistency_actual.get("independent_classifier") is not False
            ),
        ),
        (
            "tonal_consistency_classification_present",
            ASPECT_TONAL_CONSISTENCY,
            _runtime_aspect_score_value(
                bool(tonal_consistency_actual.get("structured_classification_present"))
                and tonal_consistency_actual.get("independent_classifier") is not False
            ),
        ),
        (
            "tonal_consistency_marker_hits_absent",
            ASPECT_TONAL_CONSISTENCY,
            _runtime_aspect_score_value(
                "tonal_consistency_forbidden_marker_detected"
                not in tonal_consistency_failure_codes
            ),
        ),
        (
            "tonal_consistency_contract_pass",
            ASPECT_TONAL_CONSISTENCY,
            _runtime_aspect_score_value(
                _rec(ASPECT_TONAL_CONSISTENCY).get("status")
                in {"passed", "not_applicable"}
                and tonal_consistency_actual.get("contract_pass") is not False
                and not tonal_consistency_failure_codes
            ),
        ),
        (
            "symbolic_object_resonance_policy_present",
            ASPECT_SYMBOLIC_OBJECT_RESONANCE,
            _runtime_aspect_score_value(
                bool(_expected(ASPECT_SYMBOLIC_OBJECT_RESONANCE).get("policy_present"))
            ),
        ),
        (
            "symbolic_object_resonance_target_selected",
            ASPECT_SYMBOLIC_OBJECT_RESONANCE,
            _runtime_aspect_score_value(
                bool(symbolic_object_selected.get("selected_object_ids"))
            ),
        ),
        (
            "symbolic_object_resonance_source_refs_valid",
            ASPECT_SYMBOLIC_OBJECT_RESONANCE,
            _runtime_aspect_score_value(
                "symbolic_object_resonance_source_ref_mismatch"
                not in symbolic_object_failure_codes
                and "symbolic_object_resonance_unselected_object"
                not in symbolic_object_failure_codes
            ),
        ),
        (
            "symbolic_object_resonance_budget_pass",
            ASPECT_SYMBOLIC_OBJECT_RESONANCE,
            _runtime_aspect_score_value(
                "symbolic_object_resonance_budget_exceeded"
                not in symbolic_object_failure_codes
            ),
        ),
        (
            "symbolic_object_resonance_contract_pass",
            ASPECT_SYMBOLIC_OBJECT_RESONANCE,
            _runtime_aspect_score_value(
                _rec(ASPECT_SYMBOLIC_OBJECT_RESONANCE).get("status")
                in {"passed", "not_applicable"}
                and symbolic_object_actual.get("contract_pass") is not False
                and not symbolic_object_failure_codes
            ),
        ),
        (
            "improvisational_coherence_policy_present",
            ASPECT_IMPROVISATIONAL_COHERENCE,
            _runtime_aspect_score_value(
                bool(_expected(ASPECT_IMPROVISATIONAL_COHERENCE).get("policy_present"))
            ),
        ),
        (
            "improvisational_coherence_target_selected",
            ASPECT_IMPROVISATIONAL_COHERENCE,
            _runtime_aspect_score_value(
                bool(
                    improvisational_selected.get("contribution_id")
'''
