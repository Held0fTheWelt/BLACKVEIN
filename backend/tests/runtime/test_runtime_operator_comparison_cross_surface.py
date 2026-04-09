"""Runtime operator comparison: compact ``compact_operator_comparison`` grammar across surfaces (G-T3-01 … G-T3-08)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.content.module_models import ContentModule, ModuleMetadata
from app.runtime.adapter_registry import clear_registry, register_adapter_model
from app.runtime.ai_turn_executor import execute_turn_with_ai
from app.runtime.area2_operator_truth import (
    AREA2_OPERATOR_COMPARISON_GRAMMAR_VERSION,
    COMPACT_OPERATOR_COMPARISON_KEYS,
    build_area2_operator_truth,
)
from app.runtime.area2_routing_authority import (
    AUTHORITY_SOURCE_IMPROVEMENT,
    AUTHORITY_SOURCE_RUNTIME,
)
from app.runtime.model_routing_contracts import RouteReasonCode
from app.runtime.operator_audit import RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS
from app.runtime.routing_registry_bootstrap import bootstrap_routing_registry_from_config
from app.runtime.runtime_models import SessionState

from .doc_test_paths import architecture_style_doc
from .test_runtime_operational_bootstrap_and_routing_registry import assert_operator_audit_truth_payload_shape
from .test_runtime_staged_orchestration import (  # noqa: PLC2701
    StagedRecordingAdapter,
    _llm_spec,
    _slm_spec,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
G_T3_DOC_FILES = (
    "area2_task3_closure_gates.md",
    "area2_operator_comparison_closure_report.md",
    "llm_slm_role_stratification.md",
    "ai_story_contract.md",
)
AREA2_OPERATOR_TRUTH_PY = REPO_ROOT / "backend" / "app" / "runtime" / "area2_operator_truth.py"


def _first_pass_operator_view(audit: dict) -> dict:
    """G-T3-02 / G-T3-06: only compact comparison + audit_summary (no timeline or traces)."""
    truth = audit.get("area2_operator_truth") if isinstance(audit.get("area2_operator_truth"), dict) else {}
    return {
        "audit_summary": audit.get("audit_summary") if isinstance(audit.get("audit_summary"), dict) else {},
        "compact_operator_comparison": truth.get("compact_operator_comparison"),
    }


def _assert_story_from_first_pass(view: dict, *, expected_surface: str) -> None:
    coc = view.get("compact_operator_comparison")
    assert isinstance(coc, dict), "compact_operator_comparison required for first-pass readability"
    assert coc.get("surface") == expected_surface
    assert isinstance(coc.get("route_status"), str) and coc.get("route_status")
    assert isinstance(coc.get("authority_source"), str) and coc.get("authority_source")
    assert "policy_execution_comparison" in coc
    pec = coc["policy_execution_comparison"]
    assert isinstance(pec, dict) and pec.get("posture") in (
        "aligned",
        "misaligned",
        "mixed",
        "unknown",
        "not_applicable",
    )
    summary = view.get("audit_summary") or {}
    assert summary.get("surface") == expected_surface
    assert summary.get("primary_concern_code") == coc.get("primary_operational_concern")
    nem = coc.get("no_eligible_operator_meaning")
    assert isinstance(nem, dict) and "operator_meaning_token" in nem
    svs = coc.get("selected_vs_executed")
    assert isinstance(svs, dict) and "per_stage" in svs and "legacy_roll_up" in svs


@pytest.mark.asyncio
async def test_operator_comparison_compact_truth_payload_under_bootstrap(
    app_bootstrap_on,
    client_bootstrap_on,
    auth_headers_bootstrap_on,
):
    """G-T3-01: mandatory compact comparison grammar on Runtime, Writers-Room, Improvement."""
    from app.services.writers_room_model_routing import build_writers_room_model_route_specs

    clear_registry()
    bootstrap_routing_registry_from_config(app_bootstrap_on)
    try:
        with app_bootstrap_on.app_context():
            slm_ad = StagedRecordingAdapter("gt3_slm", slm_sufficient=True)
            llm_ad = StagedRecordingAdapter("gt3_llm", slm_sufficient=True)
            register_adapter_model(_slm_spec("gt3_slm"), slm_ad)
            register_adapter_model(_llm_spec("gt3_llm"), llm_ad)
            meta = ModuleMetadata(
                module_id="m1",
                title="T",
                version="1",
                contract_version="1.0.0",
            )
            mod = ContentModule(metadata=meta, scenes={}, characters={})
            session = SessionState(
                session_id="gt3-rt",
                execution_mode="ai",
                adapter_name="gt3_slm",
                module_id="m1",
                module_version="1",
                current_scene_id="scene1",
            )
            session.canonical_state = {}
            await execute_turn_with_ai(session, 1, slm_ad, mod)
            log = (session.metadata.get("ai_decision_logs") or [])[-1]
            rt_audit = log.operator_audit or {}
            rt_truth = rt_audit.get("area2_operator_truth") or {}
            assert_operator_audit_truth_payload_shape(rt_truth)
            coc_rt = rt_truth["compact_operator_comparison"]
            assert set(coc_rt.keys()) == COMPACT_OPERATOR_COMPARISON_KEYS
            assert coc_rt["grammar_version"] == AREA2_OPERATOR_COMPARISON_GRAMMAR_VERSION
    finally:
        clear_registry()

    wr = client_bootstrap_on.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers_bootstrap_on,
        json={"module_id": "god_of_carnage", "focus": "G-T3-01"},
    )
    assert wr.status_code == 200
    wr_audit = wr.get_json().get("operator_audit") or {}
    wr_truth = wr_audit.get("area2_operator_truth") or {}
    assert_operator_audit_truth_payload_shape(wr_truth)
    coc_wr = wr_truth["compact_operator_comparison"]
    assert set(coc_wr.keys()) == COMPACT_OPERATOR_COMPARISON_KEYS
    assert coc_wr["grammar_version"] == AREA2_OPERATOR_COMPARISON_GRAMMAR_VERSION

    variant_resp = client_bootstrap_on.post(
        "/api/v1/improvement/variants",
        headers=auth_headers_bootstrap_on,
        json={"baseline_id": "god_of_carnage", "candidate_summary": "G-T3-01 variant."},
    )
    assert variant_resp.status_code == 201
    variant_id = variant_resp.get_json()["variant_id"]
    exp = client_bootstrap_on.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers_bootstrap_on,
        json={"variant_id": variant_id, "test_inputs": ["t3"]},
    )
    assert exp.status_code == 200
    imp_audit = (exp.get_json().get("recommendation_package") or {}).get("operator_audit") or {}
    imp_truth = imp_audit.get("area2_operator_truth") or {}
    assert_operator_audit_truth_payload_shape(imp_truth)
    coc_imp = imp_truth["compact_operator_comparison"]
    assert set(coc_imp.keys()) == COMPACT_OPERATOR_COMPARISON_KEYS
    assert coc_imp["grammar_version"] == AREA2_OPERATOR_COMPARISON_GRAMMAR_VERSION

    specs = list(build_writers_room_model_route_specs())
    synthetic = build_area2_operator_truth(
        surface="improvement",
        authority_source=AUTHORITY_SOURCE_IMPROVEMENT,
        bootstrap_enabled=True,
        registry_model_spec_count=len(specs),
        specs_for_coverage=specs,
        bounded_traces=[],
    )
    assert_operator_audit_truth_payload_shape(synthetic)


@pytest.mark.asyncio
async def test_operator_comparison_bounded_http_readability(
    app_bootstrap_on,
    client_bootstrap_on,
    auth_headers_bootstrap_on,
):
    """G-T3-02: primary story from compact_operator_comparison + audit_summary only."""
    clear_registry()
    bootstrap_routing_registry_from_config(app_bootstrap_on)
    try:
        with app_bootstrap_on.app_context():
            slm_ad = StagedRecordingAdapter("gt302_slm", slm_sufficient=True)
            llm_ad = StagedRecordingAdapter("gt302_llm", slm_sufficient=True)
            register_adapter_model(_slm_spec("gt302_slm"), slm_ad)
            register_adapter_model(_llm_spec("gt302_llm"), llm_ad)
            meta = ModuleMetadata(
                module_id="m1",
                title="T",
                version="1",
                contract_version="1.0.0",
            )
            mod = ContentModule(metadata=meta, scenes={}, characters={})
            session = SessionState(
                session_id="gt302-rt",
                execution_mode="ai",
                adapter_name="gt302_slm",
                module_id="m1",
                module_version="1",
                current_scene_id="scene1",
            )
            session.canonical_state = {}
            await execute_turn_with_ai(session, 1, slm_ad, mod)
            log = (session.metadata.get("ai_decision_logs") or [])[-1]
            fp = _first_pass_operator_view(log.operator_audit or {})
            _assert_story_from_first_pass(fp, expected_surface="runtime")
    finally:
        clear_registry()

    wr = client_bootstrap_on.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers_bootstrap_on,
        json={"module_id": "god_of_carnage", "focus": "G-T3-02"},
    )
    assert wr.status_code == 200
    _assert_story_from_first_pass(_first_pass_operator_view(wr.get_json().get("operator_audit") or {}), expected_surface="writers_room")

    variant_resp = client_bootstrap_on.post(
        "/api/v1/improvement/variants",
        headers=auth_headers_bootstrap_on,
        json={"baseline_id": "god_of_carnage", "candidate_summary": "G-T3-02 variant."},
    )
    assert variant_resp.status_code == 201
    variant_id = variant_resp.get_json()["variant_id"]
    exp = client_bootstrap_on.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers_bootstrap_on,
        json={"variant_id": variant_id, "test_inputs": ["t"]},
    )
    assert exp.status_code == 200
    imp_audit = (exp.get_json().get("recommendation_package") or {}).get("operator_audit") or {}
    _assert_story_from_first_pass(_first_pass_operator_view(imp_audit), expected_surface="improvement")


def test_operator_comparison_policy_execution_fields():
    """G-T3-03: posture is derived from alignment / execution_deviation flags only."""
    from app.services.writers_room_model_routing import build_writers_room_model_route_specs

    specs = list(build_writers_room_model_route_specs())

    aligned_trace = {
        "stage_id": "preflight",
        "decision": {
            "route_reason_code": RouteReasonCode.role_matrix_primary.value,
            "selected_adapter_name": "mock",
        },
        "routing_evidence": {
            "route_reason_code": RouteReasonCode.role_matrix_primary.value,
            "policy_execution_aligned": True,
            "diagnostics_overview": {"summary": "Primary route"},
        },
    }
    truth_ok = build_area2_operator_truth(
        surface="improvement",
        authority_source=AUTHORITY_SOURCE_IMPROVEMENT,
        bootstrap_enabled=True,
        registry_model_spec_count=len(specs),
        specs_for_coverage=specs,
        bounded_traces=[aligned_trace],
    )
    assert truth_ok["compact_operator_comparison"]["policy_execution_comparison"]["posture"] == "aligned"

    misaligned_trace = {
        "stage_id": "preflight",
        "decision": {
            "route_reason_code": RouteReasonCode.role_matrix_primary.value,
            "selected_adapter_name": "mock",
        },
        "routing_evidence": {
            "route_reason_code": RouteReasonCode.role_matrix_primary.value,
            "policy_execution_aligned": False,
            "execution_deviation": {"note": "bounded executor mismatch"},
        },
    }
    truth_bad = build_area2_operator_truth(
        surface="improvement",
        authority_source=AUTHORITY_SOURCE_IMPROVEMENT,
        bootstrap_enabled=True,
        registry_model_spec_count=len(specs),
        specs_for_coverage=specs,
        bounded_traces=[misaligned_trace],
    )
    assert truth_bad["compact_operator_comparison"]["policy_execution_comparison"]["posture"] == "misaligned"

    mixed_traces = [
        aligned_trace,
        {
            "stage_id": "synthesis",
            "decision": {
                "route_reason_code": RouteReasonCode.role_matrix_primary.value,
                "selected_adapter_name": "mock",
            },
            "routing_evidence": {
                "route_reason_code": RouteReasonCode.role_matrix_primary.value,
                "policy_execution_aligned": False,
            },
        },
    ]
    truth_mixed = build_area2_operator_truth(
        surface="improvement",
        authority_source=AUTHORITY_SOURCE_IMPROVEMENT,
        bootstrap_enabled=True,
        registry_model_spec_count=len(specs),
        specs_for_coverage=specs,
        bounded_traces=mixed_traces,
    )
    assert truth_mixed["compact_operator_comparison"]["policy_execution_comparison"]["posture"] == "mixed"


@pytest.mark.asyncio
async def test_operator_comparison_runtime_writers_room_improvement_shape(
    app_bootstrap_on,
    client_bootstrap_on,
    auth_headers_bootstrap_on,
):
    """G-T3-04: same grammar; bounded surfaces expose explicit null runtime_path_summary slots."""
    from app.services.writers_room_model_routing import build_writers_room_model_route_specs

    clear_registry()
    bootstrap_routing_registry_from_config(app_bootstrap_on)
    try:
        with app_bootstrap_on.app_context():
            slm_ad = StagedRecordingAdapter("gt304_slm", slm_sufficient=True)
            llm_ad = StagedRecordingAdapter("gt304_llm", slm_sufficient=True)
            register_adapter_model(_slm_spec("gt304_slm"), slm_ad)
            register_adapter_model(_llm_spec("gt304_llm"), llm_ad)
            meta = ModuleMetadata(
                module_id="m1",
                title="T",
                version="1",
                contract_version="1.0.0",
            )
            mod = ContentModule(metadata=meta, scenes={}, characters={})
            session = SessionState(
                session_id="gt304-rt",
                execution_mode="ai",
                adapter_name="gt304_slm",
                module_id="m1",
                module_version="1",
                current_scene_id="scene1",
            )
            session.canonical_state = {}
            await execute_turn_with_ai(session, 1, slm_ad, mod)
            log = (session.metadata.get("ai_decision_logs") or [])[-1]
            rt_coc = ((log.operator_audit or {}).get("area2_operator_truth") or {}).get("compact_operator_comparison") or {}
            rps_rt = rt_coc.get("runtime_path_summary") or {}
            assert set(rps_rt.keys()) == set(RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS)
            assert any(v is not None for v in rps_rt.values()), (
                "runtime must populate at least one runtime_path_summary slot when staged orchestration ran"
            )
    finally:
        clear_registry()

    wr = client_bootstrap_on.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers_bootstrap_on,
        json={"module_id": "god_of_carnage", "focus": "G-T3-04"},
    )
    assert wr.status_code == 200
    wr_coc = ((wr.get_json().get("operator_audit") or {}).get("area2_operator_truth") or {}).get(
        "compact_operator_comparison"
    ) or {}
    rps_wr = wr_coc.get("runtime_path_summary") or {}
    assert all(v is None for v in rps_wr.values()), "bounded surface must use explicit null runtime_path_summary values"

    variant_resp = client_bootstrap_on.post(
        "/api/v1/improvement/variants",
        headers=auth_headers_bootstrap_on,
        json={"baseline_id": "god_of_carnage", "candidate_summary": "G-T3-04 variant."},
    )
    assert variant_resp.status_code == 201
    variant_id = variant_resp.get_json()["variant_id"]
    exp = client_bootstrap_on.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers_bootstrap_on,
        json={"variant_id": variant_id, "test_inputs": ["t"]},
    )
    assert exp.status_code == 200
    imp_coc = (
        ((exp.get_json().get("recommendation_package") or {}).get("operator_audit") or {}).get("area2_operator_truth") or {}
    ).get("compact_operator_comparison") or {}
    rps_imp = imp_coc.get("runtime_path_summary") or {}
    assert all(v is None for v in rps_imp.values())

    specs = list(build_writers_room_model_route_specs())
    assert set(wr_coc.keys()) == set(imp_coc.keys()) == COMPACT_OPERATOR_COMPARISON_KEYS


@pytest.mark.asyncio
async def test_operator_comparison_primary_concern_visible_when_present(app_bootstrap_on, client_bootstrap_on, auth_headers_bootstrap_on):
    """G-T3-05: compact primary concern matches audit_summary."""
    clear_registry()
    bootstrap_routing_registry_from_config(app_bootstrap_on)
    try:
        with app_bootstrap_on.app_context():
            slm_ad = StagedRecordingAdapter("gt305_slm", slm_sufficient=True)
            llm_ad = StagedRecordingAdapter("gt305_llm", slm_sufficient=True)
            register_adapter_model(_slm_spec("gt305_slm"), slm_ad)
            register_adapter_model(_llm_spec("gt305_llm"), llm_ad)
            meta = ModuleMetadata(
                module_id="m1",
                title="T",
                version="1",
                contract_version="1.0.0",
            )
            mod = ContentModule(metadata=meta, scenes={}, characters={})
            session = SessionState(
                session_id="gt305-rt",
                execution_mode="ai",
                adapter_name="gt305_slm",
                module_id="m1",
                module_version="1",
                current_scene_id="scene1",
            )
            session.canonical_state = {}
            await execute_turn_with_ai(session, 1, slm_ad, mod)
            log = (session.metadata.get("ai_decision_logs") or [])[-1]
            audit = log.operator_audit or {}
            coc = (audit.get("area2_operator_truth") or {}).get("compact_operator_comparison") or {}
            assert coc.get("primary_operational_concern") == (audit.get("audit_summary") or {}).get("primary_concern_code")
    finally:
        clear_registry()

    wr = client_bootstrap_on.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers_bootstrap_on,
        json={"module_id": "god_of_carnage", "focus": "G-T3-05"},
    )
    assert wr.status_code == 200
    aud = wr.get_json().get("operator_audit") or {}
    coc = (aud.get("area2_operator_truth") or {}).get("compact_operator_comparison") or {}
    assert coc.get("primary_operational_concern") == (aud.get("audit_summary") or {}).get("primary_concern_code")

    variant_resp = client_bootstrap_on.post(
        "/api/v1/improvement/variants",
        headers=auth_headers_bootstrap_on,
        json={"baseline_id": "god_of_carnage", "candidate_summary": "G-T3-05 variant."},
    )
    assert variant_resp.status_code == 201
    variant_id = variant_resp.get_json()["variant_id"]
    exp = client_bootstrap_on.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers_bootstrap_on,
        json={"variant_id": variant_id, "test_inputs": ["t"]},
    )
    assert exp.status_code == 200
    imp_aud = (exp.get_json().get("recommendation_package") or {}).get("operator_audit") or {}
    imp_coc = (imp_aud.get("area2_operator_truth") or {}).get("compact_operator_comparison") or {}
    assert imp_coc.get("primary_operational_concern") == (imp_aud.get("audit_summary") or {}).get(
        "primary_concern_code"
    )


@pytest.mark.asyncio
async def test_operator_comparison_no_hidden_reconstruction_dependency(
    app_bootstrap_on,
    client_bootstrap_on,
    auth_headers_bootstrap_on,
):
    """G-T3-06: first-pass view suffices; deep timeline and traces still exist on full audit."""
    clear_registry()
    bootstrap_routing_registry_from_config(app_bootstrap_on)
    try:
        with app_bootstrap_on.app_context():
            slm_ad = StagedRecordingAdapter("gt306_slm", slm_sufficient=True)
            llm_ad = StagedRecordingAdapter("gt306_llm", slm_sufficient=True)
            register_adapter_model(_slm_spec("gt306_slm"), slm_ad)
            register_adapter_model(_llm_spec("gt306_llm"), llm_ad)
            meta = ModuleMetadata(
                module_id="m1",
                title="T",
                version="1",
                contract_version="1.0.0",
            )
            mod = ContentModule(metadata=meta, scenes={}, characters={})
            session = SessionState(
                session_id="gt306-rt",
                execution_mode="ai",
                adapter_name="gt306_slm",
                module_id="m1",
                module_version="1",
                current_scene_id="scene1",
            )
            session.canonical_state = {}
            await execute_turn_with_ai(session, 1, slm_ad, mod)
            log = (session.metadata.get("ai_decision_logs") or [])[-1]
            audit = log.operator_audit or {}
            fp = _first_pass_operator_view(audit)
            _assert_story_from_first_pass(fp, expected_surface="runtime")
            assert isinstance(audit.get("audit_timeline"), list) and audit["audit_timeline"]
            assert isinstance(log.runtime_stage_traces, list)
    finally:
        clear_registry()

    wr = client_bootstrap_on.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers_bootstrap_on,
        json={"module_id": "god_of_carnage", "focus": "G-T3-06"},
    )
    assert wr.status_code == 200
    aud = wr.get_json().get("operator_audit") or {}
    _assert_story_from_first_pass(_first_pass_operator_view(aud), expected_surface="writers_room")
    assert isinstance(aud.get("audit_timeline"), list) and aud["audit_timeline"]


def test_operator_comparison_docs_list_task3_gate_ids():
    """G-T3-07: listed architecture docs reference every G-T3 gate and the grammar version."""
    for name in G_T3_DOC_FILES:
        path = architecture_style_doc(name)
        assert path.is_file(), f"missing doc {name}"
        text = path.read_text(encoding="utf-8")
        for n in range(1, 9):
            assert f"G-T3-{n:02d}" in text, f"{name} missing G-T3-{n:02d}"
        assert "area2_operator_comparison_v1" in text, f"{name} must name the grammar version string"
        assert "compact_operator_comparison" in text, f"{name} must name compact_operator_comparison"


def test_operator_comparison_authority_semantics_safe():
    """G-T3-08: area2_operator_truth does not import or directly invoke route_model."""
    text = AREA2_OPERATOR_TRUTH_PY.read_text(encoding="utf-8")
    assert "from app.runtime.model_routing import" not in text
    assert "import model_routing" not in text
    assert "route_model(" not in text
    truth = build_area2_operator_truth(
        surface="runtime",
        authority_source=AUTHORITY_SOURCE_RUNTIME,
        bootstrap_enabled=True,
        registry_model_spec_count=1,
        specs_for_coverage=None,
        runtime_stage_traces=[],
        model_routing_trace=None,
        runtime_orchestration_summary={},
    )
    assert_operator_audit_truth_payload_shape(truth)
