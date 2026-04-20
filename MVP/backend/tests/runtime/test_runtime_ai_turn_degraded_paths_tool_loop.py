"""Task 4: Runtime E2E hardening — degraded paths, tool loop after staged synthesis, empty registry honesty."""

from __future__ import annotations

import asyncio
import json

import pytest

from app.content.module_models import ContentModule, ModuleMetadata
from app.runtime.adapter_registry import clear_registry, register_adapter_model
from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.ai_turn_executor import execute_turn_with_ai
from app.runtime.model_routing_contracts import (
    AdapterModelSpec,
    CostClass,
    LLMOrSLM,
    LatencyClass,
    ModelTier,
    StructuredOutputReliability,
    TaskKind,
    WorkflowPhase,
)
from app.runtime.runtime_models import SessionState

from .test_runtime_staged_orchestration import (  # noqa: PLC2701 — reuse Task 1 fixtures
    StagedRecordingAdapter,
    _llm_spec,
    _slm_spec,
)


def _synthesis_only_llm_spec(name: str) -> AdapterModelSpec:
    """Specs eligible only for synthesis (generation / narrative_formulation)."""

    return AdapterModelSpec(
        adapter_name=name,
        provider_name="p",
        model_name="llm",
        model_tier=ModelTier.premium,
        llm_or_slm=LLMOrSLM.llm,
        cost_class=CostClass.medium,
        latency_class=LatencyClass.medium,
        supported_phases=frozenset({WorkflowPhase.generation}),
        supported_task_kinds=frozenset({TaskKind.narrative_formulation}),
        structured_output_reliability=StructuredOutputReliability.high,
    )


def _slm_preflight_signal_only_spec(name: str) -> AdapterModelSpec:
    """Preflight + signal only; generation / narrative_formulation has no matching spec."""

    return AdapterModelSpec(
        adapter_name=name,
        provider_name="p",
        model_name="slm",
        model_tier=ModelTier.light,
        llm_or_slm=LLMOrSLM.slm,
        cost_class=CostClass.low,
        latency_class=LatencyClass.low,
        supported_phases=frozenset({WorkflowPhase.preflight, WorkflowPhase.interpretation}),
        supported_task_kinds=frozenset(
            {TaskKind.cheap_preflight, TaskKind.repetition_consistency_check, TaskKind.ranking}
        ),
        structured_output_reliability=StructuredOutputReliability.high,
    )


def _signal_and_synthesis_spec(name: str) -> AdapterModelSpec:
    """Eligible for signal + synthesis but not preflight (no preflight phase)."""

    return AdapterModelSpec(
        adapter_name=name,
        provider_name="p",
        model_name="hybrid",
        model_tier=ModelTier.standard,
        llm_or_slm=LLMOrSLM.llm,
        cost_class=CostClass.medium,
        latency_class=LatencyClass.medium,
        supported_phases=frozenset({WorkflowPhase.interpretation, WorkflowPhase.generation}),
        supported_task_kinds=frozenset(
            {TaskKind.repetition_consistency_check, TaskKind.ranking, TaskKind.narrative_formulation}
        ),
        structured_output_reliability=StructuredOutputReliability.high,
    )


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
async def test_degraded_early_skip_then_synthesis_when_preflight_and_signal_unroutable(
    minimal_module: ContentModule,
):
    """G-RUN-03: No eligible specs for preflight/signal; synthesis still routes (synthesis-only spec)."""

    clear_registry()
    syn_ad = StagedRecordingAdapter("syn_only", slm_sufficient=False)
    register_adapter_model(_synthesis_only_llm_spec("syn_only"), syn_ad)

    session = SessionState(
        session_id="s-degraded-early",
        execution_mode="ai",
        adapter_name="syn_only",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}

    await execute_turn_with_ai(session, 1, syn_ad, minimal_module)

    pre = [t for t in syn_ad.stages_seen if t == "preflight"]
    sig = [t for t in syn_ad.stages_seen if t == "signal_consistency"]
    assert not pre and not sig, "preflight and signal should not call adapter when unroutable"

    assert "synthesis" in syn_ad.stages_seen
    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    summary = log.runtime_orchestration_summary or {}
    assert summary.get("final_path") == "degraded_early_skip_then_synthesis"
    traces = log.runtime_stage_traces or []
    pre_t = next(t for t in traces if t.get("stage_id") == "preflight")
    sig_t = next(t for t in traces if t.get("stage_id") == "signal_consistency")
    assert pre_t.get("bounded_model_call") is False
    assert "no_eligible" in (pre_t.get("skip_reason") or "")
    assert sig_t.get("bounded_model_call") is False
    assert "no_eligible" in (sig_t.get("skip_reason") or "")
    assert log.operator_audit is not None
    assert log.operator_audit["audit_summary"].get("final_path") == "degraded_early_skip_then_synthesis"
    clear_registry()


