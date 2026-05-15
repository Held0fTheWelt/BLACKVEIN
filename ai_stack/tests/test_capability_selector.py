from __future__ import annotations

import re

import pytest

from ai_stack.capability_selector import (
    CAP_ACTION_RESOLUTION,
    CAP_BROAD_NLU_LISTENING,
    CAP_CALLBACK_WEB,
    CAP_CONVERSATIONAL_MEMORY,
    CAP_CONSEQUENCE_CASCADE,
    CAP_DRAMATIC_IRONY,
    CAP_ENVIRONMENT_STATE,
    CAP_GENRE_AWARENESS,
    CAP_INFORMATION_DISCLOSURE,
    CAP_LONG_HORIZON_FORECAST,
    CAP_NARRATOR_AUTHORITY,
    CAP_NPC_AGENCY,
    CAP_PLAYER_INTENT_INFERENCE,
    CAP_PROMPT_AUTHORITY,
    CAP_SCENE_ENERGY,
    CAP_SENSORY_CONTEXT,
    CAP_SILENCE_NEGATIVE_SPACE,
    CAP_THEMATIC_TRACKING,
    CAP_VOICE_CONSISTENCY,
    INITIAL_CAPABILITIES,
    CapabilityBudget,
    CapabilityMode,
    CapabilitySelectionResult,
    TurnSituation,
    derive_turn_situation_from_runtime_context,
    select_capabilities,
    validate_semantic_capability_name,
)


ACTIVE_LEGACY_KEY_RE = re.compile(
    r"Π\d+|(?<![A-Za-z0-9])pi_?\d+(?:\b|_)",
    re.IGNORECASE,
)


def _opening() -> TurnSituation:
    return TurnSituation(
        turn_kind="opening",
        active_actor="narrator",
        player_input_present=False,
        npc_decision_required=False,
        visible_projection_required=True,
        canonical_scene_seed=True,
    )


def test_opening_scene_selects_narrator_minimal_capabilities() -> None:
    result = select_capabilities(_opening())

    assert result.enforced == (
        CAP_NARRATOR_AUTHORITY,
        CAP_SCENE_ENERGY,
        CAP_ENVIRONMENT_STATE,
        CAP_INFORMATION_DISCLOSURE,
        CAP_VOICE_CONSISTENCY,
    )
    assert result.observed == (
        CAP_THEMATIC_TRACKING,
        CAP_CALLBACK_WEB,
        CAP_SENSORY_CONTEXT,
        CAP_GENRE_AWARENESS,
    )
    assert len(result.enforced) == 5
    assert len(result.enforced) < len(INITIAL_CAPABILITIES)


def test_opening_scene_disables_expensive_judges() -> None:
    result = select_capabilities(_opening())

    assert result.budget.max_enforced_capabilities == 5
    assert result.budget.allow_llm_judges is False
    assert result.budget.allow_heavy_forecast is False
    assert result.judged == ()
    assert "llm_judges_disabled_by_budget" in result.warnings
    assert "heavy_forecast_disabled_by_budget" in result.warnings


def test_opening_scene_does_not_select_npc_or_action_capabilities() -> None:
    result = select_capabilities(_opening())

    for capability in (
        CAP_NPC_AGENCY,
        CAP_PLAYER_INTENT_INFERENCE,
        CAP_ACTION_RESOLUTION,
        CAP_CONSEQUENCE_CASCADE,
        CAP_LONG_HORIZON_FORECAST,
        CAP_SILENCE_NEGATIVE_SPACE,
        CAP_DRAMATIC_IRONY,
    ):
        assert capability in result.excluded
        assert capability not in result.enforced
        assert capability not in result.observed


def test_player_turn_selects_action_resolution_without_forecast_by_default() -> None:
    result = select_capabilities(
        TurnSituation(
            turn_kind="player_input",
            active_actor="player",
            player_input_present=True,
            action_resolution_required=True,
            visible_projection_required=True,
        )
    )

    assert result.enforced == (
        CAP_PLAYER_INTENT_INFERENCE,
        CAP_ACTION_RESOLUTION,
        CAP_INFORMATION_DISCLOSURE,
        CAP_VOICE_CONSISTENCY,
        CAP_SCENE_ENERGY,
    )
    assert result.observed == (
        CAP_ENVIRONMENT_STATE,
        CAP_BROAD_NLU_LISTENING,
        CAP_CONVERSATIONAL_MEMORY,
        CAP_PROMPT_AUTHORITY,
        CAP_THEMATIC_TRACKING,
        CAP_CALLBACK_WEB,
        CAP_GENRE_AWARENESS,
    )
    assert CAP_LONG_HORIZON_FORECAST in result.excluded
    assert CAP_CONSEQUENCE_CASCADE in result.excluded


