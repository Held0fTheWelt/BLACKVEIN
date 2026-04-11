"""Task 1: multi-stage Runtime orchestration — integration tests (SLM-first, conditional synthesis)."""

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
from app.runtime.runtime_ai_stages import RANKING_SLM_ONLY_SKIP_REASON
from app.runtime.runtime_models import SessionState


ALL_PHASES = frozenset(WorkflowPhase)
STAGE_TASKS = frozenset(
    {
        TaskKind.cheap_preflight,
        TaskKind.repetition_consistency_check,
        TaskKind.ranking,
        TaskKind.narrative_formulation,
        TaskKind.classification,
    }
)


def _slm_spec(name: str) -> AdapterModelSpec:
    return AdapterModelSpec(
        adapter_name=name,
        provider_name="p",
        model_name="slm",
        model_tier=ModelTier.light,
        llm_or_slm=LLMOrSLM.slm,
        cost_class=CostClass.low,
        latency_class=LatencyClass.low,
        supported_phases=ALL_PHASES,
        supported_task_kinds=STAGE_TASKS,
        structured_output_reliability=StructuredOutputReliability.high,
    )


def _llm_spec(name: str) -> AdapterModelSpec:
    return AdapterModelSpec(
        adapter_name=name,
        provider_name="p",
        model_name="llm",
        model_tier=ModelTier.premium,
        llm_or_slm=LLMOrSLM.llm,
        cost_class=CostClass.medium,
        latency_class=LatencyClass.medium,
        supported_phases=ALL_PHASES,
        supported_task_kinds=STAGE_TASKS,
        structured_output_reliability=StructuredOutputReliability.high,
    )


class StagedRecordingAdapter(StoryAIAdapter):
    """Returns stage-shaped structured_payload based on ``request.metadata.runtime_stage``."""

    def __init__(
        self,
        name: str,
        *,
        slm_sufficient: bool = False,
        rank_recommend_skip: bool = False,
        rank_skip_reason: str = "test_ranked_single_clear_hypothesis",
    ):
        self._name = name
        self.calls = 0
        self.stages_seen: list[str] = []
        self._slm_sufficient = slm_sufficient
        self._rank_recommend_skip = rank_recommend_skip
        self._rank_skip_reason = rank_skip_reason

    @property
    def adapter_name(self) -> str:
        return self._name

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        self.calls += 1
        stage = (request.metadata or {}).get("runtime_stage") or ""
        self.stages_seen.append(stage)

        if stage == "preflight":
            payload = {
                "runtime_stage": "preflight",
                "ambiguity_score": 0.2,
                "trigger_signals": ["t_a"],
                "repetition_risk": "low",
                "classification_label": "dialogue",
                "preflight_ok": True,
            }
        elif stage == "signal_consistency":
            payload = {
                "runtime_stage": "signal_consistency",
                "needs_llm_synthesis": not self._slm_sufficient,
                "skip_synthesis_reason": "slm_sufficient" if self._slm_sufficient else None,
                "narrative_summary": "SLM packaged narrative summary for the scene.",
                "consistency_notes": "stable",
                "consistency_flags": [],
            }
        elif stage == "ranking":
            payload = {
                "runtime_stage": "ranking",
                "ranked_hypotheses": ["primary_read"],
                "preferred_hypothesis_index": 0,
                "recommend_skip_synthesis": self._rank_recommend_skip,
                "skip_synthesis_after_ranking_reason": (
                    self._rank_skip_reason if self._rank_recommend_skip else None
                ),
                "synthesis_recommended": not self._rank_recommend_skip,
                "ambiguity_residual": 0.1,
                "ranking_confidence": 0.85,
                "ranking_notes": [],
            }
        elif stage == "synthesis":
            payload = {
                "scene_interpretation": "Synthesis scene read",
                "detected_triggers": ["t_a"],
                "proposed_state_deltas": [],
                "rationale": "Synthesis rationale for test",
                "proposed_scene_id": None,
            }
        else:
            payload = {"error": "unknown_stage", "stage": stage}

        raw = json.dumps(payload)
        return AdapterResponse(raw_output=raw, structured_payload=payload, error=None)


@pytest.fixture
def minimal_module() -> ContentModule:
    meta = ModuleMetadata(
        module_id="m1",
        title="T",
        version="1",
        contract_version="1.0.0",
    )
    return ContentModule(metadata=meta, scenes={}, characters={})


class LegacySingleCallAdapter(StoryAIAdapter):
    """Single full story payload when ``runtime_stage`` is unset (legacy routing path)."""

    def __init__(self, name: str):
        self._name = name
        self.calls = 0

    @property
    def adapter_name(self) -> str:
        return self._name

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        self.calls += 1
        payload = {
            "scene_interpretation": "Legacy scene",
            "detected_triggers": [],
            "proposed_state_deltas": [],
            "rationale": "Legacy rationale for test",
            "proposed_scene_id": None,
        }
        return AdapterResponse(
            raw_output=json.dumps(payload),
            structured_payload=payload,
            error=None,
        )


