"""Tests for ADR-0041 ``validation_authority_bridge`` (seam vs local validators, non-commit)."""

from __future__ import annotations

import ai_stack.capabilities.capability_validator_dispatch as capability_validator_dispatch
import ai_stack.runtime_aspect_ledger as runtime_aspect_ledger
from ai_stack.capabilities.capability_validator_dispatch import ValidatorDispatchMode
from ai_stack.goc_seam_mirror_validator_adapters import (
    DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT,
    adapter_dramatic_effect_gate_mirror_contract,
)
from ai_stack.runtime_aspect_ledger import (
    ADR0041_DRIFT_ADR_STRICTER,
    ADR0041_DRIFT_ALIGNED,
    ADR0041_DRIFT_CONFLICTING_RESULT,
    ADR0041_DRIFT_MISSING_CONTEXT,
    ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV,
    ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV,
    ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV,
    ADR0041_DRIFT_SEAM_STRICTER,
    ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY,
    ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV,
    ADR0041_VALIDATION_AUTHORITY_PREVIEW_SCHEMA_VERSION,
    ASPECT_NPC_AGENCY,
    initialize_runtime_aspect_ledger,
    normalize_runtime_aspect_ledger,
)
from ai_stack.capabilities.capability_validator_registry import get_turn_class_enforced_validators
from ai_stack.tests.test_capability_validator_registry import (
    _npc_dispatch_context,
    _opening_dispatch_context,
    _player_dispatch_context,
)
from ai_stack.validation_authority_bridge import (
    VALIDATION_AUTHORITY_BRIDGE_SCHEMA_VERSION,
    VALIDATION_CO_AUTHORITY_DECISION_SCHEMA_VERSION,
    build_readiness_aggregation_decision,
    build_validation_authority_bridge,
    seam_concerns_covered_by_adr0041_validators,
)


_NPC_CONFLICT_PARTIAL_TRANSFER_SCOPE: frozenset[str] = frozenset(
    {
        "actor_lane_forbidden_contract",
        "dramatic_effect_gate_mirror_contract",
        "scene_energy_contract",
        "voice_consistency_contract",
        "npc_agency_contract",
        "hard_forbidden_runtime_contract",
    }
)

_SCOPED_CO_AUTHORITY_SCOPE_WITHOUT_OPENING: frozenset[str] = frozenset(
    {
        "actor_lane_forbidden_output",
        "dramatic_effect_gate",
        "hard_forbidden_runtime",
    }
)


def _dramatic_mirror_adapter_with_partial_defaults(entry, ctx):
    base = adapter_dramatic_effect_gate_mirror_contract(entry, ctx)
    if not isinstance(base, dict):
        return base
    merged = dict(base)
    merged["dramatic_effect_mirror_fidelity"] = "partial_defaults"
    return merged


_ORIGINAL_SANITIZE_LOCAL_EXECUTION_EVIDENCE = capability_validator_dispatch._sanitize_local_execution_evidence


def _sanitize_local_evidence_preserve_dramatic_fidelity(*, validator_id: str, raw):
    out = dict(
        _ORIGINAL_SANITIZE_LOCAL_EXECUTION_EVIDENCE(
            validator_id=validator_id,
            raw=raw,
        )
    )
    if isinstance(raw, dict) and raw.get("dramatic_effect_mirror_fidelity") is not None:
        out["dramatic_effect_mirror_fidelity"] = raw["dramatic_effect_mirror_fidelity"]
    return out


def _assert_readiness_preview_safety(preview: dict) -> None:
    assert preview["mode"] == "shadow_readiness_preview"
    assert preview["affects_commit"] is False
    assert preview["affects_readiness"] is False
    assert preview["validation_outcome_changed"] is False
    assert preview["commit_gate_changed"] is False
    assert preview["readiness_gate_changed"] is False
    assert preview["proof_level"] == "local_only"
    assert preview["live_or_staging_evidence"] is False


def _assert_readiness_enforcement_safety(enforcement: dict) -> None:
    assert enforcement["mode"] == "scoped_readiness_enforcement"
    assert enforcement["validation_outcome_changed"] is False
    assert enforcement["commit_gate_changed"] is False
    assert enforcement["readiness_gate_changed"] is False
    assert enforcement["affects_commit"] is False
    assert enforcement["affects_readiness"] is False
    assert enforcement["proof_level"] == "local_only"
    assert enforcement["live_or_staging_evidence"] is False


def _assert_readiness_aggregation_safety(agg: dict) -> None:
    assert agg["mode"] == "scoped_readiness_aggregation"
    assert agg["validation_outcome_changed"] is False
    assert agg["commit_gate_changed"] is False
    assert agg["readiness_gate_changed"] is False
    assert agg["affects_commit"] is False
    assert agg["affects_readiness"] is False
    assert agg["proof_level"] == "local_only"
    assert agg["live_or_staging_evidence"] is False
    assert agg["adr0041_can_upgrade_seam_reject"] is False


def _ledger_npc_conflict_plan_enforced(*, dispatch_context: dict) -> dict:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-npc-base",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="npc",
        raw_player_input="",
    )
    naspects = ledger["turn_aspect_ledger"][ASPECT_NPC_AGENCY]
    actors = {"primary": "veronique_vallon", "secondary": "michel_longstreet"}
    ledger["turn_aspect_ledger"][ASPECT_NPC_AGENCY] = {
        **naspects,
        "expected": {
            **(naspects.get("expected") if isinstance(naspects.get("expected"), dict) else {}),
            "candidate_actor_ids": [actors["primary"]],
        },
    }
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": dispatch_context,
        "validation_seam_summary": {"status": "approved"},
    }
    return ledger


def test_bridge_default_projection_omits_bridge(monkeypatch) -> None:
    monkeypatch.delenv("ADR0041_VALIDATOR_DISPATCH_MODE", raising=False)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br0",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    out = normalize_runtime_aspect_ledger(ledger)
    proj = out["runtime_intelligence_projection"]
    assert "validation_authority_bridge" not in proj
    assert "authority_handoff_candidate" not in proj
    assert proj["validator_dispatch_report"].get("validation_authority_bridge") is None


