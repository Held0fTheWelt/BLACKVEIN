"""Langfuse verify source segment: runtime_matrix_time_sensory_genre.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
    if aspect_obs:
        for block_key in ("output", "input", "metadata"):
            block = _coerce_dict_or_json(aspect_obs.get(block_key))
            ledger = block.get("turn_aspect_ledger") if isinstance(block, dict) else None
            if isinstance(ledger, dict) and isinstance(ledger.get("turn_aspect_ledger"), dict):
                return ledger
    return {}


def _aspect_record(ledger: dict[str, Any], aspect_name: str) -> dict[str, Any]:
    aspects = ledger.get("turn_aspect_ledger") if isinstance(ledger.get("turn_aspect_ledger"), dict) else {}
    row = aspects.get(aspect_name) if isinstance(aspects, dict) else {}
    return row if isinstance(row, dict) else {}


def _aspect_block(record: dict[str, Any], block_name: str) -> dict[str, Any]:
    block = record.get(block_name) if isinstance(record, dict) else {}
    return block if isinstance(block, dict) else {}


def _runtime_aspect_recommended_repair(main_failure: str | None) -> str | None:
    failure = str(main_failure or "").strip()
    if not failure:
        return None
    if "npc_execut" in failure:
        return "repair_npc_authority_prevent_execute_player_action"
    if "npc_narrat" in failure:
        return "repair_npc_authority_prevent_player_perception_narration"
    if "narrator_required" in failure:
        return "repair_narrator_authority_required_consequence"
    if "forbidden_capability" in failure:
        return "repair_capability_selection_block_forbidden_realization"
    if "voice" in failure or "cross_actor_voice" in failure:
        return "repair_voice_consistency_follow_character_profiles"
    if failure.startswith("tonal_consistency_"):
        return "repair_tonal_consistency_follow_policy_target"
    if failure.startswith("callback_"):
        return "repair_callback_web_bounded_committed_evidence"
    if failure.startswith("consequence_cascade_"):
        return "repair_consequence_cascade_bounded_committed_evidence"
    if failure.startswith("scene_energy_"):
        return "repair_scene_energy_structured_realization"
    if failure.startswith("genre_awareness_"):
        return "repair_genre_awareness_structured_events"
    if failure.startswith("symbolic_object_resonance_"):
        return "repair_symbolic_object_resonance_structured_selection"
    if failure.startswith("temporal_control_"):
        return "repair_temporal_control_bounded_committed_refs"
    if failure.startswith("improv_") or failure.startswith("improvisational_coherence_"):
        return "repair_improvisational_coherence_structured_acceptance"
    if failure.startswith("expectation_variation_"):
        return "repair_expectation_variation_structured_selection"
    if failure.startswith("narrative_momentum_"):
        return "repair_narrative_momentum_state_machine"
    if "beat" in failure:
        return "repair_beat_realization_or_contract_classification"
    if "origin" in failure or "projection" in failure:
        return "repair_visible_projection_origin_metadata"
    return "inspect_runtime_aspect_ledger"


def _runtime_aspect_matrix_row(raw_trace: dict[str, Any]) -> dict[str, Any]:
    path_summary = _extract_path_summary_from_trace(raw_trace)
    ledger = _extract_runtime_aspect_ledger_from_trace(raw_trace)
    det_scores, _judge = _extract_scores_split(raw_trace)
    input_rec = _aspect_record(ledger, "input")
    action_rec = _aspect_record(ledger, "action_resolution")
    beat_rec = _aspect_record(ledger, "beat")
    scene_energy_rec = _aspect_record(ledger, "scene_energy")
    pacing_rhythm_rec = _aspect_record(ledger, "pacing_rhythm")
    temporal_control_rec = _aspect_record(ledger, "temporal_control")
    sensory_context_rec = _aspect_record(ledger, "sensory_context")
'''