@pytest.mark.asyncio
async def test_staged_pipeline_runs_preflight_signal_and_synthesis_when_escalated(
    minimal_module: ContentModule,
):
    clear_registry()
    slm_ad = StagedRecordingAdapter("staged_slm", slm_sufficient=False)
    llm_ad = StagedRecordingAdapter("staged_llm", slm_sufficient=False)
    register_adapter_model(_slm_spec("staged_slm"), slm_ad)
    register_adapter_model(_llm_spec("staged_llm"), llm_ad)

    session = SessionState(
        session_id="s-staged-1",
        execution_mode="ai",
        adapter_name="staged_slm",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}

    await execute_turn_with_ai(session, 1, slm_ad, minimal_module)

    assert slm_ad.calls == 3, "expected preflight + signal + ranking on SLM adapter"
    assert llm_ad.calls == 1, "expected one synthesis call on LLM adapter"
    assert slm_ad.stages_seen == ["preflight", "signal_consistency", "ranking"]
    assert llm_ad.stages_seen == ["synthesis"]

    logs = session.metadata.get("ai_decision_logs") or []
    assert logs
    log = logs[-1]
    assert log.runtime_stage_traces
    assert len(log.runtime_stage_traces) >= 5
    stages = [t.get("stage_id") for t in log.runtime_stage_traces]
    assert "preflight" in stages
    assert "signal_consistency" in stages
    assert "ranking" in stages
    assert "synthesis" in stages
    assert "packaging" in stages

    summary = log.runtime_orchestration_summary or {}
    assert summary.get("synthesis_skipped") is False
    assert summary.get("final_path") == "ranked_then_llm"

    trace = log.model_routing_trace or {}
    assert trace.get("rollup_mode") == "synthesis_stage"
    for st in log.runtime_stage_traces:
        if st.get("stage_id") in ("preflight", "signal_consistency", "ranking", "synthesis"):
            assert "routing_evidence" in st

    assert log.operator_audit is not None
    assert log.operator_audit.get("audit_schema_version")
    assert log.operator_audit.get("audit_timeline")
    packaging_entries = [e for e in log.operator_audit["audit_timeline"] if e.get("stage_key") == "packaging"]
    assert packaging_entries, "packaging stage must appear on audit timeline"
    assert packaging_entries[-1].get("stage_kind") == "packaging"
    orch = log.runtime_orchestration_summary or {}
    assert "packaging" in orch.get("stages_without_bounded_model_call_by_design", [])
    assert "packaging" not in orch.get("stages_skipped_no_eligible_adapter", [])
    assert log.operator_audit["audit_summary"].get("final_path") == "ranked_then_llm"


@pytest.mark.asyncio
async def test_staged_pipeline_skips_synthesis_when_slm_sufficient(minimal_module: ContentModule):
    clear_registry()
    ad = StagedRecordingAdapter("staged_slm_only", slm_sufficient=True)
    register_adapter_model(_slm_spec("staged_slm_only"), ad)

    session = SessionState(
        session_id="s-staged-2",
        execution_mode="ai",
        adapter_name="staged_slm_only",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}

    await execute_turn_with_ai(session, 1, ad, minimal_module)

    assert ad.calls == 2, "expected preflight + signal only (ranking suppressed, no bounded call)"
    assert "synthesis" not in ad.stages_seen
    assert "ranking" not in ad.stages_seen

    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    summary = log.runtime_orchestration_summary or {}
    assert summary.get("synthesis_skipped") is True
    assert summary.get("final_path") == "slm_only"
    assert summary.get("ranking_suppressed_for_slm_only") is True

    rk_trace = next(t for t in (log.runtime_stage_traces or []) if t.get("stage_id") == "ranking")
    assert rk_trace.get("bounded_model_call") is False
    assert rk_trace.get("skip_reason") == RANKING_SLM_ONLY_SKIP_REASON
    assert rk_trace.get("decision") is None
    assert rk_trace.get("request", {}).get("task_kind") == "ranking"

    trace = log.model_routing_trace or {}
    assert trace.get("rollup_mode") == "slm_only_signal_stage"
    assert trace.get("synthesis_skipped") is True

    assert log.operator_audit is not None
    assert log.operator_audit["audit_summary"].get("synthesis_gate_reason") == summary.get(
        "synthesis_gate_reason"
    )
    assert log.operator_audit["audit_summary"].get("synthesis_skipped") is True


@pytest.mark.asyncio
async def test_staged_orchestration_disabled_uses_legacy_single_routing(minimal_module: ContentModule):
    clear_registry()
    ad = LegacySingleCallAdapter("legacy_path")
    register_adapter_model(_llm_spec("legacy_path"), ad)

    session = SessionState(
        session_id="s-legacy",
        execution_mode="ai",
        adapter_name="legacy_path",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}
    session.metadata["runtime_staged_orchestration"] = False

    await execute_turn_with_ai(session, 1, ad, minimal_module)

    assert ad.calls == 1

    log = (session.metadata.get("ai_decision_logs") or [])[-1]
    assert log.runtime_stage_traces is None
    assert log.runtime_orchestration_summary is None
    assert log.operator_audit is not None
    assert log.operator_audit["audit_summary"].get("surface") == "runtime"
    tl = log.operator_audit.get("audit_timeline") or []
    assert any(e.get("stage_key") == "legacy_single_route" for e in tl)


@pytest.mark.asyncio
async def test_execute_turn_guard_semantics_unchanged_for_staged_slm_only(
    minimal_module: ContentModule,
):
    """Staged SLM-only path still flows through execute_turn; empty deltas should be acceptable."""
    clear_registry()
    ad = StagedRecordingAdapter("guard_check", slm_sufficient=True)
    register_adapter_model(_slm_spec("guard_check"), ad)

    session = SessionState(
        session_id="s-guard",
        execution_mode="ai",
        adapter_name="guard_check",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}

    result = await asyncio.wait_for(execute_turn_with_ai(session, 1, ad, minimal_module), timeout=30.0)
    assert result.execution_status == "success"
    assert result.guard_outcome is not None
