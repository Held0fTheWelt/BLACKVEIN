"""Proposal, validation, commit, visible seams helpers (CANONICAL_TURN_CONTRACT_GOC.md §2)."""

from __future__ import annotations

import json
from typing import Any

from ai_stack.dramatic_effect_contract import DramaticEffectEvaluationContext
from ai_stack.dramatic_effect_gate import evaluate_dramatic_effect_gate, validation_reason_for_outcome
from ai_stack.goc_dramatic_alignment import extract_proposed_narrative_text
from ai_stack.goc_field_initialization_envelope import (
    SETTER_SURFACE_RUNTIME_HOST_SESSION,
    goc_uninitialized_field_envelope,
)
from ai_stack.goc_frozen_vocab import DIRECTOR_IMMUTABLE_FIELDS, GOC_MODULE_ID, assert_transition_pattern
from ai_stack.goc_yaml_authority import thin_edge_staging_line_from_guidance


def _gm_display_text_from_generation_content(raw: str) -> str:
    """Use narrative_response for GM lines when model content is JSON (e.g. raw graph fallback)."""
    s = raw.strip()
    if s.startswith("{") and '"narrative_response"' in s:
        try:
            parsed = json.loads(s)
            if isinstance(parsed, dict):
                narr = parsed.get("narrative_response")
                if isinstance(narr, str) and narr.strip():
                    return narr.strip()
        except json.JSONDecodeError:
            pass
    return raw


