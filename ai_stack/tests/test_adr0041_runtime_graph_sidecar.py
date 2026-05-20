"""ADR-0041 Option B: LangGraph attaches `_adr0041_runtime_graph_dispatch_context` on plan_enforced.

``normalize_runtime_aspect_ledger`` merges plan-enforced local validator execution into
``runtime_intelligence_projection.validator_dispatch_report`` without affecting
``run_validation_seam`` / ``validation_outcome``.
"""

from __future__ import annotations

from ai_stack.capabilities.capability_validator_dispatch import ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode
from ai_stack.capabilities.capability_validator_plan import JUDGE_VALIDATORS
from ai_stack.story_runtime.runtime_aspect_ledger import (
    ADR0041_DRIFT_ADR_STRICTER,
    ADR0041_DRIFT_ALIGNED,
    ADR0041_DRIFT_MISSING_CONTEXT,
    ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV,
    ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV,
    ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV,
    ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY,
    ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV,
    ASPECT_NPC_AGENCY,
    initialize_runtime_aspect_ledger,
    normalize_runtime_aspect_ledger,
)
from ai_stack.capabilities.capability_validator_registry import (
    TURN_CLASS_DEGRADED_OR_FALLBACK_TURN,
    TURN_CLASS_NPC_CONFLICT_TURN,
    TURN_CLASS_NORMAL_PLAYER_TURN,
    TURN_CLASS_OPENING_SCENE,
    TURN_CLASS_RECOVERY_TURN,
    TURN_CLASS_SYSTEM_TRANSITION,
    get_turn_class_enforced_validators,
)
from ai_stack.tests.test_capability_validator_registry import (
    _npc_dispatch_context,
    _opening_dispatch_context,
    _player_dispatch_context,
)


def _assert_sidecar_local_only(report: dict) -> None:
    assert report["proof_level"] == "local_only"
    assert report["live_or_staging_evidence"] is False
    assert report["commit_gate_changed"] is False
    assert report["readiness_gate_changed"] is False
    assert report["judge_execution_changed"] is False


def test_runtime_graph_bundle_ignored_without_plan_enforced_env(monkeypatch) -> None:
    monkeypatch.delenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, raising=False)
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
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
    projection = out["runtime_intelligence_projection"]
    report = projection["validator_dispatch_report"]
    assert report["mode"] == "dry_run"
    assert report["actually_executed"] == []
    assert report["execution_changed"] is False
    assert "validation_authority_preview" not in projection
    assert "readiness_co_authority_enforcement" not in projection


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
    projection = out["runtime_intelligence_projection"]
    report = projection["validator_dispatch_report"]
    assert report["mode"] == "plan_enforced"
    assert set(report["actually_executed"]) == set(get_turn_class_enforced_validators(TURN_CLASS_OPENING_SCENE))
    assert report["execution_changed"] is True
    assert report["adr0041_selected_turn_class"] == "opening_scene"
    assert report["seam_vs_adr0041_sidecar_drift_visibility"]["validation_seam_status"] == "approved"
    preview = projection["validation_authority_preview"]
    assert preview["affects_commit"] is False
    assert preview["affects_readiness"] is False
    assert preview["proof_level"] == "local_only"
    assert preview["live_or_staging_evidence"] is False
    drift = preview["drift_vs_validation_seam"]["classification"]
    failed = preview["pass_fail_summary"]["failed_validator_ids"]
    bridge = projection["validation_authority_bridge"]
    assert bridge["recommended_authority"] == "seam_canonical"
    assert bridge["migration_readiness"] != "not_engaged"
    assert bridge["schema_version"].startswith("validation_authority_bridge.")
    if failed:
        assert drift == ADR0041_DRIFT_ADR_STRICTER
    else:
        assert drift == ADR0041_DRIFT_ALIGNED
    assert preview == report["adr0041_authority_preview"]
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
    assert set(report["actually_executed"]) == set(get_turn_class_enforced_validators(TURN_CLASS_NORMAL_PLAYER_TURN))
    assert report["adr0041_selected_turn_class"] == "normal_player_turn"
    _assert_sidecar_local_only(report)
    assert "narrator_authority_contract" not in report["actually_executed"]
    assert set(report["actually_executed"]).isdisjoint(set(JUDGE_VALIDATORS.values()))


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
    assert set(report["actually_executed"]) == set(get_turn_class_enforced_validators(TURN_CLASS_NPC_CONFLICT_TURN))
    assert report["adr0041_selected_turn_class"] == "npc_conflict_turn"
    _assert_sidecar_local_only(report)
    assert set(report["actually_executed"]).isdisjoint(set(JUDGE_VALIDATORS.values()))


