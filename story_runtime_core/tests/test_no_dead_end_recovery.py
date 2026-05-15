from __future__ import annotations

from story_runtime_core.recovery import (
    NO_DEAD_END_RECOVERY_SCHEMA_VERSION,
    RECOVERY_CLASS_BLOCKED_PLAYABLE,
    RECOVERY_CLASS_COMMITTED_SUCCESS,
    RECOVERY_CLASS_SAFE_FALLBACK_PLAYABLE,
    build_no_dead_end_recovery_record,
    validate_no_dead_end_recovery_record,
)


def test_recoverable_rejection_builds_playable_false_truth_record() -> None:
    record = build_no_dead_end_recovery_record(
        story_session_id="s",
        module_id="m",
        turn_number=1,
        turn_kind="player_rejected_recoverable",
        player_input="Open the locked door.",
        reason="dramatic_effect_reject_continuity_pressure",
        validation_outcome={
            "status": "rejected",
            "reason": "dramatic_effect_reject_continuity_pressure",
            "recoverable_rejection": True,
            "hard_boundary_failure": False,
        },
        narrative_commit={"commit_reason_code": "recoverable_rejection"},
        committed_result={"commit_applied": False, "recoverable_rejection": True},
        visible_output_bundle={"gm_narration": ["The scene pushes back."]},
        recoverable_outcome=True,
    )

    assert record["schema_version"] == NO_DEAD_END_RECOVERY_SCHEMA_VERSION
    assert record["recovery_class"] == RECOVERY_CLASS_BLOCKED_PLAYABLE
    assert record["commit_policy"]["commits_story_truth"] is False
    assert record["commit_policy"]["committed_truth_scope"] == "none"
    assert record["playability"]["attempt_preserved"] is True
    assert record["playability"]["next_step_affordance_present"] is True
    assert record["validation"]["status"] == "approved"


def test_graph_exception_builds_safe_fallback_playable_record() -> None:
    record = build_no_dead_end_recovery_record(
        story_session_id="s",
        module_id="m",
        turn_number=2,
        turn_kind="player_graph_exception_playable",
        player_input="Do something complicated.",
        reason="graph_execution_exception",
        validation_outcome={
            "status": "rejected",
            "reason": "graph_execution_exception",
            "recoverable_rejection": True,
        },
        committed_result={"commit_applied": False},
        visible_output_bundle={"gm_narration": ["Try a simpler move from here."]},
        recoverable_outcome=True,
    )

    assert record["recovery_class"] == RECOVERY_CLASS_SAFE_FALLBACK_PLAYABLE
    assert record["obstacle_kind"] == "runtime_graph_exception"
    assert {option["option_kind"] for option in record["next_step_options"]} == {"retry", "alternate_action"}
    assert record["validation"]["recoverable_no_dead_end"] is True


def test_committed_success_record_keeps_full_truth_scope() -> None:
    record = build_no_dead_end_recovery_record(
        story_session_id="s",
        module_id="m",
        turn_number=3,
        turn_kind="player",
        player_input="Walk into the hall.",
        reason="scene_transition_allowed",
        validation_outcome={"status": "approved"},
        narrative_commit={"allowed": True, "situation_status": "transitioned"},
        committed_result={"commit_applied": True},
        visible_output_bundle={"gm_narration": ["You enter the hall."]},
    )

    assert record["recovery_class"] == RECOVERY_CLASS_COMMITTED_SUCCESS
    assert record["recovery_required"] is False
    assert record["commit_policy"]["commits_story_truth"] is True
    assert record["commit_policy"]["committed_truth_scope"] == "full_turn"
    assert record["validation"]["status"] == "approved"


def test_validation_rejects_technical_leak_and_missing_next_step() -> None:
    validation = validate_no_dead_end_recovery_record(
        {
            "schema_version": NO_DEAD_END_RECOVERY_SCHEMA_VERSION,
            "recovery_class": RECOVERY_CLASS_BLOCKED_PLAYABLE,
            "attempt": {"present": True},
            "playability": {
                "next_step_affordance_present": False,
                "technical_leak_absent": False,
            },
            "commit_policy": {
                "commits_story_truth": False,
                "committed_truth_scope": "none",
            },
            "next_step_options": [],
        }
    )

    assert validation["status"] == "rejected"
    assert "next_step_missing" in validation["failure_codes"]
    assert "technical_leak_detected" in validation["failure_codes"]
