"""Langfuse verify source segment: handler_live_opening_matrix.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        "expectation_variation_setup_supported": (
            "expectation_variation_unearned_event" not in expectation_variation_failure_codes
            and "expectation_variation_target_mismatch" not in expectation_variation_failure_codes
            if expectation_variation_actual
            else det_scores.get("expectation_variation_setup_supported")
        ),
        "expectation_variation_contract_pass": (
            expectation_variation_actual.get("contract_pass")
            if "contract_pass" in expectation_variation_actual
            else det_scores.get("expectation_variation_contract_pass")
        ),
        "expectation_variation_failure_codes": expectation_variation_failure_codes,
        "narrative_momentum_policy_present": (
            narrative_momentum_expected.get("policy_present")
            if "policy_present" in narrative_momentum_expected
            else det_scores.get("narrative_momentum_policy_present")
        ),
        "narrative_momentum_target_selected": (
            bool(narrative_momentum_target.get("target_state"))
            if narrative_momentum_target
            else det_scores.get("narrative_momentum_target_selected")
        ),
        "narrative_momentum_current_state": narrative_momentum_actual.get(
            "current_state"
        )
        or narrative_momentum_selected.get("current_state"),
        "narrative_momentum_current_score": narrative_momentum_actual.get(
            "current_score"
        )
        if "current_score" in narrative_momentum_actual
        else narrative_momentum_selected.get("current_score"),
        "narrative_momentum_target_state": narrative_momentum_target.get("target_state"),
        "narrative_momentum_target_score": narrative_momentum_target.get("target_score"),
        "narrative_momentum_trend": narrative_momentum_actual.get("trend")
        or narrative_momentum_selected.get("trend"),
        "narrative_momentum_velocity": narrative_momentum_actual.get("velocity")
        if "velocity" in narrative_momentum_actual
        else narrative_momentum_selected.get("velocity"),
        "narrative_momentum_transition_allowed": (
            narrative_momentum_actual.get("transition_allowed")
            if "transition_allowed" in narrative_momentum_actual
            else det_scores.get("narrative_momentum_transition_allowed")
        ),
        "narrative_momentum_progress_event_present": (
            narrative_momentum_progress_event_count
            >= narrative_momentum_min_progress_event_count
            if narrative_momentum_actual
            else det_scores.get("narrative_momentum_progress_event_present")
        ),
        "narrative_momentum_stall_budget_respected": (
            narrative_momentum_actual.get("stall_budget_respected")
            if "stall_budget_respected" in narrative_momentum_actual
            else det_scores.get("narrative_momentum_stall_budget_respected")
        ),
        "narrative_momentum_contract_pass": (
            narrative_momentum_actual.get("contract_pass")
            if "contract_pass" in narrative_momentum_actual
            else det_scores.get("narrative_momentum_contract_pass")
        ),
        "narrative_momentum_failure_codes": narrative_momentum_failure_codes,
        "dramatic_irony_policy_present": (
            dramatic_irony_expected.get("policy_present")
            if "policy_present" in dramatic_irony_expected
            else det_scores.get("dramatic_irony_policy_present")
        ),
        "dramatic_irony_opportunity_present": (
            bool(dramatic_irony_actual.get("opportunity_count"))
            if "opportunity_count" in dramatic_irony_actual
            else det_scores.get("dramatic_irony_opportunity_present")
        ),
        "dramatic_irony_selected_opportunities": dramatic_irony_selected.get("selected_opportunity_ids") or [],
        "dramatic_irony_realized_opportunities": dramatic_irony_actual.get("realized_opportunity_ids") or [],
'''