def test_plan_enforced_opening_readiness_preview_allow_when_flags_enabled(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-gready-open",
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
    preview = out["runtime_intelligence_projection"]["readiness_co_authority_preview"]
    assert preview["policy_stage"] == "readiness_preview_allow"
    assert preview["candidate"] is True
    assert preview["would_allow_readiness"] is True
    assert preview["turn_class"] == TURN_CLASS_OPENING_SCENE
    assert preview["validation_outcome_changed"] is False
    assert preview["affects_commit"] is False
    assert preview["affects_readiness"] is False


def test_plan_enforced_opening_readiness_enforcement_allow_when_flags_enabled(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-genf-open",
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
    enforcement = out["runtime_intelligence_projection"]["readiness_co_authority_enforcement"]
    assert enforcement["readiness_input"] == "allow"
    assert enforcement["would_affect_readiness"] is True
    assert enforcement["commit_gate_changed"] is False
    assert enforcement["validation_outcome_changed"] is False
    assert enforcement["readiness_gate_changed"] is False


def test_plan_enforced_player_readiness_preview_allow_when_flags_enabled(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-gready-player",
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
    preview = out["runtime_intelligence_projection"]["readiness_co_authority_preview"]
    assert preview["policy_stage"] == "readiness_preview_allow"
    assert preview["candidate"] is True
    assert preview["would_allow_readiness"] is True
    assert preview["turn_class"] == TURN_CLASS_NORMAL_PLAYER_TURN


def test_plan_enforced_npc_readiness_preview_allow_when_flags_enabled(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-gready-npc",
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
    preview = out["runtime_intelligence_projection"]["readiness_co_authority_preview"]
    assert preview["policy_stage"] == "readiness_preview_allow"
    assert preview["candidate"] is True
    assert preview["would_allow_readiness"] is True
    assert preview["turn_class"] == TURN_CLASS_NPC_CONFLICT_TURN


def test_graph_bundle_missing_context_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
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
    projection = out["runtime_intelligence_projection"]
    report = projection["validator_dispatch_report"]
    assert report["mode"] == "plan_enforced"
    assert report["actually_executed"] == []
    assert set(report["validators_unavailable"]) == set(get_turn_class_enforced_validators(TURN_CLASS_OPENING_SCENE))
    preview = projection["validation_authority_preview"]
    assert preview["drift_vs_validation_seam"]["classification"] == ADR0041_DRIFT_MISSING_CONTEXT
    readiness_preview = projection["readiness_co_authority_preview"]
    assert readiness_preview["policy_stage"] == "not_eligible"
    assert readiness_preview["would_allow_readiness"] is False
    assert "missing_context" in readiness_preview["blockers"]
    enforcement = projection["readiness_co_authority_enforcement"]
    assert enforcement["readiness_input"] == "block"
    assert "missing_context" in enforcement["blockers"]
    agg = projection["readiness_aggregation_decision"]
    assert agg["aggregated_readiness"] == "block"
    assert agg["adr0041_veto_applied"] is True
    assert agg["seam_readiness"] == "allow"


def test_plan_enforced_graph_bundle_runs_recovery_turn_validators(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-grecovery",
        module_id="god_of_carnage",
        turn_number=3,
        turn_kind="recovery_turn",
        raw_player_input="",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _opening_dispatch_context(),
        "validation_seam_summary": {"status": "approved"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    report = out["runtime_intelligence_projection"]["validator_dispatch_report"]
    assert set(report["actually_executed"]) == set(get_turn_class_enforced_validators(TURN_CLASS_RECOVERY_TURN))
    assert report["adr0041_selected_turn_class"] == TURN_CLASS_RECOVERY_TURN
    _assert_sidecar_local_only(report)


def test_plan_enforced_graph_bundle_runs_system_transition_validators(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-gsystem",
        module_id="god_of_carnage",
        turn_number=4,
        turn_kind="system_transition",
        raw_player_input="",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _opening_dispatch_context(),
        "validation_seam_summary": {"status": "approved"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    report = out["runtime_intelligence_projection"]["validator_dispatch_report"]
    executed = set(report["actually_executed"])
    planned = set(report["validators_would_run"])
    assert executed.issubset(planned)
    assert "information_disclosure_contract" in executed
    assert report["adr0041_selected_turn_class"] == TURN_CLASS_SYSTEM_TRANSITION
    _assert_sidecar_local_only(report)


def test_plan_enforced_graph_bundle_runs_degraded_fallback_validators(monkeypatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-gdegraded",
        module_id="god_of_carnage",
        turn_number=5,
        turn_kind="degraded_or_fallback_turn",
        raw_player_input="",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _opening_dispatch_context(),
        "validation_seam_summary": {"status": "approved"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    report = out["runtime_intelligence_projection"]["validator_dispatch_report"]
    executed = set(report["actually_executed"])
    planned = set(report["validators_would_run"])
    assert executed.issubset(planned)
    assert "information_disclosure_contract" in executed
    assert report["adr0041_selected_turn_class"] == TURN_CLASS_DEGRADED_OR_FALLBACK_TURN
    _assert_sidecar_local_only(report)