def test_npc_conflict_selects_npc_agency_and_voice_consistency() -> None:
    result = select_capabilities(
        TurnSituation(
            turn_kind="npc_turn",
            active_actor="npc",
            npc_decision_required=True,
            interpersonal_pressure="high",
            visible_projection_required=True,
            knowledge_gap_present=True,
        )
    )

    assert CAP_NPC_AGENCY in result.enforced
    assert CAP_VOICE_CONSISTENCY in result.enforced
    assert CAP_SCENE_ENERGY in result.enforced
    assert CAP_INFORMATION_DISCLOSURE in result.enforced
    assert CAP_DRAMATIC_IRONY in result.observed
    assert CAP_CALLBACK_WEB in result.observed
    assert CAP_THEMATIC_TRACKING in result.observed


def test_silence_negative_space_selected_only_for_non_lexical_input() -> None:
    ordinary = select_capabilities(
        TurnSituation(
            turn_kind="player_input",
            active_actor="player",
            player_input_present=True,
            action_resolution_required=True,
            visible_projection_required=True,
        )
    )
    non_lexical = select_capabilities(
        TurnSituation(
            turn_kind="player_input",
            active_actor="player",
            player_input_present=True,
            action_resolution_required=True,
            visible_projection_required=True,
            non_lexical_input_present=True,
        )
    )

    assert CAP_SILENCE_NEGATIVE_SPACE in ordinary.excluded
    assert CAP_SILENCE_NEGATIVE_SPACE in non_lexical.enforced


def test_dramatic_irony_selected_only_for_knowledge_gap() -> None:
    no_gap = select_capabilities(
        TurnSituation(
            turn_kind="npc_turn",
            active_actor="npc",
            npc_decision_required=True,
            interpersonal_pressure="high",
            visible_projection_required=True,
            knowledge_gap_present=False,
        )
    )
    gap = select_capabilities(
        TurnSituation(
            turn_kind="npc_turn",
            active_actor="npc",
            npc_decision_required=True,
            interpersonal_pressure="high",
            visible_projection_required=True,
            knowledge_gap_present=True,
        )
    )

    assert CAP_DRAMATIC_IRONY in no_gap.excluded
    assert CAP_DRAMATIC_IRONY in gap.observed


def test_consequence_cascade_requires_world_state_change() -> None:
    no_world_change = select_capabilities(
        TurnSituation(
            turn_kind="player_input",
            active_actor="player",
            player_input_present=True,
            action_resolution_required=True,
            visible_projection_required=True,
            world_state_change_requested=False,
        )
    )
    world_change = select_capabilities(
        TurnSituation(
            turn_kind="player_input",
            active_actor="player",
            player_input_present=True,
            action_resolution_required=True,
            visible_projection_required=True,
            world_state_change_requested=True,
        )
    )

    assert CAP_CONSEQUENCE_CASCADE in no_world_change.excluded
    assert CAP_CONSEQUENCE_CASCADE in world_change.enforced


def test_player_turn_with_npc_decision_signal_keeps_player_turn_authority() -> None:
    situation, warnings = derive_turn_situation_from_runtime_context(
        turn_kind="player",
        turn_number=2,
        raw_player_input="I ask what they are hiding.",
        input_kind="speech",
        npc_decision_required=True,
    )

    assert warnings == ()
    assert situation.turn_kind.value == "player_input"
    assert situation.active_actor.value == "player"
    assert situation.npc_decision_required is True

    result = select_capabilities(situation)
    assert CAP_PLAYER_INTENT_INFERENCE in result.enforced
    assert CAP_ACTION_RESOLUTION in result.enforced
    assert CAP_NPC_AGENCY in result.enforced


