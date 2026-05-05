"""ADR-0033 gate tests for live runtime commit semantics."""

from __future__ import annotations

from ai_stack.live_runtime_commit_semantics import evaluate_live_turn_success_gate


def _live_turn_claim(**overrides):
    payload = {
        "operation": "turn.execute",
        "runtime_profile_id": "goc_live_profile",
        "provider_id": "openai",
        "model_id": "gpt-live",
        "adapter_id": "openai",
        "adapter_kind": "real",
        "fallback_used": False,
        "model_invocation_attempted": True,
        "model_invocation_success": True,
        "model_usage_input": 128,
        "model_usage_output": 96,
        "generated_output_present": True,
        "validation_status": "approved",
        "commit_applied": True,
        "visible_scene_output": {
            "blocks": [{"block_type": "narrator", "text": "The room tightens around the accusation."}]
        },
        "story_entries": [],
        "quality_class": "healthy",
        "trace": {
            "trace_id": "trace-live-1",
            "observations": [
                {
                    "type": "generation",
                    "adapter_kind": "real",
                    "provider_id": "openai",
                    "model_id": "gpt-live",
                    "generated_output_present": True,
                    "output": {"narration": "The room tightens around the accusation."},
                }
            ],
        },
    }
    payload.update(overrides)
    return payload


def test_live_turn_with_mock_adapter_cannot_satisfy_live_success_gate():
    result = evaluate_live_turn_success_gate(
        _live_turn_claim(
            provider_id="mock",
            adapter_id="mock",
            adapter_kind="mock",
            fallback_used=True,
            model_usage_input=0,
            model_usage_output=0,
            quality_class="healthy",
            trace={
                "trace_id": "trace-mock-1",
                "observations": [
                    {
                        "type": "generation",
                        "adapter_kind": "mock",
                        "provider_id": "mock",
                        "model_id": "mock-deterministic",
                        "generated_output_present": True,
                    }
                ],
            },
        )
    )

    assert result["live_success"] is False
    assert result["quality_class"] != "healthy"
    assert result["adapter_kind"] == "mock"
    assert "mock_adapter" in result["degradation_signals"]


def test_live_turn_with_fallback_used_cannot_be_healthy():
    result = evaluate_live_turn_success_gate(
        _live_turn_claim(
            fallback_used=True,
            quality_class="healthy",
        )
    )

    assert result["live_success"] is False
    assert result["quality_class"] == "degraded"
    assert "fallback_used" in result["degradation_signals"]


def test_commit_applied_with_empty_visible_output_fails_live_gate():
    result = evaluate_live_turn_success_gate(
        _live_turn_claim(
            commit_applied=True,
            visible_scene_output={"blocks": []},
            story_entries=[],
        )
    )

    assert result["live_success"] is False
    assert result["visible_output_present"] is False
    assert result["quality_class"] != "healthy"
    assert "empty_visible_output" in result["degradation_signals"]


def test_trace_presence_without_real_generation_observation_fails_live_gate():
    result = evaluate_live_turn_success_gate(
        _live_turn_claim(
            trace={
                "trace_id": "trace-only-1",
                "observations": [
                    {"type": "span", "name": "story.phase.model_invoke", "status": "success"},
                    {"type": "span", "name": "story.phase.commit", "commit_applied": True},
                ],
            },
        )
    )

    assert result["live_success"] is False
    assert result["real_generation_observation_present"] is False
    assert "missing_real_generation_observation" in result["degradation_signals"]


def test_real_non_mock_generation_with_visible_commit_passes_live_gate():
    result = evaluate_live_turn_success_gate(_live_turn_claim())

    assert result["live_success"] is True
    assert result["quality_class"] == "healthy"
    assert result["visible_output_present"] is True
    assert result["real_generation_observation_present"] is True
    assert result["degradation_signals"] == []
