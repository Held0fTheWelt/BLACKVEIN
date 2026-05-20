"""GoC validation seam — actor-lane, knowledge gates, dramatic-effect (DS-005 / C7).

Extracted from ``god_of_carnage_turn_seams`` so commit/visible seams stay in the orchestration module
while validation branching lives in one reviewable unit.
"""

from __future__ import annotations

import re
from typing import Any

from ai_stack.actor_tracking.validation import (
    validate_w5_actor_situation,
    w5_ast_validation_enabled,
    w5_validation_fallback,
)
from ai_stack.contracts.dramatic_effect_contract import DramaticEffectEvaluationContext
from ai_stack.story_runtime.dramatic_effect.dramatic_effect_gate import evaluate_dramatic_effect_gate, validation_reason_for_outcome
from ai_stack.god_of_carnage_dramatic_alignment import extract_proposed_narrative_text
from ai_stack.god_of_carnage_frozen_vocabulary import GOC_MODULE_ID, canonicalize_goc_actor_id, expand_goc_actor_id_aliases
from ai_stack.god_of_carnage_knowledge_runtime_gates import (
    detect_hard_forbidden_runtime,
    evaluate_opening_event_coverage,
    hard_forbidden_detection_for_actor_lane_violation,
    text_from_generation_and_effects,
)

# Default when ``story_runtime_experience`` is absent (operator DB / resolved config).
GOC_NPC_LANE_TEXT_CHAR_CAP_DEFAULT = 1200


def _check_human_actor_violations(
    structured: dict[str, Any],
    ai_forbidden_actor_ids: set[str],
    human_actor_id: str,
) -> dict[str, Any] | None:
    """Scan structured AI output for human-actor boundary violations."""
    if not ai_forbidden_actor_ids:
        return None

    expanded_forbidden: set[str] = set()
    for forbidden_id in ai_forbidden_actor_ids:
        expanded_forbidden.update(expand_goc_actor_id_aliases(forbidden_id))
    expanded_forbidden.update(expand_goc_actor_id_aliases(human_actor_id))

    def _forbidden(actor_id: str) -> bool:
        if not actor_id:
            return False
        aid = str(actor_id or "").strip()
        return aid in expanded_forbidden or canonicalize_goc_actor_id(aid) in expanded_forbidden

    def _error_code(actor_id: str, block_kind: str) -> str:
        if block_kind == "responder_nomination":
            return "human_actor_selected_as_responder"
        return "ai_controlled_human_actor"

    def _rejection(actor_id: str, block_kind: str) -> dict[str, Any]:
        code = _error_code(actor_id, block_kind)
        return {
            "status": "rejected",
            "reason": code,
            "error_code": code,
            "actor_lane_validation": {
                "status": "rejected",
                "error_code": code,
                "actor_id": actor_id,
                "block_kind": block_kind,
                "human_actor_id": human_actor_id,
            },
            "validator_lane": "goc_actor_lane_enforcement_v1",
        }

    for item in (structured.get("spoken_lines") or []):
        if not isinstance(item, dict):
            continue
        sid = str(item.get("speaker_id") or "").strip()
        if _forbidden(sid):
            return _rejection(sid, "actor_line")

    for item in (structured.get("action_lines") or []):
        if not isinstance(item, dict):
            continue
        aid = str(item.get("actor_id") or "").strip()
        if _forbidden(aid):
            return _rejection(aid, "actor_action")

    emotional_shift = structured.get("emotional_shift")
    if isinstance(emotional_shift, dict):
        for key in ("actor_id", "target_actor_id"):
            eid = str(emotional_shift.get(key) or "").strip()
            if eid and _forbidden(eid):
                return _rejection(eid, "emotional_state")

    primary = str(
        structured.get("primary_responder_id") or structured.get("responder_id") or ""
    ).strip()
    if primary and _forbidden(primary):
        return _rejection(primary, "responder_nomination")

    for sid in (structured.get("secondary_responder_ids") or []):
        if not isinstance(sid, str):
            continue
        sid = sid.strip()
        if sid and _forbidden(sid):
            return _rejection(sid, "responder_nomination")

    return None


def _resolved_npc_lane_char_cap(story_runtime_experience: dict[str, Any] | None) -> int:
    if not isinstance(story_runtime_experience, dict):
        return GOC_NPC_LANE_TEXT_CHAR_CAP_DEFAULT
    try:
        v = int(story_runtime_experience.get("npc_spoken_action_text_char_cap") or GOC_NPC_LANE_TEXT_CHAR_CAP_DEFAULT)
    except (TypeError, ValueError):
        return GOC_NPC_LANE_TEXT_CHAR_CAP_DEFAULT
    return max(400, min(8000, v))


