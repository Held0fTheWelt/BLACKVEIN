"""Task 4: cross-surface contract checks for operator_audit and routing_evidence (G-XS-01)."""

from __future__ import annotations

import pytest

from app.content.module_models import ContentModule, ModuleMetadata
from app.runtime.adapter_registry import clear_registry, register_adapter_model
from app.runtime.ai_turn_executor import execute_turn_with_ai
from app.runtime.operator_audit import AUDIT_SCHEMA_VERSION, RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS
from app.runtime.runtime_models import SessionState

from .test_runtime_operational_bootstrap_and_routing_registry import assert_operator_audit_truth_payload_shape
from .test_runtime_staged_orchestration import (  # noqa: PLC2701
    StagedRecordingAdapter,
    _llm_spec,
    _slm_spec,
)

OPERATOR_AUDIT_TOP_KEYS = frozenset(
    {
        "audit_schema_version",
        "audit_summary",
        "audit_timeline",
        "audit_deviations",
        "audit_flags",
        "audit_review_fingerprint",
    }
)

AUDIT_TIMELINE_ENTRY_KEYS = frozenset(
    {
        "ordinal",
        "stage_key",
        "stage_kind",
        "bounded_model_call",
        "skip_reason",
        "route_reason_code",
        "diagnostics_route_class",
        "diagnostics_severity",
        "error_count",
    }
)

ROUTING_EVIDENCE_CONTRACT_KEYS = frozenset(
    {
        "route_reason_code",
        "requested_workflow_phase",
        "requested_task_kind",
        "routing_overview",
        "no_eligible_spec_selection",
        "diagnostics_overview",
        "diagnostics_flags",
        "diagnostics_causes",
        "policy_execution_aligned",
        "execution_deviation",
    }
)


def _assert_operator_audit_shell(audit: dict, *, expected_surface: str) -> None:
    assert isinstance(audit, dict)
    missing_top = OPERATOR_AUDIT_TOP_KEYS - set(audit.keys())
    assert not missing_top, f"operator_audit missing keys: {missing_top}"
    assert audit["audit_schema_version"] == AUDIT_SCHEMA_VERSION
    summary = audit["audit_summary"]
    assert summary.get("surface") == expected_surface
    assert "max_diagnostics_severity" in summary
    assert "primary_concern_code" in summary
    timeline = audit["audit_timeline"]
    assert isinstance(timeline, list) and timeline
    for entry in timeline:
        missing = AUDIT_TIMELINE_ENTRY_KEYS - set(entry.keys())
        assert not missing, f"audit_timeline entry missing keys: {missing}"
    # G-CONV-05: additive compact Area 2 operator truth
    truth = audit.get("area2_operator_truth")
    assert isinstance(truth, dict), "operator_audit must include area2_operator_truth"
    assert_operator_audit_truth_payload_shape(truth)


def _assert_routing_evidence_contract(ev: dict) -> None:
    missing = ROUTING_EVIDENCE_CONTRACT_KEYS - set(ev.keys())
    assert not missing, f"routing_evidence missing keys: {missing}"
    assert isinstance(ev.get("routing_overview"), dict)
    assert ev["routing_overview"].get("title")


@pytest.fixture
def minimal_module() -> ContentModule:
    meta = ModuleMetadata(
        module_id="m1",
        title="T",
        version="1",
        contract_version="1.0.0",
    )
    return ContentModule(metadata=meta, scenes={}, characters={})


@pytest.mark.asyncio
async def test_runtime_staged_operator_audit_matches_cross_surface_contract(
    minimal_module: ContentModule,
):
    clear_registry()
    slm_ad = StagedRecordingAdapter("xs_runtime_slm", slm_sufficient=False)
    llm_ad = StagedRecordingAdapter("xs_runtime_llm", slm_sufficient=False)
    register_adapter_model(_slm_spec("xs_runtime_slm"), slm_ad)
    register_adapter_model(_llm_spec("xs_runtime_llm"), llm_ad)

    session = SessionState(
        session_id="s-xs-runtime",
        execution_mode="ai",
        adapter_name="xs_runtime_slm",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}

    await execute_turn_with_ai(session, 1, slm_ad, minimal_module)
    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    audit = log.operator_audit or {}
    _assert_operator_audit_shell(audit, expected_surface="runtime")
    aus = audit.get("audit_summary") or {}
    for rk in RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS:
        assert rk in aus, f"runtime audit_summary must expose compact ranking field {rk}"
    rr = ((audit.get("area2_operator_truth") or {}).get("legibility") or {}).get("runtime_ranking_summary")
    assert isinstance(rr, dict)
    for rk in RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS:
        assert rk in rr

    for tr in log.runtime_stage_traces or []:
        if tr.get("stage_kind") != "routed_model_stage":
            continue
        ev = tr.get("routing_evidence") or {}
        if ev:
            _assert_routing_evidence_contract(ev)
        assert tr.get("stage_id"), "runtime trace should expose stage_id"
    clear_registry()
    assert llm_ad.calls >= 1


