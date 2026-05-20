from __future__ import annotations

from ai_stack.story_runtime.runtime_aspect_ledger import (
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_COMMIT,
    ASPECT_VALIDATION,
    initialize_runtime_aspect_ledger,
)


def _opening_validator_plan() -> dict:
    ledger = initialize_runtime_aspect_ledger(
        session_id="validator-plan-opening",
        module_id="example_module",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    return ledger["runtime_intelligence_projection"]["validator_execution_plan"]


def test_runtime_projection_contains_validator_execution_plan() -> None:
    plan = _opening_validator_plan()

    assert plan["validators_to_run"] == [
        "narrator_authority_contract",
        "scene_energy_contract",
        "environment_state_contract",
        "information_disclosure_contract",
        "voice_consistency_contract",
    ]
    assert plan["observer_diagnostics"] == [
        "thematic_tracking_diagnostic",
        "callback_web_diagnostic",
        "sensory_context_diagnostic",
        "genre_awareness_diagnostic",
    ]
    assert plan["reason"] == "planned from ADR-0041 capability selection; not executed yet"


def test_runtime_projection_validator_plan_is_local_only() -> None:
    plan = _opening_validator_plan()

    assert plan["proof_level"] == "local_only"
    assert plan["live_or_staging_evidence"] is False
    assert plan["implementation_proof"] is False
    assert plan["implemented_by_runtime"] is False
    assert plan["live_verified"] is False
    assert plan["staging_verified"] is False
    assert plan["provider_verified"] is False
    assert plan["capability_promoted"] is False


def test_runtime_projection_validator_plan_skips_excluded_capabilities() -> None:
    plan = _opening_validator_plan()

    assert "npc_agency_contract" in plan["validators_skipped"]
    assert "broad_nlu_listening_diagnostic" in plan["validators_skipped"]
    assert "conversational_memory_diagnostic" in plan["validators_skipped"]
    assert "prompt_authority_diagnostic" in plan["validators_skipped"]
    assert "player_intent_contract" in plan["validators_skipped"]
    assert "action_resolution_contract" in plan["validators_skipped"]
    assert "consequence_cascade_contract" in plan["validators_skipped"]
    assert "forecast_contract" in plan["validators_skipped"]
    assert "silence_negative_space_contract" in plan["validators_skipped"]
    assert "dramatic_irony_contract" in plan["validators_skipped"]


def test_runtime_projection_validator_plan_disallows_judges_by_budget() -> None:
    plan = _opening_validator_plan()

    assert plan["judges_to_run"] == []
    assert "narrator_authority_judge" in plan["judges_disallowed"]
    assert "scene_energy_judge" in plan["judges_disallowed"]
    assert "npc_agency_judge" in plan["judges_disallowed"]
    assert "action_resolution_judge" in plan["judges_disallowed"]


def test_validator_plan_does_not_change_commit_or_readiness_status() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="validator-plan-readiness",
        module_id="example_module",
        turn_number=1,
        turn_kind="player",
        raw_player_input="I check the hallway.",
    )

    aspects = ledger["turn_aspect_ledger"]
    assert "validator_execution_plan" in ledger["runtime_intelligence_projection"]
    assert ledger["runtime_intelligence_projection"]["validator_execution_plan"][
        "execution_changed"
    ] is False
    assert aspects[ASPECT_CAPABILITY_SELECTION]["status"] == "missing"
    assert aspects[ASPECT_VALIDATION]["status"] == "missing"
    assert aspects[ASPECT_COMMIT]["status"] == "missing"