def _detect_npc_narrated_player_action_violation(
    *,
    structured: dict[str, Any],
    raw_player_input: str,
    player_input_kind: str,
    human_actor_id: str,
) -> bool:
    pik = (player_input_kind or "").strip().lower()
    if pik not in ("action", "perception"):
        return False
    raw = (raw_player_input or "").strip().lower()
    raw = re.sub(r'[\u201c\u201d\u201e\u201f"„«»]', "", raw).strip()
    if len(raw) < 10:
        return False
    rows = structured.get("spoken_lines") if isinstance(structured.get("spoken_lines"), list) else []
    h = canonicalize_goc_actor_id(str(human_actor_id).strip()) or str(human_actor_id).strip()
    blob_parts: list[str] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        sid_raw = str(item.get("speaker_id") or "").strip()
        sid = canonicalize_goc_actor_id(sid_raw) or sid_raw
        if h and sid == h:
            continue
        t = str(item.get("text") or item.get("line") or "").strip().lower()
        if t:
            blob_parts.append(t)
    blob = " ".join(blob_parts)
    if len(raw) >= 14 and raw in blob:
        return True
    frag = raw[:18].strip()
    return len(frag) >= 12 and frag in blob


def _check_npc_spoken_action_lane_blob_cap(
    structured: dict[str, Any], *, npc_char_cap: int
) -> dict[str, Any] | None:
    cap = max(128, min(16000, int(npc_char_cap)))
    for lane_key in ("spoken_lines", "action_lines"):
        rows = structured.get(lane_key)
        if not isinstance(rows, list):
            continue
        for idx, item in enumerate(rows):
            if not isinstance(item, dict):
                continue
            blob = str(item.get("text") or item.get("line") or "").strip()
            if len(blob) > cap:
                return {
                    "status": "rejected",
                    "reason": "actor_lane_text_exceeds_transcript_beat",
                    "validator_lane": "goc_transcript_shell_contract_v1",
                    "transcript_shell_validation": {
                        "rule": "npc_lane_blob_cap",
                        "lane": lane_key,
                        "index": idx,
                        "char_len": len(blob),
                        "cap": cap,
                    },
                }
    return None


def _apply_w5_validation_to_outcome(
    *,
    outcome: dict[str, Any],
    w5_latest_snapshot: Any,
    generation: dict[str, Any],
    proposed_state_effects: list[dict[str, Any]],
    player_action_frame: dict[str, Any] | None,
    affordance_resolution: dict[str, Any] | None,
) -> dict[str, Any]:
    if not w5_ast_validation_enabled():
        return outcome

    try:
        diagnostic = validate_w5_actor_situation(
            snapshot=w5_latest_snapshot,
            generation=generation if isinstance(generation, dict) else {},
            proposed_state_effects=proposed_state_effects,
            player_action_frame=player_action_frame if isinstance(player_action_frame, dict) else None,
            affordance_resolution=affordance_resolution if isinstance(affordance_resolution, dict) else None,
        )
    except Exception as exc:
        text = str(exc).strip() or type(exc).__name__
        diagnostic = w5_validation_fallback(text)

    enriched = dict(outcome)
    enriched["w5_validation"] = {
        "w5_validation_enabled": True,
        "w5_validation_ran": diagnostic.get("status") != "fallback",
        "w5_validation_failed": bool(diagnostic.get("w5_validation_failed")),
        "w5_validation_failure_codes": list(diagnostic.get("w5_validation_failure_codes") or []),
        "w5_snapshot_id": diagnostic.get("w5_snapshot_id"),
        "w5_validation_source": diagnostic.get("w5_validation_source"),
        "w5_validation_fallback_reason": diagnostic.get("w5_validation_fallback_reason"),
        "w5_validation_warnings": list(diagnostic.get("warnings") or []),
        "failures": list(diagnostic.get("failures") or []),
    }
    if (
        enriched.get("status") == "approved"
        and diagnostic.get("w5_validation_failed")
        and diagnostic.get("w5_validation_failure_codes")
    ):
        reason = str(diagnostic["w5_validation_failure_codes"][0])
        enriched["status"] = "rejected"
        enriched["reason"] = reason
        enriched["error_code"] = reason
        enriched["failure_class"] = "w5_actor_situation_validation"
    return enriched


