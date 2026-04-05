"""Area 2 evolution closure — G-CONV-01 … G-CONV-08 explicit gate tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app import create_app
from app.config import TestingConfig
from app.content.module_models import ContentModule, ModuleMetadata
from app.runtime.adapter_registry import clear_registry, iter_model_specs, register_adapter_model
from app.runtime.ai_turn_executor import execute_turn_with_ai
from app.runtime.area2_operational_state import (
    Area2OperationalState,
    NoEligibleDiscipline,
    classify_area2_operational_state,
    classify_no_eligible_discipline,
    pytest_session_active,
)
from app.runtime.area2_routing_authority import (
    AREA2_AUTHORITY_REGISTRY,
    AuthorityLayer,
    CanonicalSurface,
    assert_langgraph_not_canonical_for_task2a,
    assert_routing_policy_entry_is_unique_authoritative_policy,
    authority_entries_for_surface,
)
from app.runtime.model_routing import route_model
from app.runtime.model_routing_contracts import RouteReasonCode, RoutingRequest, TaskKind, WorkflowPhase
from app.runtime.routing_registry_bootstrap import bootstrap_routing_registry_from_config
from app.runtime.runtime_models import SessionState, SessionStatus
from app.services.writers_room_model_routing import build_writers_room_model_route_specs

from .test_runtime_staged_orchestration import (  # noqa: PLC2701
    StagedRecordingAdapter,
    _llm_spec,
    _slm_spec,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ARCH_DOC_NAMES = (
    "llm_slm_role_stratification.md",
    "ai_story_contract.md",
    "area2_convergence_gates.md",
    "area2_evolution_closure_report.md",
)

AREA2_TRUTH_KEYS = frozenset(
    {
        "surface",
        "authority_source",
        "bootstrap_enabled",
        "registry_model_spec_count",
        "route_coverage_state",
        "canonical_surfaces_all_satisfied",
        "selected_vs_executed",
        "primary_operational_concern",
        "operational_state",
        "no_eligible_discipline",
        "stages_with_no_eligible_adapter",
    }
)


def test_g_conv_01_single_authority_gate():
    """G-CONV-01: one explicit Task 2A policy; LangGraph not canonical for HTTP paths."""
    assert_routing_policy_entry_is_unique_authoritative_policy()
    assert_langgraph_not_canonical_for_task2a()
    for surf in CanonicalSurface:
        entries = authority_entries_for_surface(surf)
        assert entries, f"no authority entries for {surf}"
        assert any(e.component_id == "task2a_route_model" for e in entries)
    ids = [e.component_id for e in AREA2_AUTHORITY_REGISTRY]
    assert len(ids) == len(set(ids)), "duplicate component_id in AREA2_AUTHORITY_REGISTRY"


def test_g_conv_02_healthy_bootstrap_gate_runtime_specs():
    """G-CONV-02: bootstrap populates specs; canonical runtime tuples route."""
    clear_registry()
    bootstrap_routing_registry_from_config(app=None)
    assert iter_model_specs()
    from app.runtime.runtime_ai_stages import (
        build_preflight_routing_request,
        build_signal_routing_request,
        build_synthesis_routing_request,
    )

    session = SessionState(
        module_id="m",
        module_version="1",
        current_scene_id="s1",
        status=SessionStatus.ACTIVE,
    )
    session.canonical_state = {}
    for req in (
        build_preflight_routing_request(session),
        build_signal_routing_request(session, extra_hints=[]),
        build_synthesis_routing_request(session),
    ):
        d = route_model(req)
        assert d.route_reason_code != RouteReasonCode.no_eligible_adapter, (
            "healthy bootstrap must yield eligible specs for staged runtime tuples"
        )
    clear_registry()


@pytest.mark.asyncio
async def test_g_conv_02_healthy_bootstrap_no_routine_no_eligible_on_execute_turn():
    """G-CONV-02: in-process runtime with registry specs does not routine-roll to no_eligible."""
    clear_registry()
    slm_ad = StagedRecordingAdapter("gconv_slm", slm_sufficient=True)
    llm_ad = StagedRecordingAdapter("gconv_llm", slm_sufficient=True)
    register_adapter_model(_slm_spec("gconv_slm"), slm_ad)
    register_adapter_model(_llm_spec("gconv_llm"), llm_ad)

    meta = ModuleMetadata(
        module_id="m1",
        title="T",
        version="1",
        contract_version="1.0.0",
    )
    mod = ContentModule(metadata=meta, scenes={}, characters={})
    session = SessionState(
        session_id="gconv-2",
        execution_mode="ai",
        adapter_name="gconv_slm",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}

    await execute_turn_with_ai(session, 1, slm_ad, mod)
    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    for tr in log.runtime_stage_traces or []:
        if tr.get("stage_kind") != "routed_model_stage":
            continue
        dec = tr.get("decision")
        if isinstance(dec, dict):
            assert dec.get("route_reason_code") != RouteReasonCode.no_eligible_adapter.value
    clear_registry()


def test_g_conv_03_state_classification_gate_matrix():
    """G-CONV-03: operational states are mutually exclusive and reachable."""
    assert pytest_session_active() is True
    assert (
        classify_area2_operational_state(
            bootstrap_enabled=False,
            registry_model_spec_count=0,
            canonical_surfaces_all_satisfied=None,
        )
        == Area2OperationalState.test_isolated
    )
    assert (
        classify_area2_operational_state(
            bootstrap_enabled=True,
            registry_model_spec_count=0,
            canonical_surfaces_all_satisfied=True,
        )
        == Area2OperationalState.misconfigured
    )
    assert (
        classify_area2_operational_state(
            bootstrap_enabled=True,
            registry_model_spec_count=2,
            canonical_surfaces_all_satisfied=False,
        )
        == Area2OperationalState.misconfigured
    )
    assert (
        classify_area2_operational_state(
            bootstrap_enabled=True,
            registry_model_spec_count=2,
            canonical_surfaces_all_satisfied=True,
        )
        == Area2OperationalState.healthy
    )

    with patch("app.runtime.area2_operational_state.pytest_session_active", return_value=False):
        assert (
            classify_area2_operational_state(
                bootstrap_enabled=False,
                registry_model_spec_count=1,
                canonical_surfaces_all_satisfied=True,
            )
            == Area2OperationalState.intentionally_degraded
        )


def test_g_conv_04_no_eligible_discipline_gate():
    """G-CONV-04: distinguish setup gap vs true no-eligible vs executor mismatch."""
    assert (
        classify_no_eligible_discipline(
            route_reason_code=RouteReasonCode.no_eligible_adapter.value,
            registry_spec_count=0,
            degradation_applied=False,
        )
        == NoEligibleDiscipline.test_isolated_empty_registry
    )
    with patch("app.runtime.area2_operational_state.pytest_session_active", return_value=False):
        assert (
            classify_no_eligible_discipline(
                route_reason_code=RouteReasonCode.no_eligible_adapter.value,
                registry_spec_count=0,
                degradation_applied=False,
            )
            == NoEligibleDiscipline.missing_registration_or_specs
        )
    assert (
        classify_no_eligible_discipline(
            route_reason_code=RouteReasonCode.no_eligible_adapter.value,
            registry_spec_count=3,
            degradation_applied=False,
        )
        == NoEligibleDiscipline.true_no_eligible_adapter
    )
    assert (
        classify_no_eligible_discipline(
            route_reason_code=RouteReasonCode.no_eligible_adapter.value,
            registry_spec_count=3,
            degradation_applied=True,
        )
        == NoEligibleDiscipline.intentional_degraded_route
    )
    d = classify_no_eligible_discipline(
        route_reason_code=str(RouteReasonCode.role_matrix_primary.value),
        registry_spec_count=1,
        degradation_applied=False,
        bounded_model_call=False,
        skip_reason="no_eligible_adapter_or_missing_provider_adapter",
        selected_adapter_name="openai",
    )
    assert d == NoEligibleDiscipline.bounded_executor_mismatch


def test_g_conv_06_legacy_compatibility_gate():
    """G-CONV-06: TestingConfig leaves registry empty when bootstrap off; factory unchanged."""
    clear_registry()

    class NoBootstrapConfig(TestingConfig):
        ROUTING_REGISTRY_BOOTSTRAP = False

    app = create_app(NoBootstrapConfig)
    with app.app_context():
        assert app.config["ROUTING_REGISTRY_BOOTSTRAP"] is False
        assert iter_model_specs() == []
    clear_registry()


def test_g_conv_07_documentation_truth_gate():
    """G-CONV-07: architecture docs reference every G-CONV id and authority module."""
    for name in ARCH_DOC_NAMES:
        text = (REPO_ROOT / "docs" / "architecture" / name).read_text(encoding="utf-8")
        for n in range(1, 9):
            assert f"G-CONV-{n:02d}" in text, f"{name} missing G-CONV-{n:02d}"
    strat = (REPO_ROOT / "docs" / "architecture" / "llm_slm_role_stratification.md").read_text(
        encoding="utf-8"
    )
    assert "area2_routing_authority" in strat


def test_g_conv_authority_layers_are_single_classified():
    """Each registry entry has exactly one AuthorityLayer value."""
    for e in AREA2_AUTHORITY_REGISTRY:
        assert isinstance(e.layer, AuthorityLayer)


def test_bounded_specs_cover_writers_room_and_improvement_surfaces():
    """Supports G-CONV-02 for bounded HTTP paths (shared spec builder)."""
    specs = build_writers_room_model_route_specs()
    assert specs
    from app.runtime.model_inventory_contract import InventorySurface
    from app.runtime.model_inventory_report import validate_surface_coverage

    assert validate_surface_coverage(specs, InventorySurface.writers_room).all_satisfied
    assert validate_surface_coverage(specs, InventorySurface.improvement_bounded).all_satisfied


def assert_area2_truth_shape(truth: dict) -> None:
    missing = AREA2_TRUTH_KEYS - set(truth.keys())
    assert not missing, f"area2_operator_truth missing: {missing}"
