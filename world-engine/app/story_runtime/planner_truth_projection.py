"""Planner-truth projection helpers for story-runtime commit records."""

from __future__ import annotations

from typing import Any

from ai_stack.contracts.social_state_contract import SocialStateRecord
from ai_stack.story_runtime.npc_agency.npc_agency_realization import (
    build_npc_agency_closure,
)
from ai_stack.story_runtime.semantic_planner.god_of_carnage_social_state import (
    social_state_fingerprint,
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, dict):
                actor_id = item.get("actor_id") or item.get("responder_id")
                if isinstance(actor_id, str) and actor_id.strip():
                    out.append(actor_id.strip())
                continue
            text = str(item).strip()
            if text:
                out.append(text)
        return out
    return []


def _resolve_validator_layers(
    validation: dict[str, Any], gate: dict[str, Any]
) -> list[str]:
    """Return the list of validator layers that actually ran on this turn.

    Prefers an explicit ``layers_used`` / ``validator_layers_used`` list
    published by the validator, and otherwise infers layers from observable
    signals (the ``validator_lane`` id and the presence of a dramatic-effect
    gate outcome). The result is the set of layers a reader can audit — not a
    wishlist of layers the live path *should* run.
    """
    explicit = _as_str_list(
        validation.get("validator_layers_used") or validation.get("layers_used")
    )
    if explicit:
        return explicit
    inferred: list[str] = []
    lane = validation.get("validator_lane")
    if isinstance(lane, str) and lane.strip():
        inferred.append(lane.strip())
    if isinstance(gate, dict) and gate:
        inferred.append("dramatic_effect_gate")
    return inferred


def _social_state_summary_from_graph_state(graph_state: dict[str, Any]) -> dict[str, Any]:
    """Preserve the bounded social-state record in committed planner truth."""
    explicit = _as_dict(graph_state.get("social_state_summary"))
    record = _as_dict(graph_state.get("social_state_record"))
    if not record:
        return explicit

    summary = dict(explicit)
    summary.setdefault("summary_source", "social_state_record")
    summary["record"] = record
    for key in (
        "scene_pressure_state",
        "guidance_phase_key",
        "responder_asymmetry_code",
        "social_risk_band",
        "active_thread_count",
        "thread_pressure_summary_present",
        "prior_continuity_classes",
        "prior_social_state_fingerprint",
        "prior_social_risk_band",
        "social_continuity_status",
        "relationship_pressure_codes",
        "active_relationship_axis_ids",
        "dominant_relationship_axis_id",
    ):
        if key in record:
            summary.setdefault(key, record.get(key))

    try:
        summary.setdefault(
            "fingerprint",
            social_state_fingerprint(SocialStateRecord.model_validate(record)),
        )
        summary["validated"] = True
    except Exception:
        summary["validated"] = False
    return summary


def _opt_str(*candidates: Any) -> str | None:
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _lane_count(value: Any) -> int:
    if not isinstance(value, list):
        return 0
    count = 0
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if text:
                count += 1
            continue
        if str(item).strip():
            count += 1
    return count


def _initiative_rows(initiative_events: Any) -> list[dict[str, Any]]:
    if not isinstance(initiative_events, list):
        return []
    return [row for row in initiative_events if isinstance(row, dict)]


def _initiative_summary(initiative_events: Any) -> dict[str, Any]:
    rows = _initiative_rows(initiative_events)
    if not rows:
        return {}
    types: list[str] = []
    actors: list[str] = []
    for row in rows:
        raw_type = row.get("type")
        raw_actor = row.get("actor_id")
        event_type = str(raw_type).strip() if isinstance(raw_type, str) else ""
        actor_id = str(raw_actor).strip() if isinstance(raw_actor, str) else ""
        if event_type and event_type not in types:
            types.append(event_type)
        if actor_id and actor_id not in actors:
            actors.append(actor_id)
    return {"event_count": len(rows), "event_types": types, "actors": actors}