def _reject_proposed_effects_shape(
    proposed_state_effects: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for eff in proposed_state_effects:
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


def _opening_coverage_rejection(
    *,
    opening_coverage: dict[str, Any],
    hard_detection: dict[str, Any],
    intent_surface_diagnostics: dict[str, Any],
) -> dict[str, Any] | None:
    if opening_coverage.get("opening_event_coverage_pass", True):
        return None
    reason = "opening_event_coverage_failed"
    if not opening_coverage.get("first_playable_scene_phase_pass", True):
        reason = "opening_first_playable_scene_phase_mismatch"
    return {
        "status": "rejected",
        "reason": reason,
        "error_code": reason,
        "validator_lane": "goc_knowledge_runtime_gates_v1",
        "opening_event_coverage": opening_coverage,
        "opening_event_coverage_pass": False,
        "hard_forbidden_detection": hard_detection,
        "hard_forbidden_absent": bool(hard_detection.get("hard_forbidden_absent", True)),
        "opening_summary_only_absent": bool(hard_detection.get("opening_summary_only_absent", True)),
        "recoverable_rejection": True,
        "hard_boundary_failure": False,
        "failure_class": "opening_event_coverage",
        "intent_surface_diagnostics": intent_surface_diagnostics,
    }


def _dramatic_gate_outcome(
    *,
    module_id: str,
    proposed_state_effects: list[dict[str, Any]],
    actor_lane_summary: dict[str, Any] | None,
    evaluation_context: DramaticEffectEvaluationContext | None,
    hard_detection: dict[str, Any],
    opening_coverage: dict[str, Any],
    intent_surface_diagnostics: dict[str, Any],
    player_action_frame: dict[str, Any] | None,
    affordance_resolution: dict[str, Any] | None,
    w5_latest_snapshot: Any,
    generation: dict[str, Any],
) -> dict[str, Any]:
    narr = extract_proposed_narrative_text(proposed_state_effects)
    ctx = evaluation_context
    if ctx is None:
        ctx = DramaticEffectEvaluationContext(
            module_id=module_id,
            proposed_narrative=narr,
            selected_scene_function="establish_pressure",
            pacing_mode="standard",
            silence_brevity_decision={},
            actor_lane_summary=actor_lane_summary,
        )
    elif ctx.proposed_narrative.strip() != narr.strip():
        ctx = ctx.model_copy(update={"proposed_narrative": narr, "actor_lane_summary": actor_lane_summary})

    gate_out = evaluate_dramatic_effect_gate(ctx)
    gate_dict = gate_out.to_runtime_dict()
    base: dict[str, Any] = {
        "dramatic_effect_gate_outcome": gate_dict,
        "validator_lane": "goc_rule_engine_v1",
        "intent_surface_diagnostics": intent_surface_diagnostics,
        "hard_forbidden_detection": hard_detection,
        "hard_forbidden_absent": bool(hard_detection.get("hard_forbidden_absent", True)),
        "opening_summary_only_absent": bool(hard_detection.get("opening_summary_only_absent", True)),
        "opening_event_coverage": opening_coverage,
        "opening_event_coverage_pass": bool(opening_coverage.get("opening_event_coverage_pass", True)),
        "player_action_frame": player_action_frame if isinstance(player_action_frame, dict) else None,
        "affordance_resolution": affordance_resolution if isinstance(affordance_resolution, dict) else None,
    }

    gr = gate_out.gate_result.value
    if gr == "not_supported":
        return {
            **base,
            "status": "rejected",
            "reason": "dramatic_effect_gate_not_supported",
            "dramatic_quality_gate": "effect_gate_not_supported",
        }

    if gr in (
        "rejected_empty_fluency",
        "rejected_character_implausibility",
        "rejected_scene_function_mismatch",
        "rejected_continuity_pressure",
    ):
        aff = affordance_resolution if isinstance(affordance_resolution, dict) else {}
        aff_status = str(aff.get("affordance_status") or "").strip().lower()
        commit_policy = str(aff.get("action_commit_policy") or "").strip().lower()
        if gr == "rejected_continuity_pressure" and aff_status in {"allowed", "allowed_offscreen", "partial"}:
            return _apply_w5_validation_to_outcome(
                outcome={
                    **base,
                    "status": "approved",
                    "reason": "action_resolution_continuity_supported",
                    "dramatic_quality_gate": "effect_gate_action_resolution_override",
                    "continuity_pressure_resolution": {
                        "override_applied": True,
                        "affordance_status": aff_status,
                        "action_commit_policy": commit_policy,
                    },
                },
                w5_latest_snapshot=w5_latest_snapshot,
                generation=generation,
                proposed_state_effects=proposed_state_effects,
                player_action_frame=player_action_frame,
                affordance_resolution=affordance_resolution,
            )
        if gate_out.legacy_fallback_used and gate_out.rejection_reasons:
            reason = gate_out.rejection_reasons[0]
        else:
            reason = validation_reason_for_outcome(gate_out) or "dramatic_effect_reject_unknown"
        return {
            **base,
            "status": "rejected",
            "reason": reason,
            "dramatic_quality_gate": "effect_gate_reject",
        }

    if gr == "accepted_with_weak_signal":
        return _apply_w5_validation_to_outcome(
            outcome={
                **base,
                "status": "approved",
                "reason": "goc_default_validator_pass",
                "dramatic_quality_gate": "effect_gate_weak_signal",
                "dramatic_effect_weak_signal": True,
            },
            w5_latest_snapshot=w5_latest_snapshot,
            generation=generation,
            proposed_state_effects=proposed_state_effects,
            player_action_frame=player_action_frame,
            affordance_resolution=affordance_resolution,
        )

    return _apply_w5_validation_to_outcome(
        outcome={
            **base,
            "status": "approved",
            "reason": "goc_default_validator_pass",
            "dramatic_quality_gate": "effect_gate_pass",
            "dramatic_effect_weak_signal": False,
        },
        w5_latest_snapshot=w5_latest_snapshot,
        generation=generation,
        proposed_state_effects=proposed_state_effects,
        player_action_frame=player_action_frame,
        affordance_resolution=affordance_resolution,
    )


def run_validation_seam(
    *,
    module_id: str,
    proposed_state_effects: list[dict[str, Any]],
    generation: dict[str, Any],
    evaluation_context: DramaticEffectEvaluationContext | None = None,
    actor_lane_summary: dict[str, Any] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    story_runtime_experience: dict[str, Any] | None = None,
    interpreted_input: dict[str, Any] | None = None,
    raw_player_input: str | None = None,
    player_action_frame: dict[str, Any] | None = None,
    affordance_resolution: dict[str, Any] | None = None,
    opening_scene_sequence: dict[str, Any] | None = None,
    hard_forbidden_rules: dict[str, Any] | None = None,
    turn_input_class: str | None = None,
    scene_plan_record: dict[str, Any] | None = None,
    current_scene_id: str | None = None,
    w5_latest_snapshot: Any = None,
) -> dict[str, Any]:
    """Emit validation_outcome — no player text (CANONICAL_TURN_CONTRACT_GOC.md §2.1)."""
    if actor_lane_context and isinstance(actor_lane_context, dict):
        ai_forbidden: set[str] = set()
        for raw_actor_id in (actor_lane_context.get("ai_forbidden_actor_ids") or []):
            ai_forbidden.update(expand_goc_actor_id_aliases(str(raw_actor_id)))
        human_actor_id: str = str(actor_lane_context.get("human_actor_id") or "")
        ai_forbidden.update(expand_goc_actor_id_aliases(human_actor_id))
        if ai_forbidden or human_actor_id:
            gen_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
            structured_check = (
                gen_meta.get("structured_output") if isinstance(gen_meta.get("structured_output"), dict) else {}
            )
            violation = _check_human_actor_violations(structured_check, ai_forbidden, human_actor_id)
            if violation is not None:
                detection = hard_forbidden_detection_for_actor_lane_violation(
                    reason=str(violation.get("reason") or ""),
                    hard_forbidden_rules=hard_forbidden_rules,
                )
                return {
                    **violation,
                    "hard_forbidden_detection": detection,
                    "hard_forbidden_absent": False,
                    "opening_summary_only_absent": True,
                    "hard_boundary_failure": True,
                }

    _paf_early = player_action_frame if isinstance(player_action_frame, dict) else {}
    if (
        module_id == GOC_MODULE_ID
        and str(_paf_early.get("validation_surface") or "").strip() == "authoritative_action_resolution"
    ):
        _aff_early = affordance_resolution if isinstance(affordance_resolution, dict) else {}
        return {
            "status": "approved",
            "reason": "authoritative_action_resolution_surface",
            "validator_lane": "goc_action_resolution_surface_v1",
            "dramatic_quality_gate": "waived_authoritative_action_resolution_surface",
            "dramatic_effect_weak_signal": False,
            "intent_surface_diagnostics": {"npc_narrated_player_action_violation": False},
            "player_action_frame": _paf_early,
            "affordance_resolution": _aff_early,
        }

    if module_id != GOC_MODULE_ID:
        return {
            "status": "waived",
            "reason": "non_goc_vertical_slice",
            "validator_lane": "goc_rule_engine_v1",
        }
    if generation.get("success") is False or generation.get("error"):
        return {
            "status": "rejected",
            "reason": "model_generation_failed",
            "validator_lane": "goc_rule_engine_v1",
        }

    gen_meta_pre = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured_pre = (
        gen_meta_pre.get("structured_output") if isinstance(gen_meta_pre.get("structured_output"), dict) else {}
    )
    intent_surface_diagnostics: dict[str, Any] = {"npc_narrated_player_action_violation": False}
    if structured_pre and isinstance(actor_lane_context, dict) and module_id == GOC_MODULE_ID:
        hid = str(actor_lane_context.get("human_actor_id") or "").strip()
        interp_loc = interpreted_input if isinstance(interpreted_input, dict) else {}
        raw_pi_eff = str(raw_player_input or interp_loc.get("original_text") or "").strip()
        pik_eff = str(interp_loc.get("player_input_kind") or "").strip().lower()
        if hid and raw_pi_eff and pik_eff in ("action", "perception"):
            intent_surface_diagnostics["npc_narrated_player_action_violation"] = (
                _detect_npc_narrated_player_action_violation(
                    structured=structured_pre,
                    raw_player_input=raw_pi_eff,
                    player_input_kind=pik_eff,
                    human_actor_id=hid,
                )
            )
    if structured_pre:
        shell_violation = _check_npc_spoken_action_lane_blob_cap(
            structured_pre, npc_char_cap=_resolved_npc_lane_char_cap(story_runtime_experience)
        )
        if shell_violation is not None:
            return {**shell_violation, "intent_surface_diagnostics": intent_surface_diagnostics}

    knowledge_text = text_from_generation_and_effects(
        generation=generation if isinstance(generation, dict) else {},
        proposed_state_effects=proposed_state_effects,
    )
    hard_detection = detect_hard_forbidden_runtime(
        hard_forbidden_rules=hard_forbidden_rules,
        opening_scene_sequence=opening_scene_sequence,
        text=knowledge_text,
        structured_output=structured_pre,
        actor_lane_context=actor_lane_context if isinstance(actor_lane_context, dict) else None,
        turn_input_class=turn_input_class,
    )
    if hard_detection.get("action") in {"reject", "recover"}:
        recoverable = hard_detection.get("action") == "recover"
        reason = str(hard_detection.get("reason") or "hard_forbidden_runtime_gate")
        return {
            "status": "rejected",
            "reason": reason,
            "error_code": reason,
            "validator_lane": "goc_knowledge_runtime_gates_v1",
            "hard_forbidden_detection": hard_detection,
            "hard_forbidden_absent": bool(hard_detection.get("hard_forbidden_absent")),
            "opening_summary_only_absent": bool(hard_detection.get("opening_summary_only_absent")),
            "hard_boundary_failure": not recoverable,
            "recoverable_rejection": recoverable,
            "failure_class": "hard_forbidden_runtime_gate" if not recoverable else "recoverable_opening_contract",
            "intent_surface_diagnostics": intent_surface_diagnostics,
        }

    shape_reject = _reject_proposed_effects_shape(proposed_state_effects)
    if shape_reject is not None:
        return shape_reject

    opening_coverage: dict[str, Any] = {
        "opening_event_coverage_pass": True,
        "applicable": False,
    }
    if str(turn_input_class or "").strip().lower() == "opening":
        opening_coverage = evaluate_opening_event_coverage(
            opening_scene_sequence=opening_scene_sequence,
            text=knowledge_text or extract_proposed_narrative_text(proposed_state_effects),
            structured_output=structured_pre,
            actor_lane_context=actor_lane_context if isinstance(actor_lane_context, dict) else None,
            scene_plan_record=scene_plan_record if isinstance(scene_plan_record, dict) else None,
            current_scene_id=current_scene_id,
        )
        opening_reject = _opening_coverage_rejection(
            opening_coverage=opening_coverage,
            hard_detection=hard_detection,
            intent_surface_diagnostics=intent_surface_diagnostics,
        )
        if opening_reject is not None:
            return opening_reject

    return _dramatic_gate_outcome(
        module_id=module_id,
        proposed_state_effects=proposed_state_effects,
        actor_lane_summary=actor_lane_summary,
        evaluation_context=evaluation_context,
        hard_detection=hard_detection,
        opening_coverage=opening_coverage,
        intent_surface_diagnostics=intent_surface_diagnostics,
        player_action_frame=player_action_frame if isinstance(player_action_frame, dict) else None,
        affordance_resolution=affordance_resolution if isinstance(affordance_resolution, dict) else None,
        w5_latest_snapshot=w5_latest_snapshot,
        generation=generation if isinstance(generation, dict) else {},
    )
