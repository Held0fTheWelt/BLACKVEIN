"""Tests for ADR-0041 ``validation_authority_bridge`` (seam vs local validators, non-commit)."""

from __future__ import annotations

from ai_stack.capability_validator_dispatch import ValidatorDispatchMode
from ai_stack.runtime_aspect_ledger import (
    ADR0041_DRIFT_ADR_STRICTER,
    ADR0041_DRIFT_ALIGNED,
    ADR0041_DRIFT_CONFLICTING_RESULT,
    ADR0041_DRIFT_MISSING_CONTEXT,
    ADR0041_DRIFT_SEAM_STRICTER,
    ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY,
    ADR0041_VALIDATION_AUTHORITY_PREVIEW_SCHEMA_VERSION,
    ASPECT_NPC_AGENCY,
    initialize_runtime_aspect_ledger,
    normalize_runtime_aspect_ledger,
)
from ai_stack.capability_validator_registry import get_turn_class_enforced_validators
from ai_stack.tests.test_capability_validator_registry import (
    _npc_dispatch_context,
    _opening_dispatch_context,
    _player_dispatch_context,
)
from ai_stack.validation_authority_bridge import (
    VALIDATION_AUTHORITY_BRIDGE_SCHEMA_VERSION,
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
    assert handoff["affects_commit"] is False
    assert handoff["proof_level"] == "local_only"
    assert set(handoff["scope"]) == {
        "actor_lane_forbidden_output",
        "dramatic_effect_gate",
        "hard_forbidden_runtime",
    }
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