SOURCE = r'''\
                    or improvisational_selected.get("acceptance_mode")
                    or improvisational_selected.get("required_anchor_refs")
                )
            ),
        ),
        (
            "improvisational_coherence_acknowledged",
            ASPECT_IMPROVISATIONAL_COHERENCE,
            _runtime_aspect_score_value(
                _rec(ASPECT_IMPROVISATIONAL_COHERENCE).get("status")
                in {"passed", "not_applicable"}
                and "improv_player_contribution_dropped" not in improvisational_failure_codes
            ),
        ),
        (
            "improvisational_coherence_scene_anchor_preserved",
            ASPECT_IMPROVISATIONAL_COHERENCE,
            _runtime_aspect_score_value(
                "improv_scene_anchor_missing" not in improvisational_failure_codes
            ),
        ),
        (
            "improvisational_coherence_contract_pass",
            ASPECT_IMPROVISATIONAL_COHERENCE,
            _runtime_aspect_score_value(
                _rec(ASPECT_IMPROVISATIONAL_COHERENCE).get("status")
                in {"passed", "not_applicable"}
                and improvisational_actual.get("contract_pass") is not False
                and not improvisational_failure_codes
            ),
        ),
        (
            "social_pressure_target_present",
            ASPECT_SOCIAL_PRESSURE,
            _runtime_aspect_score_value(bool(social_pressure_target)),
        ),
        (
            "social_pressure_contract_pass",
            ASPECT_SOCIAL_PRESSURE,
            _runtime_aspect_score_value(
                _rec(ASPECT_SOCIAL_PRESSURE).get("status") in {"passed", "not_applicable"}
            ),
        ),
        (
            "social_pressure_metric_bounded",
            ASPECT_SOCIAL_PRESSURE,
            _runtime_aspect_score_value(
                "social_pressure_score_out_of_bounds" not in social_pressure_failure_codes
            ),
        ),
        (
            "information_disclosure_policy_present",
            ASPECT_INFORMATION_DISCLOSURE,
            _runtime_aspect_score_value(
                bool(_expected(ASPECT_INFORMATION_DISCLOSURE).get("policy_present"))
            ),
        ),
        (
            "information_disclosure_target_selected",
            ASPECT_INFORMATION_DISCLOSURE,
            _runtime_aspect_score_value(bool(disclosure_selected.get("selected_unit_ids"))),
        ),
        (
            "information_disclosure_budget_pass",
            ASPECT_INFORMATION_DISCLOSURE,
            _runtime_aspect_score_value(
                "information_disclosure_over_budget" not in disclosure_failure_codes
            ),
        ),
        (
            "information_disclosure_premature_reveal_absent",
            ASPECT_INFORMATION_DISCLOSURE,
            _runtime_aspect_score_value(
                "information_disclosure_forbidden_unit" not in disclosure_failure_codes
            ),
        ),
        (
            "information_disclosure_contract_pass",
            ASPECT_INFORMATION_DISCLOSURE,
            _runtime_aspect_score_value(
                _rec(ASPECT_INFORMATION_DISCLOSURE).get("status")
                in {"passed", "not_applicable"}
                and disclosure_actual.get("contract_pass") is not False
                and not disclosure_failure_codes
            ),
        ),
        (
            "expectation_variation_policy_present",
            ASPECT_EXPECTATION_VARIATION,
            _runtime_aspect_score_value(
                bool(_expected(ASPECT_EXPECTATION_VARIATION).get("policy_present"))
            ),
        ),
        (
            "expectation_variation_target_selected",
            ASPECT_EXPECTATION_VARIATION,
            _runtime_aspect_score_value(
                bool(expectation_variation_selected.get("selected_variation_ids"))
            ),
        ),
        (
            "expectation_variation_budget_pass",
            ASPECT_EXPECTATION_VARIATION,
            _runtime_aspect_score_value(
                "expectation_variation_over_budget"
                not in expectation_variation_failure_codes
            ),
        ),
        (
            "expectation_variation_setup_supported",
            ASPECT_EXPECTATION_VARIATION,
            _runtime_aspect_score_value(
                "expectation_variation_unearned_event"
                not in expectation_variation_failure_codes
                and "expectation_variation_target_mismatch"
                not in expectation_variation_failure_codes
            ),
        ),
        (
            "expectation_variation_contract_pass",
            ASPECT_EXPECTATION_VARIATION,
            _runtime_aspect_score_value(
                _rec(ASPECT_EXPECTATION_VARIATION).get("status")
                in {"passed", "not_applicable"}
                and expectation_variation_actual.get("contract_pass") is not False
                and not expectation_variation_failure_codes
            ),
        ),
        (
            "narrative_momentum_policy_present",
            ASPECT_NARRATIVE_MOMENTUM,
            _runtime_aspect_score_value(
                bool(_expected(ASPECT_NARRATIVE_MOMENTUM).get("policy_present"))
            ),
        ),
        (
            "narrative_momentum_target_selected",
            ASPECT_NARRATIVE_MOMENTUM,
            _runtime_aspect_score_value(bool(narrative_momentum_target.get("target_state"))),
        ),
        (
            "narrative_momentum_transition_allowed",
            ASPECT_NARRATIVE_MOMENTUM,
            _runtime_aspect_score_value(
                narrative_momentum_actual.get("transition_allowed") is not False
                and "narrative_momentum_transition_forbidden"
                not in narrative_momentum_failure_codes
            ),
        ),
        (
            "narrative_momentum_progress_event_present",
            ASPECT_NARRATIVE_MOMENTUM,
            _runtime_aspect_score_value(
                narrative_momentum_progress_event_count
                >= narrative_momentum_min_progress_event_count
            ),
        ),
        (
            "narrative_momentum_stall_budget_respected",
            ASPECT_NARRATIVE_MOMENTUM,
            _runtime_aspect_score_value(
                narrative_momentum_actual.get("stall_budget_respected") is not False
                and "narrative_momentum_stall_budget_exceeded"
                not in narrative_momentum_failure_codes
            ),
        ),
        (
            "narrative_momentum_contract_pass",
            ASPECT_NARRATIVE_MOMENTUM,
            _runtime_aspect_score_value(
                _rec(ASPECT_NARRATIVE_MOMENTUM).get("status")
                in {"passed", "not_applicable"}
                and narrative_momentum_actual.get("contract_pass") is not False
                and not narrative_momentum_failure_codes
            ),
        ),
        (
            "dramatic_irony_policy_present",
            ASPECT_DRAMATIC_IRONY,
            _runtime_aspect_score_value(bool(dramatic_irony_expected.get("policy_present"))),
        ),
        (
            "dramatic_irony_opportunity_present",
            ASPECT_DRAMATIC_IRONY,
            _runtime_aspect_score_value(bool(dramatic_irony_actual.get("opportunity_count"))),
        ),
        (
            "dramatic_irony_contract_pass",
            ASPECT_DRAMATIC_IRONY,
            _runtime_aspect_score_value(
                _rec(ASPECT_DRAMATIC_IRONY).get("status")
                in {"passed", "not_applicable"}
                and dramatic_irony_actual.get("contract_pass") is not False
                and not dramatic_irony_violation_codes
            ),
        ),
        (
            "narrator_authority_contract_present",
            ASPECT_NARRATOR_AUTHORITY,
            _runtime_aspect_score_value(_known(ASPECT_NARRATOR_AUTHORITY)),
        ),
        (
            "narrator_required_when_expected",
            ASPECT_NARRATOR_AUTHORITY,
            _runtime_aspect_score_value((not action_requires_narrator) or narrator_required),
        ),
        (
            "narrator_owns_consequence",
            ASPECT_NARRATOR_AUTHORITY,
            _runtime_aspect_score_value(
                (not narrator_required)
                or (
                    _rec(ASPECT_NARRATOR_AUTHORITY).get("status") == "passed"
                    and narrator_actual.get("actual_owner") == "narrator"
                    and narrator_actual.get("consequence_realized") is True
                )
            ),
        ),
        (
            "narrator_consequence_present",
            ASPECT_NARRATOR_AUTHORITY,
            _runtime_aspect_score_value((not narrator_required) or narrator_actual.get("consequence_realized") is True),
        ),
        (
            "narrator_authority_contract_pass",
            ASPECT_NARRATOR_AUTHORITY,
            _runtime_aspect_score_value(_rec(ASPECT_NARRATOR_AUTHORITY).get("status") == "passed"),
        ),
        (
            "npc_authority_contract_present",
            ASPECT_NPC_AUTHORITY,
            _runtime_aspect_score_value(_known(ASPECT_NPC_AUTHORITY)),
        ),
        (
            "npc_takeover_absent",
            ASPECT_NPC_AUTHORITY,
            _runtime_aspect_score_value(not bool(npc_actual.get("npc_takeover_detected"))),
        ),
        (
            "npc_policy_realized",
'''