def strip_director_overwrites_from_structured_output(
    structured: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Remove immutable director fields from model structured output (§3.6)."""
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
    """Map structured output into proposed_state_effects list."""
    if not structured or not isinstance(structured, dict):
        return []
    raw = structured.get("proposed_state_effects")
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if structured.get("effect_type") or structured.get("description"):
        return [
            {
                "effect_type": structured.get("effect_type", "narrative_beat"),
                "description": str(structured.get("description", "")),
            }
        ]
    narr = structured.get("narrative_response")
    if isinstance(narr, str) and narr.strip():
        return [
            {
                "effect_type": "narrative_proposal",
                "description": narr.strip()[:4096],
            }
        ]
    return []


def run_validation_seam(
    *,
    module_id: str,
    proposed_state_effects: list[dict[str, Any]],
    generation: dict[str, Any],
    evaluation_context: DramaticEffectEvaluationContext | None = None,
) -> dict[str, Any]:
    """Emit validation_outcome — no player text (CANONICAL_TURN_CONTRACT_GOC.md §2.1)."""
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
    ctx = evaluation_context
    if ctx is None:
        ctx = DramaticEffectEvaluationContext(
            module_id=module_id,
            proposed_narrative=narr,
            selected_scene_function="establish_pressure",
            pacing_mode="standard",
            silence_brevity_decision={},
        )
    elif ctx.proposed_narrative.strip() != narr.strip():
        ctx = ctx.model_copy(update={"proposed_narrative": narr})

    gate_out = evaluate_dramatic_effect_gate(ctx)
    gate_dict = gate_out.to_runtime_dict()
    base: dict[str, Any] = {
        "dramatic_effect_gate_outcome": gate_dict,
        "validator_lane": "goc_rule_engine_v1",
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
) -> dict[str, Any]:
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
    return {
        "committed_effects": list(proposed_state_effects),
        "commit_applied": bool(proposed_state_effects),
        "commit_lane": "goc_commit_seam_v1",
    }


def run_visible_render(
    *,
    module_id: str,
    committed_result: dict[str, Any],
    validation_outcome: dict[str, Any],
    generation: dict[str, Any],
    transition_pattern: str,
    render_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Build visible_output_bundle aligned with committed truth (§2.2–§2.3)."""
    _ = transition_pattern  # reserved for future bundle tone selection
    content = str(generation.get("content") or generation.get("text") or "").strip()
    if not content and isinstance(generation.get("metadata"), dict):
        meta = generation["metadata"]
        if isinstance(meta.get("raw_content"), str):
            content = meta["raw_content"].strip()

    if content:
        content = _gm_display_text_from_generation_content(content)

    markers: list[str] = []
    approved = validation_outcome.get("status") == "approved"
    committed = committed_result.get("committed_effects") or []
    has_commit = bool(committed) and committed_result.get("commit_applied")
    rc = render_context if isinstance(render_context, dict) else {}
    pacing_mode = str(rc.get("pacing_mode") or "")
    silence_dec = rc.get("silence_brevity_decision") if isinstance(rc.get("silence_brevity_decision"), dict) else {}
    scene_id = str(rc.get("current_scene_id") or "")
    scene_guidance = rc.get("scene_guidance") if isinstance(rc.get("scene_guidance"), dict) else {}
    prop_excerpt = str(rc.get("proposed_narrative_excerpt") or "").strip()
    profile = rc.get("character_profile_snippet") if isinstance(rc.get("character_profile_snippet"), dict) else {}
    guidance_snips = rc.get("scene_guidance_snippets") if isinstance(rc.get("scene_guidance_snippets"), dict) else {}
    responder_actor_id = str(rc.get("responder_actor_id") or "").strip()

    responder_name_map = {
        "veronique_vallon": "Veronique",
        "annette_reille": "Annette",
        "michel_longstreet": "Michel",
        "alain_reille": "Alain",
    }

    if module_id != GOC_MODULE_ID:
        bundle = {
            "gm_narration": [content] if content else [],
            "spoken_lines": [],
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
        responder_name = responder_name_map.get(responder_actor_id)
        if responder_name and content:
            gm_lines.insert(0, f"{responder_name} reacts immediately.")
        narr_len = len(prop_excerpt) if prop_excerpt else len(content)
        if supplement and (narr_len < 50 or silence_dec.get("mode") == "withheld"):
            gm_lines.append(f"(Director staging — phase context) {supplement}")
        role = str(profile.get("formal_role") or profile.get("role") or "").strip()
        tone = str(profile.get("baseline_tone") or "").strip()
        phase_arc = str(profile.get("phase_arc_hint") or "").strip()
        ai_hint = str(guidance_snips.get("ai_guidance_hint") or "").strip()
        if role and (silence_dec.get("mode") == "withheld" or pacing_mode in ("compressed", "multi_pressure")):
            gm_lines.append(f"(Director register — responder role) {role}")
        if tone and pacing_mode in ("thin_edge", "multi_pressure"):
            gm_lines.append(f"(Director register — tonal pressure) {tone}")
        if phase_arc and narr_len < 90:
            gm_lines.append(f"(Director staging — character pressure arc) {phase_arc}")
        if ai_hint and (narr_len < 80 or pacing_mode == "multi_pressure"):
            gm_lines.append(f"(Director staging — phase pressure cue) {ai_hint}")
        if not gm_lines:
            gm_lines = ["(scene continues — committed effects applied.)"]
        bundle = {
            "gm_narration": gm_lines,
            "spoken_lines": [],
        }
        markers.append("truth_aligned")
        used_supplement = bool(
            supplement and (narr_len < 50 or silence_dec.get("mode") == "withheld")
        )
        if used_supplement:
            markers.append("bounded_ambiguity")
        return bundle, markers

    # No commit: truth-safe staging (GATE_SCORING_POLICY_GOC.md §6.3).
    safe = content if content else "(Preview staging — no committed world-state change.)"
    bundle = {
        "gm_narration": [safe],
        "spoken_lines": [],
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
    """Project operational diagnostics into canonical refs (CANONICAL_TURN_CONTRACT_GOC.md §5)."""
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
    """GATE_SCORING_POLICY_GOC.md §5.2 — required fields for operator questions."""
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
    raw = state.get(key)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return goc_uninitialized_field_envelope(
        setter_surface=SETTER_SURFACE_RUNTIME_HOST_SESSION,
        expected_source=expected_source,
    )


def _project_turn_number(state: dict[str, Any]) -> int | dict[str, Any]:
    tn = state.get("turn_number")
    if isinstance(tn, int) and tn >= 0:
        return tn
    return goc_uninitialized_field_envelope(
        setter_surface=SETTER_SURFACE_RUNTIME_HOST_SESSION,
        expected_source="RuntimeTurnGraphExecutor.run(..., turn_number=<int>) or session store turn counter",
    )


def build_roadmap_dramatic_turn_record(state: dict[str, Any]) -> dict[str, Any]:
    """Roadmap §6.3 six-block projection — read-only aggregate from ``RuntimeTurnState`` (single truth surface)."""
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
    """Single JSON-serializable operator view over post-`package_output` state (CANONICAL_TURN_CONTRACT_GOC.md §8).

    This is a read projection only — same data as `RuntimeTurnState` + nested `graph_diagnostics`, not a second truth surface.
    """
    gd = state.get("graph_diagnostics") if isinstance(state.get("graph_diagnostics"), dict) else {}
    repro = gd.get("repro_metadata") if isinstance(gd.get("repro_metadata"), dict) else {}
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
        "social_state_record": state.get("social_state_record"),
        "character_mind_records": state.get("character_mind_records"),
        "scene_plan_record": state.get("scene_plan_record"),
        "interpreted_move": state.get("interpreted_move"),
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
        "diagnostics_refs": state.get("diagnostics_refs"),
        "experiment_preview": state.get("experiment_preview"),
        "transition_pattern": state.get("transition_pattern"),
        "routing": state.get("routing"),
        "dramatic_turn_record": build_roadmap_dramatic_turn_record(state),
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
) -> list[dict[str, Any]]:
    """Emit one or more frozen continuity classes after a successful commit (bounded, YAML-vocabulary aligned)."""
    if module_id != GOC_MODULE_ID:
        return []
    primary = _SCENE_FN_TO_CONTINUITY_PRIMARY.get(selected_scene_function)
    if not primary:
        primary = "situational_pressure"
    impacts: list[dict[str, Any]] = [
        {"class": primary, "note": f"committed_scene_function:{selected_scene_function}"},
    ]
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
