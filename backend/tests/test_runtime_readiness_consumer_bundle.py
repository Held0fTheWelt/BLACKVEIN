"""Backend player session bundle + ADR-0041 runtime readiness consumer wiring."""

from __future__ import annotations

import pytest

from ai_stack.capabilities.capability_validator_dispatch import (
    ADR0041_VALIDATOR_DISPATCH_MODE_ENV,
    ValidatorDispatchMode,
)
from ai_stack.runtime_aspect_ledger import (
    ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV,
    ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV,
    ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV,
    ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV,
    ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV,
)

from app.api.v1.game_routes import _player_session_bundle


def _ready_story_state() -> dict:
    return {
        "turn_counter": 0,
        "history_count": 1,
        "committed_canonical_turn_count": 1,
        "current_scene_id": "scene_1",
        "story_window": {
            "contract": "authoritative_story_window_v1",
            "entries": [
                {
                    "kind": "opening",
                    "turn_number": 0,
                    "role": "runtime",
                    "text": "Opening line.",
                }
            ],
            "entry_count": 1,
            "latest_entry": {"kind": "opening", "turn_number": 0},
        },
    }


def _ready_created() -> dict:
    return {
        "runtime_config_status": {
            "governed_runtime_active": True,
            "runtime_profile_id": "goc_live_profile",
        },
        "opening_turn": {
            "turn_kind": "opening",
            "turn_number": 0,
            "committed_result": {"commit_applied": True},
            "runtime_governance_surface": {
                "quality_class": "healthy",
                "degradation_signals": [],
            },
            "visible_output_bundle": {
                "gm_narration": [{"text": "Opening line."}],
                "scene_blocks": [],
            },
            "visible_scene_output": {"blocks": []},
        },
    }


def _turn_with_rip(*, aggregated: str) -> dict:
    return {
        "turn_kind": "opening",
        "turn_number": 0,
        "retrieval": {
            "retrieval_authority": {"authority_level": "retrieved_unverified"},
            "boundary_guard": {"blocked_as_authority_truth": False},
        },
        "turn_aspect_ledger": {
            "runtime_intelligence_projection": {
                "readiness_aggregation_decision": {
                    "aggregated_readiness": aggregated,
                    "adr0041_veto_applied": aggregated == "block",
                    "blockers": [],
                }
            }
        },
    }


def test_bundle_readiness_default_matches_base_without_consumer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV, raising=False)
    bundle = _player_session_bundle(
        run_id="r-consumer-off",
        template_id="god_of_carnage_solo",
        module_id="god_of_carnage",
        runtime_session_id="we-1",
        state=_ready_story_state(),
        created=_ready_created(),
        turn=_turn_with_rip(aggregated="block"),
    )
    assert bundle["runtime_session_ready"] is True
    assert bundle["can_execute"] is True
    diag = bundle["governance"]["adr0041_runtime_readiness_consumer"]
    echo = bundle["governance"]["adr0041_readiness_projection_echo"]
    assert diag["consumer_enabled"] is False
    assert diag["validation_outcome_changed"] is False
    assert echo["read_only"] is True
    assert echo["schema_version"].startswith("adr0041_readiness_projection_echo")


def test_bundle_veto_when_consumer_and_prereqs_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV, "true")

    bundle = _player_session_bundle(
        run_id="r-consumer-on",
        template_id="god_of_carnage_solo",
        module_id="god_of_carnage",
        runtime_session_id="we-2",
        state=_ready_story_state(),
        created=_ready_created(),
        turn=_turn_with_rip(aggregated="block"),
    )
    assert bundle["runtime_session_ready"] is False
    assert bundle["can_execute"] is False
    diag = bundle["governance"]["adr0041_runtime_readiness_consumer"]
    echo = bundle["governance"]["adr0041_readiness_projection_echo"]
    assert diag["consumer_path_active"] is True
    assert diag["source"] == "adr0041_scoped_consumer"
    assert echo["readiness_aggregation_decision"]["aggregated_readiness"] == "block"
    retrieval_diag = bundle["governance"]["retrieval_diagnostic_context"]
    assert retrieval_diag["diagnostic_only"] is True
    assert retrieval_diag["not_readiness_authority"] is True
    assert retrieval_diag["retrieval_authority"]["authority_level"] == "retrieved_unverified"


def test_bundle_blocks_ready_state_when_turn_is_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV, "true")

    turn = _turn_with_rip(aggregated="allow")
    turn["runtime_governance_surface"] = {
        "quality_class": "degraded",
        "degradation_signals": ["fallback"],
    }

    bundle = _player_session_bundle(
        run_id="r-consumer-degraded",
        template_id="god_of_carnage_solo",
        module_id="god_of_carnage",
        runtime_session_id="we-3",
        state=_ready_story_state(),
        created=_ready_created(),
        turn=turn,
    )
    assert bundle["runtime_session_ready"] is False
    assert bundle["can_execute"] is False
    diag = bundle["governance"]["adr0041_runtime_readiness_consumer"]
    assert diag["reason"] == "adr0041_degradation_veto_over_base_allow"
    assert diag["degradation_blocking_signal"] is True
