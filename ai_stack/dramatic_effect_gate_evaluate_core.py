"""Dramatic effect gate evaluation core — DS-052."""

from __future__ import annotations

from ai_stack.dramatic_effect_contract import (
    CharacterPlausibilityPosture,
    DramaticEffectEvaluationContext,
    DramaticEffectGateOutcome,
    DramaticEffectTraceItem,
)
from ai_stack.dramatic_effect_gate_evaluate_branch_outcomes import (
    continuity_posture_for_social,
    outcome_not_goc,
    outcome_primary_accepted,
    outcome_tags_unsatisfied,
    outcome_weak_signal_accepted,
    pressure_continuation_signal,
    try_boilerplate_without_tags,
    try_legacy_alignment,
    try_off_scope_containment_mismatch,
    try_prior_blame_continuity_pressure,
    try_repair_scene_character_conflict,
)
from ai_stack.dramatic_effect_gate_evaluate_tags import scene_function_tags_satisfied


def evaluate_dramatic_effect_gate(ctx: DramaticEffectEvaluationContext) -> DramaticEffectGateOutcome:
    """Evaluate proposed narrative against planner state (GoC).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        ctx: ``ctx`` (DramaticEffectEvaluationContext); meaning follows the type and call sites.
    
    Returns:
        DramaticEffectGateOutcome:
            Returns a value of type ``DramaticEffectGateOutcome``; see the function body for structure, error paths, and sentinels.
    """
    if (early := outcome_not_goc(ctx)) is not None:
        return early

    text = ctx.proposed_narrative.strip()

    # Actor-lane fluency override BEFORE legacy alignment check.
    # If lanes are approved and non-empty, don't reject on prose emptiness or ultra-short prose.
    _actor = ctx.actor_lane_summary or {}
    thin_prose_override = False
    if (
        _actor.get("actor_lane_status") == "approved"
        and (_actor.get("spoken_line_count", 0) + _actor.get("action_line_count", 0)) > 0
    ):
        if not text:
            text = "(actor-driven turn)"
            thin_prose_override = True
        elif len(text) < 40:
            text = text + " (actor realization present)"
            thin_prose_override = True
        ctx = ctx.model_copy(update={"proposed_narrative": text})

    if (legacy := try_legacy_alignment(ctx)) is not None:
        return legacy

    low = text.lower()
    trace: list[DramaticEffectTraceItem] = []
    sf = ctx.selected_scene_function or "establish_pressure"

    # Opening turns often start with atmosphere-setting prose before heavier
    # pressure tags emerge. Treat these as weak-but-legal instead of hard
    # empty-fluency rejects to reduce fallback churn on live openings.
    if sf == "establish_pressure" and text and len(text) >= 24:
        soc = ctx.validated_social_state()
        mind = ctx.validated_character_mind()
        cont_posture = continuity_posture_for_social(soc, tags_ok=False)
        char_post = CharacterPlausibilityPosture.plausible if mind else CharacterPlausibilityPosture.uncertain
        return outcome_weak_signal_accepted(
            pressure_cont=pressure_continuation_signal(low),
            char_post=char_post,
            cont_posture=cont_posture,
            thin_prose_override=thin_prose_override,
        )

    if (o := try_off_scope_containment_mismatch(ctx, sf=sf)) is not None:
        return o
    if (o := try_prior_blame_continuity_pressure(ctx, low=low, sf=sf)) is not None:
        return o
    if (o := try_repair_scene_character_conflict(ctx, low=low, sf=sf)) is not None:
        return o

    tags_ok = scene_function_tags_satisfied(low, sf)
    if (o := try_boilerplate_without_tags(low=low, sf=sf, tags_ok=tags_ok)) is not None:
        return o
    if not tags_ok:
        # Actor-realization weak-signal bypass (Case A): when all hard violations
        # have already been cleared above and the only remaining failure is narrow
        # scene-function tag mismatch, approved actor lanes with real output lines
        # and non-trivially-short prose are accepted as weak signal rather than
        # rejected. The len >= 24 guard keeps empty/ultra-short prose rejected
        # (preserves the establish_pressure empty-narrative contract).
        if (
            _actor.get("actor_lane_status") in ("approved", "not_applicable")
            and (_actor.get("spoken_line_count", 0) + _actor.get("action_line_count", 0)) > 0
            and len(text) >= 24
        ):
            soc = ctx.validated_social_state()
            mind = ctx.validated_character_mind()
            return outcome_weak_signal_accepted(
                pressure_cont=pressure_continuation_signal(low),
                char_post=CharacterPlausibilityPosture.plausible if mind else CharacterPlausibilityPosture.uncertain,
                cont_posture=continuity_posture_for_social(soc, tags_ok=False),
                thin_prose_override=True,
            )
        return outcome_tags_unsatisfied(low=low, sf=sf)

    soc = ctx.validated_social_state()
    mind = ctx.validated_character_mind()
    cont_posture = continuity_posture_for_social(soc, tags_ok=tags_ok)
    pressure_cont = pressure_continuation_signal(low)
    weak = len(text) < 56 and sf in ("escalate_conflict", "redirect_blame", "reveal_surface")
    char_post = CharacterPlausibilityPosture.plausible if mind else CharacterPlausibilityPosture.uncertain

    if weak:
        return outcome_weak_signal_accepted(
            pressure_cont=pressure_cont,
            char_post=char_post,
            cont_posture=cont_posture,
            thin_prose_override=thin_prose_override,
        )
    return outcome_primary_accepted(
        pressure_cont=pressure_cont,
        char_post=char_post,
        cont_posture=cont_posture,
        trace=trace,
        thin_prose_override=thin_prose_override,
    )
