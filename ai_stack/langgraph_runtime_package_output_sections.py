"""Thematic sections for package_output (DS-037) — dramatic review and planner projection."""

from __future__ import annotations

from typing import Any

from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.langgraph_runtime_state import RuntimeTurnState


def append_goc_validation_reject_failure_marker(
    *,
    module_id: str,
    validation: dict[str, Any],
    failure_markers: list[Any],
) -> None:
    if module_id != GOC_MODULE_ID or validation.get("status") != "rejected":
        return
    if any(isinstance(m, dict) and m.get("failure_class") == "validation_reject" for m in failure_markers):
        return
    failure_markers.append(
        {
            "failure_class": "validation_reject",
            "closure_impacting": False,
            "note": "goc_validation_rejected_truth_safe_visible",
            "validation_reason": validation.get("reason"),
        }
    )


def compute_experiment_preview_for_package_output(
    *,
    state: RuntimeTurnState,
    module_id: str,
    validation: dict[str, Any],
    committed: dict[str, Any],
    failure_markers: list[Any],
) -> bool:
    experiment_preview = True
    if state.get("force_experiment_preview"):
        experiment_preview = True
    elif module_id != GOC_MODULE_ID:
        experiment_preview = True
    elif validation.get("status") == "waived":
        experiment_preview = True
    elif validation.get("status") != "approved":
        experiment_preview = True
    elif not state.get("goc_slice_active"):
        experiment_preview = True
    else:
        experiment_preview = False

    if module_id == GOC_MODULE_ID and validation.get("status") == "approved" and not committed.get("commit_applied"):
        pass

    for fm in failure_markers:
        fc = fm.get("failure_class") if isinstance(fm, dict) else None
        if fc in ("scope_breach", "graph_error"):
            experiment_preview = True

    return experiment_preview


def build_planner_state_projection(state: RuntimeTurnState) -> dict[str, Any]:
    return {
        "semantic_move_record": state.get("semantic_move_record"),
        "social_state_record": state.get("social_state_record"),
        "character_mind_records": state.get("character_mind_records"),
        "scene_plan_record": state.get("scene_plan_record"),
        "note": "Derived projection of RuntimeTurnState planner fields — not a second truth surface.",
    }


