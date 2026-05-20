SOURCE = r'''\
                    "trace_origin": path_summary.get("trace_origin"),
                    "execution_tier": path_summary.get("execution_tier"),
                    "canonical_player_flow": path_summary.get("canonical_player_flow"),
                },
                level=level,
                status_message=status_message,
            )
        except Exception:
            logger.debug("Langfuse runtime aspect span creation failed for %s", name, exc_info=True)
            continue
        _finish_langfuse_span(span, output=output, level=level, status_message=status_message)

    input_actual = _actual(ASPECT_INPUT)
    action_actual = _actual(ASPECT_ACTION_RESOLUTION)
    narrator_expected = _expected(ASPECT_NARRATOR_AUTHORITY)
    narrator_actual = _actual(ASPECT_NARRATOR_AUTHORITY)
    npc_actual = _actual(ASPECT_NPC_AUTHORITY)
    npc_agency_actual = _actual(ASPECT_NPC_AGENCY)
    dramatic_irony_expected = _expected(ASPECT_DRAMATIC_IRONY)
    dramatic_irony_actual = _actual(ASPECT_DRAMATIC_IRONY)
    cap_actual = _actual(ASPECT_CAPABILITY_SELECTION)
    visible_actual = _actual(ASPECT_VISIBLE_PROJECTION)
    narrative_expected = _expected(ASPECT_NARRATIVE_ASPECT)
    memory_expected = _expected(ASPECT_HIERARCHICAL_MEMORY)
    voice_expected = _expected(ASPECT_VOICE_CONSISTENCY)
    voice_actual = _actual(ASPECT_VOICE_CONSISTENCY)
    validation_actual = _actual(ASPECT_VALIDATION)
    beat_transition_allowed = _selected(ASPECT_BEAT).get("transition_allowed")
    scene_energy_target = (
        scene_energy_selected.get("target")
        if isinstance(scene_energy_selected.get("target"), dict)
        else scene_energy_selected
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
    tonal_consistency_target = (
        tonal_consistency_selected.get("target")
        if isinstance(tonal_consistency_selected.get("target"), dict)
        else tonal_consistency_selected
    )
    tonal_consistency_failure_codes = tonal_consistency_actual.get("failure_codes") or []
    if not isinstance(tonal_consistency_failure_codes, list):
        tonal_consistency_failure_codes = []
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
    disclosure_failure_codes = disclosure_actual.get("failure_codes") or []
    if not isinstance(disclosure_failure_codes, list):
        disclosure_failure_codes = []
    expectation_variation_failure_codes = (
        expectation_variation_actual.get("failure_codes") or []
    )
    if not isinstance(expectation_variation_failure_codes, list):
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
    npc_failure_reason = str(_rec(ASPECT_NPC_AUTHORITY).get("failure_reason") or "")
    violated_capabilities = cap_actual.get("violated_capabilities") or []
    if not isinstance(violated_capabilities, list):
        violated_capabilities = []
    turn_number = int(path_summary.get("turn_number") or ledger.get("turn_number") or 0)
    input_kind = str(
        action_actual.get("input_kind")
        or input_actual.get("player_input_kind")
        or input_actual.get("input_kind")
        or ""
    ).strip().lower()
    action_requires_narrator = turn_number > 0 and input_kind in {
        "action",
        "perception",
        "mixed",
        "movement_action",
        "perception_action",
    }
    narrator_required = bool(narrator_expected.get("required"))
    missing_required_capabilities = cap_actual.get("missing_required_capabilities") or []
    if not isinstance(missing_required_capabilities, list):
        missing_required_capabilities = []
    selected_theme_aspects = narrative_actual.get("selected_theme_aspects") or []
    if not isinstance(selected_theme_aspects, list):
        selected_theme_aspects = []
    narrative_semantic_classification_count = int(
        narrative_actual.get("semantic_classification_count") or 0
    )
    narrative_semantic_required_weak_alignment_count = int(
        narrative_actual.get("semantic_required_weak_alignment_count") or 0
    )
    voice_spoken_line_count = int(voice_actual.get("spoken_line_count") or 0)
    voice_semantic_classification_count = int(
        voice_actual.get("semantic_classification_count") or 0
    )
    voice_drift_counts = (
        voice_actual.get("drift_class_counts")
        if isinstance(voice_actual.get("drift_class_counts"), dict)
        else {}
    )
    voice_forbidden_marker_count = int(
        voice_drift_counts.get("forbidden_language_marker") or 0
    )
    voice_cross_actor_count = int(
        voice_actual.get("semantic_cross_actor_confusion_count")
        or voice_drift_counts.get("cross_actor_voice_confusion")
        or 0
    )
    recoverable_turn = bool(validation_actual.get("recoverable_rejection")) or str(
        path_summary.get("turn_status") or ""
    ).strip().lower() in {"rejected_recoverable", "player_rejected_recoverable"}
    http_status = int(path_summary.get("http_status") or 200)
    visible_output_for_recovery = bool(
        visible_actual.get("visible_output_present")
        or visible_actual.get("visible_block_origin_present")
        or int(visible_actual.get("scene_block_count") or 0) > 0
    )
    scores: list[tuple[str, str, float]] = [
        ("turn_aspect_ledger_present", ASPECT_INPUT, _runtime_aspect_score_value(ledger_present)),
        (
            "beat_selected",
            ASPECT_BEAT,
            _runtime_aspect_score_value(bool(beat_selected.get("selected_beat_id") or beat_selected.get("selected_scene_function"))),
        ),
        ("beat_realized", ASPECT_BEAT, _runtime_aspect_score_value(beat_actual.get("realized") is True)),
        (
            "beat_realization_visible",
            ASPECT_BEAT,
            _runtime_aspect_score_value(beat_actual.get("realized") is True and beat_actual.get("visible") is True),
        ),
        (
            "beat_transition_valid",
            ASPECT_BEAT,
            _runtime_aspect_score_value(beat_transition_allowed is not False),
        ),
        (
            "beat_contract_pass",
            ASPECT_BEAT,
            _runtime_aspect_score_value(_rec(ASPECT_BEAT).get("status") == "passed"),
        ),
        (
            "scene_energy_target_present",
            ASPECT_SCENE_ENERGY,
            _runtime_aspect_score_value(bool(scene_energy_target)),
        ),
        (
            "scene_energy_contract_pass",
            ASPECT_SCENE_ENERGY,
            _runtime_aspect_score_value(
                _rec(ASPECT_SCENE_ENERGY).get("status") in {"passed", "not_applicable"}
            ),
        ),
        (
            "scene_energy_transition_allowed",
            ASPECT_SCENE_ENERGY,
            _runtime_aspect_score_value(scene_energy_actual.get("transition_allowed") is not False),
        ),
        (
            "scene_energy_pressure_realized",
            ASPECT_SCENE_ENERGY,
            _runtime_aspect_score_value(
                "scene_energy_missing_required_pressure" not in scene_energy_failure_codes
            ),
        ),
        (
            "pacing_rhythm_target_present",
            ASPECT_PACING_RHYTHM,
            _runtime_aspect_score_value(bool(pacing_rhythm_target)),
        ),
        (
            "pacing_rhythm_contract_pass",
            ASPECT_PACING_RHYTHM,
            _runtime_aspect_score_value(
                _rec(ASPECT_PACING_RHYTHM).get("status") in {"passed", "not_applicable"}
'''
