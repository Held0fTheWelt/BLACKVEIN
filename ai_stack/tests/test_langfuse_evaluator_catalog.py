"""Tests for canonical Langfuse categorical evaluator catalog (docs/llm-as-a-judge mirror)."""

from ai_stack.langfuse_evaluator_catalog import (
    BACKEND_TURN_ROOT_TRACE_NAME,
    GATE_OVERRIDE_WARNING,
    JUDGE_TO_REPAIR_CARD,
    LLM_AS_A_JUDGE_DOC_RELATIVE_PATH,
    MATRIX_JUDGE_COLUMN_KEYS,
    WORLD_ENGINE_TURN_TRACE_NAME,
    WOS_CATEGORICAL_JUDGES_ORDER,
    build_llm_judge_interpretation,
    category_severity,
    doc_table_evaluator_names,
    get_categorical_evaluator_spec,
    judge_names_for_scope,
    normalize_judge_category_label,
)


def test_doc_table_names_match_order_length():
    assert len(doc_table_evaluator_names()) == len(WOS_CATEGORICAL_JUDGES_ORDER)
    assert doc_table_evaluator_names() == WOS_CATEGORICAL_JUDGES_ORDER


def test_new_runtime_and_authority_judges_recognized():
    for name in (
        "runtime_aspect_integrity_judge",
        "narrator_authority_judge",
        "npc_authority_violation_judge",
        "dramatic_capability_realization_judge",
        "beat_realization_judge",
        "visible_origin_consistency_judge",
        "recoverable_outcome_quality_judge",
        "relationship_pressure_judge",
        "player_turn_playability_judge",
    ):
        spec = get_categorical_evaluator_spec(name)
        assert spec is not None, name
        assert spec.qualitative_only is True
        assert spec.runtime_gate is False
        assert spec.replaces_deterministic_gates is False


def test_category_severity_buckets():
    assert category_severity("runtime_aspect_integrity_judge", "incomplete") == "failure"
    assert category_severity("runtime_aspect_integrity_judge", "complete") == "positive"
    assert category_severity("runtime_aspect_integrity_judge", "not_applicable") == "neutral"
    assert category_severity("narrator_authority_judge", "violated") == "failure"
    assert category_severity("beat_realization_judge", "weak_realization") == "failure"
    assert category_severity("dramatic_capability_realization_judge", "violated_or_missing") == "failure"
    assert category_severity("visible_origin_consistency_judge", "contradictory") == "failure"
    assert category_severity("recoverable_outcome_quality_judge", "failed_recovery") == "failure"
    assert category_severity("relationship_pressure_judge", "missing_or_wrong") == "failure"
    assert category_severity("player_turn_playability_judge", "unplayable") == "failure"


def test_legacy_category_normalization_maps_stale_labels():
    assert normalize_judge_category_label("theatrical_style_judge", "alive_style") == "theatrical"
    assert normalize_judge_category_label("rag_context_usefulness_judge", "weak_use") == "unused"
    assert normalize_judge_category_label("narrator_npc_boundary_judge", "healthy_boundary") == "clean_boundary"


def test_player_action_resolution_judge_catalog_entry():
    spec = get_categorical_evaluator_spec("player_action_resolution_judge")
    assert spec is not None
    assert spec.score_type == "categorical"
    assert spec.categories == ("resolved_well", "partially_resolved", "misresolved", "not_resolved")
    assert spec.allow_multiple_matches is False
    assert spec.qualitative_only is True
    assert spec.runtime_gate is False
    assert spec.replaces_deterministic_gates is False
    assert "qualitative review signal only" in spec.prompt.lower()
    assert spec.issue_categories == frozenset({"partially_resolved", "misresolved", "not_resolved"})
    assert spec.repair_card == "TURN-ACTION-RESOLUTION-01"
    assert spec.matrix_column_key == "player_action_resolution_category"
    assert "ADR-0033" in GATE_OVERRIDE_WARNING or "actor_lane_safety_pass" in GATE_OVERRIDE_WARNING
    assert spec.langfuse_observation_filters["Name"] == ["story.model.generation"]
    assert spec.trace_metadata_filters.get("opening_turn") is False
    assert spec.langfuse_observation_filters["Trace Name"] == [WORLD_ENGINE_TURN_TRACE_NAME]
    assert spec.legacy_trace_names == (BACKEND_TURN_ROOT_TRACE_NAME,)


