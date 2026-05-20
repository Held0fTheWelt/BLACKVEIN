"""Deterministic GOC validation seam mirrors for ADR-0041 plan-enforced dispatch.

These adapters call the same helpers as ``run_validation_seam`` where possible.
They do **not** replace the seam or alter ``validation_outcome``; they only
produce local execution evidence under ``ADR0041_VALIDATOR_DISPATCH_MODE=plan_enforced``.
"""

from __future__ import annotations

from typing import Any

from ai_stack.capability_validator_plan import ValidatorPlanEntry
from ai_stack.dramatic_effect.dramatic_effect_contract import DramaticEffectEvaluationContext
from ai_stack.dramatic_effect.dramatic_effect_gate import evaluate_dramatic_effect_gate
from ai_stack.goc_dramatic_alignment import extract_proposed_narrative_text
from ai_stack.goc_frozen_vocab import (
    GOC_MODULE_ID,
    expand_goc_actor_id_aliases,
)
from ai_stack.goc_knowledge_runtime_gates import (
    detect_hard_forbidden_runtime,
    evaluate_opening_event_coverage,
    text_from_generation_and_effects,
)
from ai_stack.goc_turn_seams import (
    _check_human_actor_violations,
    _check_npc_spoken_action_lane_blob_cap,
    _resolved_npc_lane_char_cap,
)

# Semantic validator IDs (registry / plan-enforced only; not Pi runtime keys).
ACTOR_LANE_FORBIDDEN_CONTRACT = "actor_lane_forbidden_contract"
NPC_TRANSCRIPT_SHELL_CONTRACT = "npc_transcript_shell_contract"
PROPOSED_EFFECTS_SHAPE_CONTRACT = "proposed_effects_shape_contract"
MODEL_GENERATION_PRECHECK_CONTRACT = "model_generation_precheck_contract"
HARD_FORBIDDEN_RUNTIME_CONTRACT = "hard_forbidden_runtime_contract"
OPENING_EVENT_COVERAGE_CONTRACT = "opening_event_coverage_contract"
DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT = "dramatic_effect_gate_mirror_contract"

SEAM_MIRROR_VALIDATOR_IDS: tuple[str, ...] = (
    ACTOR_LANE_FORBIDDEN_CONTRACT,
    NPC_TRANSCRIPT_SHELL_CONTRACT,
    PROPOSED_EFFECTS_SHAPE_CONTRACT,
    MODEL_GENERATION_PRECHECK_CONTRACT,
    HARD_FORBIDDEN_RUNTIME_CONTRACT,
    OPENING_EVENT_COVERAGE_CONTRACT,
    DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT,
)


def _normalize(validator_id: str, raw: dict[str, Any] | None, *, blocking: bool = True) -> dict[str, Any]:
    from ai_stack.capability_validator_registry import normalize_validator_dispatch_result

    return normalize_validator_dispatch_result(validator_id, raw, blocking=blocking)


def _unavailable(validator_id: str, *, reason: str, blocking: bool = True) -> dict[str, Any]:
    from ai_stack.capability_validator_registry import unavailable_validator_result

    return unavailable_validator_result(validator_id, reason=reason, blocking=blocking)


def _waived_non_goc(validator_id: str, ctx: dict[str, Any]) -> dict[str, Any] | None:
    mid = str(ctx.get("module_id") or "").strip()
    if not mid:
        return None
    if mid != GOC_MODULE_ID:
        return _normalize(
            validator_id,
            {
                "status": "approved",
                "contract_pass": True,
                "blocking": False,
                "reason": "waived_non_goc_vertical_slice",
            },
            blocking=False,
        )
    return None


