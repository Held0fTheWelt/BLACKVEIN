"""
Minimal controlled generalization surface for dramatic-effect evaluation
(Phase 6).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ai_stack.dramatic_effect.dramatic_effect_contract import (
    DramaticEffectEvaluationContext,
    DramaticEffectGateOutcome,
    DramaticEffectGateResult,
    DramaticEffectTraceItem,
    SemanticPlannerSupportLevel,
)
from ai_stack.dramatic_effect.dramatic_effect_gate import evaluate_dramatic_effect_gate
from ai_stack.goc_frozen_vocab import GOC_MODULE_ID


@runtime_checkable
class DramaticEffectEvaluator(Protocol):
    """``DramaticEffectEvaluator`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    def evaluate(self, ctx: DramaticEffectEvaluationContext) -> DramaticEffectGateOutcome:
        """``evaluate`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            ctx: ``ctx`` (DramaticEffectEvaluationContext); meaning follows the type and call sites.
        
        Returns:
            DramaticEffectGateOutcome:
                Returns a value of type ``DramaticEffectGateOutcome``; see the function body for structure, error paths, and sentinels.
        """
        ...


class _GoCDramaticEffectEvaluator:
    """``_GoCDramaticEffectEvaluator`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    def evaluate(self, ctx: DramaticEffectEvaluationContext) -> DramaticEffectGateOutcome:
        """``evaluate`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            ctx: ``ctx`` (DramaticEffectEvaluationContext); meaning follows the type and call sites.
        
        Returns:
            DramaticEffectGateOutcome:
                Returns a value of type ``DramaticEffectGateOutcome``; see the function body for structure, error paths, and sentinels.
        """
        return evaluate_dramatic_effect_gate(ctx)


class _NonGoCDramaticEffectEvaluator:
    """``_NonGoCDramaticEffectEvaluator`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    def evaluate(self, ctx: DramaticEffectEvaluationContext) -> DramaticEffectGateOutcome:
        """``evaluate`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            ctx: ``ctx`` (DramaticEffectEvaluationContext); meaning follows the type and call sites.
        
        Returns:
            DramaticEffectGateOutcome:
                Returns a value of type ``DramaticEffectGateOutcome``; see the function body for structure, error paths, and sentinels.
        """
        return DramaticEffectGateOutcome(
            gate_result=DramaticEffectGateResult.not_supported,
            effect_rationale_codes=["evaluator_module_not_goc"],
            diagnostic_trace=[
                DramaticEffectTraceItem(code="non_goc_evaluator", detail=ctx.module_id),
            ],
        )


def resolve_dramatic_effect_evaluator(module_id: str) -> DramaticEffectEvaluator:
    """Describe what ``resolve_dramatic_effect_evaluator`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        module_id: ``module_id`` (str); meaning follows the type and call sites.
    
    Returns:
        DramaticEffectEvaluator:
            Returns a value of type ``DramaticEffectEvaluator``; see the function body for structure, error paths, and sentinels.
    """
    if module_id == GOC_MODULE_ID:
        return _GoCDramaticEffectEvaluator()
    return _NonGoCDramaticEffectEvaluator()


def support_level_for_module(module_id: str) -> SemanticPlannerSupportLevel:
    """Describe what ``support_level_for_module`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        module_id: ``module_id`` (str); meaning follows the type and call sites.
    
    Returns:
        SemanticPlannerSupportLevel:
            Returns a value of type ``SemanticPlannerSupportLevel``; see the function body for structure, error paths, and sentinels.
    """
    if module_id == GOC_MODULE_ID:
        return SemanticPlannerSupportLevel.full_goc
    return SemanticPlannerSupportLevel.non_goc_waived
