from __future__ import annotations

from ai_stack.meta_narrative_awareness_contracts import (
    META_NARRATIVE_AWARENESS_SCHEMA_VERSION,
    META_NARRATIVE_FAILURE_DIRECT_ADDRESS,
    META_NARRATIVE_FAILURE_FORBIDDEN_MODE,
    META_NARRATIVE_FAILURE_NOT_OPTED_IN,
    META_NARRATIVE_FAILURE_SYSTEM_DISCLOSURE,
    META_NARRATIVE_FAILURE_UNAUTHORIZED_ACTOR,
    normalize_meta_narrative_awareness_policy,
)
from ai_stack.meta_narrative_awareness_engine import (
    build_meta_narrative_awareness_aspect_record,
    compact_meta_narrative_awareness_context,
    derive_meta_narrative_awareness,
    validate_meta_narrative_awareness_realization,
)


def _policy() -> dict[str, object]:
    return normalize_meta_narrative_awareness_policy(
        {
            "enabled": True,
            "allowed_intensities": ["subtle"],
            "allowed_trigger_frequencies": ["rare"],
            "characters_with_awareness": ["veronique"],
            "allowed_awareness_modes": [
                "dramatic_pattern_sense",
                "narrative_pressure_sense",
            ],
            "max_events_per_turn": 1,
        }
    )


def test_meta_narrative_awareness_requires_session_opt_in() -> None:
    result = derive_meta_narrative_awareness(
        module_runtime_policy={"meta_narrative_awareness_policy": _policy()},
        story_runtime_experience={"meta_narrative_awareness_enabled": False},
        selected_responder_set=[{"actor_id": "veronique"}],
        current_scene_id="scene_alpha",
    )
    target = result["target"]
    rejected = validate_meta_narrative_awareness_realization(
        meta_narrative_awareness_target=target,
        structured_output={
            "meta_narrative_awareness_events": [
                {"actor_id": "veronique", "awareness_mode": "dramatic_pattern_sense"}
            ]
        },
    )

    assert target["schema_version"] == META_NARRATIVE_AWARENESS_SCHEMA_VERSION
    assert target["policy_enabled"] is True
    assert target["opt_in_enabled"] is False
    assert target["active"] is False
    assert compact_meta_narrative_awareness_context(target) == {}
    assert rejected["status"] == "rejected"
    assert rejected["failure_codes"] == [META_NARRATIVE_FAILURE_NOT_OPTED_IN]


def test_meta_narrative_awareness_selects_subtle_opt_in_target_and_validates_event() -> None:
    result = derive_meta_narrative_awareness(
        module_runtime_policy={"meta_narrative_awareness_policy": _policy()},
        story_runtime_experience={
            "meta_narrative_awareness_enabled": True,
            "meta_narrative_awareness_intensity": "subtle",
            "meta_narrative_trigger_frequency": "rare",
            "meta_narrative_characters_with_awareness": ["veronique"],
        },
        selected_responder_set=[{"actor_id": "veronique"}],
        selected_scene_function="probe_motive",
        current_scene_id="scene_alpha",
        social_pressure_target={"target_band": "high", "trend": "rising"},
    )
    target = result["target"]
    compact = compact_meta_narrative_awareness_context(target)
    validation = validate_meta_narrative_awareness_realization(
        meta_narrative_awareness_target=target,
        structured_output={
            "meta_narrative_awareness_events": [
                {
                    "actor_id": "veronique",
                    "awareness_mode": "dramatic_pattern_sense",
                    "fourth_wall_level": "subtle",
                    "direct_player_address": False,
                }
            ]
        },
    )
    aspect = build_meta_narrative_awareness_aspect_record(
        target=target,
        validation=validation,
        policy=result["policy"],
        source="validator",
    )

    assert target["active"] is True
    assert target["selected_actor_ids"] == ["veronique"]
    assert compact["selected_actor_ids"] == ["veronique"]
    assert compact["structured_event_field"] == "meta_narrative_awareness_events"
    assert validation["status"] == "approved"
    assert validation["contract_pass"] is True
    assert aspect["status"] == "passed"
    assert aspect["selected"]["intensity"] == "subtle"


def test_meta_narrative_awareness_clamps_full_request_and_rejects_forbidden_event() -> None:
    result = derive_meta_narrative_awareness(
        module_runtime_policy={"meta_narrative_awareness_policy": _policy()},
        story_runtime_experience={
            "meta_narrative_awareness_enabled": True,
            "meta_narrative_awareness_intensity": "full_fourth_wall",
            "meta_narrative_trigger_frequency": "frequent",
            "meta_narrative_characters_with_awareness": ["veronique"],
        },
        selected_responder_set=[{"actor_id": "veronique"}],
    )
    target = result["target"]
    validation = validate_meta_narrative_awareness_realization(
        meta_narrative_awareness_target=target,
        structured_output={
            "meta_narrative_awareness_events": [
                {
                    "actor_id": "michel",
                    "awareness_mode": "system_prompt_disclosure",
                    "discloses_system_prompt": True,
                    "direct_player_address": True,
                    "fourth_wall_level": "full",
                }
            ]
        },
    )

    assert target["intensity"] == "subtle"
    assert "meta_narrative_requested_intensity_clamped" in target["rationale_codes"]
    assert "meta_narrative_requested_frequency_clamped" in target["rationale_codes"]
    assert validation["contract_pass"] is False
    assert META_NARRATIVE_FAILURE_UNAUTHORIZED_ACTOR in validation["failure_codes"]
    assert META_NARRATIVE_FAILURE_FORBIDDEN_MODE in validation["failure_codes"]
    assert META_NARRATIVE_FAILURE_SYSTEM_DISCLOSURE in validation["failure_codes"]
    assert META_NARRATIVE_FAILURE_DIRECT_ADDRESS in validation["failure_codes"]