def _last_actor_outcome_summary(
    *,
    primary_responder_id: str | None,
    spoken_line_count: int,
    action_line_count: int,
    initiative_summary: dict[str, Any],
    social_outcome: str | None,
    dramatic_direction: str | None,
) -> str | None:
    parts: list[str] = []
    if primary_responder_id:
        parts.append(f"primary_responder={primary_responder_id}")
    parts.append(f"spoken_lines={spoken_line_count}")
    parts.append(f"action_lines={action_line_count}")
    if initiative_summary.get("event_count"):
        parts.append(f"initiative_events={initiative_summary.get('event_count')}")
    if social_outcome:
        parts.append(f"social_outcome={social_outcome}")
    if dramatic_direction:
        parts.append(f"dramatic_direction={dramatic_direction}")
    return ", ".join(parts) if parts else None


def _realized_secondary_responder_ids(
    *,
    spoken_lines: Any,
    action_lines: Any,
    secondary_responder_ids: list[str],
) -> list[str]:
    realized: list[str] = []
    for source, key in ((spoken_lines, "speaker_id"), (action_lines, "actor_id")):
        if not isinstance(source, list):
            continue
        for item in source:
            if not isinstance(item, dict):
                continue
            actor_id = item.get(key)
            if not isinstance(actor_id, str) or not actor_id.strip():
                continue
            actor_id = actor_id.strip()
            if actor_id in secondary_responder_ids and actor_id not in realized:
                realized.append(actor_id)
    return realized


def _interruption_actor_id(initiative_events: Any) -> str | None:
    for event in _initiative_rows(initiative_events):
        if event.get("type") != "interrupt":
            continue
        actor_id = event.get("actor_id")
        if isinstance(actor_id, str) and actor_id.strip():
            return actor_id.strip()
    return None


def _actor_line_summaries(
    lines: Any,
    *,
    actor_key: str,
) -> list[dict[str, Any]]:
    if not isinstance(lines, list):
        return []
    by_actor: dict[str, list[str]] = {}
    for item in lines:
        if not isinstance(item, dict):
            continue
        actor_id = item.get(actor_key)
        text = item.get("text")
        if not isinstance(actor_id, str) or not actor_id.strip():
            continue
        if isinstance(text, str):
            by_actor.setdefault(actor_id.strip(), []).append(text)
    summaries: list[dict[str, Any]] = []
    for actor_id, texts in by_actor.items():
        preview = texts[0][:120] if texts and isinstance(texts[0], str) else None
        summaries.append(
            {"actor_id": actor_id, "line_count": len(texts), "text_preview": preview}
        )
    return summaries


def _social_pressure_shift(
    *,
    state_effects: Any,
    social_outcome: str | None,
    graph_state: dict[str, Any],
) -> str | None:
    if isinstance(state_effects, list):
        for effect in state_effects:
            if not isinstance(effect, dict) or effect.get("effect_type") != "pressure_shift":
                continue
            value = effect.get("value")
            if not isinstance(value, str):
                continue
            value = value.lower().strip()
            if value in ("escalated", "high", "spike"):
                return "escalated"
            if value in ("de-escalated", "eased"):
                return "de-escalated"
            return "shifted"
    if not social_outcome:
        return None
    prior = graph_state.get("prior_planner_truth")
    prior_social = _opt_str(
        graph_state.get("prior_social_outcome"),
        prior.get("social_outcome") if isinstance(prior, dict) else None,
    )
    if prior_social and prior_social != social_outcome:
        return "shifted"
    if prior_social == social_outcome:
        return "held"
    return None


def _carry_forward_tension_notes(
    *,
    state_effects: Any,
    initiative_events: Any,
) -> str | None:
    parts: list[str] = []
    if isinstance(state_effects, list):
        for effect in state_effects:
            if not isinstance(effect, dict):
                continue
            effect_type = effect.get("effect_type")
            value = effect.get("value")
            if effect_type == "pressure_shift" and isinstance(value, str):
                parts.append(f"pressure: {value.lower()}")
            elif effect_type in ("accusation", "grievance", "repair_failure"):
                parts.append(f"{effect_type}")
            elif isinstance(value, str) and any(
                token in value.lower() for token in ("unresolved", "pending", "open")
            ):
                parts.append(f"{effect_type}: {value[:40]}")
    if any(event.get("type") == "interrupt" for event in _initiative_rows(initiative_events)):
        parts.append("unresolved interrupt")
    if not parts:
        return None
    value = ", ".join(parts)[:280]
    return value if value else None


