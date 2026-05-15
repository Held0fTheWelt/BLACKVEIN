"""ADR-0041 Option B: LangGraph attaches `_adr0041_runtime_graph_dispatch_context` on plan_enforced.

``normalize_runtime_aspect_ledger`` merges plan-enforced local validator execution into
``runtime_intelligence_projection.validator_dispatch_report`` without affecting
``run_validation_seam`` / ``validation_outcome``.
"""

from __future__ import annotations

from ai_stack.capability_validator_dispatch import ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode
from ai_stack.capability_validator_plan import JUDGE_VALIDATORS
from ai_stack.npc_agency_contracts import normalize_npc_agency_plan
from ai_stack.runtime_aspect_ledger import (
    ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY,
    ASPECT_NPC_AGENCY,
    initialize_runtime_aspect_ledger,
    normalize_runtime_aspect_ledger,
)
from ai_stack.tests.test_capability_validator_dispatch_plan_enforced import OPENING_ENFORCED_VALIDATORS
from ai_stack.tests.test_capability_validator_registry import (
    PLAYER_TURN_ENFORCED_VALIDATORS,
    _opening_dispatch_context,
    _player_dispatch_context,
)


def _npc_dispatch_context() -> dict:
    actors = {
        "primary": "veronique_vallon",
        "secondary": "michel_longstreet",
    }
    plan = normalize_npc_agency_plan(
        {
            "primary_responder_id": actors["primary"],
            "secondary_responder_ids": [actors["secondary"]],
            "npc_initiatives": [
                {"actor_id": actors["primary"], "target_actor_id": actors["secondary"], "required": True},
                {"actor_id": actors["secondary"], "target_actor_id": actors["primary"], "required": True},
            ],
        }
    )
    structured_output = {
        "spoken_lines": [
            {"speaker_id": row["actor_id"], "text": "Visible beat."}
            for row in plan["npc_initiatives"]
        ],
        "action_lines": [],
    }
    return {
        "module_id": "god_of_carnage",
        "turn_number": 2,
        "npc_agency_plan": plan,
        "structured_output": structured_output,
        "scene_energy_target": {"minimum_actor_response_count": 1, "energy_level": "medium"},
        "information_disclosure_target": {"policy_enabled": False},
        "voice_profiles": [],
    }


def _assert_sidecar_local_only(report: dict) -> None:
    assert report["proof_level"] == "local_only"
    assert report["live_or_staging_evidence"] is False
    assert report["commit_gate_changed"] is False
    assert report["readiness_gate_changed"] is False
    assert report["judge_execution_changed"] is False


def test_runtime_graph_bundle_ignored_without_plan_enforced_env(monkeypatch) -> None:
    monkeypatch.delenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, raising=False)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-gbundle",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _opening_dispatch_context(),
        "validation_seam_summary": {"status": "approved", "reason": "fixture"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    report = out["runtime_intelligence_projection"]["validator_dispatch_report"]
    assert report["mode"] == "dry_run"
    assert report["actually_executed"] == []
    assert report["execution_changed"] is False


def test_plan_enforced_graph_bundle_runs_opening_validators(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-gopen",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _opening_dispatch_context(),
        "validation_seam_summary": {"status": "approved", "reason": "fixture"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    report = out["runtime_intelligence_projection"]["validator_dispatch_report"]
    assert report["mode"] == "plan_enforced"
    assert set(report["actually_executed"]) == set(OPENING_ENFORCED_VALIDATORS)
    assert report["execution_changed"] is True
    assert report["adr0041_selected_turn_class"] == "opening_scene"
    assert report["seam_vs_adr0041_sidecar_drift_visibility"]["validation_seam_status"] == "approved"
    _assert_sidecar_local_only(report)
    for vid in (
        "npc_agency_contract",
        "player_intent_contract",
        "action_resolution_contract",
    ):
        assert vid not in report["actually_executed"]
    assert set(report["actually_executed"]).isdisjoint(set(JUDGE_VALIDATORS.values()))


def test_plan_enforced_graph_bundle_runs_player_turn_validators(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-gpl",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Gehe ins Bad",
        input_kind="action",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _player_dispatch_context(),
        "validation_seam_summary": {"status": "approved"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    report = out["runtime_intelligence_projection"]["validator_dispatch_report"]
    assert report["mode"] == "plan_enforced"
    assert set(report["actually_executed"]) == set(PLAYER_TURN_ENFORCED_VALIDATORS)
    assert report["adr0041_selected_turn_class"] == "normal_player_turn"
    _assert_sidecar_local_only(report)
    assert "narrator_authority_contract" not in report["actually_executed"]


def test_plan_enforced_graph_bundle_runs_npc_conflict_validators(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-gnpc",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="npc",
        raw_player_input="",
    )
    naspects = ledger["turn_aspect_ledger"][ASPECT_NPC_AGENCY]
    ledger["turn_aspect_ledger"][ASPECT_NPC_AGENCY] = {
        **naspects,
        "expected": {
            **(naspects.get("expected") if isinstance(naspects.get("expected"), dict) else {}),
            "candidate_actor_ids": ["veronique_vallon"],
        },
    }
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _npc_dispatch_context(),
        "validation_seam_summary": {"status": "approved"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    report = out["runtime_intelligence_projection"]["validator_dispatch_report"]
    expected = {
        "npc_agency_contract",
        "voice_consistency_contract",
        "scene_energy_contract",
        "information_disclosure_contract",
    }
    assert set(report["actually_executed"]) == expected
    assert report["adr0041_selected_turn_class"] == "npc_conflict_turn"
    _assert_sidecar_local_only(report)


def test_graph_bundle_missing_context_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-gmiss",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": {},
        "validation_seam_summary": {"status": "approved"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    report = out["runtime_intelligence_projection"]["validator_dispatch_report"]
    assert report["mode"] == "plan_enforced"
    assert report["actually_executed"] == []
    assert set(report["validators_unavailable"]) == set(OPENING_ENFORCED_VALIDATORS)
