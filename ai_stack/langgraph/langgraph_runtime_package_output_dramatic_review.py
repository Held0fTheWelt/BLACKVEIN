"""
Dramatic review section for package_output — decomposed from *_sections
(DS-026).
"""

from __future__ import annotations

from typing import Any

from ai_stack.langgraph.langgraph_runtime_state import RuntimeTurnState


def _validation_reason_str(vo: dict[str, Any]) -> str:
    """``_validation_reason_str`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        vo: ``vo`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    return str(vo.get("reason") or "")


def _dramatic_quality_reject(reason_str: str) -> bool:
    """Describe what ``_dramatic_quality_reject`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        reason_str: ``reason_str`` (str); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return reason_str.startswith("dramatic_alignment") or reason_str.startswith("dramatic_effect_")


def _alignment_note(vo: dict[str, Any], reason_str: str, dramatic_quality_reject: bool) -> str:
    """``_alignment_note`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        vo: ``vo`` (dict[str, Any]); meaning follows the type and call sites.
        reason_str: ``reason_str`` (str); meaning follows the type and call sites.
        dramatic_quality_reject: ``dramatic_quality_reject`` (bool); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    if vo.get("status") == "rejected" and dramatic_quality_reject:
        return f"alignment_reject:{reason_str}"
    return "alignment_ok"


def _prior_continuity_impacts(state: RuntimeTurnState) -> list[Any]:
    """Describe what ``_prior_continuity_impacts`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
    
    Returns:
        list[Any]:
            Returns a value of type ``list[Any]``; see the function body for structure, error paths, and sentinels.
    """
    pci = state.get("prior_continuity_impacts")
    return pci if isinstance(pci, list) else []


def _scene_assessment_and_mpr(
    state: RuntimeTurnState,
) -> tuple[dict[str, Any], dict[str, Any], list[Any]]:
    """Describe what ``_scene_assessment_and_mpr`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
    
    Returns:
        tuple[dict[str, Any], dict[str, Any], list[Any]]:
            Returns a value of type ``tuple[dict[str, Any], dict[str, Any],
            list[Any]]``; see the function body for structure, error paths, and sentinels.
    """
    sa = state.get("scene_assessment") if isinstance(state.get("scene_assessment"), dict) else {}
    mpr = sa.get("multi_pressure_resolution") if isinstance(sa.get("multi_pressure_resolution"), dict) else {}
    ht = mpr.get("heuristic_trace") if isinstance(mpr.get("heuristic_trace"), list) else []
    return sa, mpr, ht


def _primary_responder_dict(state: RuntimeTurnState) -> dict[str, Any]:
    """``_primary_responder_dict`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    responders = state.get("selected_responder_set") if isinstance(state.get("selected_responder_set"), list) else []
    if responders and isinstance(responders[0], dict):
        return responders[0]
    return {}


def _silence_decision(state: RuntimeTurnState) -> dict[str, Any]:
    """``_silence_decision`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    s = state.get("silence_brevity_decision")
    return s if isinstance(s, dict) else {}


def _dramatic_signature(
    state: RuntimeTurnState,
    primary: dict[str, Any],
    silence: dict[str, Any],
) -> dict[str, str]:
    """``_dramatic_signature`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        primary: ``primary`` (dict[str, Any]); meaning follows the type and call sites.
        silence: ``silence`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        dict[str, str]:
            Returns a value of type ``dict[str, str]``; see the function body for structure, error paths, and sentinels.
    """
    return {
        "scene_function": str(state.get("selected_scene_function") or ""),
        "responder": str(primary.get("actor_id") or ""),
        "pacing_mode": str(state.get("pacing_mode") or ""),
        "silence_mode": str(silence.get("mode") or ""),
    }


def _current_continuity_classes(state: RuntimeTurnState) -> list[str]:
    """Describe what ``_current_continuity_classes`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
    
    Returns:
        list[str]:
            Returns a value of type ``list[str]``; see the function body for structure, error paths, and sentinels.
    """
    return [
        x.get("class")
        for x in (state.get("continuity_impacts") or [])
        if isinstance(x, dict) and x.get("class")
    ]


def _stale_pattern_and_similar_move(
    state: RuntimeTurnState,
    dramatic_signature: dict[str, str],
) -> tuple[bool, bool]:
    """Describe what ``_stale_pattern_and_similar_move`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        dramatic_signature: ``dramatic_signature`` (dict[str, str]); meaning follows the type and call sites.
    
    Returns:
        tuple[bool, bool]:
            Returns a value of type ``tuple[bool, bool]``; see the function body for structure, error paths, and sentinels.
    """
    prior_sig = state.get("prior_dramatic_signature") if isinstance(state.get("prior_dramatic_signature"), dict) else {}
    interp = state.get("interpreted_move") if isinstance(state.get("interpreted_move"), dict) else {}
    prior_intent = str(prior_sig.get("player_intent") or "")
    curr_intent = str(interp.get("player_intent") or "")
    similar_move = bool(prior_intent and curr_intent and prior_intent == curr_intent)
    stale_pattern = bool(
        prior_sig
        and prior_sig.get("scene_function") == dramatic_signature.get("scene_function")
        and prior_sig.get("responder") == dramatic_signature.get("responder")
        and similar_move
    )
    return stale_pattern, similar_move


def _quality_status(
    vo: dict[str, Any],
    dramatic_quality_reject: bool,
    state: RuntimeTurnState,
) -> str:
    """``_quality_status`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        vo: ``vo`` (dict[str, Any]); meaning follows the type and call sites.
        dramatic_quality_reject: ``dramatic_quality_reject`` (bool); meaning follows the type and call sites.
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    if vo.get("status") == "rejected" and dramatic_quality_reject:
        return "fail"
    if vo.get("status") != "approved" or "truth_aligned" not in (state.get("visibility_class_markers") or []):
        return "degraded_explainable"
    return "pass"


