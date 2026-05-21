"""Langfuse verify source segment: runtime_matrix_momentum_irony_callbacks.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        if isinstance(scene_energy_selected.get("transition"), dict)
        else {}
    )
    scene_energy_failure_codes = scene_energy_actual.get("failure_codes") or []
    if not isinstance(scene_energy_failure_codes, list):
        scene_energy_failure_codes = []
    pacing_rhythm_target = (
        pacing_rhythm_selected.get("target")
        if isinstance(pacing_rhythm_selected.get("target"), dict)
        else pacing_rhythm_selected
    )
    pacing_rhythm_failure_codes = pacing_rhythm_actual.get("failure_codes") or []
    if not isinstance(pacing_rhythm_failure_codes, list):
        pacing_rhythm_failure_codes = []
    temporal_control_target = (
        temporal_control_selected.get("target")
        if isinstance(temporal_control_selected.get("target"), dict)
        else temporal_control_selected
    )
    temporal_control_failure_codes = temporal_control_actual.get("failure_codes") or []
    if not isinstance(temporal_control_failure_codes, list):
        temporal_control_failure_codes = []
    sensory_context_target = (
        sensory_context_selected.get("target")
        if isinstance(sensory_context_selected.get("target"), dict)
        else sensory_context_selected
    )
    sensory_context_failure_codes = sensory_context_actual.get("failure_codes") or []
    if not isinstance(sensory_context_failure_codes, list):
        sensory_context_failure_codes = []
    genre_awareness_target = (
        genre_awareness_selected.get("target")
        if isinstance(genre_awareness_selected.get("target"), dict)
        else genre_awareness_selected
    )
    genre_awareness_failure_codes = genre_awareness_actual.get("failure_codes") or []
    if not isinstance(genre_awareness_failure_codes, list):
        genre_awareness_failure_codes = []
    symbolic_object_target = (
        symbolic_object_selected.get("target")
        if isinstance(symbolic_object_selected.get("target"), dict)
        else symbolic_object_selected
    )
    symbolic_object_failure_codes = symbolic_object_actual.get("failure_codes") or []
    if not isinstance(symbolic_object_failure_codes, list):
        symbolic_object_failure_codes = []
    improvisational_failure_codes = improvisational_actual.get("failure_codes") or []
    if not isinstance(improvisational_failure_codes, list):
        improvisational_failure_codes = []
    social_pressure_target = (
        social_pressure_selected.get("target")
        if isinstance(social_pressure_selected.get("target"), dict)
        else social_pressure_selected
    )
    social_pressure_failure_codes = social_pressure_actual.get("failure_codes") or []
    if not isinstance(social_pressure_failure_codes, list):
        social_pressure_failure_codes = []
    relationship_state_target = (
        relationship_state_selected.get("target")
        if isinstance(relationship_state_selected.get("target"), dict)
        else relationship_state_selected
    )
    relationship_state_failure_codes = relationship_state_actual.get("failure_codes") or []
    if not isinstance(relationship_state_failure_codes, list):
        relationship_state_failure_codes = []
    disclosure_failure_codes = disclosure_actual.get("failure_codes") or []
    if not isinstance(disclosure_failure_codes, list):
        disclosure_failure_codes = []
    expectation_variation_failure_codes = (
        expectation_variation_actual.get("failure_codes") or []
    )
    if not isinstance(expectation_variation_failure_codes, list):
'''
