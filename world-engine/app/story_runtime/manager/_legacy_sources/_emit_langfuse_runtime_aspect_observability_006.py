SOURCE = r'''\
        (
            "recoverable_turn_http_200",
            ASPECT_VALIDATION,
            _runtime_aspect_score_value((not recoverable_turn) or http_status == 200),
        ),
        (
            "recoverable_turn_visible_output_present",
            ASPECT_VISIBLE_PROJECTION,
            _runtime_aspect_score_value((not recoverable_turn) or visible_output_for_recovery),
        ),
    ]
    if narrator_path_selected:
        narrator_path_score_names = {
            "turn_aspect_ledger_present",
            "narrator_authority_contract_present",
            "narrator_required_when_expected",
            "narrator_owns_consequence",
            "narrator_consequence_present",
            "narrator_authority_contract_pass",
            "visible_block_origin_present",
            "required_visible_origin_preserved",
            "visible_projection_contract_pass",
            "narrative_aspect_policy_present",
            "narrative_aspect_selected",
            "narrative_aspect_visible_when_required",
            "narrative_aspect_contract_pass",
            "theme_tracking_policy_present",
            "theme_tracking_selected",
            "theme_semantic_classification_present",
            "theme_weak_alignment_absent",
            "theme_tracking_contract_pass",
            "recoverable_turn_http_200",
            "recoverable_turn_visible_output_present",
        }
        scores = [row for row in scores if row[0] in narrator_path_score_names]
    for score_name, aspect_name, score_value in scores:
        try:
            adapter.add_score(
                name=score_name,
                value=score_value,
                comment="deterministic runtime aspect evidence",
                metadata=_runtime_aspect_score_metadata(
                    ledger=ledger,
                    aspect_name=aspect_name,
                    score_name=score_name,
                    value=score_value,
                    path_summary=path_summary,
                ),
            )
        except Exception:
            logger.debug("Langfuse runtime aspect score write failed for %s", score_name, exc_info=True)
    branching_forecast = (
        path_summary.get("branching_forecast")
        if isinstance(path_summary.get("branching_forecast"), dict)
        else {}
    )
    if branching_forecast and not narrator_path_selected:
        branch_status = str(branching_forecast.get("status") or "").strip()
        branch_option_count = int(branching_forecast.get("option_count") or 0)
        branch_meta = {
            "branching_forecast_score": True,
            "aspect_name": "branching_forecast",
            "session_id": path_summary.get("session_id"),
            "module_id": path_summary.get("module_id"),
            "runtime_profile_id": path_summary.get("runtime_profile_id"),
            "turn_number": path_summary.get("turn_number"),
            "turn_kind": path_summary.get("turn_kind"),
            "canonical_turn_id": path_summary.get("canonical_turn_id"),
            "status": branch_status,
            "forecast_only": bool(branching_forecast.get("forecast_only")),
            "authoritative": bool(branching_forecast.get("authoritative")),
            "inactive_branches_authoritative": bool(
                branching_forecast.get("inactive_branches_authoritative")
            ),
            "mutates_canonical_state": bool(branching_forecast.get("mutates_canonical_state")),
            "trigger_reasons": list(branching_forecast.get("trigger_reasons") or []),
            "option_count": branch_option_count,
            "environment": path_summary.get("environment"),
        }
        branch_scores = [
            ("branching_forecast_present", _runtime_aspect_score_value(bool(branching_forecast))),
            ("branch_options_count", float(branch_option_count)),
            (
                "inactive_branches_non_authoritative",
                _runtime_aspect_score_value(
                    branching_forecast.get("forecast_only") is True
                    and branching_forecast.get("authoritative") is False
                    and branching_forecast.get("inactive_branches_authoritative") is False
                    and branching_forecast.get("mutates_canonical_state") is False
                ),
            ),
        ]
        for score_name, score_value in branch_scores:
            try:
                adapter.add_score(
                    name=score_name,
                    value=score_value,
                    comment="deterministic branching forecast evidence",
                    metadata={**branch_meta, "score_name": score_name, "score_value": score_value},
                )
            except Exception:
                logger.debug("Langfuse branching forecast score write failed for %s", score_name, exc_info=True)
'''