def adapter_actor_lane_forbidden_contract(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    vid = ACTOR_LANE_FORBIDDEN_CONTRACT
    w = _waived_non_goc(vid, ctx)
    if w is not None:
        return w
    al = ctx.get("actor_lane_context")
    if not isinstance(al, dict):
        return _unavailable(vid, reason="missing_actor_lane_context", blocking=True)
    structured = ctx.get("structured_output")
    if not isinstance(structured, dict):
        return _unavailable(vid, reason="missing_structured_output", blocking=True)
    ai_forbidden: set[str] = set()
    for raw_actor_id in (al.get("ai_forbidden_actor_ids") or []):
        ai_forbidden.update(expand_goc_actor_id_aliases(str(raw_actor_id)))
    human_actor_id: str = str(al.get("human_actor_id") or "")
    ai_forbidden.update(expand_goc_actor_id_aliases(human_actor_id))
    if not ai_forbidden and not human_actor_id:
        return _normalize(
            vid,
            {
                "status": "approved",
                "contract_pass": True,
                "blocking": False,
                "reason": "actor_lane_context_inactive",
            },
            blocking=False,
        )
    viol = _check_human_actor_violations(structured, ai_forbidden, human_actor_id)
    if viol is not None:
        return _normalize(vid, viol, blocking=True)
    return _normalize(
        vid,
        {"status": "approved", "contract_pass": True, "reason": "actor_lane_forbidden_pass"},
        blocking=True,
    )


def adapter_npc_transcript_shell_contract(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    vid = NPC_TRANSCRIPT_SHELL_CONTRACT
    w = _waived_non_goc(vid, ctx)
    if w is not None:
        return w
    structured = ctx.get("structured_output")
    if not isinstance(structured, dict):
        return _unavailable(vid, reason="missing_structured_output", blocking=True)
    sre = ctx.get("story_runtime_experience")
    if not isinstance(sre, dict):
        sre = ctx.get("runtime_projection")
    npc_cap = _resolved_npc_lane_char_cap(sre if isinstance(sre, dict) else None)
    viol = _check_npc_spoken_action_lane_blob_cap(structured, npc_char_cap=npc_cap)
    if viol is not None:
        return _normalize(vid, viol, blocking=True)
    return _normalize(
        vid,
        {"status": "approved", "contract_pass": True, "reason": "npc_transcript_shell_pass"},
        blocking=True,
    )


def _validate_proposed_effects_shape(proposed: list[Any]) -> dict[str, Any] | None:
    for eff in proposed:
        if not isinstance(eff, dict):
            return {
                "status": "rejected",
                "reason": "malformed_proposed_effect",
                "validator_lane": "goc_rule_engine_v1",
            }
        if "description" not in eff and "effect_type" not in eff:
            return {
                "status": "rejected",
                "reason": "incomplete_proposed_effect",
                "validator_lane": "goc_rule_engine_v1",
            }
    return None


def adapter_proposed_effects_shape_contract(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    vid = PROPOSED_EFFECTS_SHAPE_CONTRACT
    w = _waived_non_goc(vid, ctx)
    if w is not None:
        return w
    raw = ctx.get("proposed_state_effects")
    if not isinstance(raw, list):
        return _unavailable(vid, reason="missing_proposed_state_effects", blocking=True)
    err = _validate_proposed_effects_shape(raw)
    if err is not None:
        return _normalize(vid, err, blocking=True)
    return _normalize(
        vid,
        {"status": "approved", "contract_pass": True, "reason": "proposed_effects_shape_pass"},
        blocking=True,
    )


def adapter_model_generation_precheck_contract(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    vid = MODEL_GENERATION_PRECHECK_CONTRACT
    w = _waived_non_goc(vid, ctx)
    if w is not None:
        return w
    generation = ctx.get("generation")
    if not isinstance(generation, dict):
        return _unavailable(vid, reason="missing_generation", blocking=True)
    success = generation.get("success")
    if success is False or generation.get("error"):
        return _normalize(
            vid,
            {
                "status": "rejected",
                "contract_pass": False,
                "reason": "model_generation_failed",
                "validator_lane": "goc_rule_engine_v1",
            },
            blocking=True,
        )
    return _normalize(
        vid,
        {"status": "approved", "contract_pass": True, "reason": "model_generation_ok"},
        blocking=True,
    )


def adapter_hard_forbidden_runtime_contract(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    vid = HARD_FORBIDDEN_RUNTIME_CONTRACT
    w = _waived_non_goc(vid, ctx)
    if w is not None:
        return w
    generation = ctx.get("generation")
    proposed = ctx.get("proposed_state_effects")
    if not isinstance(generation, dict) or not isinstance(proposed, list):
        return _unavailable(
            vid,
            reason="missing_generation_or_proposed_state_effects",
            blocking=True,
        )
    gen_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured_pre = gen_meta.get("structured_output") if isinstance(gen_meta.get("structured_output"), dict) else {}
    knowledge_text = text_from_generation_and_effects(
        generation=generation,
        proposed_state_effects=proposed,
    )
    al = ctx.get("actor_lane_context") if isinstance(ctx.get("actor_lane_context"), dict) else None
    tic = ctx.get("turn_input_class")
    turn_input_class = str(tic).strip() if tic else None
    opening_seq = ctx.get("opening_scene_sequence")
    hf_rules = ctx.get("hard_forbidden_rules")
    hard_detection = detect_hard_forbidden_runtime(
        hard_forbidden_rules=hf_rules if isinstance(hf_rules, dict) else None,
        opening_scene_sequence=opening_seq if isinstance(opening_seq, dict) else None,
        text=knowledge_text,
        structured_output=structured_pre,
        actor_lane_context=al,
        turn_input_class=turn_input_class,
    )
    if hard_detection.get("action") in {"reject", "recover"}:
        recoverable = hard_detection.get("action") == "recover"
        reason = str(hard_detection.get("reason") or "hard_forbidden_runtime_gate")
        return _normalize(
            vid,
            {
                "status": "rejected",
                "contract_pass": False,
                "reason": reason,
                "hard_forbidden_detection": hard_detection,
                "recoverable_rejection": recoverable,
            },
            blocking=True,
        )
    return _normalize(
        vid,
        {
            "status": "approved",
            "contract_pass": True,
            "reason": "hard_forbidden_runtime_pass",
            "hard_forbidden_detection": hard_detection,
        },
        blocking=True,
    )


def adapter_opening_event_coverage_contract(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    vid = OPENING_EVENT_COVERAGE_CONTRACT
    w = _waived_non_goc(vid, ctx)
    if w is not None:
        return w
    if str(ctx.get("turn_input_class") or "").strip().lower() != "opening":
        if not str(ctx.get("turn_input_class") or "").strip():
            return _unavailable(vid, reason="missing_turn_input_class_for_opening_coverage", blocking=True)
        return _normalize(
            vid,
            {
                "status": "approved",
                "contract_pass": True,
                "blocking": False,
                "reason": "opening_coverage_not_applicable_turn",
            },
            blocking=False,
        )
    generation = ctx.get("generation")
    proposed = ctx.get("proposed_state_effects")
    if not isinstance(generation, dict) or not isinstance(proposed, list):
        return _unavailable(vid, reason="missing_generation_or_proposed_effects", blocking=True)
    gen_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured_pre = gen_meta.get("structured_output") if isinstance(gen_meta.get("structured_output"), dict) else {}
    narr = extract_proposed_narrative_text(proposed)
    knowledge_text = text_from_generation_and_effects(
        generation=generation,
        proposed_state_effects=proposed,
    )
    text = knowledge_text or narr
    osc = ctx.get("opening_scene_sequence")
    spr = ctx.get("scene_plan_record")
    csid = ctx.get("current_scene_id")
    opening_coverage = evaluate_opening_event_coverage(
        opening_scene_sequence=osc if isinstance(osc, dict) else None,
        text=text,
        structured_output=structured_pre,
        actor_lane_context=ctx.get("actor_lane_context")
        if isinstance(ctx.get("actor_lane_context"), dict)
        else None,
        scene_plan_record=spr if isinstance(spr, dict) else None,
        current_scene_id=str(csid).strip() if csid else None,
    )
    if not opening_coverage.get("opening_event_coverage_pass", True):
        reason = "opening_event_coverage_failed"
        if not opening_coverage.get("first_playable_scene_phase_pass", True):
            reason = "opening_first_playable_scene_phase_mismatch"
        return _normalize(
            vid,
            {
                "status": "rejected",
                "contract_pass": False,
                "reason": reason,
                "opening_event_coverage": opening_coverage,
            },
            blocking=True,
        )
    return _normalize(
        vid,
        {
            "status": "approved",
            "contract_pass": True,
            "reason": "opening_event_coverage_pass",
            "opening_event_coverage": opening_coverage,
        },
        blocking=True,
    )


def adapter_dramatic_effect_gate_mirror_contract(entry: ValidatorPlanEntry, ctx: dict[str, Any]) -> dict[str, Any]:
    """Best-effort mirror of ``evaluate_dramatic_effect_gate`` (partial runtime fidelity)."""
    vid = DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT
    w = _waived_non_goc(vid, ctx)
    if w is not None:
        return w
    proposed = ctx.get("proposed_state_effects")
    if not isinstance(proposed, list):
        return _unavailable(vid, reason="missing_proposed_state_effects", blocking=True)
    narr = extract_proposed_narrative_text(proposed)
    als = ctx.get("actor_lane_summary") if isinstance(ctx.get("actor_lane_summary"), dict) else {}
    sbd = (
        ctx.get("silence_brevity_decision")
        if isinstance(ctx.get("silence_brevity_decision"), dict)
        else {}
    )
    ssf_raw = ctx.get("selected_scene_function")
    ssf = str(ssf_raw).strip() if ssf_raw else "establish_pressure"
    pm_raw = ctx.get("pacing_mode")
    pacing_mode = str(pm_raw).strip() if pm_raw else "standard"
    evaluation_ctx = DramaticEffectEvaluationContext(
        module_id=str(ctx.get("module_id") or GOC_MODULE_ID),
        proposed_narrative=narr,
        selected_scene_function=ssf,
        pacing_mode=pacing_mode,
        silence_brevity_decision=sbd,
        actor_lane_summary=als,
    )
    gate_out = evaluate_dramatic_effect_gate(evaluation_ctx)
    gr = gate_out.gate_result.value
    if gr == "not_supported":
        return _normalize(
            vid,
            {
                "status": "rejected",
                "contract_pass": False,
                "reason": "dramatic_effect_gate_not_supported",
                "dramatic_effect_mirror_fidelity": "partial_defaults",
            },
            blocking=True,
        )
    if gr in (
        "rejected_empty_fluency",
        "rejected_character_implausibility",
        "rejected_scene_function_mismatch",
        "rejected_continuity_pressure",
    ):
        aff = ctx.get("affordance_resolution") if isinstance(ctx.get("affordance_resolution"), dict) else {}
        aff_status = str(aff.get("affordance_status") or "").strip().lower()
        if gr == "rejected_continuity_pressure" and aff_status in {"allowed", "allowed_offscreen", "partial"}:
            return _normalize(
                vid,
                {
                    "status": "approved",
                    "contract_pass": True,
                    "reason": "action_resolution_continuity_supported_mirror",
                    "dramatic_effect_mirror_fidelity": "partial_defaults",
                },
                blocking=True,
            )
        reason = gate_out.rejection_reasons[0] if gate_out.rejection_reasons else "dramatic_gate_reject"
        return _normalize(
            vid,
            {
                "status": "rejected",
                "contract_pass": False,
                "reason": reason,
                "dramatic_effect_mirror_fidelity": "partial_defaults",
            },
            blocking=True,
        )
    if gr == "accepted_with_weak_signal":
        return _normalize(
            vid,
            {"status": "approved", "contract_pass": True, "reason": "effect_gate_weak_signal_mirror"},
            blocking=True,
        )
    return _normalize(
        vid,
        {"status": "approved", "contract_pass": True, "reason": "effect_gate_pass_mirror"},
        blocking=True,
    )


def seam_mirror_registry_map() -> dict[str, Any]:
    """Map seam-mirror validator_id -> callable (for ADR-0041 registry merge)."""
    return {
        ACTOR_LANE_FORBIDDEN_CONTRACT: adapter_actor_lane_forbidden_contract,
        NPC_TRANSCRIPT_SHELL_CONTRACT: adapter_npc_transcript_shell_contract,
        PROPOSED_EFFECTS_SHAPE_CONTRACT: adapter_proposed_effects_shape_contract,
        MODEL_GENERATION_PRECHECK_CONTRACT: adapter_model_generation_precheck_contract,
        HARD_FORBIDDEN_RUNTIME_CONTRACT: adapter_hard_forbidden_runtime_contract,
        OPENING_EVENT_COVERAGE_CONTRACT: adapter_opening_event_coverage_contract,
        DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT: adapter_dramatic_effect_gate_mirror_contract,
    }
