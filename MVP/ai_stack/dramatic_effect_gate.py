"""Planner-aware dramatic effect gate (GoC) — bounded deterministic evaluation."""

from __future__ import annotations

from typing import Any

from ai_stack.dramatic_effect_contract import (
    CharacterPlausibilityPosture,
    ContinuitySupportPosture,
    DramaticEffectEvaluationContext,
    DramaticEffectGateOutcome,
    DramaticEffectGateResult,
    DramaticEffectTraceItem,
    EmptyFluencyRisk,
)
from ai_stack.goc_dramatic_alignment import (
    _GENERIC_BOILERPLATE_PHRASES,
    dramatic_alignment_legacy_fallback_only,
)
from ai_stack.goc_frozen_vocab import GOC_MODULE_ID

# Tag clusters: multiple substrings per tag (OR within tag). Not a single scene-function token list.
_EFFECT_TAG_CLUSTERS: dict[str, tuple[str, ...]] = {
    "pressure_intensification": (
        "rage",
        "furious",
        "shout",
        "loud",
        "slam",
        "fight",
        "attack",
        "voice",
        "angry",
        "storm",
        "insult",
    ),
    "interpersonal_blame": (
        "blame",
        "fault",
        "accus",
        "your",
        "you",
        "responsib",
        "deny",
        "denial",
    ),
    "repair_gesture": ("sorry", "apolog", "peace", "calm", "truce", "repair", "stop"),
    "exposure_secret": ("truth", "secret", "reveal", "admit", "confess", "fact", "know", "knew", "hid"),
    "inquiry_probe": ("why", "motive", "reason", "explain", "justify", "because"),
    "ambient_pressure": ("tight", "quiet", "table", "room", "watch", "still", "wait", "look"),
    "silence_evade": ("silence", "nothing", "say", "hold", "still"),
    "pivot_shift": ("turn", "shift", "instead", "leave", "topic", "door", "stay", "here", "apartment", "dinner"),
    "alliance_network": ("side", "sides", "allied", "alliance", "against", "wife", "husband", "spouse"),
}

# Each scene function: list of OR-groups (each group is satisfied if any tag in group matches).
_SCENE_FUNCTION_TAG_GROUPS: dict[str, tuple[tuple[str, ...], ...]] = {
    "escalate_conflict": (("pressure_intensification", "interpersonal_blame"),),
    "redirect_blame": (("interpersonal_blame",),),
    "reveal_surface": (("exposure_secret",),),
    "probe_motive": (("inquiry_probe",),),
    "repair_or_stabilize": (("repair_gesture",),),
    "establish_pressure": (("ambient_pressure", "pressure_intensification", "interpersonal_blame"),),
    "withhold_or_evade": (("silence_evade", "ambient_pressure"),),
    "scene_pivot": (("pivot_shift",),),
}

def _tag_active(low: str, tag: str) -> bool:
    clusters = _EFFECT_TAG_CLUSTERS.get(tag, ())
    return any(c in low for c in clusters)


def _scene_function_tags_satisfied(low: str, scene_function: str) -> bool:
    groups = _SCENE_FUNCTION_TAG_GROUPS.get(scene_function)
    if not groups:
        return True
    for or_group in groups:
        if not any(_tag_active(low, t) for t in or_group):
            return False
    return True


def _outcome_from_legacy(reason: str) -> DramaticEffectGateOutcome:
    """Legacy structural/meta failures map to empty-fluency style hard reject for gate_result."""
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


