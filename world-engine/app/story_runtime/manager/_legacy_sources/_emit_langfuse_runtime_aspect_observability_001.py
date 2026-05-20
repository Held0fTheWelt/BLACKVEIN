"""Runtime-aspect observability source chunk 001.

Contributes ordered source lines for legacy Langfuse runtime-aspect observability emission. This chunk is intentionally small and ordered by the legacy manifest.
"""
SOURCE = r'''\
                "selected": symbolic_object_selected,
                "aspect_record": _rec(ASPECT_SYMBOLIC_OBJECT_RESONANCE),
            },
        ),
        (
            "story.symbolic_object_resonance.validate",
            ASPECT_SYMBOLIC_OBJECT_RESONANCE,
            {
                "actual": symbolic_object_actual,
                "aspect_record": _rec(ASPECT_SYMBOLIC_OBJECT_RESONANCE),
            },
        ),
        (
            "story.social_pressure.target",
            ASPECT_SOCIAL_PRESSURE,
            {
                "selected": social_pressure_selected,
                "aspect_record": _rec(ASPECT_SOCIAL_PRESSURE),
            },
        ),
        (
            "story.social_pressure.validate",
            ASPECT_SOCIAL_PRESSURE,
            {
                "actual": social_pressure_actual,
                "aspect_record": _rec(ASPECT_SOCIAL_PRESSURE),
            },
        ),
        (
            "story.improvisational_coherence.target",
            ASPECT_IMPROVISATIONAL_COHERENCE,
            {
                "selected": improvisational_selected,
                "aspect_record": _rec(ASPECT_IMPROVISATIONAL_COHERENCE),
            },
        ),
        (
            "story.improvisational_coherence.validate",
            ASPECT_IMPROVISATIONAL_COHERENCE,
            {
                "actual": improvisational_actual,
                "aspect_record": _rec(ASPECT_IMPROVISATIONAL_COHERENCE),
            },
        ),
        (
            "story.information_disclosure.select",
            ASPECT_INFORMATION_DISCLOSURE,
            {
                "selected": disclosure_selected,
                "aspect_record": _rec(ASPECT_INFORMATION_DISCLOSURE),
            },
        ),
        (
            "story.information_disclosure.validate",
            ASPECT_INFORMATION_DISCLOSURE,
            {
                "actual": disclosure_actual,
                "aspect_record": _rec(ASPECT_INFORMATION_DISCLOSURE),
            },
        ),
        (
            "story.expectation_variation.select",
            ASPECT_EXPECTATION_VARIATION,
            {
                "selected": expectation_variation_selected,
                "aspect_record": _rec(ASPECT_EXPECTATION_VARIATION),
            },
        ),
        (
            "story.expectation_variation.validate",
            ASPECT_EXPECTATION_VARIATION,
            {
                "actual": expectation_variation_actual,
                "aspect_record": _rec(ASPECT_EXPECTATION_VARIATION),
            },
        ),
        (
            "story.narrative_momentum.target",
            ASPECT_NARRATIVE_MOMENTUM,
            {
                "selected": narrative_momentum_selected,
                "aspect_record": _rec(ASPECT_NARRATIVE_MOMENTUM),
            },
        ),
        (
            "story.narrative_momentum.validate",
            ASPECT_NARRATIVE_MOMENTUM,
            {
                "actual": narrative_momentum_actual,
                "aspect_record": _rec(ASPECT_NARRATIVE_MOMENTUM),
            },
        ),
        (
            "story.dramatic_irony.select",
            ASPECT_DRAMATIC_IRONY,
            {
                "selected": dramatic_irony_selected,
                "aspect_record": _rec(ASPECT_DRAMATIC_IRONY),
            },
        ),
        (
            "story.dramatic_irony.validate",
            ASPECT_DRAMATIC_IRONY,
            {
                "actual": dramatic_irony_actual,
                "aspect_record": _rec(ASPECT_DRAMATIC_IRONY),
            },
        ),
        ("story.authority.narrator", ASPECT_NARRATOR_AUTHORITY, _rec(ASPECT_NARRATOR_AUTHORITY)),
        ("story.authority.npc", ASPECT_NPC_AUTHORITY, _rec(ASPECT_NPC_AUTHORITY)),
        (
            "story.npc_agency.plan",
            ASPECT_NPC_AGENCY,
            {
                "expected": _expected(ASPECT_NPC_AGENCY),
                "selected": _selected(ASPECT_NPC_AGENCY),
                "aspect_record": _rec(ASPECT_NPC_AGENCY),
            },
        ),
        (
            "story.npc_agency.realize",
            ASPECT_NPC_AGENCY,
            {
                "actual": _actual(ASPECT_NPC_AGENCY),
                "aspect_record": _rec(ASPECT_NPC_AGENCY),
            },
        ),
        (
            "story.narrative_aspect.select",
            ASPECT_NARRATIVE_ASPECT,
            {"selected": narrative_selected, "aspect_record": _rec(ASPECT_NARRATIVE_ASPECT)},
        ),
        (
            "story.narrative_aspect.validate",
            ASPECT_NARRATIVE_ASPECT,
            {"actual": narrative_actual, "aspect_record": _rec(ASPECT_NARRATIVE_ASPECT)},
        ),
        (
            "story.voice.classify",
            ASPECT_VOICE_CONSISTENCY,
            {
                "expected": voice_expected,
                "actual": voice_actual,
                "aspect_record": _rec(ASPECT_VOICE_CONSISTENCY),
            },
        ),
        (
            "story.voice.validate",
            ASPECT_VOICE_CONSISTENCY,
            {
                "findings": voice_actual.get("findings") or [],
                "semantic_classifications": voice_actual.get("semantic_classifications") or [],
                "aspect_record": _rec(ASPECT_VOICE_CONSISTENCY),
            },
        ),
        (
            "story.memory.write",
            ASPECT_HIERARCHICAL_MEMORY,
            {"selected": memory_selected, "actual": memory_actual, "aspect_record": _rec(ASPECT_HIERARCHICAL_MEMORY)},
        ),
        (
            "story.memory.project",
            ASPECT_HIERARCHICAL_MEMORY,
            {"actual": memory_actual, "aspect_record": _rec(ASPECT_HIERARCHICAL_MEMORY)},
        ),
        ("story.validation.contract", ASPECT_VALIDATION, _rec(ASPECT_VALIDATION)),
        ("story.commit.apply", ASPECT_COMMIT, _rec(ASPECT_COMMIT)),
        ("story.visible.project", ASPECT_VISIBLE_PROJECTION, _rec(ASPECT_VISIBLE_PROJECTION)),
        (
            "story.turn.aspect_summary",
            ASPECT_INPUT,
            {
                "turn_aspect_ledger_present": ledger_present,
                "canonical_turn_id": path_summary.get("canonical_turn_id"),
                "aspect_statuses": {
                    aspect_name: (_rec(aspect_name).get("status") or "missing")
                    for aspect_name in (
                        ASPECT_INPUT,
                        ASPECT_ACTION_RESOLUTION,
                        ASPECT_BEAT,
                        ASPECT_SCENE_ENERGY,
                        ASPECT_PACING_RHYTHM,
                        ASPECT_TEMPORAL_CONTROL,
                        ASPECT_SENSORY_CONTEXT,
                        ASPECT_GENRE_AWARENESS,
                        ASPECT_TONAL_CONSISTENCY,
                        ASPECT_IMPROVISATIONAL_COHERENCE,
                        ASPECT_INFORMATION_DISCLOSURE,
                        ASPECT_EXPECTATION_VARIATION,
                        ASPECT_NARRATIVE_MOMENTUM,
                        ASPECT_CAPABILITY_SELECTION,
                        ASPECT_NARRATOR_AUTHORITY,
                        ASPECT_NPC_AUTHORITY,
                        ASPECT_NPC_AGENCY,
                        ASPECT_NARRATIVE_ASPECT,
                        ASPECT_VOICE_CONSISTENCY,
                        ASPECT_HIERARCHICAL_MEMORY,
                        ASPECT_VALIDATION,
                        ASPECT_COMMIT,
                        ASPECT_VISIBLE_PROJECTION,
                    )
                },
            },
        ),
    ]
    for name, aspect, output in span_specs:
        record = _rec(aspect)
        if narrator_path_selected:
            narrator_path_span_names = {
                "story.aspect.input",
                "story.authority.narrator",
                "story.narrative_aspect.select",
                "story.narrative_aspect.validate",
                "story.validation.contract",
                "story.commit.apply",
                "story.visible.project",
                "story.turn.aspect_summary",
            }
            if name not in narrator_path_span_names:
                continue
        level = _span_level(record)
        status_message = _span_status(aspect, record)
        try:
            span = adapter.create_child_span(
                name=name,
                input=base_input,
                output=output,
                metadata={
                    "phase": "runtime_aspect",
                    "runtime_aspect": aspect,
                    "module_id": path_summary.get("module_id"),
                    "runtime_profile_id": ledger.get("runtime_profile_id") or path_summary.get("runtime_profile_id"),
                    "turn_number": path_summary.get("turn_number"),
                    "session_id": path_summary.get("session_id"),
                    "canonical_turn_id": path_summary.get("canonical_turn_id"),
                    "selected_beat_id": beat_selected.get("selected_beat_id"),
                    "selected_capabilities": cap_selected.get("selected_capabilities") or [],
                    "authority_policy": _expected(ASPECT_NPC_AUTHORITY).get("policy"),
                    "status": record.get("status"),
                    "failure_reason": record.get("failure_reason"),
'''
