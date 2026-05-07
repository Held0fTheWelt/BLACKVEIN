"""Regression: LDSS opening fallback must preserve prior actor_lane_validation.

ADR-0033 §13.8 — Opening fallback replaces ``validation_outcome`` for policy reasons;
without copying prior ``actor_lane_validation``, Langfuse path summaries lose
``actor_lane_validation_status`` while ``actor_lane_safety_pass`` still treats
missing as pass, producing misleading unknown + pass pairs.
"""

from __future__ import annotations

from story_runtime_core.model_registry import ModelRegistry

from app.story_runtime.manager import StoryRuntimeManager


def test_ldss_opening_fallback_preserves_actor_lane_nested_in_validation_outcome() -> None:
    mgr = StoryRuntimeManager(registry=ModelRegistry(), adapters={})
    graph_state = {
        "validation_outcome": {
            "status": "approved",
            "reason": "seam_ok",
            "actor_lane_validation": {"status": "approved", "reason": "lane_ok"},
        },
        "generation": {"metadata": {}},
    }
    out = mgr._ldss_opening_fallback_state(
        graph_state,
        reason="dramatic_effect_reject_empty_fluency",
    )
    al = out["validation_outcome"]["actor_lane_validation"]
    assert al["status"] == "approved"
    assert al["reason"] == "lane_ok"
    assert out["validation_outcome"]["validator_lane"] == "opening_fallback_policy_v1"


def test_ldss_opening_fallback_preserves_actor_lane_from_graph_root_when_nested_missing() -> None:
    mgr = StoryRuntimeManager(registry=ModelRegistry(), adapters={})
    graph_state = {
        "validation_outcome": {"status": "approved", "reason": "seam_ok"},
        "actor_lane_validation": {"status": "rejected", "reason": "wrong_lane"},
        "generation": {"metadata": {}},
    }
    out = mgr._ldss_opening_fallback_state(graph_state, reason="no_visible_narration:test")
    al = out["validation_outcome"]["actor_lane_validation"]
    assert al["status"] == "rejected"
    assert al["reason"] == "wrong_lane"


def test_ldss_opening_fallback_omits_actor_lane_when_absent_before_fallback() -> None:
    mgr = StoryRuntimeManager(registry=ModelRegistry(), adapters={})
    graph_state = {
        "validation_outcome": {"status": "approved", "reason": "seam_ok"},
        "generation": {"metadata": {}},
    }
    out = mgr._ldss_opening_fallback_state(graph_state, reason="x")
    assert "actor_lane_validation" not in out["validation_outcome"]