def build_dramatic_review_section(state: RuntimeTurnState, vo: dict[str, Any]) -> dict[str, Any]:
    reason_str = str(vo.get("reason") or "")
    dramatic_quality_reject = reason_str.startswith("dramatic_alignment") or reason_str.startswith(
        "dramatic_effect_"
    )
    alignment_note = "alignment_ok"
    if vo.get("status") == "rejected" and dramatic_quality_reject:
        alignment_note = f"alignment_reject:{reason_str}"
    prior_ci = state.get("prior_continuity_impacts") if isinstance(state.get("prior_continuity_impacts"), list) else []
    sa = state.get("scene_assessment") if isinstance(state.get("scene_assessment"), dict) else {}
    mpr = sa.get("multi_pressure_resolution") if isinstance(sa.get("multi_pressure_resolution"), dict) else {}
    heuristic_trace = mpr.get("heuristic_trace") if isinstance(mpr.get("heuristic_trace"), list) else []
    responders = state.get("selected_responder_set") if isinstance(state.get("selected_responder_set"), list) else []
    primary = responders[0] if responders and isinstance(responders[0], dict) else {}
    silence = state.get("silence_brevity_decision") if isinstance(state.get("silence_brevity_decision"), dict) else {}
    dramatic_signature = {
        "scene_function": str(state.get("selected_scene_function") or ""),
        "responder": str(primary.get("actor_id") or ""),
        "pacing_mode": str(state.get("pacing_mode") or ""),
        "silence_mode": str(silence.get("mode") or ""),
    }
    current_continuity = [
        x.get("class")
        for x in (state.get("continuity_impacts") or [])
        if isinstance(x, dict) and x.get("class")
    ]
    prior_sig = state.get("prior_dramatic_signature") if isinstance(state.get("prior_dramatic_signature"), dict) else {}
    similar_move = False
    interp = state.get("interpreted_move") if isinstance(state.get("interpreted_move"), dict) else {}
    prior_intent = str(prior_sig.get("player_intent") or "")
    curr_intent = str(interp.get("player_intent") or "")
    if prior_intent and curr_intent and prior_intent == curr_intent:
        similar_move = True
    stale_pattern = bool(
        prior_sig
        and prior_sig.get("scene_function") == dramatic_signature.get("scene_function")
        and prior_sig.get("responder") == dramatic_signature.get("responder")
        and similar_move
    )
    quality_status = "pass"
    if vo.get("status") == "rejected" and dramatic_quality_reject:
        quality_status = "fail"
    elif vo.get("status") != "approved" or "truth_aligned" not in (state.get("visibility_class_markers") or []):
        quality_status = "degraded_explainable"
    alliance_shift_detected = "alliance_shift" in current_continuity
    dignity_injury_detected = "dignity_injury" in current_continuity
    pressure_shift_detected = bool(
        set(current_continuity)
        and set(current_continuity)
        != set(x.get("class") for x in prior_ci if isinstance(x, dict) and x.get("class"))
    )
    run_classification = quality_status
    if quality_status == "pass":
        run_classification = "pass"
    elif quality_status == "fail":
        run_classification = "fail"
    else:
        run_classification = "degraded_explainable"
    weak_run_explanation = "none"
    if run_classification != "pass":
        weak_run_explanation = (
            f"validation_status={vo.get('status')} reason={vo.get('reason')} "
            f"alignment={alignment_note} visibility={state.get('visibility_class_markers') or []}"
        )

    return {
        "selected_scene_function": state.get("selected_scene_function"),
        "selected_responder": primary,
        "pacing_mode": state.get("pacing_mode"),
        "silence_brevity_decision": state.get("silence_brevity_decision"),
        "prior_continuity_classes": [x.get("class") for x in prior_ci if isinstance(x, dict) and x.get("class")],
        "multi_pressure_chosen": mpr.get("chosen_scene_function"),
        "multi_pressure_candidates": mpr.get("candidates"),
        "multi_pressure_rationale": mpr.get("rationale"),
        "director_heuristic_trace": [str(x) for x in heuristic_trace][:16],
        "validation_reason": vo.get("reason"),
        "dramatic_alignment_summary": alignment_note,
        "dramatic_effect_gate_outcome": state.get("dramatic_effect_outcome"),
        "dramatic_quality_gate": vo.get("dramatic_quality_gate"),
        "dramatic_effect_weak_signal": vo.get("dramatic_effect_weak_signal"),
        "dramatic_signature": dramatic_signature,
        "pattern_repetition_risk": stale_pattern,
        "pattern_repetition_note": (
            "same_scene_function_and_responder_under_similar_intent"
            if stale_pattern
            else "pattern_variation_or_intent_shift_detected"
        ),
        "dramatic_quality_status": quality_status,
        "run_classification": run_classification,
        "current_continuity_classes": current_continuity,
        "alliance_shift_detected": alliance_shift_detected,
        "dignity_injury_detected": dignity_injury_detected,
        "pressure_shift_detected": pressure_shift_detected,
        "pressure_shift_explanation": (
            "continuity_classes_changed_from_prior_run"
            if pressure_shift_detected
            else "continuity_classes_stable_or_empty"
        ),
        "weak_run_explanation": weak_run_explanation,
        "review_explanations": {
            "responder": f"selected_responder_reason:{primary.get('reason')}",
            "scene_function": str(mpr.get("rationale") or "single_path_rule"),
            "heuristics": ",".join(str(x) for x in heuristic_trace[:8]) if heuristic_trace else "none",
            "pacing": f"pacing_mode={state.get('pacing_mode')} silence_reason={silence.get('reason')}",
            "continuity": (
                "carry_forward_classes="
                + ",".join(str(x.get("class")) for x in prior_ci if isinstance(x, dict) and x.get("class"))
            )
            if prior_ci
            else "carry_forward_classes=none",
            "dramatic_quality": f"{quality_status}:{alignment_note}",
            "pressure_shift": (
                "current_continuity="
                + ",".join(str(x) for x in current_continuity)
                + ";prior_continuity="
                + ",".join(str(x.get("class")) for x in prior_ci if isinstance(x, dict) and x.get("class"))
            ),
        },
    }