class _InvalidSignalPreflightSignalAdapter(StoryAIAdapter):
    """SLM path: valid preflight; signal JSON fails SignalStageOutput validation."""

    def __init__(self) -> None:
        self.stages: list[str] = []

    @property
    def adapter_name(self) -> str:
        return "bad_signal_slm"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        stage = (request.metadata or {}).get("runtime_stage") or ""
        self.stages.append(stage)
        if stage == "preflight":
            payload = {
                "runtime_stage": "preflight",
                "ambiguity_score": 0.1,
                "trigger_signals": [],
                "repetition_risk": "low",
                "classification_label": "dialogue",
                "preflight_ok": True,
            }
        elif stage == "signal_consistency":
            payload = {
                "runtime_stage": "signal_consistency",
                "needs_llm_synthesis": "not_a_boolean",
                "narrative_summary": "x",
                "consistency_notes": "",
                "consistency_flags": [],
            }
        else:
            payload = {"error": "unexpected", "stage": stage}
        return AdapterResponse(raw_output=json.dumps(payload), structured_payload=payload, error=None)


class _SynthesisRecoverAdapter(StoryAIAdapter):
    """LLM path: synthesis stage only."""

    def __init__(self) -> None:
        self.stages: list[str] = []

    @property
    def adapter_name(self) -> str:
        return "bad_signal_llm"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        stage = (request.metadata or {}).get("runtime_stage") or ""
        self.stages.append(stage)
        payload = {
            "scene_interpretation": "Recovered via synthesis after bad signal parse",
            "detected_triggers": [],
            "proposed_state_deltas": [],
            "rationale": "degraded path",
            "proposed_scene_id": None,
        }
        return AdapterResponse(raw_output=json.dumps(payload), structured_payload=payload, error=None)


@pytest.mark.asyncio
async def test_degraded_parse_forced_synthesis_after_signal_validation_failure(
    minimal_module: ContentModule,
):
    """G-RUN-03: Signal parse fails → synthesis gate forces LLM path; final_path reflects degradation."""

    clear_registry()
    slm_ad = _InvalidSignalPreflightSignalAdapter()
    llm_ad = _SynthesisRecoverAdapter()
    register_adapter_model(_slm_spec("bad_signal_slm"), slm_ad)
    register_adapter_model(_llm_spec("bad_signal_llm"), llm_ad)

    session = SessionState(
        session_id="s-degraded-parse",
        execution_mode="ai",
        adapter_name="bad_signal_slm",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}

    await execute_turn_with_ai(session, 1, slm_ad, minimal_module)

    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    summary = log.runtime_orchestration_summary or {}
    assert summary.get("final_path") == "degraded_parse_forced_synthesis"
    assert summary.get("synthesis_gate_reason") == "degraded_signal_parse_or_missing_forcing_synthesis"
    assert summary.get("synthesis_skipped") is False
    assert "synthesis" in llm_ad.stages
    assert log.operator_audit is not None
    assert log.operator_audit["audit_summary"].get("final_path") == "degraded_parse_forced_synthesis"
    clear_registry()


