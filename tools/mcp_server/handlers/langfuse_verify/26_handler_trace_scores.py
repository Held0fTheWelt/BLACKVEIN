"""Langfuse verify source segment: handler_trace_scores.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        "dramatic_irony_realization_status": dramatic_irony_actual.get("realization_status"),
        "dramatic_irony_leak_blocked": bool(dramatic_irony_actual.get("leak_blocked")),
        "dramatic_irony_contract_pass": (
            dramatic_irony_actual.get("contract_pass")
            if "contract_pass" in dramatic_irony_actual
            else det_scores.get("dramatic_irony_contract_pass")
        ),
        "dramatic_irony_violation_codes": dramatic_irony_violation_codes,
        "callback_web_policy_present": (
            callback_expected.get("policy_present")
            if "policy_present" in callback_expected
            else det_scores.get("callback_web_policy_present")
        ),
        "callback_web_selected": bool(
            callback_selected.get("selected_callback_edge_id")
            or callback_selected.get("selected_callback_kind")
        ),
        "callback_web_selected_edge_id": callback_selected.get("selected_callback_edge_id"),
        "callback_web_selected_kind": callback_selected.get("selected_callback_kind"),
        "callback_web_selected_continuity_classes": callback_selected.get("selected_continuity_classes")
        or [],
        "callback_web_edge_count": callback_actual.get("edge_count"),
        "callback_web_observation_count": callback_actual.get("observation_count"),
        "callback_web_graph_edge_count": callback_actual.get("graph_edge_count"),
        "callback_web_contract_pass": (
            callback_actual.get("contract_pass")
            if "contract_pass" in callback_actual
            else det_scores.get("callback_web_contract_pass")
        ),
        "callback_web_failure_codes": callback_failure_codes,
        "consequence_cascade_policy_present": (
            cascade_expected.get("policy_present")
            if "policy_present" in cascade_expected
            else det_scores.get("consequence_cascade_policy_present")
        ),
        "consequence_cascade_selected": bool(
            cascade_selected.get("selected_consequence_ids")
            or cascade_selected.get("selected_continuity_classes")
        ),
        "consequence_cascade_selected_consequence_ids": cascade_selected.get(
            "selected_consequence_ids"
        )
        or [],
        "consequence_cascade_selected_continuity_classes": cascade_selected.get(
            "selected_continuity_classes"
        )
        or [],
        "consequence_cascade_selected_statuses": cascade_selected.get("selected_statuses") or [],
        "consequence_cascade_atom_count": cascade_actual.get("atom_count"),
        "consequence_cascade_edge_count": cascade_actual.get("edge_count"),
        "consequence_cascade_active_atom_count": cascade_actual.get("active_atom_count"),
        "consequence_cascade_contract_pass": (
            cascade_actual.get("contract_pass")
            if "contract_pass" in cascade_actual
            else det_scores.get("consequence_cascade_contract_pass")
        ),
        "consequence_cascade_failure_codes": cascade_failure_codes,
        "narrator_required_when_expected": det_scores.get("narrator_required_when_expected"),
        "narrator_required": narr_expected.get("required"),
        "narrator_present": narr_actual.get("narrator_block_present") or narr_actual.get("consequence_realized"),
        "npc_policy": npc_expected.get("policy"),
        "npc_takeover_absent": (not bool(npc_actual.get("npc_takeover_detected"))) if "npc_takeover_detected" in npc_actual else det_scores.get("npc_takeover_absent"),
        "npc_takeover_detected": npc_actual.get("npc_takeover_detected"),
        "npc_agency_plan_present": bool(npc_agency_rec) if npc_agency_rec else det_scores.get("npc_agency_plan_present"),
        "npc_independent_planning_used": npc_agency_actual.get("independent_planning_used") if "independent_planning_used" in npc_agency_actual else det_scores.get("npc_independent_planning_used"),
        "npc_long_horizon_state_present": npc_agency_actual.get("long_horizon_state_present") if "long_horizon_state_present" in npc_agency_actual else det_scores.get("npc_long_horizon_state_present"),
        "npc_private_plan_resolution_present": npc_agency_actual.get("private_plan_resolution_present") if "private_plan_resolution_present" in npc_agency_actual else det_scores.get("npc_private_plan_resolution_present"),
        "npc_private_plan_visibility_respected": npc_agency_actual.get("private_plan_visibility_respected") if "private_plan_visibility_respected" in npc_agency_actual else det_scores.get("npc_private_plan_visibility_respected"),
        "npc_intention_threads_carried_forward": (
            (
                int(npc_agency_actual.get("intention_threads_carried_forward") or 0) > 0
                or int(npc_agency_actual.get("intention_threads_active") or 0)
'''
