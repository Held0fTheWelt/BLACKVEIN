from __future__ import annotations

from ai_stack.contracts.genre_awareness_contracts import (
    GENRE_AWARENESS_FAILURE_EVENT_BUDGET_EXCEEDED,
    GENRE_AWARENESS_FAILURE_FORBIDDEN_MARKER,
    GENRE_AWARENESS_FAILURE_MISSING_REQUIRED_CONVENTION,
    GENRE_AWARENESS_FAILURE_REGISTER_NOT_ALLOWED,
    GENRE_AWARENESS_FAILURE_UNSELECTED_PROFILE,
    GENRE_AWARENESS_POLICY_VERSION,
    GENRE_AWARENESS_SCHEMA_VERSION,
    normalize_genre_awareness_policy,
)
from ai_stack.story_runtime.narrative.genre_awareness_engine import (
    build_genre_awareness_aspect_record,
    compact_genre_awareness_context,
    derive_genre_awareness,
    validate_genre_awareness_realization,
)


def _policy() -> dict:
    return normalize_genre_awareness_policy(
        {
            "enabled": True,
            "schema_version": GENRE_AWARENESS_POLICY_VERSION,
            "genre_profile_id": "bourgeois_social_drama",
            "allowed_registers": ["social_drama", "restrained_theatrical"],
            "required_conventions": [
                "civility_under_pressure",
                "status_and_blame_conflict",
            ],
            "forbidden_genre_markers": [{"id": "fantasy_quest_frame"}],
            "require_structured_events": True,
            "max_genre_signals_per_turn": 1,
            "default_commit_impact": "recover",
        }
    )


def test_genre_awareness_derives_target_and_validates_structured_event() -> None:
    policy = _policy()
    result = derive_genre_awareness(
        module_runtime_policy={"runtime_governance_policy": {"genre_awareness": policy}},
        scene_plan_record={"selected_scene_function": "domestic_pressure"},
        current_scene_id="scene_alpha",
        scene_energy_target={"energy_level": "rising"},
        social_pressure_target={"target_band": "strained"},
        prior_genre_awareness_state={"current_genre_profile_id": "prior_profile"},
    )

    target = result["target"]
    state = result["state"]
    compact = compact_genre_awareness_context(target)
    validation = validate_genre_awareness_realization(
        genre_awareness_target=target,
        genre_awareness_state=state,
        structured_output={
            "genre_awareness_events": [
                {
                    "genre_profile_id": "bourgeois_social_drama",
                    "register": "social_drama",
                    "convention_ids": [
                        "civility_under_pressure",
                        "status_and_blame_conflict",
                    ],
                }
            ]
        },
    )
    aspect = build_genre_awareness_aspect_record(
        target=target,
        state=state,
        validation=validation,
        policy=policy,
        source="validator",
    )

    assert target["schema_version"] == GENRE_AWARENESS_SCHEMA_VERSION
    assert target["policy_version"] == GENRE_AWARENESS_POLICY_VERSION
    assert target["genre_profile_id"] == "bourgeois_social_drama"
    assert state["prior_genre_profile_id"] == "prior_profile"
    assert compact["structured_event_field"] == "genre_awareness_events"
    assert "scene_alpha" not in str(compact)
    assert validation["status"] == "approved"
    assert validation["contract_pass"] is True
    assert aspect["status"] == "passed"
    assert aspect["selected"]["genre_profile_id"] == "bourgeois_social_drama"


def test_genre_awareness_rejects_unselected_profile_and_forbidden_markers() -> None:
    policy = _policy()
    result = derive_genre_awareness(
        module_runtime_policy={"runtime_governance_policy": {"genre_awareness": policy}},
        scene_plan_record={"selected_scene_function": "domestic_pressure"},
    )

    validation = validate_genre_awareness_realization(
        genre_awareness_target=result["target"],
        genre_awareness_state=result["state"],
        structured_output={
            "genre_awareness_events": [
                {
                    "genre_profile_id": "fantasy_quest",
                    "register": "quest_mode",
                    "convention_ids": ["status_and_blame_conflict"],
                    "forbidden_marker_ids": ["fantasy_quest_frame"],
                    "forbidden_marker_present": True,
                },
                {
                    "genre_profile_id": "fantasy_quest",
                    "register": "quest_mode",
                    "convention_ids": [],
                },
            ]
        },
    )

    assert validation["status"] == "rejected"
    assert validation["contract_pass"] is False
    assert GENRE_AWARENESS_FAILURE_EVENT_BUDGET_EXCEEDED in validation["failure_codes"]
    assert GENRE_AWARENESS_FAILURE_UNSELECTED_PROFILE in validation["failure_codes"]
    assert GENRE_AWARENESS_FAILURE_REGISTER_NOT_ALLOWED in validation["failure_codes"]
    assert GENRE_AWARENESS_FAILURE_FORBIDDEN_MARKER in validation["failure_codes"]
    assert (
        GENRE_AWARENESS_FAILURE_MISSING_REQUIRED_CONVENTION
        in validation["failure_codes"]
    )


def test_genre_awareness_policy_disabled_is_not_applicable() -> None:
    policy = normalize_genre_awareness_policy({"enabled": False})
    result = derive_genre_awareness(
        module_runtime_policy={"runtime_governance_policy": {"genre_awareness": policy}},
        scene_plan_record={"selected_scene_function": "domestic_pressure"},
    )
    validation = validate_genre_awareness_realization(
        genre_awareness_target=result["target"],
        genre_awareness_state=result["state"],
        structured_output={"genre_awareness_events": []},
    )

    assert result["target"]["policy_enabled"] is False
    assert validation["status"] == "not_applicable"
    assert validation["contract_pass"] is True
