"""Langfuse verify source segment: handler_projection_tests.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
            symbolic_object_target.get("selected_object_ids")
            if isinstance(symbolic_object_target, dict)
            else []
        )
        or [],
        "symbolic_object_resonance_selected_symbol_ids": (
            symbolic_object_target.get("selected_symbol_ids")
            if isinstance(symbolic_object_target, dict)
            else []
        )
        or [],
        "symbolic_object_resonance_selected_roles": (
            symbolic_object_target.get("selected_resonance_roles")
            if isinstance(symbolic_object_target, dict)
            else []
        )
        or [],
        "symbolic_object_resonance_realized_object_ids": (
            symbolic_object_actual.get("realized_object_ids") or []
        ),
        "symbolic_object_resonance_realized_symbol_ids": (
            symbolic_object_actual.get("realized_symbol_ids") or []
        ),
        "symbolic_object_resonance_event_count": int(
            symbolic_object_actual.get("event_count") or 0
        ),
        "symbolic_object_resonance_source_refs_valid": (
            "symbolic_object_resonance_source_ref_mismatch"
            not in symbolic_object_failure_codes
            and "symbolic_object_resonance_unselected_object"
            not in symbolic_object_failure_codes
            if symbolic_object_actual
            else det_scores.get("symbolic_object_resonance_source_refs_valid")
        ),
        "symbolic_object_resonance_budget_pass": (
            "symbolic_object_resonance_budget_exceeded"
            not in symbolic_object_failure_codes
            if symbolic_object_actual
            else det_scores.get("symbolic_object_resonance_budget_pass")
        ),
        "symbolic_object_resonance_contract_pass": (
            symbolic_object_actual.get("contract_pass")
            if "contract_pass" in symbolic_object_actual
            else det_scores.get("symbolic_object_resonance_contract_pass")
        ),
        "symbolic_object_resonance_failure_codes": symbolic_object_failure_codes,
        "improvisational_coherence_policy_present": (
            improvisational_expected.get("policy_present")
            if "policy_present" in improvisational_expected
            else det_scores.get("improvisational_coherence_policy_present")
        ),
        "improvisational_coherence_target_selected": (
            bool(
                improvisational_selected.get("contribution_id")
                or improvisational_selected.get("acceptance_mode")
                or improvisational_selected.get("required_anchor_refs")
            )
            if improvisational_selected
            else det_scores.get("improvisational_coherence_target_selected")
        ),
        "improvisational_coherence_contribution_id": improvisational_selected.get(
            "contribution_id"
        ),
        "improvisational_coherence_contribution_kind": improvisational_selected.get(
            "contribution_kind"
        ),
        "improvisational_coherence_acceptance_mode": (
            improvisational_selected.get("acceptance_mode")
            or improvisational_actual.get("acceptance_mode")
        ),
        "improvisational_coherence_advance_class": improvisational_actual.get(
            "advance_class"
'''
