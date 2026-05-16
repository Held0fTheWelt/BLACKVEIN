"""Tests for Langfuse observation tree selection policy."""

from __future__ import annotations

from story_runtime_core.observability_tree_policy import (
    classify_observation_tree,
    normalize_enabled_observation_trees,
    should_emit_observation,
)


def test_normalize_observation_trees_supports_all_none_and_unknowns() -> None:
    assert normalize_enabled_observation_trees(None) == ["minimal"]
    assert normalize_enabled_observation_trees("none") == []
    assert "scores" in normalize_enabled_observation_trees("all")
    assert normalize_enabled_observation_trees(["scores", "unknown", "minimal"]) == ["minimal", "scores"]


def test_classify_known_runtime_observations() -> None:
    assert classify_observation_tree("story.graph.path_summary") == "minimal"
    assert classify_observation_tree("story.phase.model_invoke") == "model_io"
    assert classify_observation_tree("story.rag.retrieval", as_type="retriever") == "retrieval"
    assert classify_observation_tree("story.visible.project", metadata={"phase": "runtime_aspect"}) == "scene_projection"
    assert classify_observation_tree("story.phase.narrator") == "narrator"
    assert classify_observation_tree("turn_aspect_ledger_present", as_type="score") == "scores"


def test_should_emit_observation_requires_selected_tree() -> None:
    assert should_emit_observation(["minimal"], "story.graph.path_summary") is True
    assert should_emit_observation(["minimal"], "story.phase.model_invoke") is False
    assert should_emit_observation(["model_io"], "story.phase.model_invoke") is True
