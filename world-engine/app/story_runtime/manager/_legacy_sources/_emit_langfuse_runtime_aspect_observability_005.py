SOURCE = r'''\
            ASPECT_NPC_AUTHORITY,
            _runtime_aspect_score_value(_rec(ASPECT_NPC_AUTHORITY).get("status") == "passed"),
        ),
        (
            "npc_agency_plan_present",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(_known(ASPECT_NPC_AGENCY)),
        ),
        (
            "npc_independent_planning_used",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(bool(npc_agency_actual.get("independent_planning_used"))),
        ),
        (
            "npc_long_horizon_state_present",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(bool(npc_agency_actual.get("long_horizon_state_present"))),
        ),
        (
            "npc_private_plan_resolution_present",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(bool(npc_agency_actual.get("private_plan_resolution_present"))),
        ),
        (
            "npc_private_plan_visibility_respected",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(
                npc_agency_actual.get("private_plan_visibility_respected") is not False
                and not bool(npc_agency_actual.get("unrealized_selected_private_plan_actor_ids"))
            ),
        ),
        (
            "npc_intention_threads_carried_forward",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(
                int(npc_agency_actual.get("intention_threads_carried_forward") or 0) > 0
                or int(npc_agency_actual.get("intention_threads_active") or 0)
                > len(npc_agency_actual.get("candidate_actor_ids") or [])
            ),
        ),
        (
            "npc_required_initiatives_realized",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(not bool(npc_agency_actual.get("missing_required_actor_ids"))),
        ),
        (
            "multi_npc_initiative_realized",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(bool(npc_agency_actual.get("multi_npc_initiative_realized"))),
        ),
        (
            "npc_carry_forward_closed",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(
                not bool(npc_agency_actual.get("carry_forward_actor_ids"))
                and not bool(npc_agency_actual.get("missing_required_actor_ids"))
            ),
        ),
        (
            "npc_forbidden_actor_absent",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(
                not bool(npc_agency_actual.get("forbidden_planned_actor_ids"))
                and not bool(npc_agency_actual.get("forbidden_realized_actor_ids"))
            ),
        ),
        (
            "npc_consequence_takeover_absent",
            ASPECT_NPC_AUTHORITY,
            _runtime_aspect_score_value(not bool(npc_actual.get("npc_takeover_detected"))),
        ),
        (
            "npc_exposition_absent",
            ASPECT_NPC_AUTHORITY,
            _runtime_aspect_score_value("narrated_player_perception" not in npc_failure_reason and "explained_environment" not in npc_failure_reason),
        ),
        (
            "player_agency_violation_absent",
            ASPECT_NPC_AUTHORITY,
            _runtime_aspect_score_value(
                "ai_controlled_human_actor" not in npc_failure_reason
                and "npc.force_player_speech.forbidden" not in violated_capabilities
            ),
        ),
        (
            "capability_selection_present",
            ASPECT_CAPABILITY_SELECTION,
            _runtime_aspect_score_value(_known(ASPECT_CAPABILITY_SELECTION)),
        ),
        (
            "capability_selection_valid",
            ASPECT_CAPABILITY_SELECTION,
            _runtime_aspect_score_value(_rec(ASPECT_CAPABILITY_SELECTION).get("status") != "failed"),
        ),
        (
            "forbidden_capability_absent",
            ASPECT_CAPABILITY_SELECTION,
            _runtime_aspect_score_value(not bool(cap_actual.get("forbidden_capability_realized"))),
        ),
        (
            "selected_capabilities_realized",
            ASPECT_CAPABILITY_SELECTION,
            _runtime_aspect_score_value(not missing_required_capabilities),
        ),
        (
            "dramatic_capability_contract_pass",
            ASPECT_CAPABILITY_SELECTION,
            _runtime_aspect_score_value(_rec(ASPECT_CAPABILITY_SELECTION).get("status") == "passed"),
        ),
        (
            "visible_block_origin_present",
            ASPECT_VISIBLE_PROJECTION,
            _runtime_aspect_score_value(bool(visible_actual.get("visible_block_origin_present"))),
        ),
        (
            "required_visible_origin_preserved",
            ASPECT_VISIBLE_PROJECTION,
            _runtime_aspect_score_value(bool(visible_actual.get("required_visible_origin_preserved"))),
        ),
        (
            "visible_projection_contract_pass",
            ASPECT_VISIBLE_PROJECTION,
            _runtime_aspect_score_value(_rec(ASPECT_VISIBLE_PROJECTION).get("status") == "passed"),
        ),
        (
            "narrative_aspect_policy_present",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(bool(narrative_expected.get("policy_present"))),
        ),
        (
            "narrative_aspect_selected",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(bool(narrative_selected.get("selected_aspects"))),
        ),
        (
            "narrative_aspect_visible_when_required",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(narrative_actual.get("visible_when_required") is not False),
        ),
        (
            "narrative_aspect_contract_pass",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(_rec(ASPECT_NARRATIVE_ASPECT).get("status") in {"passed", "not_applicable"}),
        ),
        (
            "theme_tracking_policy_present",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(bool(narrative_expected.get("theme_tracking_policy_present"))),
        ),
        (
            "theme_tracking_selected",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(bool(selected_theme_aspects)),
        ),
        (
            "theme_semantic_classification_present",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(
                (
                    not bool(narrative_expected.get("semantic_tracking_enabled"))
                    or not selected_theme_aspects
                    or narrative_semantic_classification_count >= len(selected_theme_aspects)
                )
            ),
        ),
        (
            "theme_weak_alignment_absent",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(narrative_semantic_required_weak_alignment_count == 0),
        ),
        (
            "theme_tracking_contract_pass",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(
                _rec(ASPECT_NARRATIVE_ASPECT).get("status") in {"passed", "not_applicable"}
                and narrative_semantic_required_weak_alignment_count == 0
            ),
        ),
        (
            "voice_consistency_policy_present",
            ASPECT_VOICE_CONSISTENCY,
            _runtime_aspect_score_value(bool(voice_expected.get("policy_present"))),
        ),
        (
            "voice_semantic_classification_present",
            ASPECT_VOICE_CONSISTENCY,
            _runtime_aspect_score_value(
                (
                    not bool(voice_expected.get("semantic_classification_enabled"))
                    or voice_spoken_line_count <= 0
                    or voice_semantic_classification_count >= voice_spoken_line_count
                )
            ),
        ),
        (
            "voice_cross_actor_confusion_absent",
            ASPECT_VOICE_CONSISTENCY,
            _runtime_aspect_score_value(voice_cross_actor_count == 0),
        ),
        (
            "voice_forbidden_markers_absent",
            ASPECT_VOICE_CONSISTENCY,
            _runtime_aspect_score_value(voice_forbidden_marker_count == 0),
        ),
        (
            "voice_consistency_contract_pass",
            ASPECT_VOICE_CONSISTENCY,
            _runtime_aspect_score_value(
                _rec(ASPECT_VOICE_CONSISTENCY).get("status")
                in {"passed", "not_applicable"}
            ),
        ),
        (
            "hierarchical_memory_present",
            ASPECT_HIERARCHICAL_MEMORY,
            _runtime_aspect_score_value(bool(memory_actual.get("memory_present"))),
        ),
        (
            "memory_policy_applied",
            ASPECT_HIERARCHICAL_MEMORY,
            _runtime_aspect_score_value(
                (not bool(memory_expected.get("policy_present")))
                or _rec(ASPECT_HIERARCHICAL_MEMORY).get("status") in {"passed", "not_applicable"}
            ),
        ),
        (
            "memory_write_from_committed_turn",
            ASPECT_HIERARCHICAL_MEMORY,
            _runtime_aspect_score_value(not bool(memory_actual.get("uncommitted_write_detected"))),
        ),
        (
            "memory_context_bounded",
            ASPECT_HIERARCHICAL_MEMORY,
            _runtime_aspect_score_value(bool(memory_actual.get("context_bounded")) or not bool(memory_expected.get("policy_present"))),
        ),
        (
            "hierarchical_memory_contract_pass",
            ASPECT_HIERARCHICAL_MEMORY,
            _runtime_aspect_score_value(_rec(ASPECT_HIERARCHICAL_MEMORY).get("status") in {"passed", "not_applicable"}),
        ),
'''
