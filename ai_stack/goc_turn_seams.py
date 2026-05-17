"""
Proposal, validation, commit, visible seams helpers
(CANONICAL_TURN_CONTRACT_GOC.md §2).
"""

from __future__ import annotations

import json
import re
from typing import Any

from ai_stack.dramatic_effect_contract import DramaticEffectEvaluationContext
from ai_stack.dramatic_effect_gate import evaluate_dramatic_effect_gate, validation_reason_for_outcome
from ai_stack.goc_dramatic_alignment import extract_proposed_narrative_text
from ai_stack.goc_field_initialization_envelope import (
    SETTER_SURFACE_RUNTIME_HOST_SESSION,
    goc_uninitialized_field_envelope,
)
from ai_stack.goc_frozen_vocab import (
    DIRECTOR_IMMUTABLE_FIELDS,
    GOC_MODULE_ID,
    assert_transition_pattern,
    canonicalize_goc_actor_id,
    expand_goc_actor_id_aliases,
)
from ai_stack.goc_npc_transcript_projection import goc_spoken_lines_multi_speaker_row_markers
from ai_stack.goc_yaml_authority import (
    select_goc_director_surface_hints_for_turn,
    thin_edge_staging_line_from_guidance,
)
from ai_stack.goc_knowledge_runtime_gates import (
    detect_hard_forbidden_runtime,
    evaluate_opening_event_coverage,
    hard_forbidden_detection_for_actor_lane_violation,
    text_from_generation_and_effects,
)
from ai_stack.opening_shape_normalizer import narration_summary_to_plain_str

_GOC_ACTOR_DISPLAY_NAMES = {
    "veronique_vallon": "Veronique",
    "annette_reille": "Annette",
    "michel_longstreet": "Michel",
    "alain_reille": "Alain",
}


def _goc_structured_rows_filtered_for_human_lane(
    rows: Any,
    *,
    human_actor_id: str | None,
    selected_player_role: str | None,
    actor_key: str,
) -> tuple[list[Any], int]:
    """Drop dict rows whose actor matches the live human lane (player truth is not model output)."""
    if not isinstance(rows, list):
        return [], 0
    out: list[Any] = []
    dropped = 0
    for item in rows:
        if not isinstance(item, dict):
            out.append(item)
            continue
        actor_raw = str(item.get(actor_key) or "").strip()
        if not actor_raw:
            out.append(item)
            continue
        canon = canonicalize_goc_actor_id(actor_raw) or actor_raw
        match = False
        if human_actor_id:
            h = canonicalize_goc_actor_id(str(human_actor_id).strip())
            if h and canon == h:
                match = True
        if not match and selected_player_role:
            r = canonicalize_goc_actor_id(str(selected_player_role).strip())
            if r and canon == r:
                match = True
        if match:
            dropped += 1
            continue
        out.append(item)
    return out, dropped


def _gm_display_text_from_generation_content(raw: str) -> str:
    """Use narrative_response for GM lines when model content is JSON (e.g.
    raw graph fallback).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        raw: ``raw`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    s = raw.strip()
    if s.startswith("{"):
        try:
            parsed = json.loads(s)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            actor_lines = []
            actor_lines.extend(_coerce_actor_lines(parsed.get("spoken_lines"), actor_key="speaker_id"))
            actor_lines.extend(_coerce_actor_lines(parsed.get("action_lines"), actor_key="actor_id"))
            if str(parsed.get("schema_version") or "").strip() == "runtime_actor_turn_v1" and actor_lines:
                return "\n".join(actor_lines[:4])
            narr = narration_summary_to_plain_str(parsed.get("narration_summary"))
            if not narr.strip():
                narr = narration_summary_to_plain_str(parsed.get("narrative_response"))
            if narr.strip():
                return narr.strip()
            if actor_lines:
                return "\n".join(actor_lines[:4])
    return raw


def _coerce_actor_lines(value: Any, *, actor_key: str) -> list[str]:
    if isinstance(value, str):
        line = value.strip()
        return [line] if line else []
    if not isinstance(value, list):
        return []
    lines: list[str] = []
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            actor = str(item.get(actor_key) or "").strip()
            actor = _GOC_ACTOR_DISPLAY_NAMES.get(actor, actor)
            tone = str(item.get("tone") or "").strip()
            prefix = f"{actor}: " if actor else ""
            suffix = f" ({tone})" if tone else ""
            lines.append(f"{prefix}{text}{suffix}".strip())
            continue
        line = str(item).strip()
        if line:
            lines.append(line)
    return lines


def strip_director_overwrites_from_structured_output(
    structured: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Remove immutable director fields from model structured output
    (§3.6).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        structured: ``structured`` (dict[str, Any] |
            None); meaning follows the type and call sites.
    
    Returns:
        tuple[dict[str, Any] | None, list[dict[str, Any]]]:
            Returns a value of type ``tuple[dict[str, Any] | None,
            list[dict[str, Any]]]``; see the function body for structure, error paths, and sentinels.
    """
    if not structured or not isinstance(structured, dict):
        return structured, []
    markers: list[dict[str, Any]] = []
    cleaned = dict(structured)
    for key in DIRECTOR_IMMUTABLE_FIELDS:
        if key in cleaned:
            del cleaned[key]
            markers.append(
                {
                    "marker": "stripped_model_overwrite_attempt",
                    "field": key,
                    "note": "CANONICAL_TURN_CONTRACT_GOC.md §3.6 — model cannot replace director fields.",
                }
            )
    return cleaned, markers