def _initiative_seizer_id(initiative_events: Any) -> str | None:
    for event in _initiative_rows(initiative_events):
        if str(event.get("type") or "").lower() not in ("seize", "counter", "escalate"):
            continue
        actor_id = event.get("actor_id")
        if isinstance(actor_id, str) and actor_id.strip():
            return actor_id.strip()
    return None


def _initiative_loser_id(
    *,
    initiative_events: Any,
    primary_responder_id: str | None,
) -> str | None:
    rows = _initiative_rows(initiative_events)
    for event in rows:
        if str(event.get("type") or "").lower() not in ("interrupt", "counter"):
            continue
        target_id = event.get("target_id")
        if isinstance(target_id, str) and target_id.strip():
            return target_id.strip()
    for event in rows:
        if str(event.get("type") or "").lower() in ("interrupt", "counter"):
            return primary_responder_id
    return None


def _initiative_pressure_label(initiative_events: Any) -> str | None:
    rows = _initiative_rows(initiative_events)
    if not rows:
        return None
    event_types = {str(event.get("type") or "").lower() for event in rows}
    if "interrupt" in event_types or "counter" in event_types:
        return "contested"
    if "seize" in event_types or "escalate" in event_types:
        return "floor_claimed"
    if "deflect" in event_types:
        return "deflected"
    return "stable"


