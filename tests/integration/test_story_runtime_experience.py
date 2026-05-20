"""Story Runtime Experience: config + packaging truth tests.

Evidence for operator-configurable scene delivery. These tests are
intentionally storage-agnostic — they run on the pure ``ai_stack`` pieces so
they prove the truth-surface and mode-difference contract without needing a
live backend or docker stack.
"""

from __future__ import annotations

import pytest

from ai_stack.story_runtime.story_runtime_experience import (
    DEGRADATION_LIVE_NOT_FULLY_HONORED,
    DEGRADATION_PULSE_CAP_APPLIED,
    canonical_defaults,
    extract_policy_from_resolved_config,
    normalize_story_runtime_experience,
    resolve_story_runtime_experience_policy,
    validate_story_runtime_experience,
)
from ai_stack.story_runtime.story_runtime_experience_packaging import package_bundle_with_policy


# -- Canonical settings model --------------------------------------------


def test_canonical_defaults_are_recap_and_safe():
    defaults = canonical_defaults()
    assert defaults["experience_mode"] == "turn_based_narrative_recap"
    assert defaults["delivery_profile"] == "classic_recap"
    assert defaults["max_scene_pulses_per_response"] == 1
    assert defaults["allow_scene_progress_without_player_action"] is False
    assert defaults.get("npc_spoken_action_text_char_cap") == 1200
    assert defaults["meta_narrative_awareness_enabled"] is False
    assert defaults["meta_narrative_awareness_tier"] == "off"
    assert defaults["meta_narrative_awareness_intensity"] == "subtle"
    assert defaults["meta_narrative_characters_with_awareness"] == []
    assert defaults["meta_narrative_allow_direct_player_address"] is False
    assert defaults["meta_narrative_allow_cross_session_memory"] is False


def test_normalize_drops_unknown_keys_and_coerces():
    normalized = normalize_story_runtime_experience(
        {
            "experience_mode": "dramatic_turn",
            "delivery_profile": "lean_dramatic",
            "prose_density": "HIGH",
            "max_scene_pulses_per_response": "2",
            "allow_scene_progress_without_player_action": "true",
            "unknown_key": "dropped",
        }
    )
    assert normalized["experience_mode"] == "dramatic_turn"
    assert normalized["delivery_profile"] == "lean_dramatic"
    assert normalized["prose_density"] == "high"
    assert normalized["max_scene_pulses_per_response"] == 2
    assert normalized["allow_scene_progress_without_player_action"] is True
    assert "unknown_key" not in normalized
    assert normalized.get("npc_spoken_action_text_char_cap") == 1200


def test_normalize_meta_narrative_awareness_opt_in_settings():
    normalized = normalize_story_runtime_experience(
        {
            "meta_narrative_awareness_enabled": "true",
            "meta_narrative_awareness_tier": "FULL",
            "meta_narrative_awareness_intensity": "FULL_FOURTH_WALL",
            "meta_narrative_trigger_frequency": "OCCASIONAL",
            "meta_narrative_characters_with_awareness": ["veronique", "", "veronique"],
            "meta_narrative_allow_player_toggle": "false",
            "meta_narrative_allow_direct_player_address": "true",
            "meta_narrative_allow_narrator_negotiation": "true",
            "meta_narrative_allow_cross_session_memory": "true",
            "meta_narrative_memory_retention_scope": "CROSS_SESSION",
            "meta_narrative_max_direct_addresses_per_turn": "2",
        }
    )
    policy = resolve_story_runtime_experience_policy(normalized)

    assert normalized["meta_narrative_awareness_enabled"] is True
    assert normalized["meta_narrative_awareness_tier"] == "full"
    assert normalized["meta_narrative_awareness_intensity"] == "full_fourth_wall"
    assert normalized["meta_narrative_trigger_frequency"] == "occasional"
    assert normalized["meta_narrative_characters_with_awareness"] == ["veronique"]
    assert normalized["meta_narrative_allow_player_toggle"] is False
    assert normalized["meta_narrative_allow_direct_player_address"] is True
    assert normalized["meta_narrative_allow_narrator_negotiation"] is True
    assert normalized["meta_narrative_allow_cross_session_memory"] is True
    assert normalized["meta_narrative_memory_retention_scope"] == "cross_session"
    assert normalized["meta_narrative_max_direct_addresses_per_turn"] == 2
    assert policy.meta_narrative_awareness_enabled is True
    assert policy.meta_narrative_awareness_tier == "full"
    assert policy.meta_narrative_awareness_intensity == "full_fourth_wall"
    assert policy.meta_narrative_characters_with_awareness == ["veronique"]
    assert policy.meta_narrative_allow_direct_player_address is True
    assert policy.meta_narrative_allow_cross_session_memory is True


