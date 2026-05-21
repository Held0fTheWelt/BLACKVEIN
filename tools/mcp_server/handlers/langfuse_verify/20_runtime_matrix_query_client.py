"""Langfuse verify source segment: runtime_matrix_query_client.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
            and "pacing_rhythm_forced_speech_violation" not in pacing_rhythm_failure_codes
            if pacing_rhythm_actual
            else det_scores.get("pacing_rhythm_pause_respected")
        ),
        "pacing_rhythm_failure_codes": pacing_rhythm_failure_codes,
        "temporal_control_policy_present": (
            temporal_control_expected.get("policy_present")
            if "policy_present" in temporal_control_expected
            else det_scores.get("temporal_control_policy_present")
        ),
        "temporal_control_target_selected": (
            bool(temporal_control_target.get("operation"))
            if temporal_control_selected
            else det_scores.get("temporal_control_target_selected")
        ),
        "temporal_control_operation": temporal_control_target.get("operation")
        if isinstance(temporal_control_target, dict)
        else None,
        "temporal_control_recalled_turn_ids": temporal_control_target.get(
            "recalled_turn_ids"
        )
        if isinstance(temporal_control_target, dict)
        else [],
        "temporal_control_recalled_consequence_ids": temporal_control_target.get(
            "recalled_consequence_ids"
        )
        if isinstance(temporal_control_target, dict)
        else [],
        "temporal_control_event_count": int(
            temporal_control_actual.get("event_count") or 0
        ),
        "temporal_control_committed_sources_bounded": (
            "temporal_control_uncommitted_source" not in temporal_control_failure_codes
            and "temporal_control_unbounded_jump" not in temporal_control_failure_codes
            if temporal_control_actual
            else det_scores.get("temporal_control_committed_sources_bounded")
        ),
        "temporal_control_history_rewrite_absent": (
            "temporal_control_history_rewrite_attempt"
            not in temporal_control_failure_codes
            and "temporal_control_branch_state_adoption"
            not in temporal_control_failure_codes
            if temporal_control_actual
            else det_scores.get("temporal_control_history_rewrite_absent")
        ),
        "temporal_control_contract_pass": (
            temporal_control_actual.get("contract_pass")
            if "contract_pass" in temporal_control_actual
            else det_scores.get("temporal_control_contract_pass")
        ),
        "temporal_control_failure_codes": temporal_control_failure_codes,
        "sensory_context_target_present": (
            bool(sensory_context_target)
            if sensory_context_rec
            else det_scores.get("sensory_context_target_present")
        ),
        "sensory_context_intensity": sensory_context_target.get("intensity"),
        "sensory_context_location_id": sensory_context_target.get("location_id"),
        "sensory_context_object_id": sensory_context_target.get("object_id"),
        "sensory_context_contract_pass": (
            sensory_context_actual.get("contract_pass")
            if "contract_pass" in sensory_context_actual
            else det_scores.get("sensory_context_contract_pass")
        ),
        "sensory_context_required_layers_realized": (
            "sensory_context_missing_required_layer" not in sensory_context_failure_codes
            and "sensory_context_structured_event_missing" not in sensory_context_failure_codes
            if sensory_context_actual
            else det_scores.get("sensory_context_required_layers_realized")
        ),
        "sensory_context_source_refs_valid": (
            "sensory_context_source_ref_mismatch" not in sensory_context_failure_codes
'''
