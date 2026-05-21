"""Langfuse verify source segment: handler_opening_contract.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        "relationship_state_contract_pass": (
            relationship_state_actual.get("contract_pass")
            if "contract_pass" in relationship_state_actual
            else det_scores.get("relationship_state_contract_pass")
        ),
        "relationship_state_failure_codes": relationship_state_failure_codes,
        "information_disclosure_policy_present": (
            disclosure_expected.get("policy_present")
            if "policy_present" in disclosure_expected
            else det_scores.get("information_disclosure_policy_present")
        ),
        "information_disclosure_target_selected": (
            bool(disclosure_selected.get("selected_unit_ids"))
            if disclosure_selected
            else det_scores.get("information_disclosure_target_selected")
        ),
        "information_disclosure_selected_units": disclosure_selected.get("selected_unit_ids") or [],
        "information_disclosure_visible_units": disclosure_actual.get("visible_unit_ids") or [],
        "information_disclosure_withheld_units": disclosure_selected.get("withheld_unit_ids")
        or disclosure_actual.get("withheld_unit_ids")
        or [],
        "information_disclosure_budget_used": disclosure_actual.get("budget_used"),
        "information_disclosure_budget_pass": (
            "information_disclosure_over_budget" not in disclosure_failure_codes
            if disclosure_actual
            else det_scores.get("information_disclosure_budget_pass")
        ),
        "information_disclosure_premature_reveal_absent": (
            "information_disclosure_forbidden_unit" not in disclosure_failure_codes
            if disclosure_actual
            else det_scores.get("information_disclosure_premature_reveal_absent")
        ),
        "information_disclosure_contract_pass": (
            disclosure_actual.get("contract_pass")
            if "contract_pass" in disclosure_actual
            else det_scores.get("information_disclosure_contract_pass")
        ),
        "information_disclosure_failure_codes": disclosure_failure_codes,
        "expectation_variation_policy_present": (
            expectation_variation_expected.get("policy_present")
            if "policy_present" in expectation_variation_expected
            else det_scores.get("expectation_variation_policy_present")
        ),
        "expectation_variation_target_selected": (
            bool(expectation_variation_selected.get("selected_variation_ids"))
            if expectation_variation_selected
            else det_scores.get("expectation_variation_target_selected")
        ),
        "expectation_variation_selected_ids": expectation_variation_selected.get(
            "selected_variation_ids"
        )
        or [],
        "expectation_variation_selected_types": expectation_variation_selected.get(
            "selected_variation_types"
        )
        or [],
        "expectation_variation_realized_ids": expectation_variation_actual.get(
            "realized_variation_ids"
        )
        or [],
        "expectation_variation_realized_types": expectation_variation_actual.get(
            "realized_variation_types"
        )
        or [],
        "expectation_variation_budget_used": expectation_variation_actual.get(
            "budget_used"
        ),
        "expectation_variation_budget_pass": (
            "expectation_variation_over_budget" not in expectation_variation_failure_codes
            if expectation_variation_actual
            else det_scores.get("expectation_variation_budget_pass")
        ),
'''
