"""Langfuse verify source segment: handler_opening_judge_scores.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
                > len(npc_agency_actual.get("candidate_actor_ids") or [])
            )
            if (
                "intention_threads_carried_forward" in npc_agency_actual
                or "intention_threads_active" in npc_agency_actual
            )
            else det_scores.get("npc_intention_threads_carried_forward")
        ),
        "npc_required_initiatives_realized": (
            not bool(npc_agency_actual.get("missing_required_actor_ids"))
            if "missing_required_actor_ids" in npc_agency_actual
            else det_scores.get("npc_required_initiatives_realized")
        ),
        "multi_npc_initiative_realized": npc_agency_actual.get("multi_npc_initiative_realized") if "multi_npc_initiative_realized" in npc_agency_actual else det_scores.get("multi_npc_initiative_realized"),
        "npc_carry_forward_closed": (
            (
                not bool(npc_agency_actual.get("carry_forward_actor_ids"))
                and not bool(npc_agency_actual.get("missing_required_actor_ids"))
            )
            if (
                "carry_forward_actor_ids" in npc_agency_actual
                or "missing_required_actor_ids" in npc_agency_actual
            )
            else det_scores.get("npc_carry_forward_closed")
        ),
        "npc_forbidden_actor_absent": (
            not bool(npc_agency_actual.get("forbidden_planned_actor_ids"))
            and not bool(npc_agency_actual.get("forbidden_realized_actor_ids"))
            if (
                "forbidden_planned_actor_ids" in npc_agency_actual
                or "forbidden_realized_actor_ids" in npc_agency_actual
            )
            else det_scores.get("npc_forbidden_actor_absent")
        ),
        "npc_agency_candidate_actor_ids": npc_agency_actual.get("candidate_actor_ids") or [],
        "npc_agency_missing_required_actor_ids": npc_agency_actual.get("missing_required_actor_ids") or [],
        "npc_agency_claim_readiness_status": claim_readiness.get("claim_status"),
        "npc_agency_full_claim_allowed": claim_readiness.get("full_claim_allowed"),
        "capability_selection_present": bool(cap_rec) if cap_rec else det_scores.get("capability_selection_present"),
        "selected_capabilities": cap_selected.get("selected_capabilities") or [],
        "realized_capabilities": cap_actual.get("realized_capabilities") or [],
        "selected_capabilities_realized": (
            not bool(cap_actual.get("missing_required_capabilities"))
            if "missing_required_capabilities" in cap_actual
            else det_scores.get("selected_capabilities_realized")
        ),
        "forbidden_capability_realized": cap_actual.get("forbidden_capability_realized"),
        "visible_block_origin_present": vis_actual.get("visible_block_origin_present") if "visible_block_origin_present" in vis_actual else det_scores.get("visible_block_origin_present"),
        "visible_origin_present": vis_actual.get("visible_block_origin_present") if "visible_block_origin_present" in vis_actual else det_scores.get("visible_block_origin_present"),
        "narrative_aspect_policy_present": narrative_expected.get("policy_present") if "policy_present" in narrative_expected else det_scores.get("narrative_aspect_policy_present"),
        "narrative_aspect_selected": bool(narrative_selected.get("selected_aspects")) if narrative_selected else det_scores.get("narrative_aspect_selected"),
        "selected_narrative_aspects": narrative_selected.get("selected_aspects") or [],
        "realized_narrative_aspects": narrative_actual.get("realized_aspects") or [],
        "narrative_aspect_visible_when_required": narrative_actual.get("visible_when_required") if "visible_when_required" in narrative_actual else det_scores.get("narrative_aspect_visible_when_required"),
        "narrative_aspect_contract_pass": det_scores.get("narrative_aspect_contract_pass"),
        "theme_tracking_policy_present": narrative_expected.get("theme_tracking_policy_present") if "theme_tracking_policy_present" in narrative_expected else det_scores.get("theme_tracking_policy_present"),
        "theme_tracking_selected": bool(narrative_actual.get("selected_theme_aspects")) if narrative_actual else det_scores.get("theme_tracking_selected"),
        "selected_theme_aspects": narrative_actual.get("selected_theme_aspects") or narrative_selected.get("selected_theme_aspects") or [],
        "realized_theme_aspects": narrative_actual.get("realized_theme_aspects") or [],
        "theme_semantic_classification_present": det_scores.get("theme_semantic_classification_present"),
        "theme_semantic_classification_count": narrative_actual.get("semantic_classification_count"),
        "theme_weak_alignment_count": narrative_actual.get("semantic_weak_alignment_count"),
        "theme_tracking_contract_pass": det_scores.get("theme_tracking_contract_pass"),
        "voice_consistency_policy_present": voice_expected.get("policy_present") if "policy_present" in voice_expected else det_scores.get("voice_consistency_policy_present"),
        "voice_semantic_classification_enabled": voice_expected.get("semantic_classification_enabled"),
        "voice_semantic_classification_present": det_scores.get("voice_semantic_classification_present"),
        "voice_semantic_classification_count": voice_actual.get("semantic_classification_count"),
        "voice_spoken_line_count": voice_actual.get("spoken_line_count"),
        "voice_cross_actor_confusion_absent": (
            voice_cross_actor_count == 0
            if voice_actual
            else det_scores.get("voice_cross_actor_confusion_absent")
'''
