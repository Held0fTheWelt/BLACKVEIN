"""Task 2 — routing registry bootstrap, inventory helpers, and surface coverage."""

from app import create_app
from app.config import TestingConfig
from app.runtime.adapter_registry import (
    clear_registry,
    get_adapter,
    get_model_spec,
    iter_model_specs,
    register_adapter,
    register_adapter_model,
    snapshot_registry_keys,
)
from app.runtime.ai_adapter import AdapterResponse, MockStoryAIAdapter, StoryAIAdapter
from app.runtime.model_inventory_contract import InventorySurface
from app.runtime.model_inventory_report import (
    SetupClassification,
    classify_no_eligible_setup,
    classify_policy_degradation,
    inventory_summary_dict,
    report_registry_inventory,
    validate_surface_coverage,
)
from app.runtime.model_routing import route_model
from app.runtime.model_routing_contracts import (
    AdapterModelSpec,
    CostClass,
    LatencyClass,
    LLMOrSLM,
    ModelTier,
    RouteReasonCode,
    RoutingRequest,
    StructuredOutputReliability,
    TaskKind,
    WorkflowPhase,
)
from app.runtime.routing_registry_bootstrap import (
    bootstrap_routing_registry_from_config,
    build_default_mock_story_adapter_model_spec,
)
from app.runtime.runtime_ai_stages import (
    build_preflight_routing_request,
    build_signal_routing_request,
    build_synthesis_routing_request,
)
from app.runtime.runtime_models import SessionState, SessionStatus
from app.services.writers_room_model_routing import build_writers_room_model_route_specs


class _NamedStoryAdapter(StoryAIAdapter):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def adapter_name(self) -> str:
        return self._name

    def generate(self, request):
        return AdapterResponse(raw_output="ok")


def _minimal_session() -> SessionState:
    return SessionState(
        module_id="m",
        module_version="1",
        current_scene_id="s1",
        status=SessionStatus.ACTIVE,
    )


def test_build_default_mock_story_adapter_model_spec_covers_runtime_tuples():
    spec = build_default_mock_story_adapter_model_spec()
    assert spec.adapter_name == "mock"
    assert spec.structured_output_reliability == StructuredOutputReliability.high
    session = _minimal_session()
    pre = build_preflight_routing_request(session)
    sig = build_signal_routing_request(session, extra_hints=[])
    syn = build_synthesis_routing_request(session)
    for req in (pre, sig, syn):
        d = route_model(req, specs=[spec])
        assert d.route_reason_code != RouteReasonCode.no_eligible_adapter
        assert d.selected_adapter_name == "mock"


def test_bootstrap_registers_mock_adapter_and_spec():
    clear_registry()
    assert bootstrap_routing_registry_from_config(app=None) is True
    assert get_adapter("mock") is not None
    assert isinstance(get_adapter("mock"), MockStoryAIAdapter)
    assert get_model_spec("mock") is not None
    clear_registry()


def test_create_app_with_bootstrap_disabled_skips_registry_population():
    clear_registry()

    class NoBootstrapConfig(TestingConfig):
        ROUTING_REGISTRY_BOOTSTRAP = False

    app = create_app(NoBootstrapConfig)
    assert app.config["ROUTING_REGISTRY_BOOTSTRAP"] is False
    assert iter_model_specs() == []
    clear_registry()


def test_create_app_with_bootstrap_enabled_registers_mock():
    """Opt-in subclass turns bootstrap on; default TestingConfig keeps the registry clean."""

    class BootstrapOn(TestingConfig):
        ROUTING_REGISTRY_BOOTSTRAP = True

    clear_registry()
    create_app(BootstrapOn)
    assert get_model_spec("mock") is not None
    assert isinstance(get_adapter("mock"), MockStoryAIAdapter)
    clear_registry()


def test_runtime_staged_requests_routed_after_bootstrap():
    clear_registry()
    bootstrap_routing_registry_from_config(app=None)
    session = _minimal_session()
    specs = iter_model_specs()
    assert specs
    for req in (
        build_preflight_routing_request(session),
        build_signal_routing_request(session, extra_hints=[]),
        build_synthesis_routing_request(session),
    ):
        d = route_model(req)
        assert d.route_reason_code != RouteReasonCode.no_eligible_adapter
    clear_registry()


