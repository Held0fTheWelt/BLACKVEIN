"""
Planner-aware dramatic effect gate (GoC) — bounded deterministic
evaluation.
"""

from __future__ import annotations

from typing import Any

from ai_stack.dramatic_effect_contract import (
    DramaticEffectEvaluationContext,
    DramaticEffectGateOutcome,
    DramaticEffectGateResult,
)
from ai_stack.dramatic_effect_gate_evaluate_core import evaluate_dramatic_effect_gate


def build_evaluation_context_from_runtime_state(
    *,
    module_id: str,
    proposed_narrative: str,
    selected_scene_function: str,
    pacing_mode: str,
    silence_brevity_decision: dict[str, Any],
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
    character_mind_records: list[dict[str, Any]],
    scene_plan_record: dict[str, Any] | None,
    prior_continuity_impacts: list[dict[str, Any]] | None,
    selected_responder_set: list[dict[str, Any]] | None,
    actor_lane_summary: dict[str, Any] | None = None,
) -> DramaticEffectEvaluationContext:
    """Pick primary responder mind record aligned with
    selected_responder_set.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        module_id: ``module_id`` (str); meaning follows the type and call sites.
        proposed_narrative: ``proposed_narrative`` (str); meaning follows the type and call sites.
        selected_scene_function: ``selected_scene_function`` (str); meaning follows the type and call sites.
        pacing_mode: ``pacing_mode`` (str); meaning follows the type and call sites.
        silence_brevity_decision: ``silence_brevity_decision`` (dict[str, Any]); meaning follows the type and call sites.
        semantic_move_record: ``semantic_move_record`` (dict[str, Any] | None); meaning follows the type and call sites.
        social_state_record: ``social_state_record`` (dict[str, Any] | None); meaning follows the type and call sites.
        character_mind_records: ``character_mind_records`` (list[dict[str, Any]]); meaning follows the type and call sites.
        scene_plan_record: ``scene_plan_record`` (dict[str, Any] | None); meaning follows the type and call sites.
        prior_continuity_impacts: ``prior_continuity_impacts`` (list[dict[str, Any]] | None); meaning follows the type and call sites.
        selected_responder_set: ``selected_responder_set`` (list[dict[str, Any]] | None); meaning follows the type and call sites.
    
    Returns:
        DramaticEffectEvaluationContext:
            Returns a value of type ``DramaticEffectEvaluationContext``; see the function body for structure, error paths, and sentinels.
    """
    primary: dict[str, Any] | None = None
    actors = character_mind_records or []
    want = ""
    if selected_responder_set and isinstance(selected_responder_set[0], dict):
        want = str(selected_responder_set[0].get("actor_id") or "")
    if want and actors:
        for m in actors:
            if isinstance(m, dict) and str(m.get("runtime_actor_id") or "") == want:
                primary = m
                break
        if primary is None:
            primary = actors[0] if actors else None
    elif actors:
        primary = actors[0]

    return DramaticEffectEvaluationContext(
        module_id=module_id,
        proposed_narrative=proposed_narrative,
        selected_scene_function=selected_scene_function,
        pacing_mode=pacing_mode,
        silence_brevity_decision=dict(silence_brevity_decision or {}),
        semantic_move_record=semantic_move_record,
        social_state_record=social_state_record,
        primary_character_mind=primary,
        scene_plan_record=scene_plan_record,
        prior_continuity_impacts=list(prior_continuity_impacts or []),
        actor_lane_summary=actor_lane_summary,
    )


def validation_reason_for_outcome(out: DramaticEffectGateOutcome) -> str | None:
    """Machine reason for validation_outcome when status should be
    rejected.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        out: ``out`` (DramaticEffectGateOutcome); meaning follows the type and call sites.
    
    Returns:
        str | None:
            Returns a value of type ``str | None``; see the function body for structure, error paths, and sentinels.
    """
    gr = out.gate_result
    if gr == DramaticEffectGateResult.accepted or gr == DramaticEffectGateResult.accepted_with_weak_signal:
        return None
    if gr == DramaticEffectGateResult.rejected_empty_fluency:
        return "dramatic_effect_reject_empty_fluency"
    if gr == DramaticEffectGateResult.rejected_scene_function_mismatch:
        return "dramatic_effect_reject_scene_function_mismatch"
    if gr == DramaticEffectGateResult.rejected_character_implausibility:
        return "dramatic_effect_reject_character_implausibility"
    if gr == DramaticEffectGateResult.rejected_continuity_pressure:
        return "dramatic_effect_reject_continuity_pressure"
    return "dramatic_effect_reject_unknown"