def test_writers_room_operator_audit_and_routing_evidence_contract(client, auth_headers):
    response = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "canon consistency"},
    )
    assert response.status_code == 200
    data = response.get_json()
    audit = data.get("operator_audit") or {}
    _assert_operator_audit_shell(audit, expected_surface="writers_room")
    assert "interpretation_layer" in (audit.get("audit_summary") or {})

    t2a = (data.get("model_generation") or {}).get("task_2a_routing") or {}
    for key in ("preflight", "synthesis"):
        st = t2a.get(key) or {}
        assert st.get("stage_id") == key
        assert st.get("stage") == key, "stage_id must alias stage for bounded surfaces"
        _assert_routing_evidence_contract(st.get("routing_evidence") or {})


def test_improvement_operator_audit_and_deterministic_base_separation(client, auth_headers):
    variant_resp = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={"baseline_id": "god_of_carnage", "candidate_summary": "Cross-surface contract variant."},
    )
    assert variant_resp.status_code == 201
    variant_id = variant_resp.get_json()["variant_id"]

    experiment_resp = client.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers,
        json={
            "variant_id": variant_id,
            "test_inputs": [
                "I argue with measured tone.",
                "I repeat the same accusation again and again.",
                "I try to de-escalate the conflict.",
            ],
        },
    )
    assert experiment_resp.status_code == 200
    payload = experiment_resp.get_json()
    recommendation = payload["recommendation_package"]
    audit = recommendation.get("operator_audit") or {}
    _assert_operator_audit_shell(audit, expected_surface="improvement")
    assert "interpretation_layer" in (audit.get("audit_summary") or {})

    t2a = recommendation.get("task_2a_routing") or {}
    for key in ("preflight", "synthesis"):
        st = t2a.get(key) or {}
        assert st.get("stage_id") == key
        assert st.get("stage") == key
        _assert_routing_evidence_contract(st.get("routing_evidence") or {})

    assert recommendation.get("deterministic_recommendation_base")
    mai = recommendation.get("model_assisted_interpretation") or {}
    assert mai.get("disclaimer")
    assert "Advisory" in mai["disclaimer"] or "advisory" in mai["disclaimer"].lower()


def test_operator_truth_coherent_across_bounded_http_surfaces(client, auth_headers):
    """G-CONV-08: same area2_operator_truth key set across Runtime, WR, Improvement."""
    wr = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "canon consistency"},
    )
    assert wr.status_code == 200
    wr_truth = (wr.get_json().get("operator_audit") or {}).get("area2_operator_truth") or {}
    assert_operator_audit_truth_payload_shape(wr_truth)

    variant_resp = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={"baseline_id": "god_of_carnage", "candidate_summary": "G-CONV-08 coherence variant."},
    )
    assert variant_resp.status_code == 201
    variant_id = variant_resp.get_json()["variant_id"]
    exp = client.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers,
        json={
            "variant_id": variant_id,
            "test_inputs": ["one", "two", "three"],
        },
    )
    assert exp.status_code == 200
    imp_truth = (exp.get_json().get("recommendation_package") or {}).get("operator_audit") or {}
    imp_truth = imp_truth.get("area2_operator_truth") or {}
    assert_operator_audit_truth_payload_shape(imp_truth)

    assert set(wr_truth.keys()) == set(imp_truth.keys()), "WR vs Improvement area2_operator_truth keys must match"


@pytest.mark.asyncio
async def test_runtime_operator_truth_keys_align_with_bounded_http(
    client,
    auth_headers,
    minimal_module: ContentModule,
):
    """Runtime (in-process) and Writers-Room HTTP share the same area2_operator_truth key set."""
    clear_registry()
    slm_ad = StagedRecordingAdapter("gconv8_slm", slm_sufficient=True)
    llm_ad = StagedRecordingAdapter("gconv8_llm", slm_sufficient=True)
    register_adapter_model(_slm_spec("gconv8_slm"), slm_ad)
    register_adapter_model(_llm_spec("gconv8_llm"), llm_ad)
    session = SessionState(
        session_id="gconv8-runtime",
        execution_mode="ai",
        adapter_name="gconv8_slm",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}
    await execute_turn_with_ai(session, 1, slm_ad, minimal_module)
    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    rt_truth = (log.operator_audit or {}).get("area2_operator_truth") or {}
    assert_operator_audit_truth_payload_shape(rt_truth)
    clear_registry()

    wr = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "G-CONV-08 runtime vs bounded keys"},
    )
    assert wr.status_code == 200
    wr_truth = (wr.get_json().get("operator_audit") or {}).get("area2_operator_truth") or {}
    assert_operator_audit_truth_payload_shape(wr_truth)
    assert set(rt_truth.keys()) == set(wr_truth.keys()), "Runtime vs Writers-Room area2_operator_truth keys must match"
