"""Dramatic effect gate behavior and golden cases."""

from __future__ import annotations

from ai_stack.dramatic_effect_contract import (
    DramaticEffectEvaluationContext,
    DramaticEffectGateResult,
    EmptyFluencyRisk,
)
from ai_stack.dramatic_effect_gate import evaluate_dramatic_effect_gate
from ai_stack.goc_frozen_vocab import GOC_MODULE_ID


def _ctx(
    *,
    narr: str,
    scene_fn: str = "escalate_conflict",
    sem: dict | None = None,
    soc: dict | None = None,
    mind: dict | None = None,
    prior: list | None = None,
) -> DramaticEffectEvaluationContext:
    return DramaticEffectEvaluationContext(
        module_id=GOC_MODULE_ID,
        proposed_narrative=narr,
        selected_scene_function=scene_fn,
        pacing_mode="standard",
        silence_brevity_decision={},
        semantic_move_record=sem,
        social_state_record=soc,
        primary_character_mind=mind,
        scene_plan_record=None,
        prior_continuity_impacts=list(prior or []),
    )


def test_fluent_empty_fluff_rejected_elevated_empty_fluency() -> None:
    """Atmosphere-only prose under escalate — no pressure tags."""
    fluff = (
        "The atmosphere thickens with unspoken tension as everyone senses something shifting beneath "
        "the polite surface; the mood deepens and a sense of uneasy anticipation fills the space."
    )
    sem = {
        "move_type": "direct_accusation",
        "social_move_family": "attack",
        "target_actor_hint": None,
        "directness": "direct",
        "pressure_tactic": None,
        "scene_risk_band": "high",
        "interpretation_trace": [],
        "feature_snapshot": {},
    }
    out = evaluate_dramatic_effect_gate(
        _ctx(narr=fluff, scene_fn="escalate_conflict", sem=sem),
    )
    assert out.gate_result == DramaticEffectGateResult.rejected_empty_fluency
    assert out.empty_fluency_risk == EmptyFluencyRisk.elevated
    assert not out.legacy_fallback_used
    assert "generic_boilerplate" in " ".join(out.effect_rationale_codes) or "tags_unsatisfied" in out.effect_rationale_codes[0]


def test_surface_variant_escalation_stable_accepted() -> None:
    """Same dramatic move, different wording — still passes tag detection."""
    sem = {
        "move_type": "direct_accusation",
        "social_move_family": "attack",
        "target_actor_hint": None,
        "directness": "direct",
        "pressure_tactic": None,
        "scene_risk_band": "high",
        "interpretation_trace": [],
        "feature_snapshot": {},
    }
    a = (
        "Michel's voice rises sharply; he accuses you of insulting his judgment and slams his hand "
        "on the table, furious that you would attack him here."
    )
    b = (
        "Michel storms; his voice is loud and angry as he accuses you and fights your claim at the table."
    )
    oa = evaluate_dramatic_effect_gate(_ctx(narr=a, scene_fn="escalate_conflict", sem=sem))
    ob = evaluate_dramatic_effect_gate(_ctx(narr=b, scene_fn="escalate_conflict", sem=sem))
    assert oa.gate_result == DramaticEffectGateResult.accepted
    assert ob.gate_result == DramaticEffectGateResult.accepted
    assert oa.legacy_fallback_used is False
    assert ob.legacy_fallback_used is False


def test_repair_weak_signal_approved_not_hard_rejected() -> None:
    """Borderline length but tags present → accepted_with_weak_signal, not rejected."""
    sem = {
        "move_type": "direct_accusation",
        "social_move_family": "attack",
        "target_actor_hint": None,
        "directness": "direct",
        "pressure_tactic": None,
        "scene_risk_band": "high",
        "interpretation_trace": [],
        "feature_snapshot": {},
    }
    short_tagged = "Michel accuses; voice loud, furious, slamming table."
    out = evaluate_dramatic_effect_gate(_ctx(narr=short_tagged, scene_fn="escalate_conflict", sem=sem))
    assert out.gate_result == DramaticEffectGateResult.accepted_with_weak_signal
    assert out.empty_fluency_risk == EmptyFluencyRisk.moderate


def test_legacy_fallback_meta_commentary() -> None:
    out = evaluate_dramatic_effect_gate(
        _ctx(
            narr="In dramatic terms the scene symbolizes the conflict at the table with loud voices.",
            scene_fn="escalate_conflict",
            sem={
                "move_type": "direct_accusation",
                "social_move_family": "attack",
                "target_actor_hint": None,
                "directness": "direct",
                "pressure_tactic": None,
                "scene_risk_band": "high",
                "interpretation_trace": [],
                "feature_snapshot": {},
            },
        )
    )
    assert out.legacy_fallback_used is True
    assert out.gate_result == DramaticEffectGateResult.rejected_empty_fluency
    assert any("dramatic_alignment" in r for r in out.rejection_reasons)


def test_goc_golden_path_not_legacy_dominated() -> None:
    """Typical strong escalation passes primary without legacy."""
    sem = {
        "move_type": "direct_accusation",
        "social_move_family": "attack",
        "target_actor_hint": None,
        "directness": "direct",
        "pressure_tactic": None,
        "scene_risk_band": "high",
        "interpretation_trace": [],
        "feature_snapshot": {},
    }
    out = evaluate_dramatic_effect_gate(
        _ctx(
            narr="You shout and rage; Michel slams his fist, furious, accusing you of insulting him.",
            scene_fn="escalate_conflict",
            sem=sem,
        )
    )
    assert out.gate_result == DramaticEffectGateResult.accepted
    assert out.legacy_fallback_used is False


def test_authority_commit_depends_on_validation_not_gate_outcome_alone() -> None:
    """Gate is advisory; seam mapping still requires validation_outcome (structural check)."""
    from ai_stack.goc_turn_seams import run_commit_seam

    proposed = [{"effect_type": "narrative_beat", "description": "x"}]
    cr = run_commit_seam(
        module_id=GOC_MODULE_ID,
        validation_outcome={"status": "rejected", "reason": "dramatic_effect_reject_empty_fluency"},
        proposed_state_effects=proposed,
    )
    assert cr.get("commit_applied") is False


def test_off_scope_move_type_vs_scene_hard_reject() -> None:
    sem = {
        "move_type": "off_scope_containment",
        "social_move_family": "deflect",
        "target_actor_hint": None,
        "directness": "direct",
        "pressure_tactic": None,
        "scene_risk_band": "low",
        "interpretation_trace": [],
        "feature_snapshot": {},
    }
    out = evaluate_dramatic_effect_gate(
        _ctx(
            narr="Michel accuses you furiously and slams the table at the dinner.",
            scene_fn="escalate_conflict",
            sem=sem,
        )
    )
    assert out.gate_result == DramaticEffectGateResult.rejected_scene_function_mismatch
