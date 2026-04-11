from app.content.compiler import compile_module


def test_compile_god_of_carnage_produces_deterministic_projection():
    output = compile_module("god_of_carnage")

    assert output.canonical_model == "content_module.scene_trigger_ending.v1"
    assert output.runtime_projection.module_id == "god_of_carnage"
    assert output.runtime_projection.start_scene_id
    assert output.runtime_projection.scenes
    assert output.runtime_projection.triggers
    assert output.runtime_projection.endings
    assert output.retrieval_corpus_seed.chunks
    assert output.review_export_seed.summary["scene_count"] == len(output.runtime_projection.scenes)
