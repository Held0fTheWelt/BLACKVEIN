from __future__ import annotations

from ai_stack.capabilities.dramatic_capability_contracts import NPC_ACTION_CONTROLS_HUMAN_ACTOR_REASON
from ai_stack.npc_agency.npc_agency_contracts import normalize_npc_agency_plan
from ai_stack.npc_agency.npc_agency_realization import validate_npc_initiative_realization
from ai_stack.story_runtime_playability import (
    build_rewrite_instruction,
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
    assert d2.should_retry is True
    assert d2.allow_degraded_commit is False

    exhausted = decide_playability_recovery(
        turn_number=1,
        attempt_index=3,
        max_attempts=2,
        outcome={"status": "rejected", "reason": "dramatic_alignment_narrative_too_short"},
        generation={"success": True, "content": "x" * 120, "metadata": {}},
        proposed_state_effects=[{"type": "narrative", "text": "y"}],
        allow_degraded_commit_after_retries=True,
    )
    assert exhausted.should_retry is False
    assert exhausted.allow_degraded_commit is True


def test_degraded_commit_blocked_for_actor_lane_illegal_reason() -> None:
    decision = decide_playability_recovery(
        turn_number=2,
        attempt_index=3,
        max_attempts=2,
        outcome={"status": "rejected", "reason": "actor_lane_illegal_actor"},
        generation={"success": True, "content": "x" * 140, "metadata": {}},
        proposed_state_effects=[{"type": "narrative", "text": "y"}],
        allow_degraded_commit_after_retries=True,
        actor_lane_validation={"status": "rejected", "reason": "actor_lane_illegal_actor"},
    )
    assert decision.should_retry is False
    assert decision.allow_degraded_commit is False


def test_transcript_shell_npc_lane_rejection_triggers_retry() -> None:
    d = decide_playability_recovery(
        turn_number=2,
        attempt_index=1,
        max_attempts=3,
        outcome={"status": "rejected", "reason": "actor_lane_text_exceeds_transcript_beat"},
        generation={"success": True, "content": "x" * 200, "metadata": {}},
        proposed_state_effects=[{"description": "ok", "effect_type": "narrative_projection"}],
        allow_degraded_commit_after_retries=True,
    )
    assert d.should_retry is True
    assert "actor_lane_text_exceeds_transcript_beat" in d.feedback_codes


def test_degraded_commit_blocked_for_parser_failure_feedback() -> None:
    decision = decide_playability_recovery(
        turn_number=2,
        attempt_index=3,
        max_attempts=2,
        outcome={"status": "rejected", "reason": "dramatic_alignment_narrative_too_short"},
        generation={"success": True, "content": "x" * 120, "metadata": {"langchain_parser_error": "boom"}},
        proposed_state_effects=[{"type": "narrative", "text": "y"}],
        allow_degraded_commit_after_retries=True,
    )
    assert decision.should_retry is False
    assert decision.allow_degraded_commit is False


def test_runtime_aspect_failures_are_retryable_but_not_degradable() -> None:
    retry = decide_playability_recovery(
        turn_number=2,
        attempt_index=1,
        max_attempts=2,
        outcome={
            "status": "rejected",
            "reason": "narrator_required_missing",
            "recoverable_rejection": True,
            "runtime_aspect_failure": {
                "failure_reason": "narrator_required_missing",
                "expected_owner": "narrator",
            },
        },
        generation={"success": True, "content": "x" * 140, "metadata": {}},
        proposed_state_effects=[],
        allow_degraded_commit_after_retries=True,
    )
    assert retry.should_retry is True
    assert "narrator_required_missing" in retry.feedback_codes
    assert "expected_owner:narrator" in retry.feedback_codes

    exhausted = decide_playability_recovery(
        turn_number=2,
        attempt_index=3,
        max_attempts=2,
        outcome={
            "status": "rejected",
            "reason": "narrator_required_missing",
            "recoverable_rejection": True,
            "runtime_aspect_failure": {"failure_reason": "narrator_required_missing"},
        },
        generation={"success": True, "content": "x" * 140, "metadata": {}},
        proposed_state_effects=[],
        allow_degraded_commit_after_retries=True,
    )
    assert exhausted.should_retry is False
    assert exhausted.allow_degraded_commit is False


def test_npc_coercion_runtime_aspect_is_retryable_but_not_degradable() -> None:
    outcome = {
        "status": "rejected",
        "reason": NPC_ACTION_CONTROLS_HUMAN_ACTOR_REASON,
        "recoverable_rejection": True,
        "runtime_aspect_failure": {
            "failure_reason": NPC_ACTION_CONTROLS_HUMAN_ACTOR_REASON,
        },
    }

    retry = decide_playability_recovery(
        turn_number=2,
        attempt_index=1,
        max_attempts=2,
        outcome=outcome,
        generation={"success": True, "content": "x" * 140, "metadata": {}},
        proposed_state_effects=[{"description": "ok", "effect_type": "narrative_projection"}],
        allow_degraded_commit_after_retries=True,
    )

    exhausted = decide_playability_recovery(
        turn_number=2,
        attempt_index=3,
        max_attempts=2,
        outcome=outcome,
        generation={"success": True, "content": "x" * 140, "metadata": {}},
        proposed_state_effects=[{"description": "ok", "effect_type": "narrative_projection"}],
        allow_degraded_commit_after_retries=True,
    )

    assert retry.should_retry is True
    assert NPC_ACTION_CONTROLS_HUMAN_ACTOR_REASON in retry.feedback_codes
    assert exhausted.should_retry is False
    assert exhausted.allow_degraded_commit is False


def test_npc_agency_missing_required_feedback_is_retryable_but_not_degradable() -> None:
    actor_ids = ["npc_primary", "npc_secondary"]
    plan = normalize_npc_agency_plan(
        {},
        selected_primary_responder_id=actor_ids[0],
        selected_secondary_responder_ids=actor_ids[1:],
        preferred_reaction_order_ids=actor_ids,
    )
    structured_output = {
        "spoken_lines": [{"speaker_id": actor_ids[0], "text": "Visible beat."}],
        "action_lines": [],
        "initiative_events": [],
    }
    validation = validate_npc_initiative_realization(plan, structured_output)
    outcome = {
        "status": validation["status"],
        "reason": validation["feedback_code"],
        "recoverable_rejection": True,
        "npc_initiative_validation": validation,
    }

    retry = decide_playability_recovery(
        turn_number=2,
        attempt_index=1,
        max_attempts=2,
        outcome=outcome,
        generation={"success": True, "content": "x" * 140, "metadata": {}},
        proposed_state_effects=[{"description": "ok", "effect_type": "narrative_projection"}],
        allow_degraded_commit_after_retries=True,
    )

    missing_actor_codes = [
        f"missing_required_npc_initiative:{actor_id}"
        for actor_id in validation["missing_required_actor_ids"]
    ]
    assert retry.should_retry is True
    assert validation["feedback_code"] in retry.feedback_codes
    assert all(code in retry.feedback_codes for code in missing_actor_codes)

    exhausted = decide_playability_recovery(
        turn_number=2,
        attempt_index=3,
        max_attempts=2,
        outcome=outcome,
        generation={"success": True, "content": "x" * 140, "metadata": {}},
        proposed_state_effects=[{"description": "ok", "effect_type": "narrative_projection"}],
        allow_degraded_commit_after_retries=True,
    )
    instruction = build_rewrite_instruction(
        retry.feedback_codes,
        allowed_actor_ids=plan["required_actor_ids"],
    )

    assert exhausted.should_retry is False
    assert exhausted.allow_degraded_commit is False
    assert all(actor_id in instruction for actor_id in plan["required_actor_ids"])


def test_dramatic_irony_failure_feedback_is_retryable_but_not_degradable() -> None:
    violation_code = "dramatic_irony_hidden_fact_echo"
    outcome = {
        "status": "rejected",
        "reason": violation_code,
        "recoverable_rejection": True,
        "dramatic_irony_validation": {
            "status": "rejected",
            "violation_codes": [violation_code],
        },
    }

    retry = decide_playability_recovery(
        turn_number=2,
        attempt_index=1,
        max_attempts=2,
        outcome=outcome,
        generation={"success": True, "content": "x" * 140, "metadata": {}},
        proposed_state_effects=[{"description": "ok", "effect_type": "narrative_projection"}],
        allow_degraded_commit_after_retries=True,
    )
    exhausted = decide_playability_recovery(
        turn_number=2,
        attempt_index=3,
        max_attempts=2,
        outcome=outcome,
        generation={"success": True, "content": "x" * 140, "metadata": {}},
        proposed_state_effects=[{"description": "ok", "effect_type": "narrative_projection"}],
        allow_degraded_commit_after_retries=True,
    )
    instruction = build_rewrite_instruction(retry.feedback_codes)

    assert retry.should_retry is True
    assert violation_code in retry.feedback_codes
    assert exhausted.should_retry is False
    assert exhausted.allow_degraded_commit is False
    assert "private motive" in instruction
