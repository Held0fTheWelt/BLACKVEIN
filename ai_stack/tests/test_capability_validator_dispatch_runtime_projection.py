from __future__ import annotations

from ai_stack.runtime_aspect_ledger import (
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_COMMIT,
    ASPECT_VALIDATION,
    initialize_runtime_aspect_ledger,
)


def _opening_dispatch_report() -> dict:
    ledger = initialize_runtime_aspect_ledger(
        session_id="validator-dispatch-opening",
        module_id="example_module",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    return ledger["runtime_intelligence_projection"]["validator_dispatch_report"]


def test_runtime_projection_contains_validator_dispatch_report() -> None:
    report = _opening_dispatch_report()

    assert report["mode"] == "dry_run"
    assert report["validators_would_run"] == [
        "narrator_authority_contract",
        "scene_energy_contract",
        "environment_state_contract",
        "information_disclosure_contract",
        "voice_consistency_contract",
    ]
    assert report["diagnostics_would_run"] == [
        "thematic_tracking_diagnostic",
        "callback_web_diagnostic",
        "sensory_context_diagnostic",
    ]
    assert report["reason"].startswith("ADR-0041 dry-run dispatch projection only")


def test_opening_dispatch_runtime_projection_skips_excluded_validators() -> None:
    report = _opening_dispatch_report()

    for validator_id in (
        "npc_agency_contract",
        "player_intent_contract",
        "action_resolution_contract",
        "consequence_cascade_contract",
        "forecast_contract",
        "silence_negative_space_contract",
        "dramatic_irony_contract",
    ):
        assert validator_id in report["validators_would_skip"]


def test_opening_dispatch_runtime_projection_disallows_judges_by_budget() -> None:
    report = _opening_dispatch_report()

    assert "narrator_authority_judge" in report["judges_would_be_disallowed"]
    assert "scene_energy_judge" in report["judges_would_be_disallowed"]


def test_dispatch_projection_is_local_only() -> None:
    report = _opening_dispatch_report()

    assert report["proof_level"] == "local_only"
    assert report["live_or_staging_evidence"] is False
    assert report["capability_promoted"] is False


def test_dispatch_projection_marks_execution_changed_false() -> None:
    report = _opening_dispatch_report()

    assert report["execution_changed"] is False
    assert report["actually_executed"] == []


def test_dispatch_does_not_change_commit_or_readiness_status() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="validator-dispatch-readiness",
        module_id="example_module",
        turn_number=1,
        turn_kind="player",
        raw_player_input="I check the hallway.",
    )

    aspects = ledger["turn_aspect_ledger"]
    assert "validator_dispatch_report" in ledger["runtime_intelligence_projection"]
    assert ledger["runtime_intelligence_projection"]["validator_dispatch_report"][
        "execution_changed"
    ] is False
    assert aspects[ASPECT_CAPABILITY_SELECTION]["status"] == "missing"
    assert aspects[ASPECT_VALIDATION]["status"] == "missing"
    assert aspects[ASPECT_COMMIT]["status"] == "missing"
    assert "validator_dispatch" not in aspects
