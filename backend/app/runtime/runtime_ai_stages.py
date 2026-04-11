"""Task 1 — Multi-stage Runtime AI orchestration (SLM-first, conditional LLM synthesis).

Bounded stage contracts, deterministic packaging into the canonical structured story
shape, and inspectable per-stage routing evidence. Authority remains in ``execute_turn``;
this module only prepares ``AdapterResponse`` for ``process_adapter_response``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field, field_validator, model_validator

from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter, generate_with_timeout
from app.runtime.model_routing import route_model
from app.runtime.model_routing_contracts import (
    Complexity,
    EscalationHint,
    LatencyBudget,
    CostSensitivity,
    RoutingDecision,
    RoutingRequest,
    TaskKind,
    WorkflowPhase,
)
from app.runtime.model_routing_evidence import build_routing_evidence
from app.runtime.runtime_ai_stages_sections import (
    annotate_runtime_stage_request,
    finalize_slm_only_staged_generation,
    finalize_synthesis_staged_generation,
    run_preflight_signal_ranking_gate,
)
from app.runtime.runtime_models import DegradedMarker, SessionState
from app.runtime.runtime_stage_ids import RANKING_SLM_ONLY_SKIP_REASON, RuntimeStageId


class OrchestrationFinalPath(str, Enum):
    """High-level outcome of the staged pipeline (inspectable, deterministic)."""

    slm_then_llm = "slm_then_llm"
    slm_only = "slm_only"
    ranked_then_llm = "ranked_then_llm"
    ranked_slm_only = "ranked_slm_only"
    degraded_early_skip_then_synthesis = "degraded_early_skip_then_synthesis"
    degraded_parse_forced_synthesis = "degraded_parse_forced_synthesis"
    degraded_ranking_parse_forcing_synthesis = "degraded_ranking_parse_forcing_synthesis"
    degraded_ranking_no_eligible_fallback = "degraded_ranking_no_eligible_fallback"


class PreflightStageOutput(BaseModel):
    """Structured output expected in ``structured_payload`` for preflight stage calls."""

    runtime_stage: str = "preflight"
    ambiguity_score: float = Field(ge=0.0, le=1.0, default=0.0)
    trigger_signals: list[str] = Field(default_factory=list, max_length=32)
    repetition_risk: str = "low"
    classification_label: str = ""
    preflight_ok: bool = True

    @field_validator("trigger_signals")
    @classmethod
    def cap_triggers(cls, v: list[str]) -> list[str]:
        return list(v)[:32]


class SignalStageOutput(BaseModel):
    """Structured output for signal / consistency stage (escalation recommendation)."""

    runtime_stage: str = "signal_consistency"
    needs_llm_synthesis: bool = True
    skip_synthesis_reason: str | None = None
    narrative_summary: str = ""
    consistency_notes: str = ""
    consistency_flags: list[str] = Field(default_factory=list, max_length=16)

    @field_validator("consistency_flags")
    @classmethod
    def cap_flags(cls, v: list[str]) -> list[str]:
        return list(v)[:16]


class RankingStageOutput(BaseModel):
    """Bounded structured output for the ranking stage (interpretation narrowing, not story JSON)."""

    runtime_stage: str = "ranking"
    ranked_hypotheses: list[str] = Field(default_factory=list, max_length=8)
    preferred_hypothesis_index: int = Field(ge=0, le=7, default=0)
    recommend_skip_synthesis: bool = False
    skip_synthesis_after_ranking_reason: str | None = None
    synthesis_recommended: bool = True
    ambiguity_residual: float = Field(ge=0.0, le=1.0, default=0.0)
    ranking_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    ranking_notes: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("ranked_hypotheses", "ranking_notes")
    @classmethod
    def cap_str_lists(cls, v: list[str]) -> list[str]:
        return [str(x)[:400] for x in list(v)[:8]]

    @field_validator("skip_synthesis_after_ranking_reason")
    @classmethod
    def cap_skip_reason(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s[:500] if s else None

    @model_validator(mode="after")
    def skip_reason_when_recommend_skip(self) -> RankingStageOutput:
        if self.recommend_skip_synthesis and not (self.skip_synthesis_after_ranking_reason or "").strip():
            raise ValueError("skip_synthesis_after_ranking_reason required when recommend_skip_synthesis is true")
        return self


def _session_complexity(session: SessionState) -> Complexity:
    meta = session.metadata if isinstance(session.metadata, dict) else {}
    raw = meta.get("routing_complexity")
    if isinstance(raw, str):
        try:
            return Complexity(raw)
        except ValueError:
            pass
    return Complexity.medium


def _session_latency_cost(session: SessionState) -> tuple[LatencyBudget, CostSensitivity]:
    meta = session.metadata if isinstance(session.metadata, dict) else {}
    latency_budget = LatencyBudget.normal
    cost_sensitivity = CostSensitivity.medium
    lb = meta.get("routing_latency_budget")
    if isinstance(lb, str):
        try:
            latency_budget = LatencyBudget(lb)
        except ValueError:
            pass
    cs = meta.get("routing_cost_sensitivity")
    if isinstance(cs, str):
        try:
            cost_sensitivity = CostSensitivity(cs)
        except ValueError:
            pass
    return latency_budget, cost_sensitivity


def _session_base_escalation_hints(session: SessionState) -> list[EscalationHint]:
    hints: list[EscalationHint] = []
    markers = session.degraded_state.active_markers
    if DegradedMarker.FALLBACK_ACTIVE in markers or DegradedMarker.RETRY_EXHAUSTED in markers:
        hints.append(EscalationHint.continuity_risk)
    return hints


def build_preflight_routing_request(session: SessionState) -> RoutingRequest:
    """Stage routing: cheap SLM-oriented preflight."""
    latency_budget, cost_sensitivity = _session_latency_cost(session)
    return RoutingRequest(
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        complexity=_session_complexity(session),
        latency_budget=latency_budget,
        cost_sensitivity=cost_sensitivity,
        requires_structured_output=True,
        escalation_hints=list(_session_base_escalation_hints(session)),
    )


def build_ranking_routing_request(
    session: SessionState,
    *,
    extra_hints: list[EscalationHint],
) -> RoutingRequest:
    """Stage routing: interpretation ranking / hypothesis narrowing (SLM-first ``TaskKind.ranking``)."""

    latency_budget, cost_sensitivity = _session_latency_cost(session)
    merged = list(_session_base_escalation_hints(session))
    merged.extend(extra_hints)
    return RoutingRequest(
        workflow_phase=WorkflowPhase.interpretation,
        task_kind=TaskKind.ranking,
        complexity=_session_complexity(session),
        latency_budget=latency_budget,
        cost_sensitivity=cost_sensitivity,
        requires_structured_output=True,
        escalation_hints=merged,
    )


def build_signal_routing_request(
    session: SessionState,
    *,
    extra_hints: list[EscalationHint],
) -> RoutingRequest:
    """Stage routing: signal / repetition-consistency (SLM-first task kind)."""
    latency_budget, cost_sensitivity = _session_latency_cost(session)
    merged = list(_session_base_escalation_hints(session))
    merged.extend(extra_hints)
    return RoutingRequest(
        workflow_phase=WorkflowPhase.interpretation,
        task_kind=TaskKind.repetition_consistency_check,
        complexity=_session_complexity(session),
        latency_budget=latency_budget,
        cost_sensitivity=cost_sensitivity,
        requires_structured_output=True,
        escalation_hints=merged,
    )


def build_synthesis_routing_request(session: SessionState) -> RoutingRequest:
    """Stage routing: LLM-heavy narrative synthesis (same semantics as legacy runtime request)."""
    meta = session.metadata if isinstance(session.metadata, dict) else {}
    task_kind = TaskKind.narrative_formulation
    raw_tk = meta.get("routing_task_kind")
    if isinstance(raw_tk, str):
        try:
            task_kind = TaskKind(raw_tk)
        except ValueError:
            pass
    latency_budget, cost_sensitivity = _session_latency_cost(session)
    hints = list(_session_base_escalation_hints(session))
    return RoutingRequest(
        workflow_phase=WorkflowPhase.generation,
        task_kind=task_kind,
        complexity=_session_complexity(session),
        latency_budget=latency_budget,
        cost_sensitivity=cost_sensitivity,
        requires_structured_output=True,
        escalation_hints=hints,
    )


def escalation_hints_from_preflight(preflight: PreflightStageOutput | None) -> list[EscalationHint]:
    """Deterministic mapping from preflight output to routing hints (not model authority)."""
    if preflight is None:
        return []
    out: list[EscalationHint] = []
    if preflight.repetition_risk in ("high", "medium"):
        out.append(EscalationHint.continuity_risk)
    if preflight.ambiguity_score >= 0.55:
        out.append(EscalationHint.ambiguity_high)
    return out


def parse_preflight_payload(payload: dict[str, Any] | None) -> tuple[PreflightStageOutput | None, list[str]]:
    if not payload or not isinstance(payload, dict):
        return None, ["preflight: missing structured_payload"]
    try:
        return PreflightStageOutput.model_validate(payload), []
    except Exception as exc:
        return None, [f"preflight: validate failed: {exc}"]


def parse_signal_payload(payload: dict[str, Any] | None) -> tuple[SignalStageOutput | None, list[str]]:
    if not payload or not isinstance(payload, dict):
        return None, ["signal: missing structured_payload"]
    try:
        return SignalStageOutput.model_validate(payload), []
    except Exception as exc:
        return None, [f"signal: validate failed: {exc}"]


def parse_ranking_payload(payload: dict[str, Any] | None) -> tuple[RankingStageOutput | None, list[str]]:
    if not payload or not isinstance(payload, dict):
        return None, ["ranking: missing structured_payload"]
    try:
        return RankingStageOutput.model_validate(payload), []
    except Exception as exc:
        return None, [f"ranking: validate failed: {exc}"]


def compute_needs_llm_synthesis(
    *,
    signal: SignalStageOutput | None,
    signal_parse_ok: bool,
    preflight_parse_ok: bool,
) -> tuple[bool, str]:
    """Deterministic synthesis gate; parse failures force synthesis for safe degradation."""
    if not signal_parse_ok or signal is None:
        return True, "degraded_signal_parse_or_missing_forcing_synthesis"
    if not preflight_parse_ok:
        return True, "degraded_preflight_parse_forcing_synthesis"
    if signal.needs_llm_synthesis:
        return True, "signal_requested_synthesis"
    reason = (signal.skip_synthesis_reason or "slm_sufficient").strip() or "slm_sufficient"
    return False, reason


def compute_synthesis_gate_after_ranking(
    *,
    base_needs_llm: bool,
    base_reason: str,
    signal: SignalStageOutput | None,
    signal_parse_ok: bool,
    ranking_out: RankingStageOutput | None,
    ranking_parse_ok: bool,
    ranking_bounded_ran: bool,
    ranking_no_eligible_adapter: bool,
) -> tuple[bool, str, str]:
    """Merge signal base gate with ranking output; returns (needs_llm, gate_reason, ranking_effect).

    Degraded policy (binding):
    - Ranking parse failure after a bounded call forces synthesis.
    - Ranking no-eligible falls back to the base signal gate with an explicit degraded reason.
    - Pre-signal / preflight degradation reasons ignore ranking skip recommendations.
    """

    if not base_needs_llm:
        return False, base_reason, "suppressed_slm_only_path"

    if base_reason.startswith("degraded_signal") or base_reason.startswith("degraded_preflight"):
        return True, base_reason, "ignored_ranking_due_to_upstream_degrade"

    if ranking_no_eligible_adapter:
        return True, "degraded_ranking_no_eligible_adapter_fallback_to_signal_gate", "degraded_no_eligible_fallback"

    if ranking_bounded_ran and not ranking_parse_ok:
        return True, "degraded_ranking_parse_forcing_synthesis", "degraded_parse_forcing_synthesis"

    if ranking_bounded_ran and ranking_parse_ok and ranking_out is not None:
        skip_ok = (
            ranking_out.recommend_skip_synthesis
            and (ranking_out.skip_synthesis_after_ranking_reason or "").strip()
            and signal is not None
            and signal_parse_ok
        )
        if skip_ok:
            return False, "ranking_skip_synthesis", "ranked_skip_synthesis"
        return True, "ranked_preserves_synthesis", "ranked_preserves_synthesis"

    if ranking_bounded_ran:
        return True, base_reason, "ranking_inconclusive_fallback"

    return True, base_reason, "ranking_not_executed_fallback"


def build_slm_only_structured_payload(
    *,
    preflight: PreflightStageOutput | None,
    signal: SignalStageOutput,
    ranking: RankingStageOutput | None = None,
) -> dict[str, Any]:
    """Deterministic packaging: canonical story JSON for ``process_adapter_response`` (advisory only)."""
    scene = (signal.narrative_summary or "").strip() or "[staged-runtime/slm_only] Continuity packaged without LLM synthesis."
    trig = list(preflight.trigger_signals if preflight else [])[:32]
    rationale = (
        f"[staged-runtime/slm_only] {signal.skip_synthesis_reason or 'slm_sufficient'}; "
        f"consistency_notes={signal.consistency_notes[:500]}"
    )
    if ranking is not None:
        hyp = ranking.ranked_hypotheses[:3] if ranking.ranked_hypotheses else []
        rationale = (
            f"{rationale}; ranking_gate={ranking.skip_synthesis_after_ranking_reason or 'ranked'}; "
            f"hypotheses={hyp!s}"
        )[:8000]
    return {
        "scene_interpretation": scene[:8000],
        "detected_triggers": trig,
        "proposed_state_deltas": [],
        "rationale": rationale[:8000],
        "proposed_scene_id": None,
        "dialogue_impulses": [],
        "conflict_vector": None,
        "confidence": None,
    }


def resolve_staged_orchestration_final_path(
    *,
    needs_llm: bool,
    synth_gate_reason: str,
    preflight_skipped: bool,
    signal_skipped: bool,
    ranking_bounded_parse_ok: bool,
    ranking_bounded_ran: bool,
    base_reason: str,
) -> OrchestrationFinalPath:
    if not needs_llm:
        if synth_gate_reason == "ranking_skip_synthesis":
            return OrchestrationFinalPath.ranked_slm_only
        return OrchestrationFinalPath.slm_only
    # Preserve the legacy final-path label when both early routed stages had no eligible adapter.
    if preflight_skipped and signal_skipped:
        return OrchestrationFinalPath.degraded_early_skip_then_synthesis
    if synth_gate_reason == "degraded_ranking_parse_forcing_synthesis":
        return OrchestrationFinalPath.degraded_ranking_parse_forcing_synthesis
    if synth_gate_reason == "degraded_ranking_no_eligible_adapter_fallback_to_signal_gate":
        return OrchestrationFinalPath.degraded_ranking_no_eligible_fallback
    if base_reason.startswith("degraded_") and synth_gate_reason == base_reason:
        return OrchestrationFinalPath.degraded_parse_forced_synthesis
    if (
        ranking_bounded_ran
        and ranking_bounded_parse_ok
        and synth_gate_reason == "ranked_preserves_synthesis"
    ):
        return OrchestrationFinalPath.ranked_then_llm
    return OrchestrationFinalPath.slm_then_llm


def build_legacy_model_routing_rollup(
    *,
    synthesis_ran: bool,
    synthesis_request: RoutingRequest | None,
    synthesis_decision: RoutingDecision | None,
    synthesis_execution_adapter: StoryAIAdapter | None,
    synthesis_resolved_via_registry: bool | None,
    passed_adapter: StoryAIAdapter,
    signal_request: RoutingRequest,
    signal_decision: RoutingDecision,
    signal_execution_adapter: StoryAIAdapter,
    signal_resolved: bool,
    final_path: OrchestrationFinalPath,
    ranking_request: RoutingRequest | None = None,
    ranking_decision: RoutingDecision | None = None,
    ranking_execution_adapter: StoryAIAdapter | None = None,
    ranking_resolved_via_registry: bool | None = None,
    ranking_suppressed_slm_only: bool = False,
    ranked_skip_synthesis: bool = False,
    synthesis_gate_reason: str | None = None,
) -> dict[str, Any]:
    """Legacy-shaped trace for ``last_model_routing_trace`` / ``AIDecisionLog.model_routing_trace``."""

    ranking_context: dict[str, Any] = {
        "ranking_suppressed_slm_only": ranking_suppressed_slm_only,
        "ranked_skip_synthesis": ranked_skip_synthesis,
        "synthesis_gate_reason": synthesis_gate_reason,
    }
    if ranking_request is not None:
        ranking_context["ranking_request"] = ranking_request.model_dump(mode="json")
    if ranking_decision is not None:
        ranking_context["ranking_decision"] = ranking_decision.model_dump(mode="json")
    if ranking_execution_adapter is not None:
        ranking_context["ranking_executed_adapter_name"] = ranking_execution_adapter.adapter_name

    if synthesis_ran and synthesis_request and synthesis_decision and synthesis_execution_adapter:
        out = {
            "routing_invoked": True,
            "rollup_mode": "synthesis_stage",
            "final_path": final_path.value,
            "request": synthesis_request.model_dump(mode="json"),
            "decision": synthesis_decision.model_dump(mode="json"),
            "passed_adapter_name": passed_adapter.adapter_name,
            "executed_adapter_name": synthesis_execution_adapter.adapter_name,
            "selected_adapter_name": synthesis_decision.selected_adapter_name,
            "selected_model": synthesis_decision.selected_model,
            "resolved_via_get_adapter": bool(synthesis_resolved_via_registry),
            "fallback_to_passed_adapter": not bool(synthesis_resolved_via_registry),
            "escalation_applied": synthesis_decision.escalation_applied,
            "degradation_applied": synthesis_decision.degradation_applied,
            "routing_evidence": build_routing_evidence(
                routing_request=synthesis_request,
                routing_decision=synthesis_decision,
                executed_adapter_name=synthesis_execution_adapter.adapter_name,
                passed_adapter_name=passed_adapter.adapter_name,
                resolved_via_get_adapter=bool(synthesis_resolved_via_registry),
                fallback_to_passed_adapter=not bool(synthesis_resolved_via_registry),
                bounded_model_call=True,
                skip_reason=None,
            ),
            "ranking_context": ranking_context,
        }
        return out

    if ranked_skip_synthesis and ranking_request and ranking_decision and ranking_execution_adapter:
        rk_resolved = bool(ranking_resolved_via_registry)
        return {
            "routing_invoked": True,
            "rollup_mode": "slm_only_after_ranking_skip",
            "final_path": final_path.value,
            "synthesis_skipped": True,
            "request": ranking_request.model_dump(mode="json"),
            "decision": ranking_decision.model_dump(mode="json"),
            "passed_adapter_name": passed_adapter.adapter_name,
            "executed_adapter_name": ranking_execution_adapter.adapter_name if rk_resolved else passed_adapter.adapter_name,
            "selected_adapter_name": ranking_decision.selected_adapter_name,
            "selected_model": ranking_decision.selected_model,
            "resolved_via_get_adapter": rk_resolved,
            "fallback_to_passed_adapter": not rk_resolved,
            "escalation_applied": ranking_decision.escalation_applied,
            "degradation_applied": ranking_decision.degradation_applied,
            "routing_evidence": build_routing_evidence(
                routing_request=ranking_request,
                routing_decision=ranking_decision,
                executed_adapter_name=ranking_execution_adapter.adapter_name,
                passed_adapter_name=passed_adapter.adapter_name,
                resolved_via_get_adapter=rk_resolved,
                fallback_to_passed_adapter=not rk_resolved,
                bounded_model_call=True,
                skip_reason=None,
            ),
            "ranking_context": ranking_context,
        }

    base_rollup = {
        "routing_invoked": True,
        "rollup_mode": "slm_only_signal_stage",
        "final_path": final_path.value,
        "synthesis_skipped": True,
        "request": signal_request.model_dump(mode="json"),
        "decision": signal_decision.model_dump(mode="json"),
        "passed_adapter_name": passed_adapter.adapter_name,
        "executed_adapter_name": signal_execution_adapter.adapter_name if signal_resolved else passed_adapter.adapter_name,
        "selected_adapter_name": signal_decision.selected_adapter_name,
        "selected_model": signal_decision.selected_model,
        "resolved_via_get_adapter": signal_resolved,
        "fallback_to_passed_adapter": not signal_resolved,
        "escalation_applied": signal_decision.escalation_applied,
        "degradation_applied": signal_decision.degradation_applied,
        "routing_evidence": build_routing_evidence(
            routing_request=signal_request,
            routing_decision=signal_decision,
            executed_adapter_name=signal_execution_adapter.adapter_name,
            passed_adapter_name=passed_adapter.adapter_name,
            resolved_via_get_adapter=signal_resolved,
            fallback_to_passed_adapter=not signal_resolved,
            bounded_model_call=True,
            skip_reason=None,
        ),
        "ranking_context": ranking_context,
    }
    return base_rollup


@dataclass
class StagedGenerationResult:
    """Outcome of ``run_runtime_staged_generation`` for the AI turn executor."""

    response: AdapterResponse
    runtime_stage_traces: list[dict[str, Any]] = field(default_factory=list)
    runtime_orchestration_summary: dict[str, Any] = field(default_factory=dict)
    model_routing_trace: dict[str, Any] = field(default_factory=dict)
    operator_audit: dict[str, Any] = field(default_factory=dict)
    synthesis_skipped: bool = False
    final_path: OrchestrationFinalPath = OrchestrationFinalPath.slm_then_llm
    synthesis_attempt_count: int = 0
    final_execution_adapter: StoryAIAdapter | None = None


def run_runtime_staged_generation(
    *,
    session: SessionState,
    passed_adapter: StoryAIAdapter,
    adapter_generate_timeout_ms: int,
    build_adapter_request_fn: Callable[[int], AdapterRequest],
    enrich_request_fn: Callable[[AdapterRequest], None],
    mark_retry_context_fn: Callable[[], None] | None = None,
) -> StagedGenerationResult:
    """Execute preflight → signal → ranking → optional synthesis, or deterministic SLM-only packaging.

    Each routed stage uses a distinct ``RoutingRequest`` (meaningful phase/task_kind).
    """
    gate = run_preflight_signal_ranking_gate(
        session=session,
        passed_adapter=passed_adapter,
        adapter_generate_timeout_ms=adapter_generate_timeout_ms,
        build_adapter_request_fn=build_adapter_request_fn,
        enrich_request_fn=enrich_request_fn,
        route_model=route_model,
    )

    if gate.needs_llm:
        return finalize_synthesis_staged_generation(
            traces=gate.traces,
            packaging_notes=gate.packaging_notes,
            session=session,
            passed_adapter=passed_adapter,
            adapter_generate_timeout_ms=adapter_generate_timeout_ms,
            build_adapter_request_fn=build_adapter_request_fn,
            enrich_request_fn=enrich_request_fn,
            annotate_request_for_stage_fn=lambda base, request_role_structured_output: annotate_runtime_stage_request(
                base,
                RuntimeStageId.synthesis,
                request_role_structured_output=request_role_structured_output,
            ),
            mark_retry_context_fn=mark_retry_context_fn,
            route_model=route_model,
            signal_rr=gate.signal_rr,
            signal_dec=gate.signal_dec,
            signal_adapter=gate.signal_adapter,
            signal_resolved_via=gate.signal_resolved_via,
            ranking_rr=gate.ranking_rr,
            ranking_dec_for_rollup=gate.ranking_dec_for_rollup,
            ranking_exec_for_rollup=gate.ranking_exec_for_rollup,
            ranking_resolved_for_rollup=gate.ranking_resolved_for_rollup,
            ranking_suppressed_slm_only=gate.ranking_suppressed_slm_only,
            synth_gate_reason=gate.synth_gate_reason,
            final_path=gate.final_path,
            ranking_effect=gate.ranking_effect,
            ranking_bounded_ran=gate.ranking_bounded_ran,
            ranking_no_eligible=gate.ranking_no_eligible,
            base_needs_llm=gate.base_needs_llm,
        )

    return finalize_slm_only_staged_generation(
        traces=gate.traces,
        packaging_notes=gate.packaging_notes,
        preflight_out=gate.preflight_out,
        signal_out=gate.signal_out,
        ranking_out=gate.ranking_out,
        ranked_skip_synthesis=gate.ranked_skip_synthesis,
        synth_gate_reason=gate.synth_gate_reason,
        final_path=gate.final_path,
        passed_adapter=passed_adapter,
        signal_rr=gate.signal_rr,
        signal_dec=gate.signal_dec,
        signal_adapter=gate.signal_adapter,
        signal_resolved_via=gate.signal_resolved_via,
        ranking_rr=gate.ranking_rr,
        ranking_dec_for_rollup=gate.ranking_dec_for_rollup,
        ranking_exec_for_rollup=gate.ranking_exec_for_rollup,
        ranking_resolved_for_rollup=gate.ranking_resolved_for_rollup,
        ranking_suppressed_slm_only=gate.ranking_suppressed_slm_only,
        ranking_effect=gate.ranking_effect,
        ranking_bounded_ran=gate.ranking_bounded_ran,
        ranking_no_eligible=gate.ranking_no_eligible,
        base_needs_llm=gate.base_needs_llm,
    )
