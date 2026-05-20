from __future__ import annotations

from ai_stack.contracts.temporal_control_contracts import (
    TEMPORAL_CONTROL_FAILURE_HISTORY_REWRITE_ATTEMPT,
    TEMPORAL_CONTROL_FAILURE_UNCOMMITTED_SOURCE,
    TEMPORAL_CONTROL_POLICY_VERSION,
    TEMPORAL_CONTROL_SCHEMA_VERSION,
    normalize_temporal_control_policy,
)
from ai_stack.story_runtime.narrative.temporal_control_engine import (
    build_temporal_control_aspect_record,
    compact_temporal_control_context,
    derive_temporal_control,
    validate_temporal_control_realization,
)


def _policy(*, require_events: bool = False) -> dict:
    return normalize_temporal_control_policy(
        {
            "enabled": True,
            "schema_version": TEMPORAL_CONTROL_POLICY_VERSION,
            "allowed_operations": [
                "hold_current_moment",
                "advance_elapsed_time",
                "recall_committed_past",
                "summarize_gap",
                "resume_present",
            ],
            "require_structured_events": require_events,
            "max_recalled_turns": 2,
            "max_elapsed_turns": 4,
            "default_commit_impact": "recover",
        }
    )


def test_temporal_control_selects_committed_recall_and_validates_event() -> None:
    policy = _policy(require_events=True)
    result = derive_temporal_control(
        scene_plan_record={"selected_scene_function": "probe_motive"},
        semantic_move_record={"move_type": "question"},
        prior_consequence_cascade_state={
            "items": [
                {
                    "source_turn_id": "turn-alpha",
                    "source_turn_number": 2,
                    "consequence_id": "cons-alpha",
                    "continuity_class": "blame_pressure",
                    "status": "active",
                }
            ]
        },
        turn_id="turn-current",
        turn_number=3,
        module_runtime_policy={"runtime_governance_policy": {"temporal_control": policy}},
    )

    target = result["target"]
    state = result["state"]
    compact = compact_temporal_control_context(target)
    validation = validate_temporal_control_realization(
        temporal_control_target=target,
        temporal_control_state=state,
        structured_output={
            "temporal_control_events": [
                {
                    "operation": "recall_committed_past",
                    "source_turn_ids": ["turn-alpha"],
                    "source_consequence_ids": ["cons-alpha"],
                    "elapsed_turns": 0,
                }
            ]
        },
    )
    aspect = build_temporal_control_aspect_record(
        target=target,
        state=state,
        validation=validation,
        policy=policy,
        source="validator",
    )

    assert target["schema_version"] == TEMPORAL_CONTROL_SCHEMA_VERSION
    assert target["operation"] == "recall_committed_past"
    assert target["recalled_turn_ids"] == ["turn-alpha"]
    assert target["recalled_consequence_ids"] == ["cons-alpha"]
    assert compact["operation"] == "recall_committed_past"
    assert validation["status"] == "approved"
    assert validation["contract_pass"] is True
    assert aspect["status"] == "passed"
    assert aspect["selected"]["operation"] == "recall_committed_past"


def test_temporal_control_rejects_uncommitted_or_rewrite_events() -> None:
    policy = _policy(require_events=False)
    result = derive_temporal_control(
        scene_plan_record={"selected_scene_function": "probe_motive"},
        semantic_move_record={"move_type": "question"},
        prior_consequence_cascade_state={
            "items": [
                {
                    "source_turn_id": "turn-alpha",
                    "source_turn_number": 2,
                    "consequence_id": "cons-alpha",
                    "status": "active",
                }
            ]
        },
        module_runtime_policy={"runtime_governance_policy": {"temporal_control": policy}},
    )

    validation = validate_temporal_control_realization(
        temporal_control_target=result["target"],
        temporal_control_state=result["state"],
        structured_output={
            "temporal_control_events": [
                {
                    "operation": "recall_committed_past",
                    "source_turn_ids": ["turn-unselected"],
                    "rewrites_history": True,
                }
            ]
        },
    )

    assert validation["status"] == "rejected"
    assert validation["contract_pass"] is False
    assert TEMPORAL_CONTROL_FAILURE_UNCOMMITTED_SOURCE in validation["failure_codes"]
    assert TEMPORAL_CONTROL_FAILURE_HISTORY_REWRITE_ATTEMPT in validation["failure_codes"]


def test_temporal_control_policy_disabled_is_not_applicable() -> None:
    policy = normalize_temporal_control_policy({"enabled": False})
    result = derive_temporal_control(
        scene_plan_record={"selected_scene_function": "scene_pivot"},
        module_runtime_policy={"runtime_governance_policy": {"temporal_control": policy}},
    )
    validation = validate_temporal_control_realization(
        temporal_control_target=result["target"],
        temporal_control_state=result["state"],
        structured_output={"temporal_control_events": []},
    )

    assert result["target"]["policy_enabled"] is False
    assert result["target"]["operation"] == "resume_present"
    assert validation["status"] == "not_applicable"
    assert validation["contract_pass"] is True
