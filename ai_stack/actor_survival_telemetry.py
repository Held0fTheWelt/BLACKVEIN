"""Actor-survival telemetry: canonical vitality telemetry + compatibility surfaces.

Phase 5 hardens telemetry around a fixed, versioned schema so operators can
answer why a turn felt passive using diagnostics alone.
"""

from __future__ import annotations

from typing import Any

from ai_stack.runtime_turn_contracts import (
    DEGRADATION_SIGNAL_DEGRADED_COMMIT,
    DEGRADATION_SIGNAL_FALLBACK_USED,
    DEGRADATION_SIGNAL_RETRY_EXHAUSTED,
    PASSIVITY_DIAGNOSIS_REQUIRED_FIELDS,
    PASSIVITY_DIAGNOSIS_SCHEMA_VERSION,
    VITALITY_TELEMETRY_REQUIRED_FIELDS,
    VITALITY_TELEMETRY_SCHEMA_VERSION,
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe_strings(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if cleaned and cleaned not in out:
            out.append(cleaned)
    return out


def _coerce_dict_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _actor_id_from_rendered_item(item: Any) -> str:
    if isinstance(item, dict):
        return _clean_text(item.get("speaker_id") or item.get("actor_id"))
    text = _clean_text(item)
    if ":" in text:
        candidate = _clean_text(text.split(":", 1)[0])
        if candidate and " " not in candidate:
            return candidate
    return ""


def _collect_actor_ids_from_rows(rows: list[dict[str, Any]], *, speaker_key: str, actor_key: str) -> list[str]:
    ids: list[str] = []
    for row in rows:
        actor_id = _clean_text(row.get(speaker_key) or row.get(actor_key))
        if actor_id and actor_id not in ids:
            ids.append(actor_id)
    return ids


def _collect_rendered_actor_ids(spoken: list[Any], action: list[Any]) -> list[str]:
    ids: list[str] = []
    for row in list(spoken) + list(action):
        actor_id = _actor_id_from_rendered_item(row)
        if actor_id and actor_id not in ids:
            ids.append(actor_id)
    return ids


def _extract_initiative_summary(
    *,
    state: dict[str, Any],
    generated_initiative_rows: list[dict[str, Any]],
    validated_initiative_rows: list[dict[str, Any]],
    selected_primary_responder_id: str | None,
) -> tuple[int, int, str | None, str | None, str | None]:
    generated_count = len(generated_initiative_rows)
    preserved_count = len(validated_initiative_rows)

    initiative_seizer_id = _clean_text(state.get("initiative_seizer_id")) or None
    initiative_loser_id = _clean_text(state.get("initiative_loser_id")) or None
    initiative_pressure_label = _clean_text(state.get("initiative_pressure_label")) or None

    if initiative_seizer_id or initiative_loser_id or initiative_pressure_label:
        return (
            generated_count,
            preserved_count,
            initiative_seizer_id,
            initiative_loser_id,
            initiative_pressure_label,
        )

    event_types: list[str] = []
    for event in validated_initiative_rows:
        event_type = _clean_text(event.get("type")).lower()
        if event_type and event_type not in event_types:
            event_types.append(event_type)
        if initiative_seizer_id is None and event_type in {"seize", "counter", "interrupt"}:
            actor_id = _clean_text(event.get("actor_id"))
            if actor_id:
                initiative_seizer_id = actor_id
        if initiative_loser_id is None and event_type in {"counter", "interrupt"}:
            target_id = _clean_text(event.get("target_id"))
            if target_id:
                initiative_loser_id = target_id

    if initiative_loser_id is None and initiative_seizer_id and selected_primary_responder_id and initiative_seizer_id != selected_primary_responder_id:
        initiative_loser_id = selected_primary_responder_id

    if "interrupt" in event_types or "counter" in event_types:
        initiative_pressure_label = "contested"
    elif "seize" in event_types:
        initiative_pressure_label = "floor_claimed"

    return (
        generated_count,
        preserved_count,
        initiative_seizer_id,
        initiative_loser_id,
        initiative_pressure_label,
    )


def _has_prior_tension(state: dict[str, Any]) -> bool:
    prior_planner = state.get("prior_planner_truth") if isinstance(state.get("prior_planner_truth"), dict) else {}
    carry_forward = _clean_text(prior_planner.get("carry_forward_tension_notes"))
    social_shift = _clean_text(prior_planner.get("social_pressure_shift")).lower()
    return bool(carry_forward or social_shift in {"escalated", "contested"})


def _preferred_reaction_order_ids(responders: list[Any]) -> list[str]:
    """Stable actor order from ``selected_responder_set`` using ``preferred_reaction_order``."""
    scored: list[tuple[int, str]] = []
    for row in responders:
        if not isinstance(row, dict):
            continue
        actor_id = _clean_text(row.get("actor_id") or row.get("responder_id"))
        if not actor_id:
            continue
        try:
            seq = int(row.get("preferred_reaction_order"))
        except (TypeError, ValueError):
            seq = 999
        scored.append((seq, actor_id))
    scored.sort(key=lambda item: item[0])
    ordered: list[str] = []
    for _, actor_id in scored:
        if actor_id not in ordered:
            ordered.append(actor_id)
    return ordered


def _is_sparse_input(state: dict[str, Any]) -> bool:
    raw_input = _clean_text(state.get("raw_input"))
    if raw_input and (len(raw_input) <= 3 or len(raw_input.split()) <= 1):
        return True

    interpreted_input = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
    semantic_move = state.get("semantic_move_record") if isinstance(state.get("semantic_move_record"), dict) else {}

    kinds = {
        _clean_text(interpreted_input.get("kind")).lower(),
        _clean_text(interpreted_input.get("mode")).lower(),
        _clean_text(interpreted_input.get("move_type")).lower(),
        _clean_text(semantic_move.get("move_type")).lower(),
    }
    sparse_markers = {
        "silence",
        "silence_withdrawal",
        "refusal",
        "withhold_or_evade",
        "evasive",
        "brevity",
        "brief",
        "awkward_brevity",
    }
    return any(marker in kinds for marker in sparse_markers)


def _build_vitality_telemetry_v1(
    state: dict[str, Any],
    *,
    generation_ok: bool,
    validation_ok: bool,
    commit_applied: bool,
    fallback_taken: bool,
) -> dict[str, Any]:
    responders = state.get("selected_responder_set") if isinstance(state.get("selected_responder_set"), list) else []

    selected_primary_responder_id = _clean_text(state.get("responder_id"))
    if not selected_primary_responder_id:
        for row in responders:
            if not isinstance(row, dict):
                continue
            role = _clean_text(row.get("role")).lower()
            actor_id = _clean_text(row.get("actor_id") or row.get("responder_id"))
            if actor_id and role in {"primary_responder", "primary"}:
                selected_primary_responder_id = actor_id
                break
        if not selected_primary_responder_id:
            for row in responders:
                if not isinstance(row, dict):
                    continue
                actor_id = _clean_text(row.get("actor_id") or row.get("responder_id"))
                if actor_id:
                    selected_primary_responder_id = actor_id
                    break

    selected_secondary_responder_ids = _dedupe_strings(
        [
            _clean_text(row.get("actor_id") or row.get("responder_id"))
            for row in responders
            if isinstance(row, dict) and _clean_text(row.get("role")).lower() == "secondary_reactor"
        ]
        + [
            _clean_text(value)
            for value in (state.get("secondary_responder_ids") or [])
            if _clean_text(value)
        ]
    )

    generation = state.get("generation") if isinstance(state.get("generation"), dict) else {}
    generation_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    validated_structured = (
        generation_meta.get("structured_output")
        if isinstance(generation_meta.get("structured_output"), dict)
        else {}
    )

    generated_spoken_rows = _coerce_dict_rows(state.get("spoken_lines"))
    generated_action_rows = _coerce_dict_rows(state.get("action_lines"))
    generated_initiative_rows = _coerce_dict_rows(state.get("initiative_events"))

    if not generated_spoken_rows:
        generated_spoken_rows = _coerce_dict_rows(validated_structured.get("spoken_lines"))
    if not generated_action_rows:
        generated_action_rows = _coerce_dict_rows(validated_structured.get("action_lines"))
    if not generated_initiative_rows:
        generated_initiative_rows = _coerce_dict_rows(validated_structured.get("initiative_events"))

    validated_spoken_rows = _coerce_dict_rows(validated_structured.get("spoken_lines"))
    validated_action_rows = _coerce_dict_rows(validated_structured.get("action_lines"))
    validated_initiative_rows = _coerce_dict_rows(validated_structured.get("initiative_events"))

    visible_bundle = state.get("visible_output_bundle") if isinstance(state.get("visible_output_bundle"), dict) else {}
    rendered_spoken_lines = (
        list(visible_bundle.get("spoken_lines"))
        if isinstance(visible_bundle.get("spoken_lines"), list)
        else []
    )
    rendered_action_lines = (
        list(visible_bundle.get("action_lines"))
        if isinstance(visible_bundle.get("action_lines"), list)
        else []
    )

    generated_actor_ids = _collect_actor_ids_from_rows(
        generated_spoken_rows + generated_action_rows,
        speaker_key="speaker_id",
        actor_key="actor_id",
    )
    realized_actor_ids = _collect_actor_ids_from_rows(
        validated_spoken_rows + validated_action_rows,
        speaker_key="speaker_id",
        actor_key="actor_id",
    )
    rendered_actor_ids = _collect_rendered_actor_ids(rendered_spoken_lines, rendered_action_lines)

    realized_secondary_responder_ids = [
        actor_id for actor_id in selected_secondary_responder_ids if actor_id in realized_actor_ids
    ]

    (
        initiative_generated_count,
        initiative_preserved_count,
        initiative_seizer_id,
        initiative_loser_id,
        initiative_pressure_label,
    ) = _extract_initiative_summary(
        state=state,
        generated_initiative_rows=generated_initiative_rows,
        validated_initiative_rows=validated_initiative_rows,
        selected_primary_responder_id=selected_primary_responder_id or None,
    )

    pacing_mode = _clean_text(state.get("pacing_mode"))
    silence_decision = (
        state.get("silence_brevity_decision")
        if isinstance(state.get("silence_brevity_decision"), dict)
        else {}
    )
    silence_mode = _clean_text(silence_decision.get("mode") or state.get("silence_mode"))

    thin_edge_applied = pacing_mode == "thin_edge"
    withheld_applied = silence_mode == "withheld"
    compressed_applied = pacing_mode == "compressed" or silence_mode == "brief"
    prior_tension_present = _has_prior_tension(state)

    quality_class = _clean_text(state.get("quality_class")) or "healthy"
    degradation_signals = _dedupe_strings([str(signal) for signal in (state.get("degradation_signals") or [])])

    fallback_used = bool(fallback_taken or DEGRADATION_SIGNAL_FALLBACK_USED in degradation_signals)
    degraded_commit = bool(
        DEGRADATION_SIGNAL_DEGRADED_COMMIT in degradation_signals
        or (validation_ok and not commit_applied)
    )
    retry_exhausted = bool(DEGRADATION_SIGNAL_RETRY_EXHAUSTED in degradation_signals)

    rendered_spoken_line_count = len([line for line in rendered_spoken_lines if _clean_text(line)])
    rendered_action_line_count = len([line for line in rendered_action_lines if _clean_text(line)])

    response_present = bool(rendered_spoken_line_count or rendered_action_line_count)
    initiative_present = initiative_preserved_count > 0
    multi_actor_realized = len(realized_actor_ids) >= 2

    preferred_reaction_order_ids = _preferred_reaction_order_ids(responders)
    reaction_order_divergence: str | None = None
    if selected_secondary_responder_ids and response_present and not multi_actor_realized:
        reaction_order_divergence = "secondary_responder_nominated_not_realized_in_output"

    sparse_input_detected = _is_sparse_input(state)
    sparse_input_recovery_applied = bool(
        sparse_input_detected
        and response_present
        and (initiative_present or multi_actor_realized or rendered_spoken_line_count > 0)
    )

    telemetry = {
        "identity_stage": "runtime_turn_vitality_telemetry",
        "schema_version": VITALITY_TELEMETRY_SCHEMA_VERSION,
        "turn_number": state.get("turn_number"),
        "trace_id": state.get("trace_id"),
        "selected_primary_responder_id": selected_primary_responder_id or None,
        "selected_secondary_responder_ids": selected_secondary_responder_ids,
        "realized_actor_ids": realized_actor_ids,
        "realized_secondary_responder_ids": realized_secondary_responder_ids,
        "rendered_actor_ids": rendered_actor_ids,
        "generated_spoken_line_count": len(generated_spoken_rows),
        "generated_action_line_count": len(generated_action_rows),
        "validated_spoken_line_count": len(validated_spoken_rows),
        "validated_action_line_count": len(validated_action_rows),
        "rendered_spoken_line_count": rendered_spoken_line_count,
        "rendered_action_line_count": rendered_action_line_count,
        "initiative_generated_count": initiative_generated_count,
        "initiative_preserved_count": initiative_preserved_count,
        "initiative_seizer_id": initiative_seizer_id,
        "initiative_loser_id": initiative_loser_id,
        "initiative_pressure_label": initiative_pressure_label,
        "pacing_mode": pacing_mode or None,
        "silence_mode": silence_mode or None,
        "thin_edge_applied": thin_edge_applied,
        "withheld_applied": withheld_applied,
        "compressed_applied": compressed_applied,
        "prior_tension_present": prior_tension_present,
        "quality_class": quality_class,
        "degradation_signals": degradation_signals,
        "fallback_used": fallback_used,
        "degraded_commit": degraded_commit,
        "retry_exhausted": retry_exhausted,
        "response_present": response_present,
        "initiative_present": initiative_present,
        "multi_actor_realized": multi_actor_realized,
        "sparse_input_recovery_applied": sparse_input_recovery_applied,
        "preferred_reaction_order_ids": preferred_reaction_order_ids,
        "reaction_order_divergence": reaction_order_divergence,
        # Optional diagnostic helper fields (non-required)
        "sparse_input_detected": sparse_input_detected,
        "generated_actor_ids": generated_actor_ids,
        "generated_ok": bool(generation_ok),
        "validation_ok": bool(validation_ok),
        "commit_applied": bool(commit_applied),
    }

    for field in VITALITY_TELEMETRY_REQUIRED_FIELDS:
        telemetry.setdefault(field, None)

    return telemetry


def _derive_passivity_factors(vitality: dict[str, Any]) -> list[str]:
    factors: list[str] = []
    if vitality.get("fallback_used"):
        factors.append("fallback_used")
    if vitality.get("retry_exhausted"):
        factors.append("retry_exhausted")
    if vitality.get("degraded_commit"):
        factors.append("degraded_commit")
    if vitality.get("thin_edge_applied") and vitality.get("withheld_applied"):
        factors.append("thin_edge_withheld")
    if not vitality.get("response_present"):
        factors.append("no_visible_actor_response")
    if vitality.get("selected_secondary_responder_ids") and not vitality.get("multi_actor_realized"):
        factors.append("single_actor_only")
    if vitality.get("quality_class") == "weak_but_legal":
        factors.append("weak_signal_accepted")
    if vitality.get("sparse_input_detected") and not vitality.get("sparse_input_recovery_applied"):
        factors.append("sparse_input_not_recovered")
    return factors


def _assess_agency_level(vitality: dict[str, Any]) -> str:
    if not vitality.get("generated_ok"):
        return "generation_failed"
    if vitality.get("fallback_used"):
        return "fallback_active"
    if not vitality.get("validation_ok"):
        return "validation_constrained"
    if not vitality.get("commit_applied"):
        return "commit_blocked"
    if not vitality.get("response_present"):
        return "narration_only"
    return "full_actor_agency"


def _legacy_actor_survival_view(vitality: dict[str, Any]) -> dict[str, Any]:
    responder_attribution_present = bool(vitality.get("generated_actor_ids"))
    return {
        "configured_responder_set_count": 1 + len(vitality.get("selected_secondary_responder_ids") or []),
        "configured_primary_responder": vitality.get("selected_primary_responder_id"),
        "configured_scene_function": _clean_text(vitality.get("selected_scene_function")),
        "generation_phase": {
            "generation_attempted": bool(vitality.get("generated_ok")),
            "generation_fallback_used": bool(vitality.get("fallback_used")),
            "spoken_lines_generated": int(vitality.get("generated_spoken_line_count") or 0),
            "action_lines_generated": int(vitality.get("generated_action_line_count") or 0),
            "responder_attribution_present": responder_attribution_present,
        },
        "validation_phase": {
            "validation_attempted": True,
            "validation_approved": bool(vitality.get("validation_ok")),
            "validation_reason": _clean_text(vitality.get("validation_reason")),
            "actor_legality_checked": True,
        },
        "commit_phase": {
            "commit_applied": bool(vitality.get("commit_applied")),
            "committed_effects_count": int(vitality.get("committed_effects_count") or 0),
            "responder_outcome_summary": vitality.get("responder_outcome_summary"),
            "initiative_summary": {
                "event_count": int(vitality.get("initiative_preserved_count") or 0),
                "initiative_seizer_id": vitality.get("initiative_seizer_id"),
                "initiative_loser_id": vitality.get("initiative_loser_id"),
                "initiative_pressure_label": vitality.get("initiative_pressure_label"),
            },
        },
        "render_phase": {
            "spoken_lines_rendered": int(vitality.get("rendered_spoken_line_count") or 0),
            "narration_blocks_rendered": int(vitality.get("rendered_narration_block_count") or 0),
            "continuity_state_present": bool(vitality.get("continuity_state_present")),
            "responder_trace_present": bool(vitality.get("rendered_actor_ids")),
        },
        "nominated_vs_realized": {
            "nominated_secondary_count": len(vitality.get("selected_secondary_responder_ids") or []),
            "generated_actor_count": len(vitality.get("generated_actor_ids") or []),
        },
        "degradation_markers": {
            "fallback_used": bool(vitality.get("fallback_used")),
            "validation_failed": not bool(vitality.get("validation_ok")),
            "commit_not_applied": not bool(vitality.get("commit_applied")),
            "fallback_reason": "fallback_used" if vitality.get("fallback_used") else "none",
        },
    }


def _build_operator_hints(vitality: dict[str, Any]) -> dict[str, Any]:
    passivity_factors = _derive_passivity_factors(vitality)
    hints: list[str] = []

    if "fallback_used" in passivity_factors:
        hints.append("Turn used fallback generation; dramatic realization may be reduced.")
    if "retry_exhausted" in passivity_factors:
        hints.append("Self-correction exhausted retries before acceptance.")
    if "no_visible_actor_response" in passivity_factors:
        hints.append("No visible actor-lane response reached render output.")
    if "single_actor_only" in passivity_factors:
        hints.append("Selected secondaries were not fully realized in actor lanes.")
    if "sparse_input_not_recovered" in passivity_factors:
        hints.append("Sparse/evasive input did not recover into lively actor response.")

    if not passivity_factors:
        hints.append("Turn completed with healthy actor vitality across generation, validation, commit, and render.")

    return {
        "hints": hints,
        "actor_agency_level": _assess_agency_level(vitality),
        "why_turn_felt_passive": passivity_factors,
        "primary_passivity_factors": passivity_factors[:3],
    }


def _build_passivity_diagnosis_v1(vitality: dict[str, Any]) -> dict[str, Any]:
    diagnosis = {
        "schema_version": PASSIVITY_DIAGNOSIS_SCHEMA_VERSION,
        **_build_operator_hints(vitality),
    }
    for field in PASSIVITY_DIAGNOSIS_REQUIRED_FIELDS:
        diagnosis.setdefault(field, None)
    return diagnosis


def build_actor_survival_telemetry(
    state: dict[str, Any],
    *,
    generation_ok: bool,
    validation_ok: bool,
    commit_applied: bool,
    fallback_taken: bool,
) -> dict[str, Any]:
    """Build canonical vitality telemetry plus compatibility views.

    The canonical payload is ``vitality_telemetry_v1`` and must preserve stage
    separation for all lane counts.
    """
    vitality = _build_vitality_telemetry_v1(
        state,
        generation_ok=generation_ok,
        validation_ok=validation_ok,
        commit_applied=commit_applied,
        fallback_taken=fallback_taken,
    )
    diagnosis = _build_passivity_diagnosis_v1(vitality)

    return {
        "turn_telemetry_version": "2.0",
        "vitality_telemetry_v1": vitality,
        "passivity_diagnosis_v1": diagnosis,
        # Compatibility surface for existing consumers/tests.
        "actor_survival": _legacy_actor_survival_view(vitality),
        "operator_diagnostic_hints": {
            "hints": list(diagnosis.get("hints") or []),
            "actor_agency_level": diagnosis.get("actor_agency_level"),
            "why_turn_felt_passive": list(diagnosis.get("why_turn_felt_passive") or []),
            "primary_passivity_factors": list(diagnosis.get("primary_passivity_factors") or []),
        },
    }


def build_operator_turn_history_row(
    turn_number: int,
    turn_kind: str,
    primary_responder: str | None,
    scene_function: str,
    telemetry: dict[str, Any],
    visible_output: dict[str, Any],
) -> dict[str, Any]:
    """Format one turn row for operator turn-history surfaces."""
    vitality = telemetry.get("vitality_telemetry_v1") if isinstance(telemetry.get("vitality_telemetry_v1"), dict) else {}
    diagnosis = telemetry.get("passivity_diagnosis_v1") if isinstance(telemetry.get("passivity_diagnosis_v1"), dict) else {}
    hints = telemetry.get("operator_diagnostic_hints") if isinstance(telemetry.get("operator_diagnostic_hints"), dict) else {}
    canonical = diagnosis if diagnosis else hints

    response_present = bool(vitality.get("response_present"))
    return {
        "turn_number": turn_number,
        "turn_kind": turn_kind,
        "responder": primary_responder or vitality.get("selected_primary_responder_id") or "(narrator)",
        "scene_function": scene_function or "(unknown)",
        "validation_passed": bool(vitality.get("validation_ok")),
        "commit_applied": bool(vitality.get("commit_applied")),
        "spoken_lines_count": int(vitality.get("rendered_spoken_line_count") or 0),
        "action_lines_count": int(vitality.get("rendered_action_line_count") or 0),
        "fallback_used": bool(vitality.get("fallback_used")),
        "quality_class": vitality.get("quality_class") or "healthy",
        "agency_level": canonical.get("actor_agency_level", "unknown"),
        "diagnostic_hints": list(canonical.get("hints") or []),
        "why_turn_felt_passive": list(canonical.get("why_turn_felt_passive") or []),
        "primary_passivity_factors": list(canonical.get("primary_passivity_factors") or []),
        "vitality_breakdown": {
            "response_present": response_present,
            "initiative_present": bool(vitality.get("initiative_present")),
            "multi_actor_realized": bool(vitality.get("multi_actor_realized")),
            "selected_secondary_count": len(vitality.get("selected_secondary_responder_ids") or []),
            "realized_actor_count": len(vitality.get("realized_actor_ids") or []),
            "rendered_actor_count": len(vitality.get("rendered_actor_ids") or []),
        },
        "visible_output_type": "actor_agency" if response_present else "narration_only",
        "degradation_signals": list(vitality.get("degradation_signals") or []),
        "quality_posture": "degraded" if vitality.get("quality_class") in {"degraded", "failed"} else "non_degraded",
        "has_render_support": bool(isinstance(visible_output, dict) and visible_output.get("render_support")),
    }


__all__ = [
    "build_actor_survival_telemetry",
    "build_operator_turn_history_row",
]
