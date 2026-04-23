"""Branch outcomes for dramatic effect gate evaluation (DS-008)."""

from __future__ import annotations

from ai_stack.dramatic_effect_contract import (
    CharacterPlausibilityPosture,
    ContinuitySupportPosture,
    DramaticEffectEvaluationContext,
    DramaticEffectGateOutcome,
    DramaticEffectGateResult,
    DramaticEffectTraceItem,
    EmptyFluencyRisk,
)
from ai_stack.dramatic_effect_gate_evaluate_tags import scene_function_tags_satisfied, tag_active
from ai_stack.goc_dramatic_alignment import _GENERIC_BOILERPLATE_PHRASES, dramatic_alignment_legacy_fallback_only
from ai_stack.goc_frozen_vocab import GOC_MODULE_ID


def outcome_not_goc(ctx: DramaticEffectEvaluationContext) -> DramaticEffectGateOutcome | None:
    """``outcome_not_goc`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        ctx: ``ctx`` (DramaticEffectEvaluationContext); meaning follows the type and call sites.
    
    Returns:
        DramaticEffectGateOutcome | None:
            Returns a value of type ``DramaticEffectGateOutcome | None``; see the function body for structure, error paths, and sentinels.
    """
    if ctx.module_id != GOC_MODULE_ID:
        return DramaticEffectGateOutcome(
            gate_result=DramaticEffectGateResult.not_supported,
            effect_rationale_codes=["evaluator_module_not_goc"],
            diagnostic_trace=[
                DramaticEffectTraceItem(code="module_unsupported", detail=ctx.module_id),
            ],
        )
    return None


def outcome_from_legacy(reason: str) -> DramaticEffectGateOutcome:
    """Legacy structural/meta failures map to empty-fluency style hard
    reject for gate_result.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        reason: ``reason`` (str); meaning follows the type and call sites.
    
    Returns:
        DramaticEffectGateOutcome:
            Returns a value of type ``DramaticEffectGateOutcome``; see the function body for structure, error paths, and sentinels.
    """
    return DramaticEffectGateOutcome(
        gate_result=DramaticEffectGateResult.rejected_empty_fluency,
        rejection_reasons=[reason],
        supports_scene_function=False,
        continues_or_changes_pressure=False,
        character_plausibility_posture=CharacterPlausibilityPosture.uncertain,
        continuity_support_posture=ContinuitySupportPosture.none,
        empty_fluency_risk=EmptyFluencyRisk.elevated,
        effect_rationale_codes=["legacy_structural_or_meta", reason],
        legacy_fallback_used=True,
        diagnostic_trace=[
            DramaticEffectTraceItem(code="legacy_fallback", detail=reason),
        ],
    )


def try_legacy_alignment(ctx: DramaticEffectEvaluationContext) -> DramaticEffectGateOutcome | None:
    """``try_legacy_alignment`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        ctx: ``ctx`` (DramaticEffectEvaluationContext); meaning follows the type and call sites.
    
    Returns:
        DramaticEffectGateOutcome | None:
            Returns a value of type ``DramaticEffectGateOutcome | None``; see the function body for structure, error paths, and sentinels.
    """
    legacy_reason = dramatic_alignment_legacy_fallback_only(
        selected_scene_function=ctx.selected_scene_function,
        pacing_mode=ctx.pacing_mode,
        silence_brevity_decision=ctx.silence_brevity_decision or None,
        proposed_narrative=ctx.proposed_narrative,
    )
    if legacy_reason:
        return outcome_from_legacy(legacy_reason)
    return None


def try_off_scope_containment_mismatch(
    ctx: DramaticEffectEvaluationContext, *, sf: str
) -> DramaticEffectGateOutcome | None:
    """Describe what ``try_off_scope_containment_mismatch`` does in one
    line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        ctx: ``ctx`` (DramaticEffectEvaluationContext); meaning follows the type and call sites.
        sf: ``sf`` (str); meaning follows the type and call sites.
    
    Returns:
        DramaticEffectGateOutcome | None:
            Returns a value of type ``DramaticEffectGateOutcome | None``; see the function body for structure, error paths, and sentinels.
    """
    sem = ctx.validated_semantic_move()
    if sem is not None and sem.move_type == "off_scope_containment" and sf not in ("scene_pivot", "establish_pressure"):
        return DramaticEffectGateOutcome(
            gate_result=DramaticEffectGateResult.rejected_scene_function_mismatch,
            rejection_reasons=["dramatic_effect_reject_scene_function_mismatch"],
            supports_scene_function=False,
            empty_fluency_risk=EmptyFluencyRisk.moderate,
            effect_rationale_codes=["move_type_off_scope_vs_scene_function", f"scene_function:{sf}"],
            legacy_fallback_used=False,
            diagnostic_trace=[DramaticEffectTraceItem(code="move_type_mismatch", detail=sem.move_type)],
        )
    return None


