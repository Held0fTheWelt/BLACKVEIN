"""Langfuse verify source segment: runtime_matrix_authority_agency_capabilities.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        expectation_variation_failure_codes = []
    narrative_momentum_target = (
        narrative_momentum_selected.get("target")
        if isinstance(narrative_momentum_selected.get("target"), dict)
        else narrative_momentum_selected
    )
    narrative_momentum_failure_codes = narrative_momentum_actual.get("failure_codes") or []
    if not isinstance(narrative_momentum_failure_codes, list):
        narrative_momentum_failure_codes = []
    try:
        narrative_momentum_progress_event_count = int(
            narrative_momentum_actual.get("progress_event_count") or 0
        )
    except (TypeError, ValueError):
        narrative_momentum_progress_event_count = 0
    try:
        narrative_momentum_min_progress_event_count = int(
            narrative_momentum_target.get("min_progress_event_count") or 0
        )
    except (TypeError, ValueError):
        narrative_momentum_min_progress_event_count = 0
    dramatic_irony_violation_codes = dramatic_irony_actual.get("violation_codes") or []
    if not isinstance(dramatic_irony_violation_codes, list):
        dramatic_irony_violation_codes = []
    callback_failure_codes = callback_actual.get("failure_codes") or []
    if not isinstance(callback_failure_codes, list):
        callback_failure_codes = []
    cascade_failure_codes = cascade_actual.get("failure_codes") or []
    if not isinstance(cascade_failure_codes, list):
        cascade_failure_codes = []
    failed_records = [
        r
        for r in (
            narr_rec,
            npc_rec,
            npc_agency_rec,
            cap_rec,
            beat_rec,
            scene_energy_rec,
            pacing_rhythm_rec,
            temporal_control_rec,
            sensory_context_rec,
            genre_awareness_rec,
            symbolic_object_rec,
            improvisational_rec,
            social_pressure_rec,
            relationship_state_rec,
            disclosure_rec,
            expectation_variation_rec,
            narrative_momentum_rec,
            dramatic_irony_rec,
            callback_rec,
            cascade_rec,
            vis_rec,
            narrative_rec,
            voice_rec,
            tonal_rec,
            memory_rec,
        )
        if r.get("status") == "failed"
    ]
    partial_records = [
        r
        for r in (
            beat_rec,
            scene_energy_rec,
            pacing_rhythm_rec,
            temporal_control_rec,
            sensory_context_rec,
            genre_awareness_rec,
            symbolic_object_rec,
            improvisational_rec,
'''