@pytest.mark.asyncio
async def test_preflight_skipped_when_spec_lacks_preflight_phase_but_signal_runs(
    minimal_module: ContentModule,
):
    """G-NEG-01: Honest skip on preflight only; signal and later stages still behave."""

    clear_registry()

    class DualStageAdapter(StoryAIAdapter):
        def __init__(self) -> None:
            self.seen: list[str] = []

        @property
        def adapter_name(self) -> str:
            return "dual_sig_syn"

        def generate(self, request: AdapterRequest) -> AdapterResponse:
            stage = (request.metadata or {}).get("runtime_stage") or ""
            self.seen.append(stage)
            if stage == "signal_consistency":
                payload = {
                    "runtime_stage": "signal_consistency",
                    "needs_llm_synthesis": True,
                    "narrative_summary": "sig",
                    "consistency_notes": "",
                    "consistency_flags": [],
                }
            elif stage == "ranking":
                payload = {
                    "runtime_stage": "ranking",
                    "ranked_hypotheses": ["h1"],
                    "preferred_hypothesis_index": 0,
                    "recommend_skip_synthesis": False,
                    "skip_synthesis_after_ranking_reason": None,
                    "synthesis_recommended": True,
                    "ambiguity_residual": 0.2,
                    "ranking_confidence": 0.8,
                    "ranking_notes": [],
                }
            elif stage == "synthesis":
                payload = {
                    "scene_interpretation": "syn",
                    "detected_triggers": [],
                    "proposed_state_deltas": [],
                    "rationale": "r",
                    "proposed_scene_id": None,
                }
            else:
                payload = {"unexpected": stage}
            return AdapterResponse(raw_output=json.dumps(payload), structured_payload=payload, error=None)

    ad = DualStageAdapter()
    register_adapter_model(_signal_and_synthesis_spec("dual_sig_syn"), ad)

    session = SessionState(
        session_id="s-preflight-skip",
        execution_mode="ai",
        adapter_name="dual_sig_syn",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}

    await execute_turn_with_ai(session, 1, ad, minimal_module)

    assert "preflight" not in ad.seen
    assert "signal_consistency" in ad.seen
    assert "ranking" in ad.seen
    assert "synthesis" in ad.seen
    traces = ((session.metadata.get("ai_decision_logs") or [])[-1].runtime_stage_traces) or []
    pf = next(t for t in traces if t.get("stage_id") == "preflight")
    assert pf.get("bounded_model_call") is False
    clear_registry()


@pytest.mark.asyncio
async def test_synthesis_routing_no_eligible_spec_falls_back_to_passed_adapter(
    minimal_module: ContentModule,
):
    """G-NEG-01: No spec matches synthesis phase; bounded call uses passed adapter; routing_evidence stays honest."""

    clear_registry()
    ad = StagedRecordingAdapter("slm_ps_only", slm_sufficient=False)
    register_adapter_model(_slm_preflight_signal_only_spec("slm_ps_only"), ad)

    session = SessionState(
        session_id="s-synthesis-no-spec",
        execution_mode="ai",
        adapter_name="slm_ps_only",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}

    await execute_turn_with_ai(session, 1, ad, minimal_module)

    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    traces = log.runtime_stage_traces or []
    syn = next(t for t in traces if t.get("stage_id") == "synthesis")
    assert syn.get("bounded_model_call") is True
    assert syn.get("fallback_to_passed_adapter") is True
    assert syn.get("resolved_via_get_adapter") is False
    rev = syn.get("routing_evidence") or {}
    assert rev.get("no_eligible_spec_selection") is True
    assert log.model_routing_trace.get("fallback_to_passed_adapter") is True
    assert log.operator_audit is not None
    clear_registry()


FINAL_AFTER_TOOL = {
    "scene_interpretation": "Finalized after host tool execution post-staged synthesis.",
    "detected_triggers": [],
    "proposed_state_deltas": [],
    "rationale": "task4 tool loop ordering",
    "proposed_scene_id": None,
}


