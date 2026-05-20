SOURCE = r'''\
def _emit_langfuse_runtime_aspect_observability(path_summary: dict[str, Any]) -> None:
    try:
        adapter = LangfuseAdapter.get_instance()
    except Exception:
        logger.debug("Langfuse adapter unavailable for runtime aspect observability", exc_info=True)
        return
    try:
        if not adapter or not adapter.is_enabled():
            return
    except Exception:
        return

    ledger_src = path_summary.get("turn_aspect_ledger")
    ledger_present = bool(
        isinstance(ledger_src, dict)
        and isinstance(ledger_src.get("turn_aspect_ledger"), dict)
    )
    ledger = normalize_runtime_aspect_ledger(ledger_src if isinstance(ledger_src, dict) else {
        "session_id": path_summary.get("session_id"),
        "module_id": path_summary.get("module_id"),
        "turn_number": path_summary.get("turn_number"),
        "turn_kind": path_summary.get("turn_kind"),
        "turn_aspect_ledger": {},
    })
    aspects = ledger.get("turn_aspect_ledger") if isinstance(ledger.get("turn_aspect_ledger"), dict) else {}

    def _rec(aspect: str) -> dict[str, Any]:
        row = aspects.get(aspect)
        return row if isinstance(row, dict) else {}

    def _expected(aspect: str) -> dict[str, Any]:
        row = _rec(aspect).get("expected")
        return row if isinstance(row, dict) else {}

    def _selected(aspect: str) -> dict[str, Any]:
        row = _rec(aspect).get("selected")
        return row if isinstance(row, dict) else {}

    def _actual(aspect: str) -> dict[str, Any]:
        row = _rec(aspect).get("actual")
        return row if isinstance(row, dict) else {}

    def _known(aspect: str) -> bool:
        return str(_rec(aspect).get("status") or "").strip() not in {"", "missing"}

    def _span_level(record: dict[str, Any]) -> str:
        status = str(record.get("status") or "").strip()
        if status == "failed":
            return "ERROR"
        if status in {"partial", "missing"}:
            return "WARNING"
        return "DEFAULT"

    def _span_status(aspect: str, record: dict[str, Any]) -> str:
        reason = str(record.get("failure_reason") or "").strip() or "none"
        return f"aspect={aspect} status={record.get('status') or 'missing'} reason={reason}"

    base_input = {
        "session_id": path_summary.get("session_id"),
        "module_id": path_summary.get("module_id"),
        "runtime_profile_id": ledger.get("runtime_profile_id") or path_summary.get("runtime_profile_id"),
        "turn_number": path_summary.get("turn_number"),
        "turn_kind": path_summary.get("turn_kind"),
        "raw_player_input": path_summary.get("raw_player_input"),
        "canonical_turn_id": path_summary.get("canonical_turn_id"),
        "environment": path_summary.get("environment"),
    }
    narrator_path_selected = bool(path_summary.get("narrator_path_selected")) or (
        str(path_summary.get("director_path_mode") or "").strip() == "narrator_path"
    )
    beat = _rec(ASPECT_BEAT)
    beat_selected = _selected(ASPECT_BEAT)
    beat_actual = _actual(ASPECT_BEAT)
    scene_energy_selected = _selected(ASPECT_SCENE_ENERGY)
    scene_energy_actual = _actual(ASPECT_SCENE_ENERGY)
    pacing_rhythm_selected = _selected(ASPECT_PACING_RHYTHM)
    pacing_rhythm_actual = _actual(ASPECT_PACING_RHYTHM)
    temporal_control_selected = _selected(ASPECT_TEMPORAL_CONTROL)
    temporal_control_actual = _actual(ASPECT_TEMPORAL_CONTROL)
    sensory_context_selected = _selected(ASPECT_SENSORY_CONTEXT)
    sensory_context_actual = _actual(ASPECT_SENSORY_CONTEXT)
    genre_awareness_selected = _selected(ASPECT_GENRE_AWARENESS)
    genre_awareness_actual = _actual(ASPECT_GENRE_AWARENESS)
    tonal_consistency_selected = _selected(ASPECT_TONAL_CONSISTENCY)
    tonal_consistency_actual = _actual(ASPECT_TONAL_CONSISTENCY)
    symbolic_object_selected = _selected(ASPECT_SYMBOLIC_OBJECT_RESONANCE)
    symbolic_object_actual = _actual(ASPECT_SYMBOLIC_OBJECT_RESONANCE)
    social_pressure_selected = _selected(ASPECT_SOCIAL_PRESSURE)
    social_pressure_actual = _actual(ASPECT_SOCIAL_PRESSURE)
    improvisational_selected = _selected(ASPECT_IMPROVISATIONAL_COHERENCE)
    improvisational_actual = _actual(ASPECT_IMPROVISATIONAL_COHERENCE)
    cap_selected = _selected(ASPECT_CAPABILITY_SELECTION)
    disclosure_selected = _selected(ASPECT_INFORMATION_DISCLOSURE)
    disclosure_actual = _actual(ASPECT_INFORMATION_DISCLOSURE)
    expectation_variation_selected = _selected(ASPECT_EXPECTATION_VARIATION)
    expectation_variation_actual = _actual(ASPECT_EXPECTATION_VARIATION)
    narrative_momentum_selected = _selected(ASPECT_NARRATIVE_MOMENTUM)
    narrative_momentum_actual = _actual(ASPECT_NARRATIVE_MOMENTUM)
    dramatic_irony_selected = _selected(ASPECT_DRAMATIC_IRONY)
    dramatic_irony_actual = _actual(ASPECT_DRAMATIC_IRONY)
    narrative_selected = _selected(ASPECT_NARRATIVE_ASPECT)
    narrative_actual = _actual(ASPECT_NARRATIVE_ASPECT)
    memory_selected = _selected(ASPECT_HIERARCHICAL_MEMORY)
    memory_actual = _actual(ASPECT_HIERARCHICAL_MEMORY)
    voice_expected = _expected(ASPECT_VOICE_CONSISTENCY)
    voice_actual = _actual(ASPECT_VOICE_CONSISTENCY)
    span_specs: list[tuple[str, str, dict[str, Any]]] = [
        ("story.aspect.input", ASPECT_INPUT, _rec(ASPECT_INPUT)),
        ("story.action.resolve", ASPECT_ACTION_RESOLUTION, _rec(ASPECT_ACTION_RESOLUTION)),
        (
            "story.affordance.evaluate",
            ASPECT_ACTION_RESOLUTION,
            {
                "affordance_status": _actual(ASPECT_ACTION_RESOLUTION).get("affordance_status"),
                "resolved_target_status": _actual(ASPECT_ACTION_RESOLUTION).get("resolved_target_status"),
                "action_commit_policy": _actual(ASPECT_ACTION_RESOLUTION).get("action_commit_policy"),
                "aspect_record": _rec(ASPECT_ACTION_RESOLUTION),
            },
        ),
        ("story.capability.select", ASPECT_CAPABILITY_SELECTION, _rec(ASPECT_CAPABILITY_SELECTION)),
        (
            "story.capability.realize",
            ASPECT_CAPABILITY_SELECTION,
            {
                "selected": cap_selected,
                "actual": _actual(ASPECT_CAPABILITY_SELECTION),
                "aspect_record": _rec(ASPECT_CAPABILITY_SELECTION),
            },
        ),
        (
            "story.beat.state",
            ASPECT_BEAT,
            {
                "prior_beat_id": _expected(ASPECT_BEAT).get("prior_beat_id"),
                "candidate_beats": _expected(ASPECT_BEAT).get("candidate_beats"),
                "aspect_record": beat,
            },
        ),
        ("story.beat.select", ASPECT_BEAT, {"selected": beat_selected, "aspect_record": beat}),
        ("story.beat.realize", ASPECT_BEAT, {"actual": beat_actual, "aspect_record": beat}),
        (
            "story.scene_energy.target",
            ASPECT_SCENE_ENERGY,
            {
                "selected": scene_energy_selected,
                "aspect_record": _rec(ASPECT_SCENE_ENERGY),
            },
        ),
        (
            "story.scene_energy.validate",
            ASPECT_SCENE_ENERGY,
            {
                "actual": scene_energy_actual,
                "aspect_record": _rec(ASPECT_SCENE_ENERGY),
            },
        ),
        (
            "story.pacing_rhythm.target",
            ASPECT_PACING_RHYTHM,
            {
                "selected": pacing_rhythm_selected,
                "aspect_record": _rec(ASPECT_PACING_RHYTHM),
            },
        ),
        (
            "story.pacing_rhythm.validate",
            ASPECT_PACING_RHYTHM,
            {
                "actual": pacing_rhythm_actual,
                "aspect_record": _rec(ASPECT_PACING_RHYTHM),
            },
        ),
        (
            "story.temporal_control.target",
            ASPECT_TEMPORAL_CONTROL,
            {
                "selected": temporal_control_selected,
                "aspect_record": _rec(ASPECT_TEMPORAL_CONTROL),
            },
        ),
        (
            "story.temporal_control.validate",
            ASPECT_TEMPORAL_CONTROL,
            {
                "actual": temporal_control_actual,
                "aspect_record": _rec(ASPECT_TEMPORAL_CONTROL),
            },
        ),
        (
            "story.sensory_context.target",
            ASPECT_SENSORY_CONTEXT,
            {
                "selected": sensory_context_selected,
                "aspect_record": _rec(ASPECT_SENSORY_CONTEXT),
            },
        ),
        (
            "story.sensory_context.validate",
            ASPECT_SENSORY_CONTEXT,
            {
                "actual": sensory_context_actual,
                "aspect_record": _rec(ASPECT_SENSORY_CONTEXT),
            },
        ),
        (
            "story.genre_awareness.target",
            ASPECT_GENRE_AWARENESS,
            {
                "selected": genre_awareness_selected,
                "aspect_record": _rec(ASPECT_GENRE_AWARENESS),
            },
        ),
        (
            "story.genre_awareness.validate",
            ASPECT_GENRE_AWARENESS,
            {
                "actual": genre_awareness_actual,
                "aspect_record": _rec(ASPECT_GENRE_AWARENESS),
            },
        ),
        (
            "story.tonal_consistency.target",
            ASPECT_TONAL_CONSISTENCY,
            {
                "selected": tonal_consistency_selected,
                "aspect_record": _rec(ASPECT_TONAL_CONSISTENCY),
            },
        ),
        (
            "story.tonal_consistency.validate",
            ASPECT_TONAL_CONSISTENCY,
            {
                "actual": tonal_consistency_actual,
                "aspect_record": _rec(ASPECT_TONAL_CONSISTENCY),
            },
        ),
        (
            "story.symbolic_object_resonance.target",
            ASPECT_SYMBOLIC_OBJECT_RESONANCE,
            {
'''
