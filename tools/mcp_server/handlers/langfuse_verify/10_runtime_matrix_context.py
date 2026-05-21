"""Langfuse verify source segment: runtime_matrix_context.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        ev["adr0041_proof_level"] = merged.get("proof_level")
        ev["adr0041_live_or_staging_claim"] = merged.get("live_or_staging_evidence")
        ev["adr0041_observation_kind"] = merged.get("observation_kind")
        ev["adr0041_langfuse_evidence_contract"] = merged.get("langfuse_evidence_contract")
        pk = out_b.get("projection_keys")
        if isinstance(pk, list):
            ev["adr0041_projection_keys_sample"] = [str(x) for x in pk[:40]]

    if not isinstance(ev.get("npc_actor_ids"), list):
        ev["npc_actor_ids"] = []

    sources = {
        "path_summary_source": path_summary_source,
        "score_source": score_source,
        "status_message_fallback_used": status_message_fallback_used,
        "adr0041_observation_source": (
            "langfuse.observations" if adr_obs else "missing"
        ),
    }
    return ev, sources


def _trace_summary(raw_trace: dict[str, Any]) -> dict[str, Any]:
    metadata = _extract_metadata(raw_trace)
    scores = _extract_scores(raw_trace)
    trace_id = str(raw_trace.get("id") or raw_trace.get("trace_id") or "").strip()
    return {
        "trace_id": trace_id,
        "name": raw_trace.get("name"),
        "timestamp": raw_trace.get("timestamp"),
        "metadata": metadata,
        "scores": scores,
    }


_RUNTIME_ASPECT_MATRIX_COLUMNS: tuple[str, ...] = (
    "session_id",
    "trace_id",
    "canonical_turn_id",
    "environment",
    "turn_number",
    "raw_input",
    "input_kind",
    "action_kind",
    "turn_aspect_ledger_present",
    "beat_selected",
    "selected_beat",
    "beat_realized",
    "scene_energy_target_present",
    "scene_energy_level",
    "scene_energy_transition",
    "scene_energy_contract_pass",
    "scene_energy_transition_allowed",
    "scene_energy_pressure_realized",
    "scene_energy_failure_codes",
    "pacing_rhythm_target_present",
    "pacing_rhythm_cadence",
    "pacing_rhythm_response_shape",
    "pacing_rhythm_contract_pass",
    "pacing_rhythm_density_respected",
    "pacing_rhythm_pause_respected",
    "pacing_rhythm_failure_codes",
    "temporal_control_policy_present",
    "temporal_control_target_selected",
    "temporal_control_operation",
    "temporal_control_recalled_turn_ids",
    "temporal_control_recalled_consequence_ids",
    "temporal_control_event_count",
    "temporal_control_committed_sources_bounded",
    "temporal_control_history_rewrite_absent",
    "temporal_control_contract_pass",
    "temporal_control_failure_codes",
'''