def try_prior_blame_continuity_pressure(
    ctx: DramaticEffectEvaluationContext, *, low: str, sf: str
) -> DramaticEffectGateOutcome | None:
    """Describe what ``try_prior_blame_continuity_pressure`` does in one
    line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        ctx: ``ctx`` (DramaticEffectEvaluationContext); meaning follows the type and call sites.
        low: ``low`` (str); meaning follows the type and call sites.
        sf: ``sf`` (str); meaning follows the type and call sites.
    
    Returns:
        DramaticEffectGateOutcome | None:
            Returns a value of type ``DramaticEffectGateOutcome | None``; see the function body for structure, error paths, and sentinels.
    """
    prior_classes = [
        str(x.get("class") or "")
        for x in (ctx.prior_continuity_impacts or [])
        if isinstance(x, dict)
    ]
    if "blame_pressure" in prior_classes and sf in ("redirect_blame", "escalate_conflict", "reveal_surface"):
        if not (
            tag_active(low, "interpersonal_blame")
            or tag_active(low, "pressure_intensification")
            or tag_active(low, "alliance_network")
            or tag_active(low, "exposure_secret")
        ):
            return DramaticEffectGateOutcome(
                gate_result=DramaticEffectGateResult.rejected_continuity_pressure,
                rejection_reasons=["dramatic_effect_reject_continuity_pressure"],
                supports_scene_function=False,
                continuity_support_posture=ContinuitySupportPosture.weak,
                empty_fluency_risk=EmptyFluencyRisk.moderate,
                effect_rationale_codes=["prior_blame_pressure_unaddressed"],
                legacy_fallback_used=False,
                diagnostic_trace=[
                    DramaticEffectTraceItem(code="continuity_blame_carry", detail="prior_blame_pressure"),
                ],
            )
    return None


def try_repair_scene_character_conflict(
    ctx: DramaticEffectEvaluationContext, *, low: str, sf: str
) -> DramaticEffectGateOutcome | None:
    """Describe what ``try_repair_scene_character_conflict`` does in one
    line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        ctx: ``ctx`` (DramaticEffectEvaluationContext); meaning follows the type and call sites.
        low: ``low`` (str); meaning follows the type and call sites.
        sf: ``sf`` (str); meaning follows the type and call sites.
    
    Returns:
        DramaticEffectGateOutcome | None:
            Returns a value of type ``DramaticEffectGateOutcome | None``; see the function body for structure, error paths, and sentinels.
    """
    if sf != "repair_or_stabilize":
        return None
    mind = ctx.validated_character_mind()
    if tag_active(low, "pressure_intensification") and not tag_active(low, "repair_gesture"):
        if mind and "de_escalate" in (mind.tactical_posture or "").lower():
            return DramaticEffectGateOutcome(
                gate_result=DramaticEffectGateResult.rejected_character_implausibility,
                rejection_reasons=["dramatic_effect_reject_character_implausibility"],
                supports_scene_function=False,
                character_plausibility_posture=CharacterPlausibilityPosture.implausible,
                effect_rationale_codes=["repair_scene_attack_only_de_escalate_character"],
                legacy_fallback_used=False,
                diagnostic_trace=[
                    DramaticEffectTraceItem(code="character_mind_conflict", detail=mind.tactical_posture),
                ],
            )
    return None


def try_boilerplate_without_tags(*, low: str, sf: str, tags_ok: bool) -> DramaticEffectGateOutcome | None:
    """Describe what ``try_boilerplate_without_tags`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        low: ``low`` (str); meaning follows the type and call sites.
        sf: ``sf`` (str); meaning follows the type and call sites.
        tags_ok: ``tags_ok`` (bool); meaning follows the type and call sites.
    
    Returns:
        DramaticEffectGateOutcome | None:
            Returns a value of type ``DramaticEffectGateOutcome | None``; see the function body for structure, error paths, and sentinels.
    """
    boilerplate_hit = any(p in low for p in _GENERIC_BOILERPLATE_PHRASES)
    if boilerplate_hit and not tags_ok:
        return DramaticEffectGateOutcome(
            gate_result=DramaticEffectGateResult.rejected_empty_fluency,
            rejection_reasons=["dramatic_effect_reject_empty_fluency"],
            supports_scene_function=False,
            empty_fluency_risk=EmptyFluencyRisk.elevated,
            effect_rationale_codes=["generic_boilerplate_without_scene_tags"],
            legacy_fallback_used=False,
            diagnostic_trace=[DramaticEffectTraceItem(code="empty_fluency", detail="boilerplate")],
        )
    return None


