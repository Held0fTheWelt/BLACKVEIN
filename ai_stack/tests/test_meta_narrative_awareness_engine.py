from __future__ import annotations

from ai_stack.contracts.meta_narrative_awareness_contracts import (
    META_NARRATIVE_AWARENESS_SCHEMA_VERSION,
    META_NARRATIVE_AWARENESS_SCHEMA_VERSION_V2,
    META_NARRATIVE_FAILURE_CONSENT_SCOPE_EXCEEDED,
    META_NARRATIVE_FAILURE_CROSS_SESSION_MEMORY_UNVERIFIED,
    META_NARRATIVE_FAILURE_DIRECT_ADDRESS,
    META_NARRATIVE_FAILURE_FALSE_SELF_MEMORY,
    META_NARRATIVE_FAILURE_FORBIDDEN_MODE,
    META_NARRATIVE_FAILURE_NOT_OPTED_IN,
    META_NARRATIVE_FAILURE_PRIVACY_BOUNDARY,
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


def _full_policy() -> dict[str, object]:
    return normalize_meta_narrative_awareness_policy(
        {
            "enabled": True,
            "schema_version": "meta_narrative_awareness_policy.v2",
            "allowed_awareness_tiers": ["subtle", "adaptive", "full"],
            "default_awareness_tier": "subtle",
            "allowed_intensities": ["subtle", "moderate", "full_fourth_wall"],
            "allowed_trigger_frequencies": ["rare", "occasional", "frequent"],
            "characters_with_awareness": ["veronique"],
            "allowed_awareness_modes": [
                "dramatic_pattern_sense",
                "adaptive_pattern_recognition",
                "direct_player_address",
                "narrator_negotiation",
                "cross_session_memory_reference",
            ],
            "allowed_fourth_wall_levels": ["none", "subtle", "direct", "full_fourth_wall"],
            "max_events_per_turn": 2,
            "max_direct_addresses_per_turn": 1,
            "allow_direct_player_address": True,
            "allow_narrator_negotiation": True,
            "allow_cross_session_memory": True,
            "allowed_memory_scopes": ["session", "cross_session"],
            "default_memory_retention_scope": "cross_session",
            "max_cross_session_memory_refs": 2,
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


def test_full_meta_narrative_awareness_allows_direct_address_and_verified_memory_ref() -> None:
    result = derive_meta_narrative_awareness(
        module_runtime_policy={"meta_narrative_awareness_policy": _full_policy()},
        story_runtime_experience={
            "meta_narrative_awareness_enabled": True,
            "meta_narrative_awareness_tier": "full",
            "meta_narrative_awareness_intensity": "full_fourth_wall",
            "meta_narrative_trigger_frequency": "frequent",
            "meta_narrative_characters_with_awareness": ["veronique"],
            "meta_narrative_allow_direct_player_address": True,
            "meta_narrative_allow_narrator_negotiation": True,
            "meta_narrative_allow_cross_session_memory": True,
        },
        selected_responder_set=[{"actor_id": "veronique"}],
        social_pressure_target={"target_band": "high", "trend": "rising"},
        dramatic_irony_record={"selected_opportunity_ids": ["irony_alpha"]},
        relationship_state_record={
            "pressure_band": "high",
            "transition_events": [{"transition_code": "trust_fracture"}],
        },
        semantic_move_record={"move_type": "probe_motive"},
        hierarchical_memory_context={
            "items": [
                {"memory_id": "mem_return_1", "tier": "cross_session"},
                {"memory_id": "mem_return_2", "tier": "actor"},
            ]
        },
    )
    target = result["target"]
    compact = compact_meta_narrative_awareness_context(target)
    validation = validate_meta_narrative_awareness_realization(
        meta_narrative_awareness_target=target,
        structured_output={
            "meta_narrative_awareness_events": [
                {
                    "actor_id": "veronique",
                    "awareness_mode": "direct_player_address",
                    "fourth_wall_level": "full_fourth_wall",
                    "direct_player_address": True,
                    "memory_ref_ids": ["mem_return_1"],
                    "player_agency_preserved": True,
                    "system_disclosure_absent": True,
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

    assert target["schema_version"] == META_NARRATIVE_AWARENESS_SCHEMA_VERSION_V2
    assert target["awareness_tier"] == "full"
    assert target["direct_player_address_allowed"] is True
    assert target["cross_session_memory_allowed"] is True
    assert target["selected_memory_ref_ids"] == ["mem_return_1", "mem_return_2"]
    assert "meta_narrative_adaptive_memory_context" in target["adaptive_signal_codes"]
    assert compact["max_direct_addresses_per_turn"] == 1
    assert compact["selected_memory_ref_ids"] == ["mem_return_1", "mem_return_2"]
    assert validation["status"] == "approved"
    assert validation["actual"]["direct_address_count"] == 1
    assert validation["actual"]["realized_memory_ref_ids"] == ["mem_return_1"]
    assert aspect["selected"]["awareness_tier"] == "full"
    assert aspect["selected"]["selected_memory_ref_ids"] == ["mem_return_1", "mem_return_2"]


def test_cross_session_meta_memory_rejects_unverified_or_private_claims() -> None:
    result = derive_meta_narrative_awareness(
        module_runtime_policy={"meta_narrative_awareness_policy": _full_policy()},
        story_runtime_experience={
            "meta_narrative_awareness_enabled": True,
            "meta_narrative_awareness_tier": "full",
            "meta_narrative_awareness_intensity": "full_fourth_wall",
            "meta_narrative_trigger_frequency": "frequent",
            "meta_narrative_characters_with_awareness": ["veronique"],
            "meta_narrative_allow_direct_player_address": True,
            "meta_narrative_allow_cross_session_memory": True,
        },
        selected_responder_set=[{"actor_id": "veronique"}],
        hierarchical_memory_context={"items": [{"memory_id": "mem_allowed"}]},
    )
    validation = validate_meta_narrative_awareness_realization(
        meta_narrative_awareness_target=result["target"],
        structured_output={
            "meta_narrative_awareness_events": [
                {
                    "actor_id": "veronique",
                    "awareness_mode": "cross_session_memory_reference",
                    "fourth_wall_level": "full_fourth_wall",
                    "memory_ref_ids": ["mem_fabricated"],
                    "quotes_raw_player_input": True,
                    "invented_memory": True,
                }
            ]
        },
    )

    assert validation["contract_pass"] is False
    assert META_NARRATIVE_FAILURE_CROSS_SESSION_MEMORY_UNVERIFIED in validation["failure_codes"]
    assert META_NARRATIVE_FAILURE_PRIVACY_BOUNDARY in validation["failure_codes"]
    assert META_NARRATIVE_FAILURE_FALSE_SELF_MEMORY in validation["failure_codes"]
    assert META_NARRATIVE_FAILURE_CONSENT_SCOPE_EXCEEDED not in validation["failure_codes"]