def _section_triplet(
    graph_state: dict[str, Any],
    packet: dict[str, Any],
    *,
    packet_key: str,
    state_key: str,
    target_key: str,
    validation_key: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    section = _as_dict(packet.get(packet_key))
    return (
        _as_dict(graph_state.get(state_key) or section.get("state")),
        _as_dict(graph_state.get(target_key) or section.get("target")),
        _as_dict(graph_state.get(validation_key)),
    )


def _dramatic_context_fields(graph_state: dict[str, Any]) -> dict[str, Any]:
    packet = _as_dict(graph_state.get("dramatic_generation_packet"))
    scene_energy_packet = _as_dict(packet.get("scene_energy"))
    fields: dict[str, Any] = {
        "dramatic_irony": _as_dict(
            graph_state.get("dramatic_irony_record")
            or packet.get("dramatic_irony_context")
        ),
        "scene_energy_target": _as_dict(
            graph_state.get("scene_energy_target")
            or scene_energy_packet.get("target")
        ),
        "scene_energy_transition": _as_dict(
            graph_state.get("scene_energy_transition")
            or scene_energy_packet.get("transition")
        ),
        "scene_energy_validation": _as_dict(graph_state.get("scene_energy_validation")),
    }
    specs = (
        ("pacing_rhythm", "pacing_rhythm_state", "pacing_rhythm_target", "pacing_rhythm_validation"),
        ("temporal_control", "temporal_control_state", "temporal_control_target", "temporal_control_validation"),
        ("sensory_context", "sensory_context_state", "sensory_context_target", "sensory_context_validation"),
        ("genre_awareness", "genre_awareness_state", "genre_awareness_target", "genre_awareness_validation"),
        ("symbolic_object_resonance", "symbolic_object_resonance_state", "symbolic_object_resonance_target", "symbolic_object_resonance_validation"),
        ("social_pressure", "social_pressure_state", "social_pressure_target", "social_pressure_validation"),
        ("expectation_variation", "expectation_variation_state", "expectation_variation_target", "expectation_variation_validation"),
        ("narrative_momentum", "narrative_momentum_state", "narrative_momentum_target", "narrative_momentum_validation"),
        ("relationship_state", "relationship_state_record", "relationship_dynamics_target", "relationship_state_validation"),
    )
    for packet_key, state_key, target_key, validation_key in specs:
        state, target, validation = _section_triplet(
            graph_state,
            packet,
            packet_key=packet_key,
            state_key=state_key,
            target_key=target_key,
            validation_key=validation_key,
        )
        fields[state_key] = state
        fields[target_key] = target
        fields[validation_key] = validation
    return fields


def _npc_agency_fields(graph_state: dict[str, Any]) -> dict[str, Any]:
    packet = _as_dict(graph_state.get("dramatic_generation_packet"))
    simulation = _as_dict(
        packet.get("npc_agency_simulation") or graph_state.get("npc_agency_simulation")
    )
    long_horizon = _as_dict(
        simulation.get("npc_long_horizon_state")
        or packet.get("npc_long_horizon_state")
        or graph_state.get("npc_long_horizon_state")
    )
    private_plans = [
        row
        for row in (
            simulation.get("npc_private_plans")
            or packet.get("npc_private_plans")
            or graph_state.get("npc_private_plans")
            or []
        )
        if isinstance(row, dict)
    ]
    conflict_resolution = _as_dict(
        simulation.get("npc_plan_conflict_resolution")
        or packet.get("npc_plan_conflict_resolution")
        or graph_state.get("npc_plan_conflict_resolution")
    )
    initiative_validation = _as_dict(graph_state.get("npc_initiative_validation"))
    source = simulation or _as_dict(
        packet.get("npc_agency_plan") or initiative_validation.get("npc_agency_plan")
    )
    closure = build_npc_agency_closure(
        source,
        validation=initiative_validation,
        prior_planner_truth=_as_dict(graph_state.get("prior_planner_truth")),
        actor_lane_context=_as_dict(graph_state.get("actor_lane_context")),
        turn_number=graph_state.get("turn_number"),
    )
    carried_forward = (
        list(closure.get("carried_forward_npc_initiatives") or [])
        if isinstance(closure, dict)
        else []
    )
    return {
        "npc_agency_simulation": simulation,
        "npc_long_horizon_state": long_horizon,
        "npc_private_plans": private_plans,
        "npc_plan_conflict_resolution": conflict_resolution,
        "npc_agency_closure": closure or {},
        "unresolved_npc_initiatives": carried_forward,
        "carried_forward_npc_initiatives": carried_forward,
    }


def build_planner_truth_payload(
    *,
    graph_state: dict[str, Any] | None,
    generation: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract a bounded planner-truth snapshot from the live runtime state."""
    if not isinstance(graph_state, dict):
        graph_state = {}
    gen = generation if isinstance(generation, dict) else {}
    structured = _as_dict(_as_dict(gen.get("metadata")).get("structured_output"))
    validation = _as_dict(graph_state.get("validation_outcome"))
    gate = _as_dict(graph_state.get("dramatic_effect_gate_outcome"))
    if not gate:
        gate = _as_dict(graph_state.get("dramatic_effect_gate"))
    scene_assessment = _as_dict(graph_state.get("scene_assessment"))
    if not scene_assessment:
        scene_assessment = _as_dict(graph_state.get("scene_assessment_core"))

    responder_scope = _as_str_list(
        graph_state.get("responder_scope")
        or graph_state.get("selected_responder_set")
        or structured.get("responder_scope")
    )
    primary_responder_id = _opt_str(
        graph_state.get("responder_id"),
        graph_state.get("primary_responder_id"),
        structured.get("primary_responder_id"),
        structured.get("responder_id"),
    )
    secondary_responder_ids = _as_str_list(
        graph_state.get("secondary_responder_ids")
        or structured.get("secondary_responder_ids")
        or structured.get("responder_actor_ids")
    )
    if primary_responder_id and primary_responder_id in secondary_responder_ids:
        secondary_responder_ids = [x for x in secondary_responder_ids if x != primary_responder_id]

    bundle = _as_dict(graph_state.get("visible_output_bundle"))
    spoken_line_count = _lane_count(bundle.get("spoken_lines"))
    action_line_count = _lane_count(bundle.get("action_lines"))
    initiative_events = structured.get("initiative_events")
    initiative_summary = _initiative_summary(initiative_events)
    social_outcome = _opt_str(graph_state.get("social_outcome"), structured.get("social_outcome"))
    dramatic_direction = _opt_str(
        graph_state.get("dramatic_direction"),
        structured.get("dramatic_direction"),
    )
    spoken_lines = structured.get("spoken_lines")
    action_lines = structured.get("action_lines")
    state_effects = structured.get("state_effects")
    dramatic_fields = _dramatic_context_fields(graph_state)
    npc_agency_fields = _npc_agency_fields(graph_state)

    return {
        "selected_scene_function": _opt_str(
            graph_state.get("selected_scene_function"),
            structured.get("selected_scene_function"),
        ),
        "responder_id": _opt_str(
            graph_state.get("responder_id"),
            structured.get("responder_id"),
            primary_responder_id,
        ),
        "primary_responder_id": primary_responder_id,
        "secondary_responder_ids": secondary_responder_ids,
        "responder_scope": responder_scope,
        "function_type": _opt_str(graph_state.get("function_type"), structured.get("function_type")),
        "pacing_mode": _opt_str(
            graph_state.get("pacing_mode"),
            structured.get("pacing_mode"),
            graph_state.get("selected_pacing_mode"),
        ),
        "silence_mode": _opt_str(
            graph_state.get("silence_mode"),
            structured.get("silence_mode"),
            graph_state.get("selected_silence_mode"),
        ),
        **dramatic_fields,
        "scene_energy_level": _opt_str(dramatic_fields["scene_energy_target"].get("energy_level")),
        "spoken_line_count": spoken_line_count,
        "action_line_count": action_line_count,
        "initiative_summary": initiative_summary,
        "last_actor_outcome_summary": _last_actor_outcome_summary(
            primary_responder_id=primary_responder_id,
            spoken_line_count=spoken_line_count,
            action_line_count=action_line_count,
            initiative_summary=initiative_summary,
            social_outcome=social_outcome,
            dramatic_direction=dramatic_direction,
        ),
        "scene_assessment_core": scene_assessment,
        "scene_plan_ref": _opt_str(
            graph_state.get("scene_plan_ref"),
            graph_state.get("scene_plan_id"),
            structured.get("scene_plan_ref"),
        ),
        "emotional_shift": _as_dict(graph_state.get("emotional_shift") or structured.get("emotional_shift")),
        "social_outcome": social_outcome,
        "dramatic_direction": dramatic_direction,
        "dramatic_effect_gate": gate,
        "social_state_summary": _social_state_summary_from_graph_state(graph_state),
        "character_mind_summary": _as_dict(graph_state.get("character_mind_summary")),
        "validation_status": _opt_str(validation.get("status")),
        "validation_reason": _opt_str(validation.get("reason")),
        "validator_layers_used": _resolve_validator_layers(validation, gate),
        "continuity_impacts": [
            x for x in (graph_state.get("continuity_impacts") or []) if isinstance(x, dict)
        ],
        "realized_secondary_responder_ids": _realized_secondary_responder_ids(
            spoken_lines=spoken_lines,
            action_lines=action_lines,
            secondary_responder_ids=secondary_responder_ids,
        ),
        "interruption_actor_id": _interruption_actor_id(initiative_events),
        "spoken_actor_summaries": _actor_line_summaries(spoken_lines, actor_key="speaker_id"),
        "action_actor_summaries": _actor_line_summaries(action_lines, actor_key="actor_id"),
        "social_pressure_shift": _social_pressure_shift(
            state_effects=state_effects,
            social_outcome=social_outcome,
            graph_state=graph_state,
        ),
        "carry_forward_tension_notes": _carry_forward_tension_notes(
            state_effects=state_effects,
            initiative_events=initiative_events,
        ),
        "initiative_seizer_id": _initiative_seizer_id(initiative_events),
        "initiative_loser_id": _initiative_loser_id(
            initiative_events=initiative_events,
            primary_responder_id=primary_responder_id,
        ),
        "initiative_pressure_label": _initiative_pressure_label(initiative_events),
        **npc_agency_fields,
    }
