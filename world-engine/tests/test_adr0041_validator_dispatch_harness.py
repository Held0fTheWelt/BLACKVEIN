"""ADR-0041 opt-in plan-enforced validator dispatch harness (world-engine surface).

Default runtime ledger projection remains dry-run. These tests exercise
``build_adr0041_validator_dispatch_harness_report`` only when explicitly enabled.
"""

from __future__ import annotations

from pathlib import Path

from ai_stack.capability_validator_dispatch import ValidatorDispatchMode
from ai_stack.capability_validator_plan import JUDGE_VALIDATORS
from ai_stack.capability_validator_registry import (
    build_default_semantic_validator_registry,
    build_npc_conflict_enforced_semantic_validator_registry,
    build_opening_enforced_semantic_validator_registry,
    build_player_turn_enforced_semantic_validator_registry,
)
from ai_stack.environment_state_contracts import build_environment_model, initial_environment_state
from ai_stack.npc_agency_contracts import normalize_npc_agency_plan
from ai_stack.runtime_aspect_ledger import (
    ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV,
    ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY,
    ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV,
    ADR0041_PLAN_PROJECTION_ENABLED_ENV,
    build_adr0041_validator_dispatch_harness_report,
    build_runtime_intelligence_projection,
    initialize_runtime_aspect_ledger,
    normalize_runtime_aspect_ledger,
)


def _content_root() -> Path:
    return Path(__file__).resolve().parents[1].parent / "content" / "modules"


def _runtime_projection() -> dict:
    return {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette_reille",
        "npc_actor_ids": ["alain_reille", "veronique_vallon", "michel_longstreet"],
        "actor_lanes": {
            "annette_reille": "human",
            "alain_reille": "npc",
            "veronique_vallon": "npc",
            "michel_longstreet": "npc",
        },
    }


def _opening_dispatch_context() -> dict:
    module_id = "god_of_carnage"
    model = build_environment_model(module_id=module_id)
    environment_state = initial_environment_state(
        module_id=module_id,
        environment_model=model,
        turn_number=0,
    )
    return {
        "module_id": module_id,
        "turn_number": 0,
        "narrator_required": True,
        "structured_output": {
            "narration_summary": "The foyer waits in brittle calm.",
            "spoken_lines": [{"speaker_id": "narrator", "text": "The light stays low."}],
        },
        "environment_state": environment_state,
        "environment_model": model,
        "scene_energy_target": {"minimum_actor_response_count": 1, "energy_level": "medium"},
        "information_disclosure_target": {"policy_enabled": False},
        "voice_profiles": [],
    }


def _player_dispatch_context() -> dict:
    return {
        "module_id": "god_of_carnage",
        "turn_number": 1,
        "raw_player_input": "Gehe ins Bad",
        "interpreted_input": {
            "player_input_kind": "action",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "projection_captures": {"room": "ins Bad"},
            "actor_id": "annette_reille",
        },
        "runtime_projection": _runtime_projection(),
        "content_modules_root": _content_root(),
        "scene_energy_target": {"minimum_actor_response_count": 1, "energy_level": "medium"},
        "information_disclosure_target": {"policy_enabled": False},
        "voice_profiles": [],
        "structured_output": {"spoken_lines": []},
    }


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


def _assert_local_only_dispatch(report: dict) -> None:
    assert report["proof_level"] == "local_only"
    assert report["live_or_staging_evidence"] is False
    assert report["commit_gate_changed"] is False
    assert report["readiness_gate_changed"] is False
    assert report["judge_execution_changed"] is False


def test_world_engine_default_projection_remains_dry_run() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-harness",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
        turn_id="t-open",
        trace_id="trace-harness",
    )
    proj = ledger["runtime_intelligence_projection"]
    report = proj["validator_dispatch_report"]

    assert report["mode"] == "dry_run"
    assert report["execution_changed"] is False
    assert "readiness_co_authority_preview" not in proj