def test_validate_surface_coverage_runtime_writers_room_improvement():
    clear_registry()
    bootstrap_routing_registry_from_config(app=None)
    runtime_specs = list(iter_model_specs())
    assert validate_surface_coverage(runtime_specs, InventorySurface.runtime_staged).all_satisfied
    clear_registry()

    wr_specs = build_writers_room_model_route_specs()
    assert validate_surface_coverage(wr_specs, InventorySurface.writers_room).all_satisfied
    assert validate_surface_coverage(wr_specs, InventorySurface.improvement_bounded).all_satisfied


def test_openai_spec_includes_revision_synthesis_and_degrade_to_mock():
    specs = build_writers_room_model_route_specs()
    by_name = {s.adapter_name: s for s in specs}
    openai = by_name["openai"]
    assert TaskKind.revision_synthesis in openai.supported_task_kinds
    assert openai.degrade_targets == ["mock"]
    ollama = by_name["ollama"]
    assert ollama.degrade_targets == ["mock"]
    assert by_name["mock"].degrade_targets == []


def test_writers_room_openai_fallback_chain_lists_mock_for_synthesis():
    specs = build_writers_room_model_route_specs()
    req = RoutingRequest(
        workflow_phase=WorkflowPhase.generation,
        task_kind=TaskKind.narrative_formulation,
        requires_structured_output=True,
    )
    decision = route_model(req, specs=specs)
    assert decision.selected_adapter_name == "openai"
    assert "mock" in decision.fallback_chain


def test_classify_no_eligible_setup_empty_registry():
    clear_registry()
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.preflight,
            task_kind=TaskKind.cheap_preflight,
        )
    )
    assert d.route_reason_code == RouteReasonCode.no_eligible_adapter
    assert (
        classify_no_eligible_setup(registry_spec_count=0)
        == SetupClassification.missing_registration_or_specs
    )
    assert (
        classify_no_eligible_setup(registry_spec_count=3)
        == SetupClassification.true_no_eligible_adapter
    )


def test_classify_policy_degradation_flag():
    assert classify_policy_degradation(degradation_applied=True) == SetupClassification.intentional_degraded_route
    assert classify_policy_degradation(degradation_applied=False) is None


def test_report_registry_inventory_detects_legacy_without_spec():
    clear_registry()
    register_adapter("bare_only", _NamedStoryAdapter("bare_only"))
    inv = report_registry_inventory()
    assert "bare_only" in inv.legacy_names_without_spec
    bootstrap_routing_registry_from_config(app=None)
    inv2 = report_registry_inventory()
    names_with_spec = {e.adapter_name for e in inv2.entries if e.has_model_spec}
    assert "mock" in names_with_spec
    clear_registry()


def test_snapshot_registry_keys_sorted():
    clear_registry()
    register_adapter_model(
        AdapterModelSpec(
            adapter_name="zebra",
            provider_name="p",
            model_name="m",
            model_tier=ModelTier.light,
            llm_or_slm=LLMOrSLM.slm,
            cost_class=CostClass.low,
            latency_class=LatencyClass.low,
            supported_phases=frozenset(WorkflowPhase),
            supported_task_kinds=frozenset({TaskKind.cheap_preflight}),
            structured_output_reliability=StructuredOutputReliability.high,
        ),
        _NamedStoryAdapter("zebra"),
    )
    register_adapter("alpha", _NamedStoryAdapter("alpha"))
    leg, sp = snapshot_registry_keys()
    assert leg == ["alpha", "zebra"]
    assert sp == ["zebra"]
    clear_registry()


def test_inventory_summary_dict_shape():
    clear_registry()
    bootstrap_routing_registry_from_config(app=None)
    summary = inventory_summary_dict()
    assert "mock" in summary["adapter_names"]
    assert summary["model_spec_count"] >= 1
    clear_registry()


def test_stale_spec_risk_marked_for_legacy_only_registration():
    clear_registry()
    register_adapter("legacy_x", _NamedStoryAdapter("legacy_x"))
    inv = report_registry_inventory()
    entry = next(e for e in inv.entries if e.adapter_name == "legacy_x")
    assert entry.stale_spec_risk is True
    assert entry.has_model_spec is False
    clear_registry()
