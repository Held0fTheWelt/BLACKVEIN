"""Langfuse verify source segment: assertion_contract_modes.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
            and "sensory_context_unselected_layer" not in sensory_context_failure_codes
            if sensory_context_actual
            else det_scores.get("sensory_context_source_refs_valid")
        ),
        "sensory_context_failure_codes": sensory_context_failure_codes,
        "genre_awareness_policy_present": (
            genre_awareness_expected.get("policy_present")
            if "policy_present" in genre_awareness_expected
            else det_scores.get("genre_awareness_policy_present")
        ),
        "genre_awareness_target_selected": (
            bool(genre_awareness_target.get("genre_profile_id"))
            if genre_awareness_selected
            else det_scores.get("genre_awareness_target_selected")
        ),
        "genre_awareness_profile_id": genre_awareness_target.get("genre_profile_id")
        if isinstance(genre_awareness_target, dict)
        else None,
        "genre_awareness_selected_registers": (
            genre_awareness_target.get("selected_registers")
            if isinstance(genre_awareness_target, dict)
            else []
        )
        or [],
        "genre_awareness_required_conventions": (
            genre_awareness_target.get("required_conventions")
            if isinstance(genre_awareness_target, dict)
            else []
        )
        or [],
        "genre_awareness_realized_conventions": (
            genre_awareness_actual.get("realized_conventions") or []
        ),
        "genre_awareness_event_count": int(
            genre_awareness_actual.get("event_count") or 0
        ),
        "genre_awareness_registers_valid": (
            "genre_awareness_register_not_allowed"
            not in genre_awareness_failure_codes
            if genre_awareness_actual
            else det_scores.get("genre_awareness_registers_valid")
        ),
        "genre_awareness_required_conventions_realized": (
            "genre_awareness_missing_required_convention"
            not in genre_awareness_failure_codes
            and "genre_awareness_missing_required_event"
            not in genre_awareness_failure_codes
            if genre_awareness_actual
            else det_scores.get("genre_awareness_required_conventions_realized")
        ),
        "genre_awareness_forbidden_markers_absent": (
            "genre_awareness_forbidden_marker" not in genre_awareness_failure_codes
            if genre_awareness_actual
            else det_scores.get("genre_awareness_forbidden_markers_absent")
        ),
        "genre_awareness_contract_pass": (
            genre_awareness_actual.get("contract_pass")
            if "contract_pass" in genre_awareness_actual
            else det_scores.get("genre_awareness_contract_pass")
        ),
        "genre_awareness_failure_codes": genre_awareness_failure_codes,
        "symbolic_object_resonance_policy_present": (
            symbolic_object_expected.get("policy_present")
            if "policy_present" in symbolic_object_expected
            else det_scores.get("symbolic_object_resonance_policy_present")
        ),
        "symbolic_object_resonance_target_selected": (
            bool(symbolic_object_target.get("selected_object_ids"))
            if symbolic_object_selected
            else det_scores.get("symbolic_object_resonance_target_selected")
        ),
        "symbolic_object_resonance_selected_object_ids": (
'''