def test_plan_enforced_emits_handoff_candidate_and_seam_coverage(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-handoff",
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
    proj = out["runtime_intelligence_projection"]
    bridge = proj["validation_authority_bridge"]
    handoff = proj["authority_handoff_candidate"]
    assert handoff == bridge["authority_handoff_candidate"]
    assert handoff["candidate"] is True
    assert handoff["recommended_authority"] == "adr0041_ready_for_shadow_authority"


def test_bridge_marks_retrieval_as_observation_only_when_unverified() -> None:
    bridge = build_validation_authority_bridge(
        validation_seam_summary={"status": "approved"},
        validator_dispatch_report={"mode": "dry_run", "validators_would_run": []},
        validation_authority_preview={"drift_vs_validation_seam": {"classification": ADR0041_DRIFT_ALIGNED}},
        selected_turn_class="opening_scene",
        retrieval_observation={
            "retrieval_authority": {
                "authority_level": "retrieved_unverified",
            }
        },
    )
    assert bridge["retrieval_observation_only"] is True
    assert bridge["retrieval_authority_level"] == "retrieved_unverified"
    cov = bridge["seam_concern_coverage"]
    for cid in (
        "actor_lane_forbidden_output",
        "dramatic_effect_gate",
        "npc_lane_transcript_cap",
        "authoritative_action_resolution_surface",
    ):
        assert cid in cov
        assert "coverage_status" in cov[cid]
        assert "validator_ids" in cov[cid]
        assert "turn_class_scope" in cov[cid]
        assert "authority_transfer_status" in cov[cid]
        assert "blockers" in cov[cid]
        assert "seam_area_adr0041_relationship" in cov[cid]
    buckets = bridge["seam_area_adr0041_relationship_buckets"]
    assert "mirrored_by_adr0041" in buckets
    assert "authoritative_action_resolution_surface" in buckets["seam_owned"]
    assert "intent_surface_npc_narrated_player_action" in buckets["migration_candidate"]


def test_plan_enforced_does_not_emit_scoped_co_authority_without_flag(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.delenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, raising=False)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-no-coauth",
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
    proj = out["runtime_intelligence_projection"]
    report = proj["validator_dispatch_report"]

    assert "validation_co_authority_decision" not in report
    assert "validation_co_authority_decision" not in proj


def test_default_projection_omits_readiness_co_authority_preview(monkeypatch) -> None:
    monkeypatch.delenv("ADR0041_VALIDATOR_DISPATCH_MODE", raising=False)
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-ready-default",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    out = normalize_runtime_aspect_ledger(ledger)
    proj = out["runtime_intelligence_projection"]
    assert "readiness_co_authority_preview" not in proj
    assert "readiness_co_authority_preview" not in proj["validator_dispatch_report"]


def test_plan_enforced_does_not_emit_readiness_preview_when_flag_disabled(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.delenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, raising=False)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-ready-flag-off",
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
    proj = out["runtime_intelligence_projection"]
    assert "readiness_co_authority_preview" not in proj
    assert "readiness_co_authority_preview" not in proj["validator_dispatch_report"]


def test_invalid_readiness_preview_flag_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "invalid")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-ready-invalid",
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
    proj = out["runtime_intelligence_projection"]
    assert "readiness_co_authority_preview" not in proj
    assert any(
        "readiness co-authority preview disabled" in str(w)
        for w in (proj["validator_dispatch_report"].get("warnings") or [])
    )


def test_default_projection_omits_readiness_enforcement(monkeypatch) -> None:
    monkeypatch.delenv("ADR0041_VALIDATOR_DISPATCH_MODE", raising=False)
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-enforce-default",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    out = normalize_runtime_aspect_ledger(ledger)
    proj = out["runtime_intelligence_projection"]
    assert "readiness_co_authority_enforcement" not in proj
    assert "readiness_policy_input" not in proj
    assert "readiness_aggregation_decision" not in proj


def test_enforcement_flag_disabled_omits_enforcement_output(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.delenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, raising=False)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-enforce-off",
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
    proj = out["runtime_intelligence_projection"]
    assert "readiness_co_authority_preview" in proj
    assert "readiness_co_authority_enforcement" not in proj
    assert "readiness_policy_input" not in proj


def test_invalid_readiness_aggregation_flag_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "maybe-later")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-agg-invalid",
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
    proj = out["runtime_intelligence_projection"]
    assert "readiness_aggregation_decision" not in proj
    assert any(
        "scoped readiness aggregation disabled" in str(w)
        for w in (proj["validator_dispatch_report"].get("warnings") or [])
    )


def test_enforcement_enabled_without_preview_emits_no_decision(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.delenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, raising=False)
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-enforce-no-preview",
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
    proj = out["runtime_intelligence_projection"]
    enforcement = proj["readiness_co_authority_enforcement"]
    _assert_readiness_enforcement_safety(enforcement)
    assert enforcement["readiness_input"] == "no_decision"
    assert enforcement["would_affect_readiness"] is False
    assert "readiness_aggregation_decision" not in proj
    assert any(
        "scoped readiness aggregation skipped" in str(w)
        for w in (proj["validator_dispatch_report"].get("warnings") or [])
    )


def test_invalid_enforcement_flag_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "pilot-maybe")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-enforce-invalid",
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
    proj = out["runtime_intelligence_projection"]
    assert "readiness_co_authority_enforcement" not in proj
    assert any(
        "scoped readiness enforcement disabled" in str(w)
        for w in (proj["validator_dispatch_report"].get("warnings") or [])
    )


