from app.content.compiler import compile_module


def test_compile_god_of_carnage_produces_deterministic_projection():
    output = compile_module("god_of_carnage")

    assert output.canonical_model == "content_module.scene_trigger_ending.v1"
    assert output.runtime_projection.module_id == "god_of_carnage"
    assert output.runtime_projection.start_scene_id
    assert output.runtime_projection.scenes
    for row in output.runtime_projection.scenes:
        assert row.get("id") == row.get("scene_id")
        assert row.get("id")
    assert output.runtime_projection.triggers
    assert output.runtime_projection.endings
    assert output.runtime_projection.relationship_axes
    assert output.runtime_projection.relationships
    assert output.runtime_projection.escalation_axes
    assert output.runtime_projection.opening_scene_sequence.get("id") == "goc_opening_sequence_v1"
    assert output.runtime_projection.opening_quote_anchors.get("anchors")
    assert "hard_forbidden_detection" in output.runtime_projection.hard_forbidden_rules
    assert output.runtime_projection.start_scene_id == "prologue_park_edge"
    assert len(output.runtime_projection.scenes) > 10
    assert output.runtime_projection.canonical_path.get("primary_direction_surface") is True
    assert output.runtime_projection.modularity_policy.get("authority_boundaries")
    assert output.runtime_projection.scene_graph.get("id") == "goc_scene_graph_v1"
    assert output.runtime_projection.locations.get("places")
    assert output.runtime_projection.objects.get("object_documents")
    assert output.runtime_projection.content_access_policy.get("blocked_entities")
    assert set(output.runtime_projection.character_documents.keys()) == {"veronique", "michel", "annette", "alain"}
    assert output.runtime_projection.characters
    assert any(row.get("engine_tasks") for row in output.runtime_projection.scenes)
    assert any(row.get("active_triggers") for row in output.runtime_projection.scenes)
    assert any(row.get("trigger_conditions") for row in output.runtime_projection.transition_hints)
    assert output.retrieval_corpus_seed.chunks
    assert output.review_export_seed.summary["scene_count"] == len(output.runtime_projection.scenes)


def test_retrieval_corpus_seed_indexes_structured_knowledge_with_metadata():
    """GOC-KNOWLEDGE-RUNTIME-INTEGRATION P1.3: knowledge YAML must produce dedicated chunks
    with source_path / content_kind / authority / use_for / module_id / language /
    runtime_locale_available metadata so retrievers can cite the canonical source."""
    from app.content.compiler import compile_module

    output = compile_module("god_of_carnage")
    knowledge_chunks = [c for c in output.retrieval_corpus_seed.chunks if c.kind == "knowledge"]
    assert knowledge_chunks, "retrieval seed missing knowledge chunks"

    by_kind = {c.metadata.get("content_kind"): c for c in knowledge_chunks}
    required = {
        "opening_scene_sequence",
        "opening_quote_anchors",
        "hard_forbidden_rules",
        "premise_and_backstory",
        "narrator_sensory_palette",
        "apartment_layout",
        "objects",
        "actor_pressure_profiles",
        "phase_beat_policy",
        "canonical_path",
        "modularity_policy",
        "scene_graph",
        "locations",
        "content_access_policy",
        "character_documents",
    }
    missing = required - set(by_kind.keys())
    assert not missing, f"retrieval seed missing knowledge content_kinds: {sorted(missing)}"

    for kind, chunk in by_kind.items():
        md = chunk.metadata
        assert md.get("module_id") == "god_of_carnage", f"{kind} missing module_id"
        assert md.get("language") == "en", f"{kind} language not en"
        assert md.get("authority") == "module_canonical", f"{kind} authority wrong"
        assert isinstance(md.get("use_for"), list) and md["use_for"], f"{kind} missing use_for"
        assert isinstance(md.get("source_path"), str) and md["source_path"].startswith(
            "content/modules/god_of_carnage/"
        ), f"{kind} source_path not module-rooted: {md.get('source_path')}"
        assert isinstance(md.get("runtime_locale_available"), bool)

    # Locale availability matches the actual repo layout: apartment layout and objects live next to locale/.
    assert by_kind["apartment_layout"].metadata["runtime_locale_available"] is True
    assert by_kind["objects"].metadata["runtime_locale_available"] is True
    assert by_kind["opening_scene_sequence"].metadata["runtime_locale_available"] is False
    assert by_kind["opening_quote_anchors"].metadata["runtime_locale_available"] is False
    assert by_kind["hard_forbidden_rules"].metadata["runtime_locale_available"] is False
    assert by_kind["locations"].metadata["runtime_locale_available"] is True

    # Opening + hard-forbidden must list their downstream consumers explicitly.
    assert "opening_realization" in by_kind["opening_scene_sequence"].metadata["use_for"]
    assert "quote_anchor_policy" in by_kind["opening_quote_anchors"].metadata["use_for"]
    assert "hard_forbidden_gate" in by_kind["hard_forbidden_rules"].metadata["use_for"]
    assert "story_direction" in by_kind["canonical_path"].metadata["use_for"]
    assert "reference_integrity" in by_kind["modularity_policy"].metadata["use_for"]
    assert "scene_director_navigation" in by_kind["scene_graph"].metadata["use_for"]
    assert "affordance_resolution" in by_kind["content_access_policy"].metadata["use_for"]