class _StagedToolSlmAdapter(StoryAIAdapter):
    """Preflight + signal stages for staged + tool loop test."""

    @property
    def adapter_name(self) -> str:
        return "staged_tool_slm"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        stage = (request.metadata or {}).get("runtime_stage") or ""
        if stage == "preflight":
            pl = {
                "runtime_stage": "preflight",
                "ambiguity_score": 0.2,
                "trigger_signals": [],
                "repetition_risk": "low",
                "classification_label": "dialogue",
                "preflight_ok": True,
            }
            return AdapterResponse(raw_output=json.dumps(pl), structured_payload=pl, error=None)
        if stage == "signal_consistency":
            pl = {
                "runtime_stage": "signal_consistency",
                "needs_llm_synthesis": True,
                "narrative_summary": "need synth",
                "consistency_notes": "",
                "consistency_flags": [],
            }
            return AdapterResponse(raw_output=json.dumps(pl), structured_payload=pl, error=None)
        if stage == "ranking":
            pl = {
                "runtime_stage": "ranking",
                "ranked_hypotheses": ["need_llm"],
                "preferred_hypothesis_index": 0,
                "recommend_skip_synthesis": False,
                "skip_synthesis_after_ranking_reason": None,
                "synthesis_recommended": True,
                "ambiguity_residual": 0.3,
                "ranking_confidence": 0.75,
                "ranking_notes": [],
            }
            return AdapterResponse(raw_output=json.dumps(pl), structured_payload=pl, error=None)
        pl = {"error": "slm_unexpected", "stage": stage}
        return AdapterResponse(raw_output=json.dumps(pl), structured_payload=pl, error=None)


class _StagedToolLlmAdapter(StoryAIAdapter):
    """Synthesis emits tool_request; non-staged follow-up generate returns final story JSON."""

    def __init__(self) -> None:
        self.post_synthesis_generates = 0

    @property
    def adapter_name(self) -> str:
        return "staged_tool_llm"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        stage = (request.metadata or {}).get("runtime_stage") or ""
        if stage == "synthesis":
            pl = {
                "type": "tool_request",
                "tool_name": "wos.read.current_scene",
                "arguments": {},
            }
            return AdapterResponse(raw_output="[tool-req]", structured_payload=pl, error=None)
        self.post_synthesis_generates += 1
        return AdapterResponse(
            raw_output=json.dumps(FINAL_AFTER_TOOL),
            structured_payload=FINAL_AFTER_TOOL,
            error=None,
        )


@pytest.mark.asyncio
async def test_staged_synthesis_tool_request_then_tool_loop_finalizes_via_follow_up_generate(
    minimal_module: ContentModule,
):
    """G-TOOL-01: Staged pipeline yields tool_request; host tool runs; follow-up generate finalizes."""

    clear_registry()
    slm_ad = _StagedToolSlmAdapter()
    llm_ad = _StagedToolLlmAdapter()
    register_adapter_model(_slm_spec("staged_tool_slm"), slm_ad)
    register_adapter_model(_llm_spec("staged_tool_llm"), llm_ad)

    session = SessionState(
        session_id="s-staged-tool",
        execution_mode="ai",
        adapter_name="staged_tool_slm",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}
    session.metadata["tool_loop"] = {
        "enabled": True,
        "allowed_tools": ["wos.read.current_scene"],
        "max_tool_calls_per_turn": 3,
    }

    result = await execute_turn_with_ai(session, 1, slm_ad, minimal_module)

    assert result.execution_status == "success"
    assert llm_ad.post_synthesis_generates >= 1
    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    assert log.tool_loop_summary is not None
    assert log.tool_loop_summary.get("finalized_after_tool_use") is True
    assert log.tool_loop_summary.get("stop_reason") == "finalized"
    assert len(log.tool_call_transcript or []) == 1
    assert log.runtime_stage_traces
    assert log.operator_audit is not None
    clear_registry()


@pytest.mark.asyncio
async def test_empty_registry_staged_forces_synthesis_on_passed_adapter_with_degraded_path(
    minimal_module: ContentModule,
):
    """G-NEG-01: No model specs; early stages skipped; synthesis uses passed adapter (honest degradation)."""

    clear_registry()
    ad = StagedRecordingAdapter("passed_only", slm_sufficient=False)
    session = SessionState(
        session_id="s-empty-reg",
        execution_mode="ai",
        adapter_name="passed_only",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
        metadata={},
        canonical_state={},
    )
    await execute_turn_with_ai(session, 1, ad, minimal_module)

    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    assert (log.runtime_orchestration_summary or {}).get("final_path") == "degraded_early_skip_then_synthesis"
    assert ad.stages_seen == ["synthesis"]
    assert log.operator_audit is not None
    clear_registry()
