from __future__ import annotations

import re

from ai_stack.capabilities.capability_selector import (
    ActiveActor,
    TurnKind,
    TurnSituation,
    select_capabilities,
    validate_semantic_capability_name,
)
from ai_stack.capabilities.capability_validator_dispatch import (
    DEFAULT_VALIDATOR_DISPATCH_MODE,
    DISPATCH_REPORT_REASON,
    ValidatorDispatchAction,
    ValidatorDispatchMode,
    build_validator_dispatch_report,
)
from ai_stack.capabilities.capability_validator_plan import build_validator_execution_plan


def _opening_plan():
    selection = select_capabilities(
        TurnSituation(
            turn_kind=TurnKind.OPENING,
            active_actor=ActiveActor.NARRATOR,
            player_input_present=False,
            npc_decision_required=False,
            visible_projection_required=True,
            canonical_scene_seed=True,
        )
    )
    return build_validator_execution_plan(selection)


def test_default_dispatch_mode_is_dry_run() -> None:
    report = build_validator_dispatch_report(_opening_plan())

    assert report.mode is ValidatorDispatchMode.DRY_RUN
    assert report.mode.value == DEFAULT_VALIDATOR_DISPATCH_MODE


def test_dry_run_dispatch_does_not_execute_validators() -> None:
    report = build_validator_dispatch_report(_opening_plan())

    assert report.actually_executed == ()
    assert all(entry.actually_executed is False for entry in report.entries)
    assert all(
        entry.would_execute is False or entry.actually_executed is False
        for entry in report.entries
    )


def test_opening_dispatch_reports_would_run_enforced_validators() -> None:
    report = build_validator_dispatch_report(_opening_plan())

    assert report.validators_would_run == (
        "narrator_authority_contract",
        "scene_energy_contract",
        "environment_state_contract",
        "information_disclosure_contract",
        "voice_consistency_contract",
    )
    run_entries = [
        entry
        for entry in report.entries
        if entry.dispatch_action is ValidatorDispatchAction.RUN
    ]
    assert len(run_entries) == 5
    assert all(entry.would_execute for entry in run_entries)


def test_opening_dispatch_reports_observer_diagnostics() -> None:
    report = build_validator_dispatch_report(_opening_plan())

    assert report.diagnostics_would_run == (
        "thematic_tracking_diagnostic",
        "callback_web_diagnostic",
        "sensory_context_diagnostic",
        "genre_awareness_diagnostic",
    )


def test_opening_dispatch_reports_skipped_excluded_validators() -> None:
    report = build_validator_dispatch_report(_opening_plan())

    for validator_id in (
        "npc_agency_contract",
        "player_intent_contract",
        "action_resolution_contract",
        "consequence_cascade_contract",
        "forecast_contract",
        "silence_negative_space_contract",
        "dramatic_irony_contract",
    ):
        assert validator_id in report.validators_would_skip


def test_opening_dispatch_disallows_judges_by_budget() -> None:
    report = build_validator_dispatch_report(_opening_plan())

    assert "narrator_authority_judge" in report.judges_would_be_disallowed
    assert "scene_energy_judge" in report.judges_would_be_disallowed
    assert "npc_agency_judge" in report.judges_would_be_disallowed
    assert "action_resolution_judge" in report.judges_would_be_disallowed
    assert len(report.judges_would_be_disallowed) >= len(
        report.validators_would_run
    )


def test_dispatch_projection_is_local_only() -> None:
    projection = build_validator_dispatch_report(_opening_plan()).to_runtime_projection()[
        "validator_dispatch_report"
    ]

    assert projection["proof_level"] == "local_only"
    assert projection["live_or_staging_evidence"] is False
    assert projection["implementation_proof"] is False
    assert projection["implemented_by_runtime"] is False
    assert projection["live_verified"] is False
    assert projection["staging_verified"] is False
    assert projection["provider_verified"] is False
    assert projection["capability_promoted"] is False


def test_dispatch_projection_marks_execution_changed_false() -> None:
    projection = build_validator_dispatch_report(_opening_plan()).to_runtime_projection()[
        "validator_dispatch_report"
    ]

    assert projection["execution_changed"] is False
    assert projection["actually_executed"] == []


def test_dispatch_uses_semantic_names_only() -> None:
    report = build_validator_dispatch_report(_opening_plan())
    active_pi_token = re.compile(
        r"(?<![A-Za-z0-9])pi_\d+\b|(?<![A-Za-z0-9])pi\d+_[A-Za-z0-9_]+\b|Π\d+\b",
        re.IGNORECASE,
    )

    for entry in report.entries:
        validate_semantic_capability_name(entry.capability)
        if entry.validator_id:
            validate_semantic_capability_name(entry.validator_id)
            assert not active_pi_token.search(entry.validator_id)

    for collection in (
        report.validators_would_run,
        report.diagnostics_would_run,
        report.validators_would_skip,
        report.judges_would_be_disallowed,
    ):
        for item in collection:
            validate_semantic_capability_name(item)
            assert not active_pi_token.search(item)


def test_plan_enforced_without_registry_does_not_execute_or_change_gates() -> None:
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
    )

    assert report.mode is ValidatorDispatchMode.PLAN_ENFORCED
    assert report.actually_executed == ()
    assert report.execution_changed is False
    assert report.validators_unavailable == report.validators_would_run

    default_report = build_validator_dispatch_report(_opening_plan())
    assert default_report.mode is ValidatorDispatchMode.DRY_RUN
    assert default_report.execution_changed is False


def test_dispatch_report_reason_documents_dry_run_only() -> None:
    report = build_validator_dispatch_report(_opening_plan())

    assert report.reason == DISPATCH_REPORT_REASON
    assert "dry-run" in report.reason.lower()