def test_scoped_co_authority_decision_when_flagged_and_partial_transfer_ready(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-coauth",
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
    proj = out["runtime_intelligence_projection"]
    report = proj["validator_dispatch_report"]
    decision = proj["validation_co_authority_decision"]

    assert decision == report["validation_co_authority_decision"]
    assert decision["schema_version"] == VALIDATION_CO_AUTHORITY_DECISION_SCHEMA_VERSION
    assert decision["authority_stage"] == "scoped_co_authority"
    assert decision["decision"] == "validation_co_authority_ready"
    assert set(decision["scope"]) == {
        "actor_lane_forbidden_output",
        "dramatic_effect_gate",
        "hard_forbidden_runtime",
        "opening_event_coverage",
    }
    assert {row["concern_id"] for row in decision["concern_decisions"]} == set(decision["scope"])
    assert decision["readiness_preview"]["status"] == "ready_for_scoped_co_authority"
    assert decision["validation_preview"]["status"] == "ready_for_validation_co_authority"
    assert decision["legacy_fallback_authority"] == "run_validation_seam"
    assert decision["dramatic_effect_mirror_fidelity_sufficient"] is True
    assert decision["affects_commit"] is False
    assert decision["affects_readiness"] is False
    assert decision["validation_outcome_changed"] is False
    assert decision["commit_gate_changed"] is False
    assert decision["readiness_gate_changed"] is False


def test_readiness_preview_opening_positive_allow(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-ready-opening",
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
    proj = out["runtime_intelligence_projection"]
    preview = proj["readiness_co_authority_preview"]
    _assert_readiness_preview_safety(preview)
    assert preview["policy_stage"] == "readiness_preview_allow"
    assert preview["candidate"] is True
    assert preview["would_allow_readiness"] is True
    assert preview["would_block_readiness"] is False
    assert preview["turn_class"] == "opening_scene"
    assert set(preview["scope"]) == {
        "actor_lane_forbidden_output",
        "dramatic_effect_gate",
        "hard_forbidden_runtime",
        "opening_event_coverage",
    }
    assert preview["source"] == "adr0041_validation_co_authority_decision"


def test_readiness_enforcement_opening_positive_allow(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-enforce-opening",
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
    proj = out["runtime_intelligence_projection"]
    enforcement = proj["readiness_co_authority_enforcement"]
    _assert_readiness_enforcement_safety(enforcement)
    assert enforcement["enabled"] is True
    assert enforcement["enforcement_stage"] == "pilot"
    assert enforcement["readiness_input"] == "allow"
    assert enforcement["would_affect_readiness"] is True
    assert enforcement["turn_class"] == "opening_scene"
    assert enforcement["source"] == "adr0041_readiness_co_authority_preview"
    assert proj["readiness_policy_input"] == enforcement
    agg = proj["readiness_aggregation_decision"]
    _assert_readiness_aggregation_safety(agg)
    assert agg["enabled"] is True
    assert agg["seam_readiness"] == "allow"
    assert agg["adr0041_readiness_input"] == "allow"
    assert agg["aggregated_readiness"] == "allow"
    assert agg["adr0041_veto_applied"] is False


def test_readiness_preview_player_positive_allow(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-ready-player",
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
    _assert_readiness_preview_safety(preview)
    assert preview["policy_stage"] == "readiness_preview_allow"
    assert preview["candidate"] is True
    assert preview["turn_class"] == "normal_player_turn"
    assert set(preview["scope"]) == _SCOPED_CO_AUTHORITY_SCOPE_WITHOUT_OPENING


def test_readiness_enforcement_player_positive_allow(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-enforce-player",
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
    enforcement = out["runtime_intelligence_projection"]["readiness_co_authority_enforcement"]
    _assert_readiness_enforcement_safety(enforcement)
    assert enforcement["readiness_input"] == "allow"
    assert enforcement["turn_class"] == "normal_player_turn"


def test_readiness_preview_npc_positive_allow(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    ledger = _ledger_npc_conflict_plan_enforced(dispatch_context=_npc_dispatch_context())
    out = normalize_runtime_aspect_ledger(ledger)
    preview = out["runtime_intelligence_projection"]["readiness_co_authority_preview"]
    _assert_readiness_preview_safety(preview)
    assert preview["policy_stage"] == "readiness_preview_allow"
    assert preview["candidate"] is True
    assert preview["turn_class"] == "npc_conflict_turn"
    assert set(preview["scope"]) == _SCOPED_CO_AUTHORITY_SCOPE_WITHOUT_OPENING


def test_readiness_enforcement_npc_positive_allow(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    ledger = _ledger_npc_conflict_plan_enforced(dispatch_context=_npc_dispatch_context())
    out = normalize_runtime_aspect_ledger(ledger)
    enforcement = out["runtime_intelligence_projection"]["readiness_co_authority_enforcement"]
    _assert_readiness_enforcement_safety(enforcement)
    assert enforcement["readiness_input"] == "allow"
    assert enforcement["turn_class"] == "npc_conflict_turn"


def test_readiness_aggregation_decision_unit_matrix() -> None:
    pol = {"readiness_input": "allow", "scope": ["dramatic_effect_gate"], "blockers": []}
    d = build_readiness_aggregation_decision(
        validation_seam_summary={"status": "approved"},
        readiness_policy_input=pol,
    )
    _assert_readiness_aggregation_safety(d)
    assert d["aggregated_readiness"] == "allow"
    assert d["adr0041_veto_applied"] is False

    d2 = build_readiness_aggregation_decision(
        validation_seam_summary={"status": "rejected"},
        readiness_policy_input=pol,
    )
    assert d2["aggregated_readiness"] == "unchanged"
    assert d2["adr0041_veto_applied"] is False

    pol_block = {
        "readiness_input": "block",
        "scope": ["dramatic_effect_gate"],
        "blockers": ["missing_context"],
    }
    d3 = build_readiness_aggregation_decision(
        validation_seam_summary={"status": "approved"},
        readiness_policy_input=pol_block,
    )
    assert d3["aggregated_readiness"] == "block"
    assert d3["adr0041_veto_applied"] is True

    d4 = build_readiness_aggregation_decision(
        validation_seam_summary={"status": "rejected"},
        readiness_policy_input=pol_block,
    )
    assert d4["aggregated_readiness"] == "block"
    assert d4["adr0041_veto_applied"] is False

    pol_nd = {"readiness_input": "no_decision", "scope": [], "blockers": []}
    d5 = build_readiness_aggregation_decision(
        validation_seam_summary={"status": "approved"},
        readiness_policy_input=pol_nd,
    )
    assert d5["aggregated_readiness"] == "allow"
    assert d5["adr0041_veto_applied"] is False

    d6 = build_readiness_aggregation_decision(
        validation_seam_summary={"status": "rejected"},
        readiness_policy_input=pol_nd,
    )
    assert d6["aggregated_readiness"] == "block"
    assert d6["adr0041_veto_applied"] is False


def test_readiness_aggregation_opening_veto_missing_context(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-agg-miss",
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
    proj = out["runtime_intelligence_projection"]
    agg = proj["readiness_aggregation_decision"]
    _assert_readiness_aggregation_safety(agg)
    assert agg["seam_readiness"] == "allow"
    assert agg["adr0041_readiness_input"] == "block"
    assert agg["aggregated_readiness"] == "block"
    assert agg["adr0041_veto_applied"] is True


def test_readiness_aggregation_player_veto_partial_defaults(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
    monkeypatch.setattr(
        capability_validator_dispatch,
        "_sanitize_local_execution_evidence",
        _sanitize_local_evidence_preserve_dramatic_fidelity,
    )
    orig_reg = runtime_aspect_ledger.adr0041_validator_registry_for_turn_class

    def _reg_with_partial_defaults(tc: str):
        reg = dict(orig_reg(tc))
        reg[DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT] = _dramatic_mirror_adapter_with_partial_defaults
        return reg

    monkeypatch.setattr(
        runtime_aspect_ledger,
        "adr0041_validator_registry_for_turn_class",
        _reg_with_partial_defaults,
    )
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-agg-player-partial",
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
    agg = out["runtime_intelligence_projection"]["readiness_aggregation_decision"]
    _assert_readiness_aggregation_safety(agg)
    assert agg["seam_readiness"] == "allow"
    assert agg["adr0041_readiness_input"] == "block"
    assert agg["aggregated_readiness"] == "block"
    assert agg["adr0041_veto_applied"] is True
    assert "partial_defaults" in agg["blockers"]


def test_readiness_aggregation_npc_veto_partial_defaults(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
    monkeypatch.setattr(
        capability_validator_dispatch,
        "_sanitize_local_execution_evidence",
        _sanitize_local_evidence_preserve_dramatic_fidelity,
    )
    orig_reg = runtime_aspect_ledger.adr0041_validator_registry_for_turn_class

    def _reg_with_partial_defaults(tc: str):
        reg = dict(orig_reg(tc))
        reg[DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT] = _dramatic_mirror_adapter_with_partial_defaults
        return reg

    monkeypatch.setattr(
        runtime_aspect_ledger,
        "adr0041_validator_registry_for_turn_class",
        _reg_with_partial_defaults,
    )
    ledger = _ledger_npc_conflict_plan_enforced(dispatch_context=_npc_dispatch_context())
    out = normalize_runtime_aspect_ledger(ledger)
    agg = out["runtime_intelligence_projection"]["readiness_aggregation_decision"]
    _assert_readiness_aggregation_safety(agg)
    assert agg["seam_readiness"] == "allow"
    assert agg["adr0041_readiness_input"] == "block"
    assert agg["aggregated_readiness"] == "block"
    assert agg["adr0041_veto_applied"] is True
    assert "partial_defaults" in agg["blockers"]


def test_readiness_aggregation_aggregation_on_enforcement_off_skips_decision(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.delenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, raising=False)
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-agg-no-enf",
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
    proj = out["runtime_intelligence_projection"]
    assert "readiness_aggregation_decision" not in proj
    assert any(
        "scoped readiness aggregation skipped" in str(w)
        for w in (proj["validator_dispatch_report"].get("warnings") or [])
    )


def test_scoped_co_authority_decision_blocked_without_partial_transfer_ready(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-coauth-blocked",
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
    proj = out["runtime_intelligence_projection"]

    assert proj["validation_authority_bridge"]["per_turn_class"]["opening_scene"][
        "partial_transfer_ready"
    ] is False
    assert "validation_co_authority_decision" not in proj
    assert "validation_co_authority_decision" not in proj["validator_dispatch_report"]


def test_plan_enforced_without_runtime_graph_bundle_emits_no_validation_co_authority_even_when_flagged(
    monkeypatch,
) -> None:
    """``plan_enforced`` without ``_adr0041_runtime_graph_dispatch_context`` stays on dry-run projection."""
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-coauth-no-sidecar",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    out = normalize_runtime_aspect_ledger(ledger)
    proj = out["runtime_intelligence_projection"]
    assert proj["validator_dispatch_report"]["mode"] == "dry_run"
    assert "validation_co_authority_decision" not in proj
    assert "validation_co_authority_decision" not in proj["validator_dispatch_report"]
    assert "readiness_co_authority_preview" not in proj
    assert "readiness_co_authority_preview" not in proj["validator_dispatch_report"]
    assert "readiness_co_authority_enforcement" not in proj
    assert "readiness_policy_input" not in proj
    assert "readiness_aggregation_decision" not in proj


def test_partial_defaults_dramatic_mirror_blocks_validation_co_authority_on_normalize(monkeypatch) -> None:
    """``dramatic_effect_mirror_fidelity=partial_defaults`` blocks co-authority even with flag wired."""
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setattr(
        capability_validator_dispatch,
        "_sanitize_local_execution_evidence",
        _sanitize_local_evidence_preserve_dramatic_fidelity,
    )
    orig_reg = runtime_aspect_ledger.adr0041_validator_registry_for_turn_class

    def _reg_with_partial_defaults(tc: str):
        reg = dict(orig_reg(tc))
        reg[DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT] = _dramatic_mirror_adapter_with_partial_defaults
        return reg

    monkeypatch.setattr(
        runtime_aspect_ledger,
        "adr0041_validator_registry_for_turn_class",
        _reg_with_partial_defaults,
    )
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-coauth-partial-defaults",
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
    proj = out["runtime_intelligence_projection"]
    assert proj["validation_authority_bridge"]["per_turn_class"]["opening_scene"][
        "partial_transfer_ready"
    ] is False
    assert any(
        "dramatic_mirror_fidelity_partial_defaults" in str(b)
        for b in proj["validation_authority_bridge"]["per_turn_class"]["opening_scene"][
            "partial_transfer_blocked"
        ]
    )
    assert "validation_co_authority_decision" not in proj
    assert "validation_co_authority_decision" not in proj["validator_dispatch_report"]


def test_readiness_preview_partial_defaults_not_eligible(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setattr(
        capability_validator_dispatch,
        "_sanitize_local_execution_evidence",
        _sanitize_local_evidence_preserve_dramatic_fidelity,
    )
    orig_reg = runtime_aspect_ledger.adr0041_validator_registry_for_turn_class

    def _reg_with_partial_defaults(tc: str):
        reg = dict(orig_reg(tc))
        reg[DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT] = _dramatic_mirror_adapter_with_partial_defaults
        return reg

    monkeypatch.setattr(
        runtime_aspect_ledger,
        "adr0041_validator_registry_for_turn_class",
        _reg_with_partial_defaults,
    )
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-ready-partial-defaults",
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
    _assert_readiness_preview_safety(preview)
    assert preview["policy_stage"] == "not_eligible"
    assert preview["would_allow_readiness"] is False
    assert "partial_defaults" in preview["blockers"]


def test_readiness_enforcement_partial_defaults_blocks(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setattr(
        capability_validator_dispatch,
        "_sanitize_local_execution_evidence",
        _sanitize_local_evidence_preserve_dramatic_fidelity,
    )
    orig_reg = runtime_aspect_ledger.adr0041_validator_registry_for_turn_class

    def _reg_with_partial_defaults(tc: str):
        reg = dict(orig_reg(tc))
        reg[DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT] = _dramatic_mirror_adapter_with_partial_defaults
        return reg

    monkeypatch.setattr(
        runtime_aspect_ledger,
        "adr0041_validator_registry_for_turn_class",
        _reg_with_partial_defaults,
    )
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-enforce-partial-defaults",
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
    _assert_readiness_enforcement_safety(enforcement)
    assert enforcement["readiness_input"] == "block"
    assert "partial_defaults" in enforcement["blockers"]


def test_drift_not_aligned_blocks_validation_co_authority_with_flag(monkeypatch) -> None:
    """Non-``aligned`` drift blocks handoff and therefore ``validation_co_authority_decision``."""
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-coauth-drift",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _opening_dispatch_context(),
        "validation_seam_summary": {"status": "rejected", "reason": "fixture_seam_stricter"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    proj = out["runtime_intelligence_projection"]
    assert proj["authority_handoff_candidate"]["candidate"] is False
    bridge = proj["validation_authority_bridge"]
    assert bridge["drift_classification"] != ADR0041_DRIFT_ALIGNED
    assert "validation_co_authority_decision" not in proj
    assert "validation_co_authority_decision" not in proj["validator_dispatch_report"]


def test_readiness_preview_drift_not_aligned_blocks(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-ready-drift",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _opening_dispatch_context(),
        "validation_seam_summary": {"status": "rejected", "reason": "fixture_seam_stricter"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    preview = out["runtime_intelligence_projection"]["readiness_co_authority_preview"]
    _assert_readiness_preview_safety(preview)
    assert preview["policy_stage"] in {"readiness_preview_block", "not_eligible"}
    assert preview["would_allow_readiness"] is False
    assert "drift_not_aligned" in preview["blockers"]


def test_readiness_enforcement_drift_not_aligned_blocks(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-enforce-drift",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _opening_dispatch_context(),
        "validation_seam_summary": {"status": "rejected", "reason": "fixture_seam_stricter"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    enforcement = out["runtime_intelligence_projection"]["readiness_co_authority_enforcement"]
    _assert_readiness_enforcement_safety(enforcement)
    assert enforcement["readiness_input"] == "block"
    assert "drift_not_aligned" in enforcement["blockers"]
    agg = out["runtime_intelligence_projection"]["readiness_aggregation_decision"]
    _assert_readiness_aggregation_safety(agg)
    assert agg["seam_readiness"] == "reject"
    assert agg["adr0041_readiness_input"] == "block"
    assert agg["aggregated_readiness"] == "block"
    assert agg["adr0041_veto_applied"] is False


def test_scoped_co_authority_player_turn_positive_path_scope_excludes_opening_event_coverage(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-coauth-player",
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
    proj = out["runtime_intelligence_projection"]
    decision = proj["validation_co_authority_decision"]
    report = proj["validator_dispatch_report"]
    assert decision == report["validation_co_authority_decision"]
    assert set(decision["scope"]) == _SCOPED_CO_AUTHORITY_SCOPE_WITHOUT_OPENING
    assert "opening_event_coverage" not in decision["scope"]
    assert {row["concern_id"] for row in decision["concern_decisions"]} == set(decision["scope"])
    assert decision["dramatic_effect_mirror_fidelity_sufficient"] is True
    assert decision["validation_outcome_changed"] is False
    assert decision["commit_gate_changed"] is False
    assert decision["readiness_gate_changed"] is False
    assert decision["affects_commit"] is False
    assert decision["affects_readiness"] is False
    assert decision["proof_level"] == "local_only"
    assert decision["live_or_staging_evidence"] is False


def test_scoped_co_authority_npc_conflict_positive_path_scope_excludes_opening_event_coverage(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    ledger = _ledger_npc_conflict_plan_enforced(dispatch_context=_npc_dispatch_context())
    out = normalize_runtime_aspect_ledger(ledger)
    proj = out["runtime_intelligence_projection"]
    decision = proj["validation_co_authority_decision"]
    report = proj["validator_dispatch_report"]
    assert decision == report["validation_co_authority_decision"]
    assert set(decision["scope"]) == _SCOPED_CO_AUTHORITY_SCOPE_WITHOUT_OPENING
    assert "opening_event_coverage" not in decision["scope"]
    assert {row["concern_id"] for row in decision["concern_decisions"]} == set(decision["scope"])
    assert decision["dramatic_effect_mirror_fidelity_sufficient"] is True
    assert decision["validation_outcome_changed"] is False
    assert decision["commit_gate_changed"] is False
    assert decision["readiness_gate_changed"] is False
    assert decision["affects_commit"] is False
    assert decision["affects_readiness"] is False
    assert decision["proof_level"] == "local_only"
    assert decision["live_or_staging_evidence"] is False


def test_handoff_blocked_when_missing_context_opening(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-miss",
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
    proj = out["runtime_intelligence_projection"]
    handoff = proj["authority_handoff_candidate"]
    assert handoff["candidate"] is False
    assert handoff["recommended_authority"] == "blocked"


def test_readiness_preview_missing_context_not_eligible(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-ready-missing-context",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": {},
        "validation_seam_summary": {"status": "approved", "reason": "fixture"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    preview = out["runtime_intelligence_projection"]["readiness_co_authority_preview"]
    _assert_readiness_preview_safety(preview)
    assert preview["policy_stage"] == "not_eligible"
    assert preview["would_allow_readiness"] is False
    assert "missing_context" in preview["blockers"]


def test_readiness_enforcement_missing_context_blocks(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-enforce-missing-context",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": {},
        "validation_seam_summary": {"status": "approved", "reason": "fixture"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    enforcement = out["runtime_intelligence_projection"]["readiness_co_authority_enforcement"]
    _assert_readiness_enforcement_safety(enforcement)
    assert enforcement["readiness_input"] == "block"
    assert "missing_context" in enforcement["blockers"]


def test_readiness_preview_unavailable_validator_not_eligible() -> None:
    report = {
        "mode": "plan_enforced",
        "validators_would_run": ["narrator_authority_contract"],
        "validators_unavailable": ["narrator_authority_contract"],
        "actually_executed": [],
        "entries": [],
    }
    preview = {
        "drift_vs_validation_seam": {"classification": ADR0041_DRIFT_MISSING_CONTEXT},
        "pass_fail_summary": {"failed_validator_ids": []},
    }
    bridge = build_validation_authority_bridge(
        validation_seam_summary={"status": "approved"},
        validator_dispatch_report=report,
        validation_authority_preview=preview,
        selected_turn_class="opening_scene",
    )
    from ai_stack.validation_authority_bridge import build_readiness_co_authority_preview

    readiness = build_readiness_co_authority_preview(
        validation_authority_bridge=bridge,
        validator_dispatch_report=report,
        selected_turn_class="opening_scene",
        validation_co_authority_decision=None,
        feature_flag_name=ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV,
        feature_flag_enabled=True,
    )
    _assert_readiness_preview_safety(readiness)
    assert readiness["policy_stage"] == "not_eligible"
    assert "unavailable_validator" in readiness["blockers"]


def test_readiness_enforcement_unavailable_validator_blocks() -> None:
    report = {
        "mode": "plan_enforced",
        "validators_would_run": ["narrator_authority_contract"],
        "validators_unavailable": ["narrator_authority_contract"],
        "actually_executed": [],
        "entries": [],
    }
    preview = {
        "mode": "shadow_readiness_preview",
        "policy_stage": "not_eligible",
        "would_allow_readiness": False,
        "would_block_readiness": True,
        "scope": [
            "actor_lane_forbidden_output",
            "dramatic_effect_gate",
            "hard_forbidden_runtime",
            "opening_event_coverage",
        ],
        "turn_class": "opening_scene",
        "drift_classification": ADR0041_DRIFT_MISSING_CONTEXT,
        "blockers": ["unavailable_validator", "missing_context"],
        "evidence": {
            "unavailable_validators": ["narrator_authority_contract"],
            "failed_validators": [],
            "mirror_fidelity_gate_passed": True,
        },
    }
    from ai_stack.validation_authority_bridge import build_readiness_co_authority_enforcement

    enforcement = build_readiness_co_authority_enforcement(
        readiness_co_authority_preview=preview,
        validator_dispatch_report=report,
        selected_turn_class="opening_scene",
        feature_flag_name=ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV,
        feature_flag_enabled=True,
    )
    _assert_readiness_enforcement_safety(enforcement)
    assert enforcement["readiness_input"] == "block"
    assert "unavailable_validator" in enforcement["blockers"]


def test_player_turn_negative_dramatic_gate_fails_handoff(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    bad = _player_dispatch_context()
    bad["proposed_state_effects"] = []
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-pl-bad",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="x",
        input_kind="action",
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": bad,
        "validation_seam_summary": {"status": "approved"},
    }
    out = normalize_runtime_aspect_ledger(ledger)
    handoff = out["runtime_intelligence_projection"]["authority_handoff_candidate"]
    assert handoff["candidate"] is False
    assert handoff["recommended_authority"] == "blocked"
    report = out["runtime_intelligence_projection"]["validator_dispatch_report"]
    assert "dramatic_effect_gate_mirror_contract" in (report.get("actually_executed") or [])
    assert any(
        isinstance(e, dict)
        and e.get("validator_id") == "dramatic_effect_gate_mirror_contract"
        and isinstance(e.get("local_execution_evidence"), dict)
        and e["local_execution_evidence"].get("passed") is False
        for e in (report.get("entries") or [])
    )


def test_plan_enforced_includes_bridge_opening(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br1",
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
    proj = out["runtime_intelligence_projection"]
    bridge = proj["validation_authority_bridge"]
    assert bridge["schema_version"] == VALIDATION_AUTHORITY_BRIDGE_SCHEMA_VERSION
    assert bridge["recommended_authority"] == "seam_canonical"
    assert bridge["affects_commit"] is False
    assert bridge["affects_readiness"] is False
    assert bridge["drift_classification"] is not None
    assert bridge["seam_status"]["status"] == "approved"
    assert bridge["adr0041_status"]["engagement"] == "plan_enforced"
    assert set(bridge["adr0041_status"]["executed_validator_ids"]) == set(
        get_turn_class_enforced_validators("opening_scene")
    )
    osnap = bridge["per_turn_class"]["opening_scene"]
    assert osnap["complete_enough_for_future_seam_partial_transfer"] is True
    assert osnap["partial_transfer_scope_registry_satisfied"] is True
    assert osnap["partial_transfer_ready"] is True
    assert osnap["partial_transfer_blocked"] == []
    assert "actor_lane_forbidden_output" not in osnap["uncovered_seam_concern_ids"]
    for key in ("normal_player_turn", "npc_conflict_turn"):
        snap = bridge["per_turn_class"][key]
        assert snap["complete_enough_for_future_seam_partial_transfer"] is True
        assert snap["partial_transfer_ready"] is False
        assert any("execution_not_observed" in b for b in snap["partial_transfer_blocked"])


def test_bridge_player_and_npc_turn_classes(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)

    ledger_p = initialize_runtime_aspect_ledger(
        session_id="s-brpl",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Gehe ins Bad",
        input_kind="action",
    )
    ledger_p[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _player_dispatch_context(),
        "validation_seam_summary": {"status": "approved"},
    }
    out_p = normalize_runtime_aspect_ledger(ledger_p)
    b_p = out_p["runtime_intelligence_projection"]["validation_authority_bridge"]
    assert b_p["selected_turn_class"] == "normal_player_turn"
    assert b_p["adr0041_status"]["engagement"] == "plan_enforced"

    ledger_n = initialize_runtime_aspect_ledger(
        session_id="s-brn",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="npc",
        raw_player_input="",
    )
    naspects = ledger_n["turn_aspect_ledger"][ASPECT_NPC_AGENCY]
    actors = {"primary": "veronique_vallon", "secondary": "michel_longstreet"}
    ledger_n["turn_aspect_ledger"][ASPECT_NPC_AGENCY] = {
        **naspects,
        "expected": {
            **(naspects.get("expected") if isinstance(naspects.get("expected"), dict) else {}),
            "candidate_actor_ids": [actors["primary"]],
        },
    }
    ledger_n[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _npc_dispatch_context(),
        "validation_seam_summary": {"status": "approved"},
    }
    out_n = normalize_runtime_aspect_ledger(ledger_n)
    b_n = out_n["runtime_intelligence_projection"]["validation_authority_bridge"]
    assert b_n["selected_turn_class"] == "npc_conflict_turn"


def test_build_bridge_drift_missing_context_migration_blocked() -> None:
    report = {
        "mode": "plan_enforced",
        "validators_would_run": ["narrator_authority_contract"],
        "validators_unavailable": ["narrator_authority_contract"],
        "actually_executed": [],
        "entries": [],
    }
    preview = {
        "schema_version": ADR0041_VALIDATION_AUTHORITY_PREVIEW_SCHEMA_VERSION,
        "drift_vs_validation_seam": {"classification": ADR0041_DRIFT_MISSING_CONTEXT},
    }
    b = build_validation_authority_bridge(
        validation_seam_summary={"status": "approved"},
        validator_dispatch_report=report,
        validation_authority_preview=preview,
        selected_turn_class="opening_scene",
    )
    assert b["drift_classification"] == ADR0041_DRIFT_MISSING_CONTEXT
    assert b["migration_readiness"] == "blocked_validator_unavailable"
    assert any(x.startswith("adr0041_validator_unavailable:") for x in b["blockers"])


def test_build_bridge_drift_adr_stricter() -> None:
    report = {
        "mode": "plan_enforced",
        "validators_would_run": ["scene_energy_contract"],
        "validators_unavailable": [],
        "actually_executed": ["scene_energy_contract"],
        "entries": [
            {
                "validator_id": "scene_energy_contract",
                "actually_executed": True,
                "unavailable": False,
                "local_execution_evidence": {"validator_id": "scene_energy_contract", "passed": False},
            }
        ],
    }
    preview = {
        "drift_vs_validation_seam": {"classification": ADR0041_DRIFT_ADR_STRICTER},
        "pass_fail_summary": {"failed_validator_ids": ["scene_energy_contract"]},
    }
    b = build_validation_authority_bridge(
        validation_seam_summary={"status": "approved"},
        validator_dispatch_report=report,
        validation_authority_preview=preview,
        selected_turn_class="opening_scene",
    )
    assert b["drift_classification"] == ADR0041_DRIFT_ADR_STRICTER
    assert b["migration_readiness"] == "drift_asymmetric_requires_review"
    assert "drift:adr0041_stricter_vs_seam" in b["blockers"]


def test_build_bridge_drift_seam_stricter() -> None:
    report = {
        "mode": "plan_enforced",
        "validators_would_run": ["scene_energy_contract"],
        "validators_unavailable": [],
        "actually_executed": ["scene_energy_contract"],
        "entries": [
            {
                "validator_id": "scene_energy_contract",
                "actually_executed": True,
                "unavailable": False,
                "local_execution_evidence": {"validator_id": "scene_energy_contract", "passed": True},
            }
        ],
    }
    preview = {"drift_vs_validation_seam": {"classification": ADR0041_DRIFT_SEAM_STRICTER}}
    b = build_validation_authority_bridge(
        validation_seam_summary={"status": "rejected", "reason": "dramatic_effect"},
        validator_dispatch_report=report,
        validation_authority_preview=preview,
        selected_turn_class="opening_scene",
    )
    assert b["migration_readiness"] == "drift_asymmetric_requires_review"
    assert "drift:seam_stricter_vs_adr0041" in b["blockers"]


def test_partial_transfer_blocked_when_dramatic_mirror_emits_partial_defaults_fidelity() -> None:
    """``partial_transfer_ready`` stays false if dramatic mirror evidence self-reports partial_defaults."""
    req_ids = [
        "actor_lane_forbidden_contract",
        "dramatic_effect_gate_mirror_contract",
        "scene_energy_contract",
        "hard_forbidden_runtime_contract",
        "opening_event_coverage_contract",
    ]
    entries: list[dict] = []
    for vid in req_ids:
        ev: dict = {"validator_id": vid, "passed": True}
        if vid == "dramatic_effect_gate_mirror_contract":
            ev["dramatic_effect_mirror_fidelity"] = "partial_defaults"
        entries.append(
            {
                "validator_id": vid,
                "actually_executed": True,
                "unavailable": False,
                "local_execution_evidence": ev,
            }
        )
    report = {
        "mode": "plan_enforced",
        "validators_would_run": req_ids,
        "validators_unavailable": [],
        "actually_executed": req_ids,
        "entries": entries,
    }
    preview = {"drift_vs_validation_seam": {"classification": ADR0041_DRIFT_ALIGNED}}
    b = build_validation_authority_bridge(
        validation_seam_summary={"status": "approved"},
        validator_dispatch_report=report,
        validation_authority_preview=preview,
        selected_turn_class="opening_scene",
    )
    snap = b["per_turn_class"]["opening_scene"]
    assert snap["partial_transfer_scope_registry_satisfied"] is True
    assert snap["partial_transfer_ready"] is False
    assert any("dramatic_mirror_fidelity_partial_defaults" in x for x in snap["partial_transfer_blocked"])


def test_normal_player_turn_partial_transfer_ready_when_sidecar_aligned(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-br-player-pt",
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
    snap = out["runtime_intelligence_projection"]["validation_authority_bridge"]["per_turn_class"][
        "normal_player_turn"
    ]
    assert snap["partial_transfer_scope_registry_satisfied"] is True
    assert snap["partial_transfer_ready"] is True
    assert snap["partial_transfer_blocked"] == []


def test_npc_conflict_turn_partial_transfer_ready_when_sidecar_aligned(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    ledger = _ledger_npc_conflict_plan_enforced(dispatch_context=_npc_dispatch_context())
    out = normalize_runtime_aspect_ledger(ledger)
    bridge = out["runtime_intelligence_projection"]["validation_authority_bridge"]
    report = out["runtime_intelligence_projection"]["validator_dispatch_report"]
    assert bridge["selected_turn_class"] == "npc_conflict_turn"
    snap = bridge["per_turn_class"]["npc_conflict_turn"]
    assert snap["partial_transfer_scope_registry_satisfied"] is True
    assert snap["partial_transfer_ready"] is True
    assert snap["partial_transfer_blocked"] == []
    executed = set(report.get("actually_executed") or [])
    assert _NPC_CONFLICT_PARTIAL_TRANSFER_SCOPE <= executed
    for ent in report.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        if ent.get("validator_id") != "dramatic_effect_gate_mirror_contract":
            continue
        ev = ent.get("local_execution_evidence")
        assert isinstance(ev, dict)
        assert ev.get("dramatic_effect_mirror_fidelity") != "partial_defaults"
        assert ev.get("passed") is True


def test_npc_conflict_turn_partial_transfer_blocked_when_dispatch_context_incomplete(monkeypatch) -> None:
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    ledger = _ledger_npc_conflict_plan_enforced(dispatch_context={})
    out = normalize_runtime_aspect_ledger(ledger)
    snap = out["runtime_intelligence_projection"]["validation_authority_bridge"]["per_turn_class"][
        "npc_conflict_turn"
    ]
    assert snap["partial_transfer_scope_registry_satisfied"] is True
    assert snap["partial_transfer_ready"] is False
    assert any("partial_transfer:validators_not_executed:" in b for b in snap["partial_transfer_blocked"])


def test_npc_conflict_turn_partial_transfer_blocked_when_dramatic_mirror_partial_defaults_fidelity() -> None:
    req_ids = sorted(_NPC_CONFLICT_PARTIAL_TRANSFER_SCOPE)
    entries: list[dict] = []
    for vid in req_ids:
        ev: dict = {"validator_id": vid, "passed": True}
        if vid == "dramatic_effect_gate_mirror_contract":
            ev["dramatic_effect_mirror_fidelity"] = "partial_defaults"
        entries.append(
            {
                "validator_id": vid,
                "actually_executed": True,
                "unavailable": False,
                "local_execution_evidence": ev,
            }
        )
    report = {
        "mode": "plan_enforced",
        "validators_would_run": req_ids,
        "validators_unavailable": [],
        "actually_executed": req_ids,
        "entries": entries,
    }
    preview = {"drift_vs_validation_seam": {"classification": ADR0041_DRIFT_ALIGNED}}
    b = build_validation_authority_bridge(
        validation_seam_summary={"status": "approved"},
        validator_dispatch_report=report,
        validation_authority_preview=preview,
        selected_turn_class="npc_conflict_turn",
    )
    snap = b["per_turn_class"]["npc_conflict_turn"]
    assert snap["partial_transfer_ready"] is False
    assert any("dramatic_mirror_fidelity_partial_defaults" in x for x in snap["partial_transfer_blocked"])


def test_build_bridge_drift_conflicting() -> None:
    report = {
        "mode": "plan_enforced",
        "validators_would_run": ["scene_energy_contract"],
        "validators_unavailable": [],
        "actually_executed": ["scene_energy_contract"],
        "entries": [
            {
                "validator_id": "scene_energy_contract",
                "actually_executed": True,
                "unavailable": False,
                "local_execution_evidence": {"validator_id": "scene_energy_contract", "passed": False},
            }
        ],
    }
    preview = {"drift_vs_validation_seam": {"classification": ADR0041_DRIFT_CONFLICTING_RESULT}}
    b = build_validation_authority_bridge(
        validation_seam_summary={"status": "rejected"},
        validator_dispatch_report=report,
        validation_authority_preview=preview,
        selected_turn_class="opening_scene",
    )
    assert b["migration_readiness"] == "drift_conflicting_requires_review"
    assert "drift:conflicting_result" in b["blockers"]


def test_seam_concerns_covered_helper() -> None:
    out = seam_concerns_covered_by_adr0041_validators({"scene_energy_contract", "player_intent_contract"})
    assert "dramatic_effect_gate" in out["covered_seam_concern_ids"]
    assert "actor_lane_forbidden_output" in out["uncovered_seam_concern_ids"]