def test_normalize_clamps_npc_spoken_action_text_char_cap():
    n = normalize_story_runtime_experience({"npc_spoken_action_text_char_cap": 50_000})
    assert n["npc_spoken_action_text_char_cap"] == 8000
    n2 = normalize_story_runtime_experience({"npc_spoken_action_text_char_cap": 100})
    assert n2["npc_spoken_action_text_char_cap"] == 400


def test_policy_npc_spoken_action_text_char_cap_property():
    policy = resolve_story_runtime_experience_policy(canonical_defaults())
    assert policy.npc_spoken_action_text_char_cap == 1200


def test_delivery_profile_overrides_apply_before_advanced_fields():
    # Pick npc_forward profile without overriding dialogue_priority; it should
    # pick up the profile override.
    normalized = normalize_story_runtime_experience(
        {"experience_mode": "dramatic_turn", "delivery_profile": "npc_forward"}
    )
    assert normalized["dialogue_priority"] == "high"
    assert normalized["npc_initiative"] == "assertive"


def test_validate_catches_misleading_live_combination():
    warnings = validate_story_runtime_experience(
        {
            **canonical_defaults(),
            "experience_mode": "live_dramatic_scene_simulator",
            "max_scene_pulses_per_response": 1,
            "inter_npc_exchange_intensity": "off",
        }
    )
    assert warnings, "live mode with 1 pulse + no exchange should warn"


def test_validate_catches_auto_progress_on_recap():
    warnings = validate_story_runtime_experience(
        {
            **canonical_defaults(),
            "experience_mode": "turn_based_narrative_recap",
            "allow_scene_progress_without_player_action": True,
        }
    )
    assert any("allow_scene_progress" in w for w in warnings)


# -- Policy caps and degradation markers ----------------------------------


def test_recap_policy_caps_pulses_and_exchange():
    policy = resolve_story_runtime_experience_policy(
        {
            **canonical_defaults(),
            "experience_mode": "turn_based_narrative_recap",
            "max_scene_pulses_per_response": 3,
            "inter_npc_exchange_intensity": "strong",
            "allow_scene_progress_without_player_action": True,
        }
    )
    assert policy.effective["max_scene_pulses_per_response"] == 1
    assert policy.effective["inter_npc_exchange_intensity"] == "off"
    assert policy.effective["allow_scene_progress_without_player_action"] is False
    marker_ids = {m["marker"] for m in policy.degradation_markers}
    assert DEGRADATION_PULSE_CAP_APPLIED in marker_ids


def test_dramatic_turn_caps_to_two_pulses():
    policy = resolve_story_runtime_experience_policy(
        {
            **canonical_defaults(),
            "experience_mode": "dramatic_turn",
            "max_scene_pulses_per_response": 3,
        }
    )
    assert policy.effective["max_scene_pulses_per_response"] == 2


def test_live_mode_is_marked_partial_foundation():
    policy = resolve_story_runtime_experience_policy(
        {
            **canonical_defaults(),
            "experience_mode": "live_dramatic_scene_simulator",
            "max_scene_pulses_per_response": 3,
            "inter_npc_exchange_intensity": "strong",
        }
    )
    marker_ids = {m["marker"] for m in policy.degradation_markers}
    assert DEGRADATION_LIVE_NOT_FULLY_HONORED in marker_ids, (
        "live mode must be truthfully reported as partial foundation, not as fully honored"
    )


def test_extract_policy_from_resolved_config_missing_section_uses_defaults():
    policy = extract_policy_from_resolved_config({})
    assert policy.experience_mode == "turn_based_narrative_recap"


# -- Packaging mode differences ------------------------------------------


def _raw_bundle() -> dict:
    return {
        "gm_narration": [
            "Michel leans forward with a tight smile. \"We should be calm about this.\" "
            "Annette glances toward the door. Veronique steps closer to the coffee table. "
            "The room presses in around the four of them, and nobody moves for a long beat."
        ],
        "spoken_lines": [],
        "responder_actor_id": "michel_longstreet",
    }


