"""Runtime routing registry bootstrap, operational state classification, and operator-audit truth shape."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from .doc_test_paths import architecture_style_doc

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
    AUTHORITY_SOURCE_IMPROVEMENT,
    AUTHORITY_SOURCE_RUNTIME,
    AUTHORITY_SOURCE_WRITERS_ROOM,
    AuthorityLayer,
    CanonicalSurface,
    assert_langgraph_not_canonical_for_task2a,
    assert_routing_policy_entry_is_unique_authoritative_policy,
    authority_entries_for_surface,
)
from app.runtime.model_routing import route_model
from app.runtime.model_routing_contracts import RouteReasonCode, RoutingRequest, TaskKind, WorkflowPhase
from app.runtime.area2_operator_truth import (
    AREA2_OPERATOR_COMPARISON_GRAMMAR_VERSION,
    COMPACT_OPERATOR_COMPARISON_KEYS,
    NO_ELIGIBLE_OPERATOR_MEANING_KEYS,
    POLICY_EXECUTION_COMPARISON_KEYS,
    build_area2_operator_truth,
)
from app.runtime.operator_audit import RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS
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

AREA2_LEGIBILITY_KEYS = frozenset(
    {
        "authority_source",
        "operational_state",
        "route_status",
        "selected_vs_executed",
        "primary_operational_concern",
        "startup_profile",
        "runtime_ranking_summary",
    }
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
        "canonical_authority_summary",
        "legibility",
        "compact_operator_comparison",
    }
)


def test_routing_registry_single_authority_policy():
    """G-CONV-01: one explicit Task 2A policy; LangGraph not canonical for HTTP paths."""
    assert_routing_policy_entry_is_unique_authoritative_policy()
    assert_langgraph_not_canonical_for_task2a()
    for surf in CanonicalSurface:
        entries = authority_entries_for_surface(surf)
        assert entries, f"no authority entries for {surf}"
        assert any(e.component_id == "task2a_route_model" for e in entries)
    ids = [e.component_id for e in AREA2_AUTHORITY_REGISTRY]
    assert len(ids) == len(set(ids)), "duplicate component_id in AREA2_AUTHORITY_REGISTRY"


def test_bootstrap_registry_populates_adapter_specs_for_staged_tuples():
    """G-CONV-02: bootstrap populates specs; canonical runtime tuples route."""
    clear_registry()
    bootstrap_routing_registry_from_config(app=None)
    assert iter_model_specs()
    from app.runtime.runtime_ai_stages import (
        build_preflight_routing_request,
        build_ranking_routing_request,
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
        build_ranking_routing_request(session, extra_hints=[]),
        build_synthesis_routing_request(session),
    ):
        d = route_model(req)
        assert d.route_reason_code != RouteReasonCode.no_eligible_adapter, (
            "healthy bootstrap must yield eligible specs for staged runtime tuples"
        )
    clear_registry()


@pytest.mark.asyncio
async def test_execute_turn_with_specs_avoids_routine_no_eligible_adapter():
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
    audit = log.operator_audit or {}
    aus = audit.get("audit_summary") or {}
    for rk in RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS:
        assert rk in aus, f"audit_summary must mirror staged ranking truth ({rk})"
    truth = audit.get("area2_operator_truth") or {}
    rr = (truth.get("legibility") or {}).get("runtime_ranking_summary")
    assert isinstance(rr, dict), "canonical staged runtime must expose runtime_ranking_summary dict"
    for rk in RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS:
        assert rk in rr, f"runtime_ranking_summary must include {rk}"
    for tr in log.runtime_stage_traces or []:
        if tr.get("stage_kind") != "routed_model_stage":
            continue
        dec = tr.get("decision")
        if isinstance(dec, dict):
            assert dec.get("route_reason_code") != RouteReasonCode.no_eligible_adapter.value
    clear_registry()


def test_classify_operational_state_matrix():
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


def test_classify_no_eligible_discipline_matrix():
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


def test_bootstrap_off_keeps_registry_empty_in_testing_config():
    """G-CONV-06: TestingConfig leaves registry empty when bootstrap off; factory unchanged."""
    clear_registry()

    class NoBootstrapConfig(TestingConfig):
        ROUTING_REGISTRY_BOOTSTRAP = False

    app = create_app(NoBootstrapConfig)
    with app.app_context():
        assert app.config["ROUTING_REGISTRY_BOOTSTRAP"] is False
        assert iter_model_specs() == []
    clear_registry()


def test_docs_list_routing_evolution_gate_identifiers():
    """Archived architecture docs still enumerate G-CONV acceptance ids and name routing authority."""
    for name in ARCH_DOC_NAMES:
        path = architecture_style_doc(name)
        text = path.read_text(encoding="utf-8")
        for n in range(1, 9):
            assert f"G-CONV-{n:02d}" in text, f"{path.name} missing G-CONV-{n:02d}"
    strat = architecture_style_doc("llm_slm_role_stratification.md").read_text(encoding="utf-8")
    assert "area2_routing_authority" in strat


def test_each_routing_authority_entry_has_exactly_one_layer():
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


def assert_operator_audit_truth_payload_shape(truth: dict) -> None:
    missing = AREA2_TRUTH_KEYS - set(truth.keys())
    assert not missing, f"area2_operator_truth missing: {missing}"
    assert isinstance(truth.get("canonical_authority_summary"), str)
    leg = truth.get("legibility")
    assert isinstance(leg, dict), "area2_operator_truth.legibility must be a dict"
    miss_leg = AREA2_LEGIBILITY_KEYS - set(leg.keys())
    assert not miss_leg, f"area2_operator_truth.legibility missing: {miss_leg}"
    rr = leg.get("runtime_ranking_summary")
    assert rr is None or isinstance(rr, dict), "runtime_ranking_summary must be None or a dict"
    coc = truth.get("compact_operator_comparison")
    assert isinstance(coc, dict), "compact_operator_comparison must be a dict"
    miss_coc = COMPACT_OPERATOR_COMPARISON_KEYS - set(coc.keys())
    assert not miss_coc, f"compact_operator_comparison missing: {miss_coc}"
    assert coc.get("grammar_version") == AREA2_OPERATOR_COMPARISON_GRAMMAR_VERSION
    nem = coc.get("no_eligible_operator_meaning")
    assert isinstance(nem, dict)
    assert not NO_ELIGIBLE_OPERATOR_MEANING_KEYS - set(nem.keys())
    pec = coc.get("policy_execution_comparison")
    assert isinstance(pec, dict)
    assert not POLICY_EXECUTION_COMPARISON_KEYS - set(pec.keys())
    svs = coc.get("selected_vs_executed")
    assert isinstance(svs, dict)
    assert "per_stage" in svs and "legacy_roll_up" in svs
    rps = coc.get("runtime_path_summary")
    assert isinstance(rps, dict)
    for k in RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS:
        assert k in rps


# --- Practical convergence acceptance block (historical G-A ids); defers to startup-profile suite for HTTP proofs ---
# Lazy-import startup suite inside tests to avoid import cycles with this module.


def _assert_primary_authority_sources_per_surface() -> None:
    """Each canonical surface lists registry entries; spec source strings are non-empty."""
    for surf in CanonicalSurface:
        assert authority_entries_for_surface(surf), f"no authority entries for {surf.value}"
    assert AUTHORITY_SOURCE_RUNTIME.strip()
    assert AUTHORITY_SOURCE_WRITERS_ROOM.strip()
    assert AUTHORITY_SOURCE_IMPROVEMENT == AUTHORITY_SOURCE_WRITERS_ROOM


def test_routing_primary_authority_coherence_across_surfaces() -> None:
    """G-A-01: one primary Task 2A policy; registry entries per surface; spec authority strings."""
    from . import test_runtime_startup_profiles_operator_truth as _final

    test_routing_registry_single_authority_policy()
    _final.test_operator_truth_practical_authority_registry()
    _assert_primary_authority_sources_per_surface()


def test_auxiliary_authority_layers_are_explicitly_bounded() -> None:
    """G-A-02: auxiliary layers explicit, bounded, and non-competing with route_model."""
    assert_routing_policy_entry_is_unique_authoritative_policy()
    authoritative_policy_ids = {
        e.component_id for e in AREA2_AUTHORITY_REGISTRY if e.layer == AuthorityLayer.authoritative
    }
    assert authoritative_policy_ids == {
        "task2a_route_model",
        "task2a_adapter_registry",
        "task2a_contracts",
    }, "authoritative registry must contain only route_model, adapter_registry, and contracts"
    for e in AREA2_AUTHORITY_REGISTRY:
        assert e.module_path.strip(), f"{e.component_id} missing module_path"
        assert e.description.strip(), f"{e.component_id} missing description"
        if e.layer == AuthorityLayer.compatibility_layer:
            assert e.canonical_for_task2a_paths == frozenset(), (
                f"{e.component_id}: compatibility layer must not claim canonical Task 2A surfaces"
            )
        if e.layer == AuthorityLayer.translation_layer:
            assert e.canonical_for_task2a_paths, (
                f"{e.component_id}: translation layer must declare bounded canonical surfaces"
            )


def test_operator_truth_summary_names_langgraph_compatibility_posture() -> None:
    """G-A-03: no practical split-brain — LangGraph not canonical; summary states compatibility-only."""
    assert_langgraph_not_canonical_for_task2a()
    specs = build_writers_room_model_route_specs()
    truth = build_area2_operator_truth(
        surface="writers_room",
        authority_source="build_writers_room_model_route_specs",
        bootstrap_enabled=True,
        registry_model_spec_count=len(specs),
        specs_for_coverage=list(specs),
        bounded_traces=[],
    )
    summary = truth.get("canonical_authority_summary") or ""
    assert "LangGraph" in summary or "compatibility" in summary, (
        "canonical_authority_summary must name LangGraph / compatibility-only posture explicitly"
    )


@pytest.mark.asyncio
async def test_healthy_staged_runtime_paths_under_bootstrap_on() -> None:
    """G-A-04: Runtime, Writers-Room, and Improvement healthy paths under testing_bootstrap_on."""
    from . import test_runtime_startup_profiles_operator_truth as _final

    test_bootstrap_registry_populates_adapter_specs_for_staged_tuples()
    await test_execute_turn_with_specs_avoids_routine_no_eligible_adapter()
    await _final.test_runtime_healthy_staged_paths_when_bootstrap_on()


def test_bounded_http_writers_room_and_improvement_coherent_when_bootstrap_on(
    client_bootstrap_on,
    auth_headers_bootstrap_on,
) -> None:
    """G-A-04 (HTTP): Writers-Room and Improvement bounded paths coherent when bootstrap on."""
    from . import test_runtime_startup_profiles_operator_truth as _final

    test_bounded_specs_cover_writers_room_and_improvement_surfaces()
    _final.test_writers_room_healthy_routes_when_bootstrap_on(
        client_bootstrap_on, auth_headers_bootstrap_on
    )
    _final.test_improvement_healthy_routes_when_bootstrap_on(
        client_bootstrap_on, auth_headers_bootstrap_on
    )


def test_no_eligible_states_not_collapsed_into_healthy() -> None:
    """G-A-05: no_eligible discipline; not normalized as healthy canonical success."""
    from . import test_runtime_startup_profiles_operator_truth as _final

    test_classify_no_eligible_discipline_matrix()
    _final.test_no_eligible_operator_meaning_not_normalized_away()


def test_operator_legibility_visible_on_runtime_and_bounded_http(client, auth_headers) -> None:
    """G-A-06: legibility + bounded HTTP operator truth readable (derived facts only)."""
    from . import test_runtime_startup_profiles_operator_truth as _final
    from . import test_cross_surface_operator_audit_contract as _xs

    _final.test_operator_truth_legibility_keys_present()
    _xs.test_writers_room_operator_audit_and_routing_evidence_contract(client, auth_headers)


def test_docs_reference_practical_convergence_acceptance_criteria() -> None:
    """G-A-07: architecture docs list every G-A id and reference area2_routing_authority."""
    doc_names = (
        "area2_workstream_a_gates.md",
        "area2_practical_convergence_closure_report.md",
        "area2_dual_workstream_closure_report.md",
        "llm_slm_role_stratification.md",
        "ai_story_contract.md",
    )
    for name in doc_names:
        path = architecture_style_doc(name)
        assert path.is_file(), f"missing architecture doc {name}"
        text = path.read_text(encoding="utf-8")
        for n in range(1, 8):
            assert f"G-A-{n:02d}" in text, f"{name} missing G-A-{n:02d}"
        assert "area2_routing_authority" in text, f"{name} must reference area2_routing_authority"