def evaluate_dramatic_effect_gate(ctx: DramaticEffectEvaluationContext) -> DramaticEffectGateOutcome:
    """Evaluate proposed narrative against planner state (GoC)."""
    if ctx.module_id != GOC_MODULE_ID:
        return DramaticEffectGateOutcome(
            gate_result=DramaticEffectGateResult.not_supported,
            effect_rationale_codes=["evaluator_module_not_goc"],
            diagnostic_trace=[
                DramaticEffectTraceItem(code="module_unsupported", detail=ctx.module_id),
            ],
        )

    text = ctx.proposed_narrative.strip()
    low = text.lower()
    trace: list[DramaticEffectTraceItem] = []

    sem = ctx.validated_semantic_move()
    soc = ctx.validated_social_state()
    mind = ctx.validated_character_mind()

    legacy_reason = dramatic_alignment_legacy_fallback_only(
        selected_scene_function=ctx.selected_scene_function,
        pacing_mode=ctx.pacing_mode,
        silence_brevity_decision=ctx.silence_brevity_decision or None,
        proposed_narrative=ctx.proposed_narrative,
    )
    if legacy_reason:
        return _outcome_from_legacy(legacy_reason)

    sf = ctx.selected_scene_function or "establish_pressure"

    # --- Hard mismatch: move_type vs scene (bounded) — not family tables (director + player can diverge). ---
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

    # --- Continuity: carry blame pressure ---
    prior_classes = [
        str(x.get("class") or "")
        for x in (ctx.prior_continuity_impacts or [])
        if isinstance(x, dict)
    ]
    if "blame_pressure" in prior_classes and sf in ("redirect_blame", "escalate_conflict", "reveal_surface"):
        if not (
            _tag_active(low, "interpersonal_blame")
            or _tag_active(low, "pressure_intensification")
            or _tag_active(low, "alliance_network")
            or _tag_active(low, "exposure_secret")
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

    # --- Character plausibility (bounded): repair scene but only attack idiom, no repair tag ---
    if sf == "repair_or_stabilize":
        if _tag_active(low, "pressure_intensification") and not _tag_active(low, "repair_gesture"):
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

    tags_ok = _scene_function_tags_satisfied(low, sf)

    # Generic polished emptiness without satisfying scene tags (primary empty fluency path)
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

    if not tags_ok:
        return DramaticEffectGateOutcome(
            gate_result=DramaticEffectGateResult.rejected_empty_fluency,
            rejection_reasons=["dramatic_effect_reject_empty_fluency"],
            supports_scene_function=False,
            empty_fluency_risk=EmptyFluencyRisk.elevated,
            effect_rationale_codes=["scene_function_tags_unsatisfied", f"scene_function:{sf}"],
            legacy_fallback_used=False,
            diagnostic_trace=[DramaticEffectTraceItem(code="tags_unsatisfied", detail=sf)],
        )

    # Pressure continuation estimate
    cont_posture = ContinuitySupportPosture.adequate
    if soc and soc.scene_pressure_state in ("high_tension", "high"):
        cont_posture = ContinuitySupportPosture.strong if tags_ok else ContinuitySupportPosture.weak

    pressure_cont = bool(
        _tag_active(low, "pressure_intensification")
        or _tag_active(low, "interpersonal_blame")
        or _tag_active(low, "repair_gesture")
        or _tag_active(low, "exposure_secret")
    )

    # Weak signal: borderline mass on high-stakes already passed legacy; thin content with tags
    weak = len(text) < 56 and sf in ("escalate_conflict", "redirect_blame", "reveal_surface")

    char_post = CharacterPlausibilityPosture.plausible if mind else CharacterPlausibilityPosture.uncertain

    if weak:
        return DramaticEffectGateOutcome(
            gate_result=DramaticEffectGateResult.accepted_with_weak_signal,
            rejection_reasons=[],
            supports_scene_function=True,
            continues_or_changes_pressure=pressure_cont,
            character_plausibility_posture=char_post,
            continuity_support_posture=cont_posture,
            empty_fluency_risk=EmptyFluencyRisk.moderate,
            effect_rationale_codes=["borderline_narrative_mass_with_tags"],
            legacy_fallback_used=False,
            diagnostic_trace=[DramaticEffectTraceItem(code="weak_signal", detail="short_but_tagged")],
        )

    return DramaticEffectGateOutcome(
        gate_result=DramaticEffectGateResult.accepted,
        supports_scene_function=True,
        continues_or_changes_pressure=pressure_cont,
        character_plausibility_posture=char_post,
        continuity_support_posture=cont_posture,
        empty_fluency_risk=EmptyFluencyRisk.low,
        effect_rationale_codes=["primary_gate_pass"],
        legacy_fallback_used=False,
        diagnostic_trace=trace,
    )


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
) -> DramaticEffectEvaluationContext:
    """Pick primary responder mind record aligned with selected_responder_set."""
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
    )


def validation_reason_for_outcome(out: DramaticEffectGateOutcome) -> str | None:
    """Machine reason for validation_outcome when status should be rejected."""
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