def structured_output_to_proposed_effects(structured: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Map structured output into proposed_state_effects list.

    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.

    Args:
        structured: ``structured`` (dict[str, Any] |
            None); meaning follows the type and call sites.

    Returns:
        list[dict[str, Any]]:
            Returns a value of type ``list[dict[str, Any]]``; see the function body for structure, error paths, and sentinels.
    """
    if not structured or not isinstance(structured, dict):
        return []
    effects = []
    raw = structured.get("proposed_state_effects")
    if not isinstance(raw, list) or not raw:
        raw = structured.get("state_effects")
    if isinstance(raw, list) and raw:
        effects = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            effect = dict(item)
            desc = str(effect.get("description") or "").strip()
            if not desc:
                value = str(effect.get("value") or effect.get("text") or effect.get("summary") or "").strip()
                effect_type = str(effect.get("effect_type") or "").strip()
                target = str(effect.get("target") or "").strip()
                parts = [part for part in (effect_type, target, value) if part]
                if parts:
                    effect["description"] = ": ".join(parts)
            effects.append(effect)
        narr = narration_summary_to_plain_str(structured.get("narration_summary"))
        if not narr.strip():
            narr = narration_summary_to_plain_str(structured.get("narrative_response"))
        if narr.strip():
            effects.append(
                {
                    "effect_type": "narrative_projection",
                    "description": narr.strip()[:4096],
                }
            )
    elif structured.get("effect_type") or structured.get("description"):
        effects = [
            {
                "effect_type": structured.get("effect_type", "narrative_beat"),
                "description": str(structured.get("description", "")),
            }
        ]
    else:
        narr = narration_summary_to_plain_str(structured.get("narration_summary"))
        if not narr.strip():
            narr = narration_summary_to_plain_str(structured.get("narrative_response"))
        if narr.strip():
            effects = [
                {
                    "effect_type": "narrative_proposal",
                    "description": narr.strip()[:4096],
                }
            ]

    if effects:
        semantic_meta = {}
        for key in ("responder_id", "function_type", "social_outcome", "dramatic_direction"):
            if structured.get(key):
                semantic_meta[key] = structured[key]
        if structured.get("emotional_shift") and isinstance(structured["emotional_shift"], dict):
            semantic_meta["emotional_shift"] = structured["emotional_shift"]
        spoken_count = len([x for x in structured.get("spoken_lines") or [] if isinstance(x, dict)])
        action_count = len([x for x in structured.get("action_lines") or [] if isinstance(x, dict)])
        if spoken_count or action_count:
            semantic_meta["actor_lane_count"] = spoken_count + action_count
        if semantic_meta:
            effects[-1].update(semantic_meta)

    return effects


def _check_human_actor_violations(
    structured: dict[str, Any],
    ai_forbidden_actor_ids: set[str],
    human_actor_id: str,
) -> dict[str, Any] | None:
    """Scan structured AI output for human-actor boundary violations.

    Returns a rejection dict if the human actor appears in spoken_lines,
    action_lines, emotional_shift, or responder nominations. Returns None
    if no violation is found.

    Error codes produced: ai_controlled_human_actor, human_actor_selected_as_responder.
    """
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

    # spoken_lines
    for item in (structured.get("spoken_lines") or []):
        if not isinstance(item, dict):
            continue
        sid = str(item.get("speaker_id") or "").strip()
        if _forbidden(sid):
            return _rejection(sid, "actor_line")

    # action_lines
    for item in (structured.get("action_lines") or []):
        if not isinstance(item, dict):
            continue
        aid = str(item.get("actor_id") or "").strip()
        if _forbidden(aid):
            return _rejection(aid, "actor_action")

    # emotional_shift targeting human actor
    emotional_shift = structured.get("emotional_shift")
    if isinstance(emotional_shift, dict):
        for key in ("actor_id", "target_actor_id"):
            eid = str(emotional_shift.get(key) or "").strip()
            if eid and _forbidden(eid):
                return _rejection(eid, "emotional_state")

    # primary responder
    primary = str(
        structured.get("primary_responder_id") or structured.get("responder_id") or ""
    ).strip()
    if primary and _forbidden(primary):
        return _rejection(primary, "responder_nomination")

    # secondary responders
    for sid in (structured.get("secondary_responder_ids") or []):
        if not isinstance(sid, str):
            continue
        sid = sid.strip()
        if sid and _forbidden(sid):
            return _rejection(sid, "responder_nomination")

    return None


# Default when ``story_runtime_experience`` is absent (operator DB / resolved config).
GOC_NPC_LANE_TEXT_CHAR_CAP_DEFAULT = 1200


def _resolved_npc_lane_char_cap(story_runtime_experience: dict[str, Any] | None) -> int:
    """Effective cap for NPC ``spoken_lines`` / ``action_lines`` rows from governed experience."""
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
    """Heuristic diagnostic: NPC ``spoken_lines`` echo long physical player input (PLAYER-ACTION-INTENT-01)."""
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
    """Reject a single NPC lane row that exceeds the operator-configured character cap.

    Narrator prose is not evaluated here (``narration_summary`` / narrator blocks may be
    longer). Runs only for god_of_carnage after caller checks module_id.
    """
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
) -> dict[str, Any]:
    """Emit validation_outcome — no player text
    (CANONICAL_TURN_CONTRACT_GOC.md §2.1).

    actor_lane_context (MVP2): optional dict with human_actor_id and
    ai_forbidden_actor_ids. When provided, actor-lane enforcement runs
    BEFORE the dramatic-effect gate. Rejects AI output that speaks, acts,
    emotes, or nominates the selected human actor.

    Error codes: ai_controlled_human_actor, human_actor_selected_as_responder,
    actor_lane_text_exceeds_transcript_beat (NPC lanes only; cap from story_runtime_experience).
    """
    # MVP2: Actor-lane enforcement runs before dramatic-effect gate and before commit.
    if actor_lane_context and isinstance(actor_lane_context, dict):
        ai_forbidden: set[str] = set()
        for raw_actor_id in (actor_lane_context.get("ai_forbidden_actor_ids") or []):
            ai_forbidden.update(expand_goc_actor_id_aliases(str(raw_actor_id)))
        human_actor_id: str = str(actor_lane_context.get("human_actor_id") or "")
        ai_forbidden.update(expand_goc_actor_id_aliases(human_actor_id))
        if ai_forbidden or human_actor_id:
            gen_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
            structured_check = gen_meta.get("structured_output") if isinstance(gen_meta.get("structured_output"), dict) else {}
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
    success = generation.get("success")
    if success is False or generation.get("error"):
        return {
            "status": "rejected",
            "reason": "model_generation_failed",
            "validator_lane": "goc_rule_engine_v1",
        }
    gen_meta_pre = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured_pre = gen_meta_pre.get("structured_output") if isinstance(gen_meta_pre.get("structured_output"), dict) else {}
    intent_surface_diagnostics: dict[str, Any] = {"npc_narrated_player_action_violation": False}
    if (
        structured_pre
        and isinstance(actor_lane_context, dict)
        and module_id == GOC_MODULE_ID
    ):
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
        npc_cap = _resolved_npc_lane_char_cap(story_runtime_experience)
        shell_violation = _check_npc_spoken_action_lane_blob_cap(structured_pre, npc_char_cap=npc_cap)
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

    narr = extract_proposed_narrative_text(proposed_state_effects)
    opening_coverage: dict[str, Any] = {
        "opening_event_coverage_pass": True,
        "applicable": False,
    }
    if str(turn_input_class or "").strip().lower() == "opening":
        opening_coverage = evaluate_opening_event_coverage(
            opening_scene_sequence=opening_scene_sequence,
            text=knowledge_text or narr,
            structured_output=structured_pre,
            actor_lane_context=actor_lane_context if isinstance(actor_lane_context, dict) else None,
            scene_plan_record=scene_plan_record if isinstance(scene_plan_record, dict) else None,
            current_scene_id=current_scene_id,
        )
        if not opening_coverage.get("opening_event_coverage_pass", True):
            reason = "opening_event_coverage_failed"
            if not opening_coverage.get("handover_to_scene_phase_pass", True):
                reason = "opening_handover_to_scene_phase_mismatch"
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
            return {
                **base,
                "status": "approved",
                "reason": "action_resolution_continuity_supported",
                "dramatic_quality_gate": "effect_gate_action_resolution_override",
                "continuity_pressure_resolution": {
                    "override_applied": True,
                    "affordance_status": aff_status,
                    "action_commit_policy": commit_policy,
                },
            }
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
        return {
            **base,
            "status": "approved",
            "reason": "goc_default_validator_pass",
            "dramatic_quality_gate": "effect_gate_weak_signal",
            "dramatic_effect_weak_signal": True,
        }

    return {
        **base,
        "status": "approved",
        "reason": "goc_default_validator_pass",
        "dramatic_quality_gate": "effect_gate_pass",
        "dramatic_effect_weak_signal": False,
    }


def run_commit_seam(
    *,
    module_id: str,
    validation_outcome: dict[str, Any],
    proposed_state_effects: list[dict[str, Any]],
    candidate_deltas: list[dict[str, Any]] | None = None,
    state_delta_boundary: dict[str, Any] | None = None,
    player_action_frame: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Commit approved effects after all validation passes.

    MVP2: When candidate_deltas and state_delta_boundary are provided,
    protected-path enforcement runs here before any commit is applied.
    This is the commit-seam gate for StateDeltaBoundary.

    Error codes: protected_state_mutation_rejected, state_delta_boundary_violation.
    """
    # MVP2: Protected state mutation check runs at commit seam (before any write).
    if candidate_deltas and isinstance(candidate_deltas, list):
        protected = set(
            (state_delta_boundary or {}).get("protected_paths") or [
                "canonical_scene_order", "canonical_characters", "canonical_relationships",
                "canonical_content_truth", "canonical_props", "canonical_endings",
                "content_module_id", "selected_player_role", "human_actor_id", "actor_lanes",
            ]
        )
        for delta in candidate_deltas:
            if not isinstance(delta, dict):
                continue
            path = str(delta.get("path") or "").strip()
            for root in protected:
                if path == root or path.startswith(root + ".") or path.startswith(root + "["):
                    return {
                        "committed_effects": [],
                        "commit_applied": False,
                        "commit_lane": "goc_commit_seam_v1",
                        "state_delta_rejection": {
                            "error_code": "protected_state_mutation_rejected",
                            "path": path,
                            "protected_root": root,
                        },
                    }

    if validation_outcome.get("status") != "approved":
        return {
            "committed_effects": [],
            "commit_applied": False,
            "commit_lane": "goc_commit_seam_v1",
        }
    if module_id != GOC_MODULE_ID:
        return {
            "committed_effects": [],
            "commit_applied": False,
            "commit_lane": "goc_commit_seam_v1",
        }
    base_out: dict[str, Any] = {
        "committed_effects": list(proposed_state_effects),
        "commit_applied": bool(proposed_state_effects),
        "commit_lane": "goc_commit_seam_v1",
    }
    paf = player_action_frame if isinstance(player_action_frame, dict) else {}
    if paf and validation_outcome.get("status") == "approved":
        nested = paf.get("affordance_resolution") if isinstance(paf.get("affordance_resolution"), dict) else {}
        pol = str(nested.get("action_commit_policy") or "").strip().lower()
        aff_st = str(nested.get("affordance_status") or paf.get("affordance_status") or "").strip().lower()
        verb = str(paf.get("verb") or "").strip().lower()
        applied = bool(base_out["commit_applied"])
        base_out["player_action_authority"] = {
            "player_action_committed": applied and pol == "commit_action",
            "player_speech_committed": (applied and pol == "commit_speech")
            or bool(str(paf.get("speech_text") or "").strip()),
            "action_commit_status": "committed" if applied else "skipped",
            "affordance_status": aff_st,
            "verb": verb,
            "resolved_target_id": paf.get("resolved_target_id"),
            "validation_surface": paf.get("validation_surface"),
        }
    return base_out


def run_visible_render(
    *,
    module_id: str,
    committed_result: dict[str, Any],
    validation_outcome: dict[str, Any],
    generation: dict[str, Any],
    transition_pattern: str,
    live_player_truth_surface: bool = False,
    render_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Build visible_output_bundle aligned with committed truth
    (§2.2–§2.3).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        module_id: ``module_id`` (str); meaning follows the type and call sites.
        committed_result: ``committed_result`` (dict[str,
            Any]); meaning follows the type and call sites.
        validation_outcome: ``validation_outcome`` (dict[str, Any]); meaning follows the type and call sites.
        generation: ``generation`` (dict[str, Any]); meaning follows the type and call sites.
        transition_pattern: ``transition_pattern`` (str); meaning follows the type and call sites.
        render_context: ``render_context`` (dict[str,
            Any] | None); meaning follows the type and call sites.
        live_player_truth_surface: When true, never emit preview-safe placeholder lines for live player execution.
    
    Returns:
        tuple[dict[str, Any], list[str]]:
            Returns a value of type ``tuple[dict[str, Any], list[str]]``; see the function body for structure, error paths, and sentinels.
    """
    _ = transition_pattern  # reserved for future bundle tone selection
    content = str(generation.get("content") or generation.get("text") or "").strip()
    if not content and isinstance(generation.get("metadata"), dict):
        meta = generation["metadata"]
        if isinstance(meta.get("raw_content"), str):
            content = meta["raw_content"].strip()

    if content:
        content = _gm_display_text_from_generation_content(content)
    generation_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured_source = generation_meta.get("structured_output") if isinstance(generation_meta.get("structured_output"), dict) else {}
    structured: dict[str, Any] = dict(structured_source) if structured_source else {}
    rc = render_context if isinstance(render_context, dict) else {}
    human_actor_id = str(rc.get("human_actor_id") or "").strip() or None
    selected_player_role = str(rc.get("selected_player_role") or "").strip() or None
    spoken_human_drops = 0
    action_human_drops = 0
    if module_id == GOC_MODULE_ID and structured and (human_actor_id or selected_player_role):
        filtered_spoken, spoken_human_drops = _goc_structured_rows_filtered_for_human_lane(
            structured.get("spoken_lines"),
            human_actor_id=human_actor_id,
            selected_player_role=selected_player_role,
            actor_key="speaker_id",
        )
        structured["spoken_lines"] = filtered_spoken
        filtered_action, action_human_drops = _goc_structured_rows_filtered_for_human_lane(
            structured.get("action_lines"),
            human_actor_id=human_actor_id,
            selected_player_role=selected_player_role,
            actor_key="actor_id",
        )
        structured["action_lines"] = filtered_action

    # Gate actor lanes on actor_lane_validation status
    actor_lane_validation = validation_outcome.get("actor_lane_validation") if isinstance(validation_outcome, dict) else None
    actor_lanes_rejected = False
    if isinstance(actor_lane_validation, dict) and actor_lane_validation.get("status") == "rejected":
        actor_lanes_rejected = True

    # Always render structured actor lines as strings (for vitality/player visibility)
    # Even if actor_lane_validation rejected them, the rendered text itself is still valid
    structured_spoken_lines = _coerce_actor_lines(structured.get("spoken_lines"), actor_key="speaker_id")
    structured_action_lines = _coerce_actor_lines(structured.get("action_lines"), actor_key="actor_id")

    markers: list[str] = []
    if module_id == GOC_MODULE_ID:
        markers.extend(
            goc_spoken_lines_multi_speaker_row_markers(
                structured,
                runtime_projection=rc.get("runtime_projection")
                if isinstance(rc.get("runtime_projection"), dict)
                else None,
            )
        )
    if actor_lanes_rejected:
        markers.append("actor_lanes_validation_gated")

    # R1: Add no_actor_lane_output marker when responders selected but no structured output
    actor_lane_reason = (actor_lane_validation or {}).get("reason", "")
    if actor_lane_reason == "no_structured_actor_output_with_selected_responders":
        markers.append("no_actor_lane_output_with_selected_responders")
    approved = validation_outcome.get("status") == "approved"
    committed = committed_result.get("committed_effects") or []
    has_commit = bool(committed) and committed_result.get("commit_applied")
    pacing_mode = str(rc.get("pacing_mode") or "")
    silence_dec = rc.get("silence_brevity_decision") if isinstance(rc.get("silence_brevity_decision"), dict) else {}
    scene_id = str(rc.get("current_scene_id") or "")
    scene_guidance = rc.get("scene_guidance") if isinstance(rc.get("scene_guidance"), dict) else {}
    prop_excerpt = str(rc.get("proposed_narrative_excerpt") or "").strip()
    profile = rc.get("character_profile_snippet") if isinstance(rc.get("character_profile_snippet"), dict) else {}
    guidance_snips = rc.get("scene_guidance_snippets") if isinstance(rc.get("scene_guidance_snippets"), dict) else {}
    responder_actor_id = str(rc.get("responder_actor_id") or "").strip()
    environment_render_context = (
        rc.get("environment_render_context")
        if isinstance(rc.get("environment_render_context"), dict)
        else {}
    )

    director_surface_hints: list[dict[str, str | bool]] = []

    def attach_environment_render_support(bundle: dict[str, Any]) -> None:
        if module_id != GOC_MODULE_ID or not environment_render_context:
            return
        render_support = bundle.setdefault("render_support", {})
        if not isinstance(render_support, dict):
            render_support = {}
            bundle["render_support"] = render_support
        render_support.setdefault("projection_version", "render_support.v1")
        render_support.setdefault("player_visible", False)
        render_support["environment"] = environment_render_context
        if "environment_state_bound" not in markers:
            markers.append("environment_state_bound")

    def add_director_hint(hint_type: str, text: str, source: str) -> None:
        clean = str(text or "").strip()
        if clean:
            director_surface_hints.append(
                {
                    "hint_type": hint_type,
                    "text": clean[:280],
                    "source": source,
                    "player_visible": False,
                }
            )

    if module_id != GOC_MODULE_ID:
        bundle = {
            "gm_narration": [content] if content else [],
            "spoken_lines": structured_spoken_lines,
            "action_lines": structured_action_lines,
        }
        if actor_lanes_rejected:
            bundle["render_downgrade"] = {
                "actor_lanes": "validation_rejected",
                "reason": actor_lane_validation.get("reason") if isinstance(actor_lane_validation, dict) else None,
            }
        markers.append("non_factual_staging")
        return bundle, markers

    if has_commit and approved:
        supplement = ""
        if scene_guidance and scene_id and (
            pacing_mode == "thin_edge" or silence_dec.get("mode") == "withheld"
        ):
            supplement = thin_edge_staging_line_from_guidance(scene_guidance=scene_guidance, scene_id=scene_id)
        gm_lines: list[str] = []
        if content:
            gm_lines.append(content)
        responder_name = _GOC_ACTOR_DISPLAY_NAMES.get(responder_actor_id)
        player_rc = str(rc.get("player_input") or "").strip()
        live_human_lane = bool(human_actor_id or selected_player_role)
        # Opening dramaturgy only: do not key off ``turn_number`` here — graph state can
        # still read 0 on later turns during render; ``turn_input_class`` is authoritative.
        is_opening_turn = str(rc.get("turn_input_class") or "").strip().lower() == "opening"
        # Do not stage NPC "reacts immediately" when a bound human actor just supplied live
        # player input; that line was mis-read as NPC reaction (HUMAN-INPUT-ATTRIBUTION-01).
        # Turn-0 opening must not use this staging line (OPENING-DRAMATURGY-HANDOVER-01).
        # Graph tests without actor_lane_context keep the legacy staging line on non-opening turns.
        if (
            responder_name
            and content
            and not (player_rc and live_human_lane)
            and not is_opening_turn
        ):
            gm_lines.insert(0, f"{responder_name} reacts immediately.")
        narr_len = len(prop_excerpt) if prop_excerpt else len(content)
        used_supplement = bool(
            supplement and (narr_len < 50 or silence_dec.get("mode") == "withheld")
        )
        role = str(profile.get("formal_role") or profile.get("role") or "").strip()
        tone = str(profile.get("baseline_tone") or "").strip()
        phase_arc = str(profile.get("phase_arc_hint") or "").strip()
        ai_hint = str(guidance_snips.get("ai_guidance_hint") or "").strip()
        if used_supplement:
            add_director_hint("phase_context", supplement, "scene_guidance.narrative_context")
        if role and (silence_dec.get("mode") == "withheld" or pacing_mode in ("compressed", "multi_pressure")):
            add_director_hint("responder_role", role, "character_profile.formal_role")
        if tone and pacing_mode in ("thin_edge", "multi_pressure"):
            add_director_hint("tonal_pressure", tone, "character_profile.baseline_tone")
        if phase_arc and narr_len < 90:
            add_director_hint("character_pressure_arc", phase_arc, "character_profile.phase_arc_hint")
        if ai_hint and (narr_len < 80 or pacing_mode == "multi_pressure"):
            add_director_hint("phase_pressure_cue", ai_hint, "scene_guidance.ai_guidance")
        for authored in select_goc_director_surface_hints_for_turn(
            scene_id=scene_id,
            pacing_mode=pacing_mode,
        ):
            add_director_hint(
                str(authored.get("hint_type") or "phase_context"),
                str(authored.get("text") or ""),
                str(authored.get("source") or "hints/"),
            )
        if not gm_lines:
            gm_lines = ["The exchange shifts, and the room adjusts around it."]

        # Wave 3: Count distinct actor IDs across lanes (only non-empty, non-None, stripped strings)
        # SCOPE: multi_actor_realized marker and multi_actor_render bundle are ONLY emitted in the primary render
        # path (when has_commit=True AND approved=True). Fallback branches (non-commit, non-approved, live_truth_surface)
        # do not emit multi-actor markers. This preserves the contract that only committed, dramatically validated
        # turns can claim multi-actor realization. If future code adds multi-actor tracking elsewhere, it violates
        # this invariant and breaks the actor-lane-as-truth assumption.
        actor_ids_in_render: set[str] = set()
        spoken_items = structured.get("spoken_lines")
        if isinstance(spoken_items, list):
            for item in spoken_items:
                if isinstance(item, dict):
                    sid = str(item.get("speaker_id") or "").strip()
                    if sid:
                        actor_ids_in_render.add(sid)
        action_items = structured.get("action_lines")
        if isinstance(action_items, list):
            for item in action_items:
                if isinstance(item, dict):
                    aid = str(item.get("actor_id") or "").strip()
                    if aid:
                        actor_ids_in_render.add(aid)

        bundle = {
            "gm_narration": gm_lines,
            "spoken_lines": structured_spoken_lines,
            "action_lines": structured_action_lines,
        }
        attach_environment_render_support(bundle)
        if spoken_human_drops or action_human_drops:
            render_support = bundle.setdefault("render_support", {})
            if not isinstance(render_support, dict):
                render_support = {}
                bundle["render_support"] = render_support
            render_support.setdefault("projection_version", "render_support.v1")
            render_support.setdefault("player_visible", False)
            render_support["human_lane_structured_filters"] = {
                "spoken_lines_dropped": spoken_human_drops,
                "action_lines_dropped": action_human_drops,
            }
            markers.append("generated_human_actor_output_filtered")

        # Add multi_actor_realized marker when >= 2 distinct actors in lanes (primary render path only)
        if len(actor_ids_in_render) >= 2:
            markers.append("multi_actor_realized")
            bundle["multi_actor_render"] = {
                "realized_actor_ids": sorted(actor_ids_in_render),
                "actor_count": len(actor_ids_in_render),
            }

        # Wave 3: Check sparse vitality floor for thin_edge pacing
        carry_forward_tension_notes = rc.get("carry_forward_tension_notes")
        if pacing_mode == "thin_edge" and not (structured_spoken_lines or structured_action_lines):
            if isinstance(carry_forward_tension_notes, str) and carry_forward_tension_notes.strip():
                render_support = bundle.setdefault("render_support", {})
                if not isinstance(render_support, dict):
                    render_support = {}
                    bundle["render_support"] = render_support
                render_support.setdefault("projection_version", "render_support.v1")
                render_support.setdefault("player_visible", False)
                render_support["vitality_floor_warning"] = "thin_edge_output_empty_with_prior_tension"

        # C3.1: Add reaction order divergence marker to render_support (canonical structure)
        divergence_reason = rc.get("reaction_order_divergence")
        if divergence_reason:
            render_support = bundle.setdefault("render_support", {})
            if not isinstance(render_support, dict):
                render_support = {}
                bundle["render_support"] = render_support
            render_support.setdefault("projection_version", "render_support.v1")
            render_support.setdefault("player_visible", False)
            bundle["render_support"]["reaction_order_divergence"] = {
                "divergence": rc.get("divergence", True),
                "reason": divergence_reason,
                "preferred": rc.get("preferred_reaction_order_ids") or [],
                "realized": rc.get("realized_actor_order") or [],
                "not_realized": rc.get("not_realized_actor_ids") or [],
                "non_fatal": rc.get("non_fatal", True),
                "justified": rc.get("justified", False),
                "justification": rc.get("justification"),
            }
            markers.append("reaction_order_divergence")

        if director_surface_hints:
            render_support = bundle.setdefault("render_support", {})
            if not isinstance(render_support, dict):
                render_support = {}
                bundle["render_support"] = render_support
            render_support.setdefault("projection_version", "render_support.v1")
            render_support.setdefault("player_visible", False)
            render_support["director_surface_hints"] = director_surface_hints
        if actor_lanes_rejected:
            bundle["render_downgrade"] = {
                "actor_lanes": "validation_rejected",
                "reason": actor_lane_validation.get("reason") if isinstance(actor_lane_validation, dict) else None,
            }
        markers.append("truth_aligned")
        if used_supplement:
            markers.append("bounded_ambiguity")
        return bundle, markers

    # No commit: truth-safe staging (GATE_SCORING_POLICY_GOC.md §6.3).
    if live_player_truth_surface:
        gm_lines = [content] if content else []
        bundle = {
            "gm_narration": gm_lines,
            "spoken_lines": structured_spoken_lines,
            "action_lines": structured_action_lines,
        }
        attach_environment_render_support(bundle)
        if actor_lanes_rejected:
            bundle["render_downgrade"] = {
                "actor_lanes": "validation_rejected",
                "reason": actor_lane_validation.get("reason") if isinstance(actor_lane_validation, dict) else None,
            }
        markers.append("live_truth_surface_no_preview_placeholder")
        return bundle, markers

    safe = content if content else "(Preview staging — no committed world-state change.)"
    bundle = {
        "gm_narration": [safe],
        "spoken_lines": structured_spoken_lines,
        "action_lines": structured_action_lines,
    }
    attach_environment_render_support(bundle)
    if actor_lanes_rejected:
        bundle["render_downgrade"] = {
            "actor_lanes": "validation_rejected",
            "reason": actor_lane_validation.get("reason") if isinstance(actor_lane_validation, dict) else None,
        }
    markers.append("non_factual_staging")
    return bundle, markers


def build_diagnostics_refs(
    *,
    graph_diagnostics: dict[str, Any],
    experiment_preview: bool,
    transition_pattern: str,
    gate_hints: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Project operational diagnostics into canonical refs
    (CANONICAL_TURN_CONTRACT_GOC.md §5).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        graph_diagnostics: ``graph_diagnostics`` (dict[str, Any]); meaning follows the type and call sites.
        experiment_preview: ``experiment_preview`` (bool); meaning follows the type and call sites.
        transition_pattern: ``transition_pattern`` (str); meaning follows the type and call sites.
        gate_hints: ``gate_hints`` (dict[str, Any] |
            None); meaning follows the type and call sites.
    
    Returns:
        list[dict[str, Any]]:
            Returns a value of type ``list[dict[str, Any]]``; see the function body for structure, error paths, and sentinels.
    """
    tp = assert_transition_pattern(transition_pattern)
    refs: list[dict[str, Any]] = [
        {
            "ref_type": "graph_diagnostics_projection",
            "graph_name": graph_diagnostics.get("graph_name"),
            "graph_version": graph_diagnostics.get("graph_version"),
            "nodes_executed": graph_diagnostics.get("nodes_executed"),
            "node_outcomes": graph_diagnostics.get("node_outcomes"),
            "fallback_path_taken": graph_diagnostics.get("fallback_path_taken"),
            "execution_health": graph_diagnostics.get("execution_health"),
        },
        {
            "ref_type": "experiment_preview",
            "experiment_preview": experiment_preview,
        },
        {
            "ref_type": "transition_pattern",
            "transition_pattern": tp,
        },
    ]
    if gate_hints:
        refs.append({"ref_type": "gate_review_hints", **gate_hints})
    return refs


def repro_metadata_complete(repro: dict[str, Any]) -> bool:
    """GATE_SCORING_POLICY_GOC.md §5.2 — required fields for operator
    questions.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        repro: ``repro`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    required = (
        "graph_name",
        "trace_id",
        "selected_model",
        "selected_provider",
        "retrieval_domain",
        "retrieval_profile",
        "model_attempted",
        "model_success",
        "adapter_invocation_mode",
        "graph_path_summary",
    )
    return all(repro.get(k) not in (None, "") for k in required)


def _project_turn_basis_field_str(
    state: dict[str, Any],
    key: str,
    *,
    expected_source: str,
) -> str | dict[str, Any]:
    """Describe what ``_project_turn_basis_field_str`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (dict[str, Any]); meaning follows the type and call sites.
        key: ``key`` (str); meaning follows the type and call sites.
        expected_source: ``expected_source`` (str); meaning follows the type and call sites.
    
    Returns:
        str | dict[str, Any]:
            Returns a value of type ``str | dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    raw = state.get(key)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return goc_uninitialized_field_envelope(
        setter_surface=SETTER_SURFACE_RUNTIME_HOST_SESSION,
        expected_source=expected_source,
    )


def _project_turn_number(state: dict[str, Any]) -> int | dict[str, Any]:
    """``_project_turn_number`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        int | dict[str, Any]:
            Returns a value of type ``int | dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    tn = state.get("turn_number")
    if isinstance(tn, int) and tn >= 0:
        return tn
    return goc_uninitialized_field_envelope(
        setter_surface=SETTER_SURFACE_RUNTIME_HOST_SESSION,
        expected_source="RuntimeTurnGraphExecutor.run(..., turn_number=<int>) or session store turn counter",
    )


def build_roadmap_dramatic_turn_record(state: dict[str, Any]) -> dict[str, Any]:
    """Roadmap §6.3 six-block projection — read-only aggregate from
    ``RuntimeTurnState`` (single truth surface).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    gd = state.get("graph_diagnostics") if isinstance(state.get("graph_diagnostics"), dict) else {}
    nodes = gd.get("nodes_executed") if isinstance(gd.get("nodes_executed"), list) else []
    routing = state.get("routing") if isinstance(state.get("routing"), dict) else {}
    retrieval = state.get("retrieval") if isinstance(state.get("retrieval"), dict) else {}
    validation = state.get("validation_outcome") if isinstance(state.get("validation_outcome"), dict) else {}
    committed = state.get("committed_result") if isinstance(state.get("committed_result"), dict) else {}
    generation = state.get("generation") if isinstance(state.get("generation"), dict) else {}
    gen_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    vis = state.get("visibility_class_markers") if isinstance(state.get("visibility_class_markers"), list) else []

    turn_basis: dict[str, Any] = {
        "turn_id": _project_turn_basis_field_str(
            state,
            "turn_id",
            expected_source="RuntimeTurnGraphExecutor.run(..., turn_id=<str>) or host-supplied stable turn id",
        ),
        "session_id": _project_turn_basis_field_str(
            state,
            "session_id",
            expected_source="RuntimeTurnGraphExecutor.run(..., session_id=<str>)",
        ),
        "turn_number": _project_turn_number(state),
        "timestamp": _project_turn_basis_field_str(
            state,
            "turn_timestamp_iso",
            expected_source="RuntimeTurnGraphExecutor.run(..., turn_timestamp_iso=<iso8601>)",
        ),
        "initiator_type": _project_turn_basis_field_str(
            state,
            "turn_initiator_type",
            expected_source="RuntimeTurnGraphExecutor.run(..., turn_initiator_type=<str>)",
        ),
        "input_class": _project_turn_basis_field_str(
            state,
            "turn_input_class",
            expected_source="Derived from interpreted_input.kind unless overridden via run(..., turn_input_class=)",
        ),
        "execution_mode": _project_turn_basis_field_str(
            state,
            "turn_execution_mode",
            expected_source="RuntimeTurnGraphExecutor.run(..., turn_execution_mode=<str>)",
        ),
    }

    decision_boundary_records: list[dict[str, Any]] = []
    for node_name in nodes:
        if not isinstance(node_name, str):
            continue
        decision_boundary_records.append(
            {
                "decision_name": node_name,
                "decision_class": "runtime_graph_node",
                "owner_layer": "ai_stack.langgraph_runtime",
                "input_seam_ref": f"state_before:{node_name}",
                "chosen_path": node_name,
                "validation_result": str((state.get("node_outcomes") or {}).get(node_name) or "ok"),
                "failure_seam_used": "",
                "notes_code": "graph_trace_only",
            }
        )

    routing_record: dict[str, Any] = {
        "route_mode": routing.get("route_mode"),
        "route_reason": routing.get("route_reason_code") or routing.get("reason"),
        "fallback_chain": routing.get("fallback_chain"),
        "fallback_stage_reached": routing.get("fallback_stage_reached"),
        "policy_id_used": routing.get("policy_id_used"),
        "policy_version_used": routing.get("policy_version_used"),
        "selected_model": routing.get("selected_model"),
        "selected_provider": routing.get("selected_provider"),
    }

    gov = retrieval.get("retrieval_governance_summary") if isinstance(retrieval.get("retrieval_governance_summary"), dict) else {}
    retrieval_record: dict[str, Any] = {
        "retrieval_used": bool(retrieval.get("hit_count")) or retrieval.get("status") not in (None, "", "empty"),
        "retrieval_domain": retrieval.get("domain"),
        "retrieval_lane": retrieval.get("profile") or retrieval.get("retrieval_route"),
        "retrieval_visibility_class": gov.get("dominant_visibility_class"),
        "authored_truth_refs": list(gov.get("authored_truth_refs") or []),
        "derived_artifact_refs": list(gov.get("derived_artifact_refs") or []),
        "retrieval_governance_result": gov,
    }
    continuity_query_signal = retrieval.get("continuity_query_signal")
    if isinstance(continuity_query_signal, dict):
        retrieval_record["continuity_query_signal"] = continuity_query_signal

    responders = state.get("selected_responder_set") if isinstance(state.get("selected_responder_set"), list) else []
    primary = responders[0] if responders and isinstance(responders[0], dict) else {}
    realization_record: dict[str, Any] = {
        "selected_responder": primary.get("actor_id"),
        "selected_scene_function": state.get("selected_scene_function"),
        "selected_pacing_label": state.get("pacing_mode"),
        "visibility_class": vis[0] if vis else None,
        "realization_mode": gen_meta.get("adapter_invocation_mode"),
        "degraded_wording_used": bool(generation.get("fallback_used")),
        "safe_wording_fallback_used": bool(generation.get("fallback_used")),
    }

    failure_list = state.get("failure_markers") if isinstance(state.get("failure_markers"), list) else []
    outcome_record: dict[str, Any] = {
        "commit_outcome": "applied" if committed.get("commit_applied") else "not_applied",
        "guard_outcomes": [m for m in failure_list if isinstance(m, dict)],
        "rejected_reasons": [validation.get("reason")] if validation.get("status") == "rejected" else [],
        "continuity_aftereffects": state.get("continuity_impacts"),
        "player_visible_response_class": vis,
    }

    return {
        "turn_basis": turn_basis,
        "decision_boundary_records": decision_boundary_records,
        "routing_record": routing_record,
        "retrieval_record": retrieval_record,
        "realization_record": realization_record,
        "outcome_record": outcome_record,
    }


def build_operator_canonical_turn_record(state: dict[str, Any]) -> dict[str, Any]:
    """Single JSON-serializable operator view over post-`package_output`
    state (CANONICAL_TURN_CONTRACT_GOC.md §8).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    gd = state.get("graph_diagnostics") if isinstance(state.get("graph_diagnostics"), dict) else {}
    repro = gd.get("repro_metadata") if isinstance(gd.get("repro_metadata"), dict) else {}
    interpreted_input = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
    validation_outcome = state.get("validation_outcome") if isinstance(state.get("validation_outcome"), dict) else {}
    intent_surface_diag = (
        validation_outcome.get("intent_surface_diagnostics")
        if isinstance(validation_outcome.get("intent_surface_diagnostics"), dict)
        else {}
    )
    return {
        "turn_metadata": {
            "session_id": state.get("session_id"),
            "trace_id": state.get("trace_id"),
            "module_id": state.get("module_id"),
            "current_scene_id": state.get("current_scene_id"),
            "turn_id": state.get("turn_id"),
            "turn_number": state.get("turn_number"),
            "turn_timestamp_iso": state.get("turn_timestamp_iso"),
            "turn_initiator_type": state.get("turn_initiator_type"),
            "turn_input_class": state.get("turn_input_class"),
            "turn_execution_mode": state.get("turn_execution_mode"),
        },
        "semantic_move_record": state.get("semantic_move_record"),
        "semantic_move_kind": (
            (state.get("semantic_move_record") or {}).get("move_type")
            if isinstance(state.get("semantic_move_record"), dict)
            else None
        ),
        "social_state_record": state.get("social_state_record"),
        "character_mind_records": state.get("character_mind_records"),
        "dramatic_irony_record": state.get("dramatic_irony_record"),
        "scene_plan_record": state.get("scene_plan_record"),
        "interpreted_move": state.get("interpreted_move"),
        "interpreted_input": interpreted_input or None,
        "player_action_frame": state.get("player_action_frame")
        if isinstance(state.get("player_action_frame"), dict)
        else None,
        "affordance_resolution": state.get("affordance_resolution")
        if isinstance(state.get("affordance_resolution"), dict)
        else None,
        "scene_affordance_model": state.get("scene_affordance_model")
        if isinstance(state.get("scene_affordance_model"), dict)
        else None,
        "player_local_context": state.get("player_local_context")
        if isinstance(state.get("player_local_context"), dict)
        else None,
        "local_context_transition": state.get("local_context_transition")
        if isinstance(state.get("local_context_transition"), dict)
        else None,
        "narrator_consequence_plan": state.get("narrator_consequence_plan")
        if isinstance(state.get("narrator_consequence_plan"), dict)
        else None,
        "player_input_kind": interpreted_input.get("player_input_kind") if interpreted_input else None,
        "player_action_committed": bool(interpreted_input.get("player_action_committed")) if interpreted_input else False,
        "player_speech_committed": bool(interpreted_input.get("player_speech_committed")) if interpreted_input else False,
        "narrator_response_expected": bool(interpreted_input.get("narrator_response_expected")) if interpreted_input else False,
        "npc_response_expected": bool(interpreted_input.get("npc_response_expected")) if interpreted_input else False,
        "scene_director_selection_source": (
            ((state.get("scene_assessment") or {}).get("multi_pressure_resolution") or {}).get("selection_source")
            if isinstance(state.get("scene_assessment"), dict)
            else None
        ),
        "planner_rationale_codes": (
            (state.get("scene_plan_record") or {}).get("planner_rationale_codes")
            if isinstance(state.get("scene_plan_record"), dict)
            else None
        ),
        "legacy_keyword_scene_candidates_used": (
            bool(
                (((state.get("scene_assessment") or {}).get("multi_pressure_resolution") or {}).get(
                    "legacy_keyword_scene_candidates_used"
                ))
            )
            if isinstance(state.get("scene_assessment"), dict)
            else False
        ),
        "intent_surface_diagnostics": intent_surface_diag or None,
        "npc_narrated_player_action_violation": bool(intent_surface_diag.get("npc_narrated_player_action_violation")),
        "scene_assessment": state.get("scene_assessment"),
        "selected_responder_set": state.get("selected_responder_set"),
        "selected_scene_function": state.get("selected_scene_function"),
        "pacing_mode": state.get("pacing_mode"),
        "silence_brevity_decision": state.get("silence_brevity_decision"),
        "proposed_state_effects": state.get("proposed_state_effects"),
        "validation_outcome": state.get("validation_outcome"),
        "dramatic_effect_outcome": state.get("dramatic_effect_outcome"),
        "committed_result": state.get("committed_result"),
        "visible_output_bundle": state.get("visible_output_bundle"),
        "continuity_impacts": state.get("continuity_impacts"),
        "visibility_class_markers": state.get("visibility_class_markers"),
        "failure_markers": state.get("failure_markers"),
        "fallback_markers": state.get("fallback_markers"),
        "quality_class": state.get("quality_class"),
        "degradation_signals": state.get("degradation_signals"),
        "degradation_summary": state.get("degradation_summary"),
        "diagnostics_refs": state.get("diagnostics_refs"),
        "experiment_preview": state.get("experiment_preview"),
        "transition_pattern": state.get("transition_pattern"),
        "routing": state.get("routing"),
        "dramatic_turn_record": build_roadmap_dramatic_turn_record(state),
        # WS-5: Actor-survival telemetry for operator diagnostics
        "actor_survival_telemetry": state.get("actor_survival_telemetry"),
        "vitality_telemetry_v1": (
            ((state.get("actor_survival_telemetry") or {}).get("vitality_telemetry_v1"))
            if isinstance(state.get("actor_survival_telemetry"), dict)
            else None
        ),
        "graph_diagnostics_summary": {
            "graph_name": gd.get("graph_name"),
            "graph_version": gd.get("graph_version"),
            "nodes_executed": gd.get("nodes_executed"),
            "node_outcomes": gd.get("node_outcomes"),
            "execution_health": gd.get("execution_health"),
            "fallback_path_taken": gd.get("fallback_path_taken"),
            "repro_complete": repro.get("repro_complete"),
        },
    }


_SCENE_FN_TO_CONTINUITY_PRIMARY: dict[str, str] = {
    "reveal_surface": "revealed_fact",
    "redirect_blame": "blame_pressure",
    "escalate_conflict": "situational_pressure",
    "repair_or_stabilize": "repair_attempt",
    "probe_motive": "situational_pressure",
    "establish_pressure": "situational_pressure",
    "withhold_or_evade": "silent_carry",
    "scene_pivot": "refused_cooperation",
}


def build_goc_continuity_impacts_on_commit(
    *,
    module_id: str,
    selected_scene_function: str,
    proposed_state_effects: list[dict[str, Any]],
    social_outcome: str | None = None,
    emotional_shift: dict[str, Any] | None = None,
    dramatic_direction: str | None = None,
) -> list[dict[str, Any]]:
    """Emit one or more frozen continuity classes after a successful commit
    (bounded, YAML-vocabulary aligned).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        module_id: ``module_id`` (str); meaning follows the type and call sites.
        selected_scene_function: ``selected_scene_function`` (str); meaning follows the type and call sites.
        proposed_state_effects: ``proposed_state_effects`` (list[dict[str, Any]]); meaning follows the type and call sites.
    
    Returns:
        list[dict[str, Any]]:
            Returns a value of type ``list[dict[str, Any]]``; see the function body for structure, error paths, and sentinels.
    """
    if module_id != GOC_MODULE_ID:
        return []
    primary = _SCENE_FN_TO_CONTINUITY_PRIMARY.get(selected_scene_function)
    if not primary:
        primary = "situational_pressure"
    impacts: list[dict[str, Any]] = [
        {"class": primary, "note": f"committed_scene_function:{selected_scene_function}"},
    ]

    # Model-driven continuity classification (higher precision than keyword scanning)
    _SOCIAL_OUTCOME_TO_CLASS = {
        "alliance_possible": "alliance_shift",
        "alliance_shift": "alliance_shift",
        "conflict_escalation": "tension_escalation",
        "conflict_resolution": "repair_attempt",
        "tension_escalates": "tension_escalation",
        "tension_escalation": "tension_escalation",
        "dignity_injury": "dignity_injury",
        "blame_shift": "blame_pressure",
        "repair_attempt": "repair_attempt",
    }
    if social_outcome:
        mapped = _SOCIAL_OUTCOME_TO_CLASS.get(social_outcome.lower().strip())
        if mapped and mapped != primary and len(impacts) < 2:
            impacts.append({"class": mapped, "note": f"model_social_outcome:{social_outcome}"})
    if dramatic_direction in ("escalate",) and len(impacts) < 2:
        impacts.append({"class": "tension_escalation", "note": "model_dramatic_direction:escalate"})
    elif dramatic_direction in ("defuse", "calm") and len(impacts) < 2:
        impacts.append({"class": "repair_attempt", "note": f"model_dramatic_direction:{dramatic_direction}"})

    blob = " ".join(
        str(e.get("description", "")) for e in proposed_state_effects if isinstance(e, dict)
    ).lower()
    secondary_candidates: list[dict[str, str]] = []
    if (
        "side with" in blob
        or "sides with" in blob
        or "allied" in blob
        or "against his wife" in blob
        or "against her husband" in blob
    ) and primary != "alliance_shift":
        secondary_candidates.append({"class": "alliance_shift", "note": "effect_text_alliance_shift_keyword"})
    if (
        "humiliat" in blob
        or "embarrass" in blob
        or "ashamed" in blob
        or "ridicule" in blob
        or "mocked" in blob
    ) and primary != "dignity_injury":
        secondary_candidates.append({"class": "dignity_injury", "note": "effect_text_dignity_keyword"})
    if "blame" in blob and primary != "blame_pressure":
        secondary_candidates.append({"class": "blame_pressure", "note": "effect_text_blame_keyword"})
    if ("sorry" in blob or "apolog" in blob) and primary != "repair_attempt":
        secondary_candidates.append({"class": "repair_attempt", "note": "effect_text_repair_keyword"})
    if ("silent" in blob or "say nothing" in blob) and primary != "silent_carry":
        secondary_candidates.append({"class": "silent_carry", "note": "effect_text_silence_keyword"})

    # Keep bounded carry-forward while preferring stronger relational signals first.
    for candidate in secondary_candidates:
        if candidate["class"] not in {x["class"] for x in impacts}:
            impacts.append(candidate)
        if len(impacts) >= 2:
            break
    return impacts[:2]
