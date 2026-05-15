from __future__ import annotations

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
    ActiveActor,
    TurnKind,
    TurnSituation,
    select_capabilities,
    validate_semantic_capability_name,
)
from ai_stack.capability_validator_plan import (
    JUDGE_VALIDATORS,
    VALIDATOR_PLAN_REASON,
    ValidatorPlanMode,
    build_validator_execution_plan,
)


def _opening_selection():
    return select_capabilities(
        TurnSituation(
            turn_kind=TurnKind.OPENING,
            active_actor=ActiveActor.NARRATOR,
            player_input_present=False,
            npc_decision_required=False,
            visible_projection_required=True,
            canonical_scene_seed=True,
        )
    )


def _player_selection():
    return select_capabilities(
        TurnSituation(
            turn_kind=TurnKind.PLAYER_INPUT,
            active_actor=ActiveActor.PLAYER,
            player_input_present=True,
            action_resolution_required=True,
            visible_projection_required=True,
        )
    )


def test_opening_validator_plan_runs_only_enforced_local_validators() -> None:
    plan = build_validator_execution_plan(_opening_selection())

    assert plan.validators_to_run == [
        "narrator_authority_contract",
        "scene_energy_contract",
        "environment_state_contract",
        "information_disclosure_contract",
        "voice_consistency_contract",
    ]
    local_entries = [
        entry for entry in plan.entries if entry.mode is ValidatorPlanMode.RUN_LOCAL_VALIDATOR
    ]
    assert [entry.capability for entry in local_entries] == [
        CAP_NARRATOR_AUTHORITY,
        CAP_SCENE_ENERGY,
        CAP_ENVIRONMENT_STATE,
        CAP_INFORMATION_DISCLOSURE,
        CAP_VOICE_CONSISTENCY,
    ]
    assert all(entry.blocking is True for entry in local_entries)
    assert all(entry.planned_only is True for entry in local_entries)


def test_opening_validator_plan_observes_only_observed_capabilities() -> None:
    plan = build_validator_execution_plan(_opening_selection())

    assert plan.observer_diagnostics == [
        "thematic_tracking_diagnostic",
        "callback_web_diagnostic",
        "sensory_context_diagnostic",
        "genre_awareness_diagnostic",
    ]
    diagnostic_entries = [
        entry for entry in plan.entries if entry.mode is ValidatorPlanMode.RUN_OBSERVER_DIAGNOSTIC
    ]
    assert [entry.capability for entry in diagnostic_entries] == [
        CAP_THEMATIC_TRACKING,
        CAP_CALLBACK_WEB,
        CAP_SENSORY_CONTEXT,
        CAP_GENRE_AWARENESS,
    ]
    assert all(entry.blocking is False for entry in diagnostic_entries)


def test_opening_validator_plan_skips_npc_action_cascade_forecast() -> None:
    plan = build_validator_execution_plan(_opening_selection())

    assert plan.validators_skipped == [
        "broad_nlu_listening_diagnostic",
        "conversational_memory_diagnostic",
        "prompt_authority_diagnostic",
        "npc_agency_contract",
        "player_intent_contract",
        "action_resolution_contract",
        "consequence_cascade_contract",
        "forecast_contract",
        "silence_negative_space_contract",
        "dramatic_irony_contract",
    ]
    skipped_capabilities = {
        entry.capability
        for entry in plan.entries
        if entry.mode is ValidatorPlanMode.SKIP_EXCLUDED
    }
    assert {
        CAP_BROAD_NLU_LISTENING,
        CAP_CONVERSATIONAL_MEMORY,
        CAP_PROMPT_AUTHORITY,
        CAP_NPC_AGENCY,
        CAP_PLAYER_INTENT_INFERENCE,
        CAP_ACTION_RESOLUTION,
        CAP_CONSEQUENCE_CASCADE,
        CAP_LONG_HORIZON_FORECAST,
        CAP_SILENCE_NEGATIVE_SPACE,
        CAP_DRAMATIC_IRONY,
    } <= skipped_capabilities


def test_validator_plan_marks_execution_changed_false() -> None:
    payload = build_validator_execution_plan(_opening_selection()).to_runtime_projection()[
        "validator_execution_plan"
    ]

    assert payload["execution_changed"] is False
    assert payload["reason"] == VALIDATOR_PLAN_REASON
    assert payload["validators_to_run"]


def test_validator_plan_is_local_only() -> None:
    payload = build_validator_execution_plan(_opening_selection()).to_ledger_payload()[
        "validator_execution_plan"
    ]

    assert payload["proof_level"] == "local_only"
    assert payload["evidence_scope"] == "local_runtime_selection"
    assert payload["live_or_staging_evidence"] is False
    assert payload["implementation_proof"] is False
    assert payload["implemented_by_runtime"] is False
    assert payload["live_verified"] is False
    assert payload["staging_verified"] is False
    assert payload["provider_verified"] is False
    assert payload["capability_promoted"] is False


def test_validator_plan_uses_semantic_names_only() -> None:
    payload = build_validator_execution_plan(_opening_selection()).to_runtime_projection()[
        "validator_execution_plan"
    ]
    plan_ids = [
        *payload["validators_to_run"],
        *payload["observer_diagnostics"],
        *payload["validators_skipped"],
        *payload["judges_to_run"],
        *payload["judges_disallowed"],
    ]
    entry_ids = [
        value
        for entry in payload["entries"]
        for value in (
            entry.get("capability"),
            entry.get("plan_id"),
            entry.get("validator_id"),
            entry.get("diagnostic_id"),
            entry.get("judge_id"),
        )
        if value
    ]

    assert plan_ids
    assert all(validate_semantic_capability_name(item) == item for item in plan_ids)
    assert all(validate_semantic_capability_name(item) == item for item in entry_ids)


def test_player_turn_validator_plan_includes_action_resolution() -> None:
    plan = build_validator_execution_plan(_player_selection())

    assert "action_resolution_contract" in plan.validators_to_run
    assert "player_intent_contract" in plan.validators_to_run
    assert "forecast_contract" in plan.validators_skipped


def test_judge_validators_disallowed_when_budget_disallows_judges() -> None:
    plan = build_validator_execution_plan(_opening_selection())

    assert plan.judges_to_run == []
    assert len(plan.judges_disallowed) == len(JUDGE_VALIDATORS)
    assert "narrator_authority_judge" in plan.judges_disallowed
    assert "npc_agency_judge" in plan.judges_disallowed
    assert "action_resolution_judge" in plan.judges_disallowed
