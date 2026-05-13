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
    assert "hard_forbidden_detection" in output.runtime_projection.hard_forbidden_rules
    assert output.runtime_projection.characters
    assert any(row.get("engine_tasks") for row in output.runtime_projection.scenes)
    assert any(row.get("active_triggers") for row in output.runtime_projection.scenes)
    assert any(row.get("trigger_conditions") for row in output.runtime_projection.transition_hints)
    assert output.retrieval_corpus_seed.chunks
    assert output.review_export_seed.summary["scene_count"] == len(output.runtime_projection.scenes)
