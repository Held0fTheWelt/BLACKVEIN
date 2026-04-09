"""Minimal controlled generalization surface for dramatic-effect evaluation (Phase 6)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ai_stack.dramatic_effect_contract import (
    DramaticEffectEvaluationContext,
    DramaticEffectGateOutcome,
    DramaticEffectGateResult,
    DramaticEffectTraceItem,
    SemanticPlannerSupportLevel,
)
from ai_stack.dramatic_effect_gate import evaluate_dramatic_effect_gate
from ai_stack.goc_frozen_vocab import GOC_MODULE_ID


@runtime_checkable
class DramaticEffectEvaluator(Protocol):
    def evaluate(self, ctx: DramaticEffectEvaluationContext) -> DramaticEffectGateOutcome: ...


class _GoCDramaticEffectEvaluator:
    def evaluate(self, ctx: DramaticEffectEvaluationContext) -> DramaticEffectGateOutcome:
        return evaluate_dramatic_effect_gate(ctx)


class _NonGoCDramaticEffectEvaluator:
    def evaluate(self, ctx: DramaticEffectEvaluationContext) -> DramaticEffectGateOutcome:
        return DramaticEffectGateOutcome(
            gate_result=DramaticEffectGateResult.not_supported,
            effect_rationale_codes=["evaluator_module_not_goc"],
            diagnostic_trace=[
                DramaticEffectTraceItem(code="non_goc_evaluator", detail=ctx.module_id),
            ],
        )


def resolve_dramatic_effect_evaluator(module_id: str) -> DramaticEffectEvaluator:
    if module_id == GOC_MODULE_ID:
        return _GoCDramaticEffectEvaluator()
    return _NonGoCDramaticEffectEvaluator()


def support_level_for_module(module_id: str) -> SemanticPlannerSupportLevel:
    if module_id == GOC_MODULE_ID:
        return SemanticPlannerSupportLevel.full_goc
    return SemanticPlannerSupportLevel.non_goc_waived
