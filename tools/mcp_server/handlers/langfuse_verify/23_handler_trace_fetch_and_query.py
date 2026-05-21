"""Langfuse verify source segment: handler_trace_fetch_and_query.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        ),
        "improvisational_coherence_acknowledged": (
            improvisational_actual.get("contribution_acknowledged")
            if "contribution_acknowledged" in improvisational_actual
            else (
                det_scores.get("improvisational_coherence_acknowledged")
                if "improvisational_coherence_acknowledged" in det_scores
                else det_scores.get("player_contribution_acknowledged")
            )
        ),
        "improvisational_coherence_scene_anchor_preserved": (
            "improv_scene_anchor_missing" not in improvisational_failure_codes
            if improvisational_actual
            else (
                det_scores.get("improvisational_coherence_scene_anchor_preserved")
                if "improvisational_coherence_scene_anchor_preserved" in det_scores
                else det_scores.get("improv_scene_anchor_preserved")
            )
        ),
        "improvisational_coherence_boundary_reason_code": (
            improvisational_actual.get("boundary_reason_code")
            or improvisational_selected.get("boundary_reason_code")
        ),
        "improvisational_coherence_contract_pass": (
            improvisational_actual.get("contract_pass")
            if "contract_pass" in improvisational_actual
            else (
                det_scores.get("improvisational_coherence_contract_pass")
                if "improvisational_coherence_contract_pass" in det_scores
                else det_scores.get("improv_contract_pass")
            )
        ),
        "improvisational_coherence_failure_codes": improvisational_failure_codes,
        "social_pressure_target_present": (
            bool(social_pressure_target)
            if social_pressure_rec
            else det_scores.get("social_pressure_target_present")
        ),
        "social_pressure_score": social_pressure_target.get("target_score")
        if isinstance(social_pressure_target, dict)
        else None,
        "social_pressure_band": social_pressure_target.get("target_band")
        if isinstance(social_pressure_target, dict)
        else None,
        "social_pressure_trend": social_pressure_target.get("trend")
        if isinstance(social_pressure_target, dict)
        else None,
        "social_pressure_contract_pass": (
            social_pressure_actual.get("contract_pass")
            if "contract_pass" in social_pressure_actual
            else det_scores.get("social_pressure_contract_pass")
        ),
        "social_pressure_metric_bounded": (
            "social_pressure_score_out_of_bounds" not in social_pressure_failure_codes
            if social_pressure_actual
            else det_scores.get("social_pressure_metric_bounded")
        ),
        "social_pressure_failure_codes": social_pressure_failure_codes,
        "relationship_state_target_present": (
            bool(relationship_state_target)
            if relationship_state_rec
            else det_scores.get("relationship_state_target_present")
        ),
        "relationship_state_pressure_band": relationship_state_target.get("pressure_band")
        if isinstance(relationship_state_target, dict)
        else None,
        "relationship_state_pair_count": int(
            relationship_state_actual.get("pair_count") or 0
        ),
        "relationship_state_transition_event_count": int(
            relationship_state_actual.get("transition_event_count") or 0
        ),
'''