def test_recap_packaging_is_narration_dominant():
    policy = resolve_story_runtime_experience_policy(
        {**canonical_defaults(), "experience_mode": "turn_based_narrative_recap"}
    )
    packaged = package_bundle_with_policy(_raw_bundle(), policy)
    meta = packaged["experience_packaging"]
    assert meta["experience_mode"] == "turn_based_narrative_recap"
    # Recap caps spoken lines to at most 2 and pulses to 1.
    assert meta["spoken_line_cap"] <= 2
    assert meta["pulse_cap"] == 1


def test_dramatic_turn_packaging_promotes_dialogue_and_action():
    policy = resolve_story_runtime_experience_policy(
        {
            **canonical_defaults(),
            "experience_mode": "dramatic_turn",
            "delivery_profile": "lean_dramatic",
        }
    )
    packaged = package_bundle_with_policy(_raw_bundle(), policy)
    meta = packaged["experience_packaging"]
    assert meta["experience_mode"] == "dramatic_turn"
    assert meta["pulse_cap"] >= 1
    assert meta["spoken_line_cap"] >= 3
    assert "narration_blocks" in packaged
    assert "action_pulses" in packaged


def test_live_packaging_may_emit_multiple_pulses():
    policy = resolve_story_runtime_experience_policy(
        {
            **canonical_defaults(),
            "experience_mode": "live_dramatic_scene_simulator",
            "delivery_profile": "cinematic_live",
            "max_scene_pulses_per_response": 3,
        }
    )
    packaged = package_bundle_with_policy(_raw_bundle(), policy)
    meta = packaged["experience_packaging"]
    assert meta["experience_mode"] == "live_dramatic_scene_simulator"
    assert meta["pulse_cap"] <= 3
    # Continuation state must surface so frontend can show scene_continues.
    assert packaged["continuation_state"]["scene_continues"] is True


def test_modes_produce_materially_different_packaging():
    raw = _raw_bundle()
    recap = package_bundle_with_policy(
        raw,
        resolve_story_runtime_experience_policy(
            {**canonical_defaults(), "experience_mode": "turn_based_narrative_recap"}
        ),
    )
    dramatic = package_bundle_with_policy(
        raw,
        resolve_story_runtime_experience_policy(
            {
                **canonical_defaults(),
                "experience_mode": "dramatic_turn",
                "delivery_profile": "lean_dramatic",
            }
        ),
    )
    live = package_bundle_with_policy(
        raw,
        resolve_story_runtime_experience_policy(
            {
                **canonical_defaults(),
                "experience_mode": "live_dramatic_scene_simulator",
                "delivery_profile": "cinematic_live",
                "max_scene_pulses_per_response": 3,
            }
        ),
    )
    # Mode-difference proof: packaging contract metadata is not identical.
    assert recap["experience_packaging"]["experience_mode"] != dramatic["experience_packaging"]["experience_mode"]
    assert dramatic["experience_packaging"]["experience_mode"] != live["experience_packaging"]["experience_mode"]
    # Spoken-line caps increase along the mode spectrum.
    assert (
        recap["experience_packaging"]["spoken_line_cap"]
        <= dramatic["experience_packaging"]["spoken_line_cap"]
        <= live["experience_packaging"]["spoken_line_cap"]
    )
    # Pulse caps increase along the mode spectrum.
    assert (
        recap["experience_packaging"]["pulse_cap"]
        <= dramatic["experience_packaging"]["pulse_cap"]
        <= live["experience_packaging"]["pulse_cap"]
    )


def test_truth_surface_includes_degradation_markers():
    policy = resolve_story_runtime_experience_policy(
        {
            **canonical_defaults(),
            "experience_mode": "live_dramatic_scene_simulator",
        }
    )
    surface = policy.to_truth_surface()
    assert surface["configured"]["experience_mode"] == "live_dramatic_scene_simulator"
    assert surface["effective"]["experience_mode"] == "live_dramatic_scene_simulator"
    # Live mode is explicitly partial — the degradation markers must say so
    # or the UI could dishonestly claim full support.
    assert any(m["marker"] == DEGRADATION_LIVE_NOT_FULLY_HONORED for m in surface["degradation_markers"])
    assert surface["packaging_contract_version"]


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