def outcome_tags_unsatisfied(*, low: str, sf: str) -> DramaticEffectGateOutcome:
    """Describe what ``outcome_tags_unsatisfied`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        low: ``low`` (str); meaning follows the type and call sites.
        sf: ``sf`` (str); meaning follows the type and call sites.
    
    Returns:
        DramaticEffectGateOutcome:
            Returns a value of type ``DramaticEffectGateOutcome``; see the function body for structure, error paths, and sentinels.
    """
    return DramaticEffectGateOutcome(
        gate_result=DramaticEffectGateResult.rejected_empty_fluency,
        rejection_reasons=["dramatic_effect_reject_empty_fluency"],
        supports_scene_function=False,
        empty_fluency_risk=EmptyFluencyRisk.elevated,
        effect_rationale_codes=["scene_function_tags_unsatisfied", f"scene_function:{sf}"],
        legacy_fallback_used=False,
        diagnostic_trace=[DramaticEffectTraceItem(code="tags_unsatisfied", detail=sf)],
    )


def outcome_weak_signal_accepted(
    *,
    pressure_cont: bool,
    char_post: CharacterPlausibilityPosture,
    cont_posture: ContinuitySupportPosture,
    thin_prose_override: bool = False,
) -> DramaticEffectGateOutcome:
    """Describe what ``outcome_weak_signal_accepted`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        pressure_cont: ``pressure_cont`` (bool); meaning follows the type and call sites.
        char_post: ``char_post`` (CharacterPlausibilityPosture); meaning follows the type and call sites.
        cont_posture: ``cont_posture`` (ContinuitySupportPosture); meaning follows the type and call sites.
    
    Returns:
        DramaticEffectGateOutcome:
            Returns a value of type ``DramaticEffectGateOutcome``; see the function body for structure, error paths, and sentinels.
    """
    effect_codes = ["borderline_narrative_mass_with_tags"]
    if thin_prose_override:
        effect_codes.append("actor_lanes_thin_prose_override")
    return DramaticEffectGateOutcome(
        gate_result=DramaticEffectGateResult.accepted_with_weak_signal,
        rejection_reasons=[],
        supports_scene_function=True,
        continues_or_changes_pressure=pressure_cont,
        character_plausibility_posture=char_post,
        continuity_support_posture=cont_posture,
        empty_fluency_risk=EmptyFluencyRisk.moderate,
        effect_rationale_codes=effect_codes,
        legacy_fallback_used=False,
        diagnostic_trace=[DramaticEffectTraceItem(code="weak_signal", detail="short_but_tagged")],
    )


def outcome_primary_accepted(
    *,
    pressure_cont: bool,
    char_post: CharacterPlausibilityPosture,
    cont_posture: ContinuitySupportPosture,
    trace: list[DramaticEffectTraceItem],
    thin_prose_override: bool = False,
) -> DramaticEffectGateOutcome:
    """Describe what ``outcome_primary_accepted`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        pressure_cont: ``pressure_cont`` (bool); meaning follows the type and call sites.
        char_post: ``char_post`` (CharacterPlausibilityPosture); meaning follows the type and call sites.
        cont_posture: ``cont_posture`` (ContinuitySupportPosture); meaning follows the type and call sites.
        trace: ``trace`` (list[DramaticEffectTraceItem]); meaning follows the type and call sites.
    
    Returns:
        DramaticEffectGateOutcome:
            Returns a value of type ``DramaticEffectGateOutcome``; see the function body for structure, error paths, and sentinels.
    """
    effect_codes = ["primary_gate_pass"]
    if thin_prose_override:
        effect_codes.append("actor_lanes_thin_prose_override")
    return DramaticEffectGateOutcome(
        gate_result=DramaticEffectGateResult.accepted,
        supports_scene_function=True,
        continues_or_changes_pressure=pressure_cont,
        character_plausibility_posture=char_post,
        continuity_support_posture=cont_posture,
        empty_fluency_risk=EmptyFluencyRisk.low,
        effect_rationale_codes=effect_codes,
        legacy_fallback_used=False,
        diagnostic_trace=trace,
    )


def continuity_posture_for_social(
    soc: object | None, *, tags_ok: bool
) -> ContinuitySupportPosture:
    """Describe what ``continuity_posture_for_social`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        soc: ``soc`` (object | None); meaning follows the type and call sites.
        tags_ok: ``tags_ok`` (bool); meaning follows the type and call sites.
    
    Returns:
        ContinuitySupportPosture:
            Returns a value of type ``ContinuitySupportPosture``; see the function body for structure, error paths, and sentinels.
    """
    cont_posture = ContinuitySupportPosture.adequate
    if soc and getattr(soc, "scene_pressure_state", None) in ("high_tension", "high"):
        cont_posture = ContinuitySupportPosture.strong if tags_ok else ContinuitySupportPosture.weak
    return cont_posture


def pressure_continuation_signal(low: str) -> bool:
    """Describe what ``pressure_continuation_signal`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        low: ``low`` (str); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return bool(
        tag_active(low, "pressure_intensification")
        or tag_active(low, "interpersonal_blame")
        or tag_active(low, "repair_gesture")
        or tag_active(low, "exposure_secret")
    )