def test_opening_judge_langfuse_filters_match_opening_trace():
    spec = get_categorical_evaluator_spec("opening_experience_judge")
    assert spec is not None
    assert spec.langfuse_observation_filters["Trace Name"] == ["world-engine.session.create"]
    assert spec.langfuse_observation_filters["Name"] == ["story.model.generation"]
    assert spec.trace_metadata_filters["opening_turn"] is True
    assert spec.trace_metadata_filters["turn_number"] == 0
    assert spec.legacy_trace_names == ("world-engine.session.create",)


def test_player_action_resolution_judge_in_order_and_maps():
    assert "player_action_resolution_judge" in WOS_CATEGORICAL_JUDGES_ORDER
    assert JUDGE_TO_REPAIR_CARD["player_action_resolution_judge"] == "TURN-ACTION-RESOLUTION-01"
    assert MATRIX_JUDGE_COLUMN_KEYS["player_action_resolution_judge"] == "player_action_resolution_category"


def test_turn_scope_includes_all_turn_generation_judges():
    turn_names = judge_names_for_scope("turn_generation")
    assert "beat_realization_judge" in turn_names
    assert "opening_experience_judge" not in turn_names


def test_build_llm_judge_interpretation_includes_operator_fields():
    interp = build_llm_judge_interpretation(
        {
            "runtime_aspect_integrity_judge": {
                "value": 0.0,
                "category": "incomplete",
                "reasoning": "missing ledger slices",
            }
        },
        trace_context="world-engine.turn.execute",
    )
    assert len(interp) == 1
    row = interp[0]
    assert row["evaluator"] == "runtime_aspect_integrity_judge"
    assert row["category"] == "incomplete"
    assert row["category_severity"] == "failure"
    assert row["evaluator_group"] == "runtime_aspect_integrity"
    assert row["trace_context"] == "world-engine.turn.execute"


def test_canonical_doc_path_constant_points_at_csv_table():
    assert LLM_AS_A_JUDGE_DOC_RELATIVE_PATH.endswith(".csv")
    assert "llm-as-a-judge" in LLM_AS_A_JUDGE_DOC_RELATIVE_PATH


def test_local_langfuse_judge_transfer_bundle_retargets_filters_to_local():
    from ai_stack.langfuse_evaluator_transfer import (
        TRANSFER_BUNDLE_SCHEMA_VERSION,
        build_local_langfuse_judge_transfer_bundle,
    )

    bundle = build_local_langfuse_judge_transfer_bundle(environment="local")

    assert bundle["schema_version"] == TRANSFER_BUNDLE_SCHEMA_VERSION
    assert bundle["target"] == {
        "environment": "local",
        "evidence_scope": "local_langfuse",
        "proof_level": "local_only",
        "live_or_staging_evidence": False,
        "local_only": True,
    }
    assert bundle["judge_count"] == len(WOS_CATEGORICAL_JUDGES_ORDER)
    first = bundle["judges"][0]
    assert first["local_only"] is True
    assert first["live_or_staging_evidence"] is False
    assert first["langfuse_ui_bootstrap"]["observation_filters"]["Environment"] == ["local"]
    assert first["langfuse_ui_bootstrap"]["trace_metadata_filters"]["proof_level"] == "local_only"
    assert first["runtime_gate"] is False
    assert first["replaces_deterministic_gates"] is False


def test_local_langfuse_judge_transfer_markdown_lists_judges():
    from ai_stack.langfuse_evaluator_transfer import (
        build_local_langfuse_judge_transfer_bundle,
        render_local_langfuse_judge_transfer_markdown,
    )

    md = render_local_langfuse_judge_transfer_markdown(
        build_local_langfuse_judge_transfer_bundle(environment="local", include_prompts=False)
    )

    assert "Local Langfuse Judge Transfer Bundle" in md
    assert "`opening_experience_judge`" in md
    assert "`player_turn_playability_judge`" in md
    assert "validation_outcome" in md
