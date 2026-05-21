"""Langfuse verify source segment: runtime_matrix_relationship_disclosure_variation.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
    vis_actual = _aspect_block(vis_rec, "actual")
    narrative_expected = _aspect_block(narrative_rec, "expected")
    narrative_selected = _aspect_block(narrative_rec, "selected")
    narrative_actual = _aspect_block(narrative_rec, "actual")
    voice_expected = _aspect_block(voice_rec, "expected")
    voice_actual = _aspect_block(voice_rec, "actual")
    tonal_expected = _aspect_block(tonal_rec, "expected")
    tonal_selected = _aspect_block(tonal_rec, "selected")
    tonal_actual = _aspect_block(tonal_rec, "actual")
    memory_selected = _aspect_block(memory_rec, "selected")
    memory_actual = _aspect_block(memory_rec, "actual")
    claim_readiness = assess_npc_agency_claim_readiness(
        runtime_aspect={
            **npc_agency_actual,
            "npc_independent_planning_used": npc_agency_actual.get("independent_planning_used")
            if "independent_planning_used" in npc_agency_actual
            else det_scores.get("npc_independent_planning_used"),
            "npc_forbidden_actor_absent": (
                not bool(npc_agency_actual.get("forbidden_planned_actor_ids"))
                and not bool(npc_agency_actual.get("forbidden_realized_actor_ids"))
            )
            if (
                "forbidden_planned_actor_ids" in npc_agency_actual
                or "forbidden_realized_actor_ids" in npc_agency_actual
            )
            else det_scores.get("npc_forbidden_actor_absent"),
            "long_horizon_state_present": npc_agency_actual.get("long_horizon_state_present")
            if "long_horizon_state_present" in npc_agency_actual
            else det_scores.get("npc_long_horizon_state_present"),
            "private_plan_resolution_present": npc_agency_actual.get("private_plan_resolution_present")
            if "private_plan_resolution_present" in npc_agency_actual
            else det_scores.get("npc_private_plan_resolution_present"),
            "private_plan_visibility_respected": npc_agency_actual.get("private_plan_visibility_respected")
            if "private_plan_visibility_respected" in npc_agency_actual
            else det_scores.get("npc_private_plan_visibility_respected"),
        },
        live_trace_evidence={
            "live_trace_present": str(_extract_metadata(raw_trace).get("trace_origin") or "").strip().lower()
            == "live_ui",
            "non_mock_generation_pass": det_scores.get("non_mock_generation_pass"),
            "fallback_used": not bool(det_scores.get("fallback_absent")),
        },
        mcp_evidence={"runtime_aspect_matrix_present": True},
    )
    voice_drift_counts = (
        voice_actual.get("drift_class_counts")
        if isinstance(voice_actual.get("drift_class_counts"), dict)
        else {}
    )
    voice_cross_actor_count = int(
        voice_actual.get("semantic_cross_actor_confusion_count")
        or voice_drift_counts.get("cross_actor_voice_confusion")
        or 0
    )
    voice_forbidden_marker_count = int(
        voice_drift_counts.get("forbidden_language_marker") or 0
    )
    tonal_target = (
        tonal_selected.get("target")
        if isinstance(tonal_selected.get("target"), dict)
        else tonal_selected
    )
    tonal_failure_codes = tonal_actual.get("failure_codes") or []
    if not isinstance(tonal_failure_codes, list):
        tonal_failure_codes = []
    scene_energy_target = (
        scene_energy_selected.get("target")
        if isinstance(scene_energy_selected.get("target"), dict)
        else scene_energy_selected
    )
    scene_energy_transition = (
        scene_energy_selected.get("transition")
'''
