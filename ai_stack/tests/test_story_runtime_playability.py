from __future__ import annotations

from ai_stack.story_runtime_playability import (
    decide_playability_recovery,
    degrade_validation_outcome,
    is_hard_boundary_failure,
)


def test_hard_boundary_prefix_detected() -> None:
    assert is_hard_boundary_failure({"status": "rejected", "reason": "scene_illegal_transition"}) is True
    assert is_hard_boundary_failure({"status": "rejected", "reason": "dramatic_alignment_narrative_too_short"}) is False


def test_degraded_outcome_is_approved() -> None:
    out = degrade_validation_outcome({"status": "rejected", "reason": "x", "dramatic_effect_gate_outcome": {}})
    assert out["status"] == "approved"


def test_decide_playability_retry_then_degraded_window() -> None:
    d1 = decide_playability_recovery(
        turn_number=1,
        attempt_index=1,
        max_attempts=2,
        outcome={"status": "rejected", "reason": "dramatic_alignment_narrative_too_short"},
        generation={"success": True, "content": "x" * 120, "metadata": {}},
        proposed_state_effects=[{"type": "narrative", "text": "y"}],
        allow_degraded_commit_after_retries=True,
    )
    assert d1.should_retry is True
    assert d1.allow_degraded_commit is False

    d2 = decide_playability_recovery(
        turn_number=1,
        attempt_index=2,
        max_attempts=2,
        outcome={"status": "rejected", "reason": "dramatic_alignment_narrative_too_short"},
        generation={"success": True, "content": "x" * 120, "metadata": {}},
        proposed_state_effects=[{"type": "narrative", "text": "y"}],
        allow_degraded_commit_after_retries=True,
    )
    assert d2.should_retry is False
    assert d2.allow_degraded_commit is True


def test_degraded_commit_blocked_for_actor_lane_illegal_reason() -> None:
    decision = decide_playability_recovery(
        turn_number=2,
        attempt_index=2,
        max_attempts=2,
        outcome={"status": "rejected", "reason": "actor_lane_illegal_actor"},
        generation={"success": True, "content": "x" * 140, "metadata": {}},
        proposed_state_effects=[{"type": "narrative", "text": "y"}],
        allow_degraded_commit_after_retries=True,
        actor_lane_validation={"status": "rejected", "reason": "actor_lane_illegal_actor"},
    )
    assert decision.should_retry is False
    assert decision.allow_degraded_commit is False


def test_degraded_commit_blocked_for_parser_failure_feedback() -> None:
    decision = decide_playability_recovery(
        turn_number=2,
        attempt_index=2,
        max_attempts=2,
        outcome={"status": "rejected", "reason": "dramatic_alignment_narrative_too_short"},
        generation={"success": True, "content": "x" * 120, "metadata": {"langchain_parser_error": "boom"}},
        proposed_state_effects=[{"type": "narrative", "text": "y"}],
        allow_degraded_commit_after_retries=True,
    )
    assert decision.should_retry is False
    assert decision.allow_degraded_commit is False
