"""Dramatic effect contract schema and not_supported semantics."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from ai_stack.dramatic_effect_contract import (
    DramaticEffectEvaluationContext,
    DramaticEffectGateOutcome,
    DramaticEffectGateResult,
    DramaticEffectTraceItem,
    SemanticPlannerSupportLevel,
)
from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.semantic_planner_effect_surface import resolve_dramatic_effect_evaluator, support_level_for_module


def test_evaluation_context_forbids_extra_keys() -> None:
    with pytest.raises(ValidationError):
        DramaticEffectEvaluationContext(
            module_id=GOC_MODULE_ID,
            proposed_narrative="x",
            extra_field="nope",  # type: ignore[call-arg]
        )


def test_gate_outcome_roundtrip_json() -> None:
    o = DramaticEffectGateOutcome(
        gate_result=DramaticEffectGateResult.accepted,
        effect_rationale_codes=["primary_gate_pass"],
        diagnostic_trace=[DramaticEffectTraceItem(code="t", detail="d")],
    )
    raw = json.dumps(o.to_runtime_dict())
    back = json.loads(raw)
    assert back["gate_result"] == "accepted"


def test_non_goc_evaluator_only_not_supported() -> None:
    ev = resolve_dramatic_effect_evaluator("other_module")
    ctx = DramaticEffectEvaluationContext(module_id="other_module", proposed_narrative="anything")
    out = ev.evaluate(ctx)
    assert out.gate_result == DramaticEffectGateResult.not_supported
    assert support_level_for_module("other_module") == SemanticPlannerSupportLevel.non_goc_waived
    assert support_level_for_module(GOC_MODULE_ID) == SemanticPlannerSupportLevel.full_goc