def test_budget_caps_enforced_capabilities() -> None:
    result = select_capabilities(
        _opening(),
        budget=CapabilityBudget(max_enforced_capabilities=3),
    )

    assert result.enforced == (
        CAP_NARRATOR_AUTHORITY,
        CAP_SCENE_ENERGY,
        CAP_ENVIRONMENT_STATE,
    )
    assert len(result.enforced) == 3
    assert any(warning.startswith("budget_dropped:") for warning in result.warnings)


def test_selector_rejects_or_excludes_active_pi_labels() -> None:
    assert not any(ACTIVE_LEGACY_KEY_RE.search(capability) for capability in INITIAL_CAPABILITIES)

    for legacy_name in ("pi14", "pi_14", "Pi14", "Π14"):
        with pytest.raises(ValueError):
            validate_semantic_capability_name(legacy_name)


def test_selection_projection_is_runtime_ledger_compatible() -> None:
    result = select_capabilities(_opening())

    projection = result.to_runtime_aspect_projection()
    payload = projection["capability_selection"]

    assert payload["turn_kind"] == "opening"
    assert payload["active_actor"] == "narrator"
    assert payload["selected"] == list(result.enforced)
    assert payload["observed_only"] == list(result.observed)
    assert payload["excluded"] == list(result.excluded)
    assert payload["budget"]["max_enforced"] == 5
    assert payload["budget"]["llm_judges_allowed"] is False
    assert payload["activation_modes"][CAP_NARRATOR_AUTHORITY] == CapabilityMode.ENFORCE.value
    assert payload["activation_modes"][CAP_SENSORY_CONTEXT] == CapabilityMode.OBSERVE.value
    assert payload["activation_modes"][CAP_NPC_AGENCY] == CapabilityMode.OFF.value


def test_judge_mode_does_not_downgrade_enforced_capabilities() -> None:
    result = CapabilitySelectionResult(
        situation=_opening(),
        budget=CapabilityBudget(max_enforced_capabilities=5, allow_llm_judges=True),
        enforced=(CAP_VOICE_CONSISTENCY,),
        observed=(CAP_SENSORY_CONTEXT,),
        judged=(CAP_VOICE_CONSISTENCY, CAP_SENSORY_CONTEXT),
    )

    modes = result.activation_modes()

    assert modes[CAP_VOICE_CONSISTENCY] == CapabilityMode.ENFORCE.value
    assert modes[CAP_SENSORY_CONTEXT] == CapabilityMode.JUDGE.value


def test_recoverable_runtime_turn_kinds_derive_recovery_situation() -> None:
    for turn_kind in ("player_rejected_recoverable", "player_graph_exception_playable"):
        situation, warnings = derive_turn_situation_from_runtime_context(
            turn_kind=turn_kind,
            turn_number=2,
            raw_player_input="anything",
        )

        assert situation.turn_kind.value == "recovery"
        assert situation.active_actor.value == "system"
        assert situation.last_turn_quality.value == "fallback"
        assert warnings == ()


def test_explicit_recovery_turn_derives_non_fallback_recovery_situation() -> None:
    situation, warnings = derive_turn_situation_from_runtime_context(
        turn_kind="recovery_turn",
        turn_number=3,
        raw_player_input="",
    )
    assert situation.turn_kind.value == "recovery"
    assert situation.active_actor.value == "system"
    assert situation.last_turn_quality.value == "degraded"
    assert warnings == ()


def test_system_transition_turn_kind_derives_system_transition_situation() -> None:
    situation, warnings = derive_turn_situation_from_runtime_context(
        turn_kind="system_transition",
        turn_number=4,
        raw_player_input="",
    )
    assert situation.turn_kind.value == "system_transition"
    assert situation.active_actor.value == "system"
    assert warnings == ()


def test_selection_projection_does_not_claim_live_or_staging_evidence() -> None:
    result = select_capabilities(_opening())
    payload = result.to_ledger_payload()["capability_selection"]

    assert payload["evidence_scope"] == "local_runtime_selection"
    assert payload["proof_level"] == "local_only"
    assert payload["live_or_staging_evidence"] is False
    assert payload["implementation_proof"] is False
    assert payload["implemented_by_runtime"] is False
    assert payload["live_verified"] is False
    assert payload["staging_verified"] is False
    assert payload["provider_verified"] is False
    assert payload["capability_promoted"] is False
