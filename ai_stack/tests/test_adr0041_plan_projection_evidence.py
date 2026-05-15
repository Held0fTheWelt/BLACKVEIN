"""ADR-0041 Option A: plan-aware sibling projection (ADR0041_PLAN_PROJECTION_ENABLED).

Default omits ``adr0041_plan_projection``; validator_dispatch_report remains unchanged dry-run.
"""

from __future__ import annotations

from ai_stack.runtime_aspect_ledger import (
    ADR0041_PLAN_PROJECTION_ENABLED_ENV,
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_COMMIT,
    ASPECT_NPC_AGENCY,
    ASPECT_VALIDATION,
    initialize_runtime_aspect_ledger,
    normalize_runtime_aspect_ledger,
)


def test_plan_projection_sibling_absent_by_default() -> None:
    ledger = normalize_runtime_aspect_ledger(
        initialize_runtime_aspect_ledger(
            session_id="s-plan-proj",
            module_id="god_of_carnage",
            turn_number=1,
            turn_kind="player",
            raw_player_input="I walk.",
            input_kind="action",
        )
    )
    rip = ledger["runtime_intelligence_projection"]
    assert "adr0041_plan_projection" not in rip
    report = rip["validator_dispatch_report"]
    assert report["mode"] == "dry_run"
    assert report["execution_changed"] is False
    assert report["actually_executed"] == []
    assert report["live_or_staging_evidence"] is False
    assert report["commit_gate_changed"] is False
    assert report["readiness_gate_changed"] is False
    assert report["judge_execution_changed"] is False


def test_plan_projection_sibling_when_env_enabled_opening(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_PLAN_PROJECTION_ENABLED_ENV, "true")
    ledger = normalize_runtime_aspect_ledger(
        initialize_runtime_aspect_ledger(
            session_id="s-plan-open",
            module_id="god_of_carnage",
            turn_number=0,
            turn_kind="opening",
            raw_player_input="",
        )
    )
    rip = ledger["runtime_intelligence_projection"]
    sibling = rip["adr0041_plan_projection"]
    report = rip["validator_dispatch_report"]

    assert sibling["adr0041_plan_projection_enabled"] is True
    assert sibling["selected_turn_class"] == "opening_scene"
    assert sibling["proof_level"] == "local_only"
    assert sibling["execution_changed"] is False
    assert sibling["actually_executed"] == []
    assert sibling["live_or_staging_evidence"] is False

    assert report["mode"] == "dry_run"
    assert report["execution_changed"] is False
    assert report["actually_executed"] == []
    assert "narrator_authority_contract" in sibling["planned_local_validator_ids"]
    assert "npc_agency_contract" not in sibling["planned_local_validator_ids"]

    aspects = ledger["turn_aspect_ledger"]
    assert aspects[ASPECT_CAPABILITY_SELECTION]["status"] == "missing"
    assert aspects[ASPECT_VALIDATION]["status"] == "missing"
    assert aspects[ASPECT_COMMIT]["status"] == "missing"

    drift = sibling["seam_vs_plan_projection_drift_visibility"]
    assert drift["production_validation_seam_symbol"].endswith("run_validation_seam")


def test_plan_projection_player_turn_class(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_PLAN_PROJECTION_ENABLED_ENV, "1")
    ledger = normalize_runtime_aspect_ledger(
        initialize_runtime_aspect_ledger(
            session_id="s-plan-player",
            module_id="god_of_carnage",
            turn_number=3,
            turn_kind="player",
            raw_player_input="I open the door.",
            input_kind="action",
        )
    )
    sibling = ledger["runtime_intelligence_projection"]["adr0041_plan_projection"]
    assert sibling["selected_turn_class"] == "normal_player_turn"
    assert "player_intent_contract" in sibling["planned_local_validator_ids"]
    assert "action_resolution_contract" in sibling["planned_local_validator_ids"]
    would_local = sibling["would_execute_local_validators_if_plan_enforced_with_inventory_adapters"]
    assert set(would_local) <= set(sibling["planned_local_validator_ids"])


def test_plan_projection_npc_conflict_turn_class(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_PLAN_PROJECTION_ENABLED_ENV, "on")
    base = initialize_runtime_aspect_ledger(
        session_id="s-plan-npc",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="npc",
        raw_player_input="",
    )
    naspects = base["turn_aspect_ledger"][ASPECT_NPC_AGENCY]
    naspects["expected"] = {
        **(naspects.get("expected") if isinstance(naspects.get("expected"), dict) else {}),
        "candidate_actor_ids": ["veronique_vallon"],
    }
    ledger = normalize_runtime_aspect_ledger(base)
    sibling = ledger["runtime_intelligence_projection"]["adr0041_plan_projection"]
    assert sibling["selected_turn_class"] == "npc_conflict_turn"
    assert "npc_agency_contract" in sibling["planned_local_validator_ids"]


def test_plan_projection_recovery_turn_class(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_PLAN_PROJECTION_ENABLED_ENV, "on")
    ledger = normalize_runtime_aspect_ledger(
        initialize_runtime_aspect_ledger(
            session_id="s-plan-recovery",
            module_id="god_of_carnage",
            turn_number=6,
            turn_kind="recovery_turn",
            raw_player_input="",
        )
    )
    sibling = ledger["runtime_intelligence_projection"]["adr0041_plan_projection"]
    assert sibling["selected_turn_class"] == "recovery_turn"
    assert "narrator_authority_contract" in sibling["planned_local_validator_ids"]


def test_plan_projection_system_transition_turn_class(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_PLAN_PROJECTION_ENABLED_ENV, "on")
    ledger = normalize_runtime_aspect_ledger(
        initialize_runtime_aspect_ledger(
            session_id="s-plan-system",
            module_id="god_of_carnage",
            turn_number=7,
            turn_kind="system_transition",
            raw_player_input="",
        )
    )
    sibling = ledger["runtime_intelligence_projection"]["adr0041_plan_projection"]
    assert sibling["selected_turn_class"] == "system_transition"
    assert "scene_energy_contract" in sibling["planned_local_validator_ids"]


def test_plan_projection_degraded_fallback_turn_class(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_PLAN_PROJECTION_ENABLED_ENV, "on")
    ledger = normalize_runtime_aspect_ledger(
        initialize_runtime_aspect_ledger(
            session_id="s-plan-degraded",
            module_id="god_of_carnage",
            turn_number=8,
            turn_kind="degraded_or_fallback_turn",
            raw_player_input="",
        )
    )
    sibling = ledger["runtime_intelligence_projection"]["adr0041_plan_projection"]
    assert sibling["selected_turn_class"] == "degraded_or_fallback_turn"
    assert "narrator_authority_contract" in sibling["planned_local_validator_ids"]