def _weak_run_explanation(
    *,
    run_classification: str,
    vo: dict[str, Any],
    alignment_note: str,
    state: RuntimeTurnState,
) -> str:
    """``_weak_run_explanation`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        run_classification: ``run_classification`` (str); meaning follows the type and call sites.
        vo: ``vo`` (dict[str, Any]); meaning follows the type and call sites.
        alignment_note: ``alignment_note`` (str); meaning follows the type and call sites.
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    if run_classification == "pass":
        return "none"
    return (
        f"validation_status={vo.get('status')} reason={vo.get('reason')} "
        f"alignment={alignment_note} visibility={state.get('visibility_class_markers') or []}"
    )


def _pressure_shift_detected(current_continuity: list[str], prior_ci: list[Any]) -> bool:
    """Describe what ``_pressure_shift_detected`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        current_continuity: ``current_continuity`` (list[str]); meaning follows the type and call sites.
        prior_ci: ``prior_ci`` (list[Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    prior_classes = {x.get("class") for x in prior_ci if isinstance(x, dict) and x.get("class")}
    return bool(set(current_continuity) and set(current_continuity) != prior_classes)


def _build_review_explanations(
    *,
    primary: dict[str, Any],
    mpr: dict[str, Any],
    heuristic_trace: list[Any],
    state: RuntimeTurnState,
    silence: dict[str, Any],
    prior_ci: list[Any],
    quality_status: str,
    alignment_note: str,
    current_continuity: list[str],
) -> dict[str, str]:
    """Describe what ``_build_review_explanations`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        primary: ``primary`` (dict[str, Any]); meaning follows the type and call sites.
        mpr: ``mpr`` (dict[str, Any]); meaning follows the type and call sites.
        heuristic_trace: ``heuristic_trace`` (list[Any]); meaning follows the type and call sites.
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        silence: ``silence`` (dict[str, Any]); meaning follows the type and call sites.
        prior_ci: ``prior_ci`` (list[Any]); meaning follows the type and call sites.
        quality_status: ``quality_status`` (str); meaning follows the type and call sites.
        alignment_note: ``alignment_note`` (str); meaning follows the type and call sites.
        current_continuity: ``current_continuity`` (list[str]); meaning follows the type and call sites.
    
    Returns:
        dict[str, str]:
            Returns a value of type ``dict[str, str]``; see the function body for structure, error paths, and sentinels.
    """
    return {
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
    }


def build_dramatic_review_section(state: RuntimeTurnState, vo: dict[str, Any]) -> dict[str, Any]:
    """Describe what ``build_dramatic_review_section`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        vo: ``vo`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    reason_str = _validation_reason_str(vo)
    dramatic_quality_reject = _dramatic_quality_reject(reason_str)
    alignment_note = _alignment_note(vo, reason_str, dramatic_quality_reject)
    prior_ci = _prior_continuity_impacts(state)
    _, mpr, heuristic_trace = _scene_assessment_and_mpr(state)
    primary = _primary_responder_dict(state)
    silence = _silence_decision(state)
    dramatic_signature = _dramatic_signature(state, primary, silence)
    current_continuity = _current_continuity_classes(state)
    stale_pattern, _ = _stale_pattern_and_similar_move(state, dramatic_signature)
    quality_status = _quality_status(vo, dramatic_quality_reject, state)
    run_classification = quality_status
    weak_run_explanation = _weak_run_explanation(
        run_classification=run_classification,
        vo=vo,
        alignment_note=alignment_note,
        state=state,
    )
    alliance_shift_detected = "alliance_shift" in current_continuity
    dignity_injury_detected = "dignity_injury" in current_continuity
    pressure_shift_detected = _pressure_shift_detected(current_continuity, prior_ci)

    return {
        "selected_scene_function": state.get("selected_scene_function"),
        "selected_responder": primary,
        "pacing_mode": state.get("pacing_mode"),
        "silence_brevity_decision": state.get("silence_brevity_decision"),
        "scene_energy_target": state.get("scene_energy_target"),
        "scene_energy_transition": state.get("scene_energy_transition"),
        "scene_energy_validation": state.get("scene_energy_validation"),
        "pacing_rhythm_state": state.get("pacing_rhythm_state"),
        "pacing_rhythm_target": state.get("pacing_rhythm_target"),
        "pacing_rhythm_validation": state.get("pacing_rhythm_validation"),
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
        "review_explanations": _build_review_explanations(
            primary=primary,
            mpr=mpr,
            heuristic_trace=heuristic_trace,
            state=state,
            silence=silence,
            prior_ci=prior_ci,
            quality_status=quality_status,
            alignment_note=alignment_note,
            current_continuity=current_continuity,
        ),
    }