def test_world_engine_projection_omits_readiness_preview_when_flag_disabled(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.delenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, raising=False)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-ready-off",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _opening_dispatch_context(),
        "validation_seam_summary": {"status": "approved"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    assert "readiness_co_authority_preview" not in out["runtime_intelligence_projection"]


def test_world_engine_projection_emits_readiness_preview_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-ready-on",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _opening_dispatch_context(),
        "validation_seam_summary": {"status": "approved"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    preview = out["runtime_intelligence_projection"]["readiness_co_authority_preview"]
    assert preview["policy_stage"] in {
        "shadow_only",
        "readiness_preview_candidate",
        "readiness_preview_allow",
        "readiness_preview_block",
        "not_eligible",
    }
    assert preview["affects_commit"] is False
    assert preview["affects_readiness"] is False


def test_world_engine_default_projection_executes_no_validators() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-harness",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="I walk.",
        input_kind="action",
        turn_id="t-pl",
        trace_id="trace-harness",
    )
    report = ledger["runtime_intelligence_projection"]["validator_dispatch_report"]

    assert report["actually_executed"] == []


def test_world_engine_plan_enforced_requires_explicit_flag() -> None:
    """Without harness_allow, an explicit registry must not execute validators."""
    report = build_adr0041_validator_dispatch_harness_report(
        harness_allow_plan_enforced_local_dispatch=False,
        dispatch_mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_opening_enforced_semantic_validator_registry(),
        dispatch_context=_opening_dispatch_context(),
        turn_kind="opening",
        turn_number=0,
        raw_player_input="",
        visible_projection_required=True,
    )

    assert report["actually_executed"] == []


def test_world_engine_plan_enforced_requires_explicit_registry() -> None:
    report = build_adr0041_validator_dispatch_harness_report(
        harness_allow_plan_enforced_local_dispatch=True,
        dispatch_mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=None,
        dispatch_context=_opening_dispatch_context(),
        turn_kind="opening",
        turn_number=0,
        raw_player_input="",
        visible_projection_required=True,
    )

    assert report["mode"] == "dry_run"
    assert report["actually_executed"] == []
    assert "adr0041_harness_plan_enforced_requires_explicit_validator_registry" in report["warnings"]


def test_world_engine_opening_harness_executes_only_opening_enforced_validators() -> None:
    report = build_adr0041_validator_dispatch_harness_report(
        harness_allow_plan_enforced_local_dispatch=True,
        dispatch_mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_opening_enforced_semantic_validator_registry(),
        dispatch_context=_opening_dispatch_context(),
        turn_kind="opening",
        turn_number=0,
        raw_player_input="",
        visible_projection_required=True,
    )

    expected = {
        "narrator_authority_contract",
        "scene_energy_contract",
        "environment_state_contract",
        "information_disclosure_contract",
        "voice_consistency_contract",
    }
    assert set(report["actually_executed"]) == expected
    assert report["mode"] == "plan_enforced"
    assert report["execution_changed"] is True
    _assert_local_only_dispatch(report)


def test_world_engine_player_turn_harness_executes_only_player_turn_enforced_validators() -> None:
    report = build_adr0041_validator_dispatch_harness_report(
        harness_allow_plan_enforced_local_dispatch=True,
        dispatch_mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_player_turn_enforced_semantic_validator_registry(),
        dispatch_context=_player_dispatch_context(),
        turn_kind="player_input",
        turn_number=1,
        raw_player_input="Gehe ins Bad",
        active_actor="player",
        action_resolution_required=True,
        visible_projection_required=True,
        knowledge_gap_present=False,
        non_lexical_input_present=False,
    )

    expected = {
        "player_intent_contract",
        "action_resolution_contract",
        "information_disclosure_contract",
        "voice_consistency_contract",
        "scene_energy_contract",
    }
    assert set(report["actually_executed"]) == expected
    assert report["execution_changed"] is True
    _assert_local_only_dispatch(report)


def test_world_engine_npc_conflict_harness_executes_only_npc_conflict_enforced_validators() -> None:
    report = build_adr0041_validator_dispatch_harness_report(
        harness_allow_plan_enforced_local_dispatch=True,
        dispatch_mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_npc_conflict_enforced_semantic_validator_registry(),
        dispatch_context=_npc_dispatch_context(),
        turn_kind="npc_turn",
        turn_number=2,
        active_actor="npc",
        npc_decision_required=True,
        visible_projection_required=True,
        knowledge_gap_present=False,
        non_lexical_input_present=False,
    )

    expected = {
        "npc_agency_contract",
        "voice_consistency_contract",
        "scene_energy_contract",
        "information_disclosure_contract",
    }
    assert set(report["actually_executed"]) == expected
    assert report["execution_changed"] is True
    _assert_local_only_dispatch(report)


def test_world_engine_plan_enforced_does_not_execute_excluded_validators() -> None:
    report = build_adr0041_validator_dispatch_harness_report(
        harness_allow_plan_enforced_local_dispatch=True,
        dispatch_mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_opening_enforced_semantic_validator_registry(),
        dispatch_context=_opening_dispatch_context(),
        turn_kind="opening",
        turn_number=0,
        raw_player_input="",
        visible_projection_required=True,
    )
    executed = set(report["actually_executed"])
    for vid in (
        "npc_agency_contract",
        "player_intent_contract",
        "action_resolution_contract",
        "consequence_cascade_contract",
        "forecast_contract",
        "silence_negative_space_contract",
        "dramatic_irony_contract",
    ):
        assert vid not in executed


def test_world_engine_plan_enforced_does_not_execute_judges() -> None:
    report = build_adr0041_validator_dispatch_harness_report(
        harness_allow_plan_enforced_local_dispatch=True,
        dispatch_mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_player_turn_enforced_semantic_validator_registry(),
        dispatch_context=_player_dispatch_context(),
        turn_kind="player_input",
        turn_number=1,
        raw_player_input="Gehe ins Bad",
        active_actor="player",
        action_resolution_required=True,
        visible_projection_required=True,
        knowledge_gap_present=False,
    )
    assert set(report["actually_executed"]).isdisjoint(set(JUDGE_VALIDATORS.values()))


def test_world_engine_plan_enforced_does_not_change_commit_or_readiness() -> None:
    report = build_adr0041_validator_dispatch_harness_report(
        harness_allow_plan_enforced_local_dispatch=True,
        dispatch_mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_opening_enforced_semantic_validator_registry(),
        dispatch_context=_opening_dispatch_context(),
        turn_kind="opening",
        turn_number=0,
        raw_player_input="",
        visible_projection_required=True,
    )
    assert report["commit_gate_changed"] is False
    assert report["readiness_gate_changed"] is False


def test_world_engine_plan_enforced_remains_local_only() -> None:
    report = build_adr0041_validator_dispatch_harness_report(
        harness_allow_plan_enforced_local_dispatch=True,
        dispatch_mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_npc_conflict_enforced_semantic_validator_registry(),
        dispatch_context=_npc_dispatch_context(),
        turn_kind="npc_turn",
        turn_number=2,
        active_actor="npc",
        npc_decision_required=True,
        visible_projection_required=True,
        knowledge_gap_present=False,
    )
    _assert_local_only_dispatch(report)
    assert report["capability_promoted"] is False


def test_world_engine_default_registry_remains_empty_via_import() -> None:
    assert build_default_semantic_validator_registry() == {}


def test_world_engine_plan_projection_sibling_opt_in(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_PLAN_PROJECTION_ENABLED_ENV, "true")
    ledger = normalize_runtime_aspect_ledger(
        initialize_runtime_aspect_ledger(
            session_id="s-we-plan-proj",
            module_id="god_of_carnage",
            turn_number=1,
            turn_kind="player",
            raw_player_input="Hello.",
            input_kind="action",
            turn_id="t-we",
            trace_id="trace-we",
        )
    )
    rip = ledger["runtime_intelligence_projection"]
    sibling = rip["adr0041_plan_projection"]
    assert sibling["selected_turn_class"] == "normal_player_turn"
    assert rip["validator_dispatch_report"]["mode"] == "dry_run"
    assert rip["validator_dispatch_report"]["actually_executed"] == []


def test_world_engine_runtime_projection_harness_same_semantics_as_ledger_path() -> None:
    """Ledger projection path still derives dispatch without harness registry wiring."""
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-harness",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
        turn_id="t0",
        trace_id="trace",
    )
    alt = build_runtime_intelligence_projection(ledger)
    dr = alt["validator_dispatch_report"]
    assert dr["mode"] == "dry_run"
    assert dr["actually_executed"] == []
