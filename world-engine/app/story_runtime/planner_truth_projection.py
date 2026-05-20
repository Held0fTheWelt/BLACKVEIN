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


def build_planner_truth_payload(
    *,
    graph_state: dict[str, Any] | None,
    generation: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract a bounded planner-truth snapshot from the live runtime state.

    Top-level ``RuntimeTurnState`` keys populated by the graph's
    ``proposal_normalize`` node are the primary source. When a key is missing
    from state, the extractor falls back to the model's structured output on
    ``generation.metadata.structured_output`` so partially-degraded turns still
    surface what they can. An absent value stays None / empty so readers can
    distinguish "planner did not emit" from "planner emitted empty".
    """
    if not isinstance(graph_state, dict):
        graph_state = {}
    gen = generation if isinstance(generation, dict) else {}
    meta = _as_dict(gen.get("metadata"))
    structured = _as_dict(meta.get("structured_output"))
    validation = _as_dict(graph_state.get("validation_outcome"))
    gate = _as_dict(graph_state.get("dramatic_effect_gate_outcome"))
    if not gate:
        gate = _as_dict(graph_state.get("dramatic_effect_gate"))
    scene_assessment = _as_dict(graph_state.get("scene_assessment"))
    if not scene_assessment:
        scene_assessment = _as_dict(graph_state.get("scene_assessment_core"))

    def _opt_str(*candidates: Any) -> str | None:
        for c in candidates:
            if isinstance(c, str) and c.strip():
                return c.strip()
        return None

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

    spoken_line_count = _lane_count(bundle.get("spoken_lines"))
    action_line_count = _lane_count(bundle.get("action_lines"))

    initiative_events = structured.get("initiative_events")
    initiative_summary: dict[str, Any] = {}
    if isinstance(initiative_events, list):
        types: list[str] = []
        actors: list[str] = []
        for row in initiative_events:
            if not isinstance(row, dict):
                continue
            raw_type = row.get("type")
            raw_actor = row.get("actor_id")
            event_type = str(raw_type).strip() if isinstance(raw_type, str) else ""
            actor_id = str(raw_actor).strip() if isinstance(raw_actor, str) else ""
            if event_type and event_type not in types:
                types.append(event_type)
            if actor_id and actor_id not in actors:
                actors.append(actor_id)
        initiative_summary = {
            "event_count": len([x for x in initiative_events if isinstance(x, dict)]),
            "event_types": types,
            "actors": actors,
        }

    social_outcome = _opt_str(graph_state.get("social_outcome"), structured.get("social_outcome"))
    dramatic_direction = _opt_str(
        graph_state.get("dramatic_direction"),
        structured.get("dramatic_direction"),
    )
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
    last_actor_outcome_summary = ", ".join(parts) if parts else None

    # Extract realized secondary responders from spoken/action lanes
    realized_secondary_responder_ids: list[str] = []
    spoken_lines = structured.get("spoken_lines")
    action_lines = structured.get("action_lines")
    if isinstance(spoken_lines, list):
        for item in spoken_lines:
            if isinstance(item, dict):
                speaker_id = item.get("speaker_id")
                if isinstance(speaker_id, str) and speaker_id.strip():
                    speaker_id = speaker_id.strip()
                    if speaker_id in secondary_responder_ids and speaker_id not in realized_secondary_responder_ids:
                        realized_secondary_responder_ids.append(speaker_id)
    if isinstance(action_lines, list):
        for item in action_lines:
            if isinstance(item, dict):
                actor_id = item.get("actor_id")
                if isinstance(actor_id, str) and actor_id.strip():
                    actor_id = actor_id.strip()
                    if actor_id in secondary_responder_ids and actor_id not in realized_secondary_responder_ids:
                        realized_secondary_responder_ids.append(actor_id)

    # Extract interruption actor from initiative events
    interruption_actor_id: str | None = None
    if isinstance(initiative_events, list):
        for event in initiative_events:
            if isinstance(event, dict) and event.get("type") == "interrupt":
                actor_id = event.get("actor_id")
                if isinstance(actor_id, str) and actor_id.strip():
                    interruption_actor_id = actor_id.strip()
                    break

    # Extract spoken and action summaries by actor
    spoken_actor_summaries: list[dict[str, Any]] = []
    if isinstance(spoken_lines, list):
        spoken_by_actor: dict[str, list[str]] = {}
        for item in spoken_lines:
            if isinstance(item, dict):
                speaker_id = item.get("speaker_id")
                if isinstance(speaker_id, str) and speaker_id.strip():
                    speaker_id = speaker_id.strip()
                    text = item.get("text")
                    if isinstance(text, str):
                        if speaker_id not in spoken_by_actor:
                            spoken_by_actor[speaker_id] = []
                        spoken_by_actor[speaker_id].append(text)
        for actor_id, texts in spoken_by_actor.items():
            preview = (texts[0][:120] if texts and isinstance(texts[0], str) else None)
            spoken_actor_summaries.append(
                {"actor_id": actor_id, "line_count": len(texts), "text_preview": preview}
            )

    action_actor_summaries: list[dict[str, Any]] = []
    if isinstance(action_lines, list):
        action_by_actor: dict[str, list[str]] = {}
        for item in action_lines:
            if isinstance(item, dict):
                actor_id = item.get("actor_id")
                if isinstance(actor_id, str) and actor_id.strip():
                    actor_id = actor_id.strip()
                    text = item.get("text")
                    if isinstance(text, str):
                        if actor_id not in action_by_actor:
                            action_by_actor[actor_id] = []
                        action_by_actor[actor_id].append(text)
        for actor_id, texts in action_by_actor.items():
            preview = (texts[0][:120] if texts and isinstance(texts[0], str) else None)
            action_actor_summaries.append(
                {"actor_id": actor_id, "line_count": len(texts), "text_preview": preview}
            )

    # Extract social pressure shift from state_effects, fallback to social_outcome comparison
    social_pressure_shift: str | None = None
    state_effects = structured.get("state_effects")
    if isinstance(state_effects, list):
        for effect in state_effects:
            if isinstance(effect, dict) and effect.get("effect_type") == "pressure_shift":
                value = effect.get("value")
                if isinstance(value, str):
                    value = value.lower().strip()
                    if value in ("escalated", "high", "spike"):
                        social_pressure_shift = "escalated"
                        break
                    elif value in ("de-escalated", "eased"):
                        social_pressure_shift = "de-escalated"
                        break
                    else:
                        social_pressure_shift = "shifted"
    if not social_pressure_shift and social_outcome:
        prior_social = _opt_str(
            graph_state.get("prior_social_outcome"),
            graph_state.get("prior_planner_truth", {}).get("social_outcome") if isinstance(graph_state.get("prior_planner_truth"), dict) else None,
        )
        if prior_social and prior_social != social_outcome:
            social_pressure_shift = "shifted"
        elif prior_social == social_outcome:
            social_pressure_shift = "held"

    # Extract carry-forward tension notes from state_effects and unresolved initiatives
    carry_forward_tension_notes: str | None = None
    tension_parts: list[str] = []
    if isinstance(state_effects, list):
        for effect in state_effects:
            if isinstance(effect, dict):
                effect_type = effect.get("effect_type")
                value = effect.get("value")
                if effect_type == "pressure_shift" and isinstance(value, str):
                    tension_parts.append(f"pressure: {value.lower()}")
                elif effect_type in ("accusation", "grievance", "repair_failure"):
                    tension_parts.append(f"{effect_type}")
                elif isinstance(value, str) and any(x in value.lower() for x in ("unresolved", "pending", "open")):
                    tension_parts.append(f"{effect_type}: {value[:40]}")
    if isinstance(initiative_events, list):
        for event in initiative_events:
            if isinstance(event, dict) and event.get("type") == "interrupt":
                tension_parts.append("unresolved interrupt")
                break
    if tension_parts:
        tension_str = ", ".join(tension_parts)[:280]
        carry_forward_tension_notes = tension_str if tension_str else None

    # Extract initiative_seizer_id: first actor_id from seize/counter/escalate event
    initiative_seizer_id: str | None = None
    if isinstance(initiative_events, list):
        for event in initiative_events:
            if isinstance(event, dict) and str(event.get("type") or "").lower() in ("seize", "counter", "escalate"):
                actor_id = event.get("actor_id")
                if isinstance(actor_id, str) and actor_id.strip():
                    initiative_seizer_id = actor_id.strip()
                    break

    # Extract initiative_loser_id with derivation priority
    initiative_loser_id: str | None = None
    if isinstance(initiative_events, list):
        for event in initiative_events:
            if isinstance(event, dict) and str(event.get("type") or "").lower() in ("interrupt", "counter"):
                # Priority 1: use explicit target_id if present
                target_id = event.get("target_id")
                if isinstance(target_id, str) and target_id.strip():
                    initiative_loser_id = target_id.strip()
                    break
        # Priority 2 fallback: primary_responder_id when no explicit target
        if not initiative_loser_id and isinstance(initiative_events, list):
            for event in initiative_events:
                if isinstance(event, dict) and str(event.get("type") or "").lower() in ("interrupt", "counter"):
                    if primary_responder_id:
                        initiative_loser_id = primary_responder_id
                    break

    # Derive initiative_pressure_label from event types
    initiative_pressure_label: str | None = None
    if isinstance(initiative_events, list) and initiative_events:
        event_types_lower = {
            str(e.get("type") or "").lower()
            for e in initiative_events
            if isinstance(e, dict)
        }
        if "interrupt" in event_types_lower or "counter" in event_types_lower:
            initiative_pressure_label = "contested"
        elif "seize" in event_types_lower or "escalate" in event_types_lower:
            initiative_pressure_label = "floor_claimed"
        elif "deflect" in event_types_lower:
            initiative_pressure_label = "deflected"
        else:
            initiative_pressure_label = "stable"

    dramatic_packet = _as_dict(graph_state.get("dramatic_generation_packet"))
    dramatic_packet_scene_energy = _as_dict(dramatic_packet.get("scene_energy"))
    dramatic_irony = _as_dict(
        graph_state.get("dramatic_irony_record")
        or dramatic_packet.get("dramatic_irony_context")
    )
    scene_energy_target = _as_dict(
        graph_state.get("scene_energy_target")
        or dramatic_packet_scene_energy.get("target")
    )
    scene_energy_transition = _as_dict(
        graph_state.get("scene_energy_transition")
        or dramatic_packet_scene_energy.get("transition")
    )
    scene_energy_validation = _as_dict(graph_state.get("scene_energy_validation"))
    dramatic_packet_pacing_rhythm = _as_dict(dramatic_packet.get("pacing_rhythm"))
    pacing_rhythm_state = _as_dict(
        graph_state.get("pacing_rhythm_state")
        or dramatic_packet_pacing_rhythm.get("state")
    )
    pacing_rhythm_target = _as_dict(
        graph_state.get("pacing_rhythm_target")
        or dramatic_packet_pacing_rhythm.get("target")
    )
    pacing_rhythm_validation = _as_dict(graph_state.get("pacing_rhythm_validation"))
    dramatic_packet_temporal_control = _as_dict(dramatic_packet.get("temporal_control"))
    temporal_control_state = _as_dict(
        graph_state.get("temporal_control_state")
        or dramatic_packet_temporal_control.get("state")
    )
    temporal_control_target = _as_dict(
        graph_state.get("temporal_control_target")
        or dramatic_packet_temporal_control.get("target")
    )
    temporal_control_validation = _as_dict(graph_state.get("temporal_control_validation"))
    dramatic_packet_sensory_context = _as_dict(dramatic_packet.get("sensory_context"))
    sensory_context_state = _as_dict(
        graph_state.get("sensory_context_state")
        or dramatic_packet_sensory_context.get("state")
    )
    sensory_context_target = _as_dict(
        graph_state.get("sensory_context_target")
        or dramatic_packet_sensory_context.get("target")
    )
    sensory_context_validation = _as_dict(graph_state.get("sensory_context_validation"))
    dramatic_packet_genre_awareness = _as_dict(dramatic_packet.get("genre_awareness"))
    genre_awareness_state = _as_dict(
        graph_state.get("genre_awareness_state")
        or dramatic_packet_genre_awareness.get("state")
    )
    genre_awareness_target = _as_dict(
        graph_state.get("genre_awareness_target")
        or dramatic_packet_genre_awareness.get("target")
    )
    genre_awareness_validation = _as_dict(graph_state.get("genre_awareness_validation"))
    dramatic_packet_symbolic_object = _as_dict(
        dramatic_packet.get("symbolic_object_resonance")
    )
    symbolic_object_resonance_state = _as_dict(
        graph_state.get("symbolic_object_resonance_state")
        or dramatic_packet_symbolic_object.get("state")
    )
    symbolic_object_resonance_target = _as_dict(
        graph_state.get("symbolic_object_resonance_target")
        or dramatic_packet_symbolic_object.get("target")
    )
    symbolic_object_resonance_validation = _as_dict(
        graph_state.get("symbolic_object_resonance_validation")
    )
    dramatic_packet_social_pressure = _as_dict(dramatic_packet.get("social_pressure"))
    social_pressure_state = _as_dict(
        graph_state.get("social_pressure_state")
        or dramatic_packet_social_pressure.get("state")
    )
    social_pressure_target = _as_dict(
        graph_state.get("social_pressure_target")
        or dramatic_packet_social_pressure.get("target")
    )
    social_pressure_validation = _as_dict(graph_state.get("social_pressure_validation"))
    dramatic_packet_expectation_variation = _as_dict(
        dramatic_packet.get("expectation_variation")
    )
    expectation_variation_state = _as_dict(
        graph_state.get("expectation_variation_state")
        or dramatic_packet_expectation_variation.get("state")
    )
    expectation_variation_target = _as_dict(
        graph_state.get("expectation_variation_target")
        or dramatic_packet_expectation_variation.get("target")
    )
    expectation_variation_validation = _as_dict(
        graph_state.get("expectation_variation_validation")
    )
    dramatic_packet_narrative_momentum = _as_dict(
        dramatic_packet.get("narrative_momentum")
    )
    narrative_momentum_state = _as_dict(
        graph_state.get("narrative_momentum_state")
        or dramatic_packet_narrative_momentum.get("state")
    )
    narrative_momentum_target = _as_dict(
        graph_state.get("narrative_momentum_target")
        or dramatic_packet_narrative_momentum.get("target")
    )
    narrative_momentum_validation = _as_dict(
        graph_state.get("narrative_momentum_validation")
    )
    dramatic_packet_relationship_state = _as_dict(dramatic_packet.get("relationship_state"))
    relationship_state_record = _as_dict(
        graph_state.get("relationship_state_record")
        or dramatic_packet_relationship_state.get("state")
    )
    relationship_dynamics_target = _as_dict(
        graph_state.get("relationship_dynamics_target")
        or dramatic_packet_relationship_state.get("target")
    )
    relationship_state_validation = _as_dict(graph_state.get("relationship_state_validation"))
    npc_agency_simulation = _as_dict(
        dramatic_packet.get("npc_agency_simulation")
        or graph_state.get("npc_agency_simulation")
    )
    npc_long_horizon_state = _as_dict(
        npc_agency_simulation.get("npc_long_horizon_state")
        or dramatic_packet.get("npc_long_horizon_state")
        or graph_state.get("npc_long_horizon_state")
    )
    npc_private_plans = [
        row
        for row in (
            npc_agency_simulation.get("npc_private_plans")
            or dramatic_packet.get("npc_private_plans")
            or graph_state.get("npc_private_plans")
            or []
        )
        if isinstance(row, dict)
    ]
    npc_plan_conflict_resolution = _as_dict(
        npc_agency_simulation.get("npc_plan_conflict_resolution")
        or dramatic_packet.get("npc_plan_conflict_resolution")
        or graph_state.get("npc_plan_conflict_resolution")
    )
    npc_initiative_validation = _as_dict(graph_state.get("npc_initiative_validation"))
    npc_agency_source = npc_agency_simulation or _as_dict(
        dramatic_packet.get("npc_agency_plan")
        or npc_initiative_validation.get("npc_agency_plan")
    )
    npc_agency_closure = build_npc_agency_closure(
        npc_agency_source,
        validation=npc_initiative_validation,
        prior_planner_truth=_as_dict(graph_state.get("prior_planner_truth")),
        actor_lane_context=_as_dict(graph_state.get("actor_lane_context")),
        turn_number=graph_state.get("turn_number"),
    )
    carried_forward_npc_initiatives = (
        list(npc_agency_closure.get("carried_forward_npc_initiatives") or [])
        if isinstance(npc_agency_closure, dict)
        else []
    )

    return dict(
        selected_scene_function=_opt_str(
            graph_state.get("selected_scene_function"),
            structured.get("selected_scene_function"),
        ),
        responder_id=_opt_str(
            graph_state.get("responder_id"),
            structured.get("responder_id"),
            primary_responder_id,
        ),
        primary_responder_id=primary_responder_id,
        secondary_responder_ids=secondary_responder_ids,
        responder_scope=responder_scope,
        function_type=_opt_str(
            graph_state.get("function_type"), structured.get("function_type")
        ),
        pacing_mode=_opt_str(
            graph_state.get("pacing_mode"),
            structured.get("pacing_mode"),
            graph_state.get("selected_pacing_mode"),
        ),
        silence_mode=_opt_str(
            graph_state.get("silence_mode"),
            structured.get("silence_mode"),
            graph_state.get("selected_silence_mode"),
        ),
        scene_energy_target=scene_energy_target,
        scene_energy_transition=scene_energy_transition,
        scene_energy_validation=scene_energy_validation,
        scene_energy_level=_opt_str(scene_energy_target.get("energy_level")),
        pacing_rhythm_state=pacing_rhythm_state,
        pacing_rhythm_target=pacing_rhythm_target,
        pacing_rhythm_validation=pacing_rhythm_validation,
        temporal_control_state=temporal_control_state,
        temporal_control_target=temporal_control_target,
        temporal_control_validation=temporal_control_validation,
        sensory_context_state=sensory_context_state,
        sensory_context_target=sensory_context_target,
        sensory_context_validation=sensory_context_validation,
        genre_awareness_state=genre_awareness_state,
        genre_awareness_target=genre_awareness_target,
        genre_awareness_validation=genre_awareness_validation,
        symbolic_object_resonance_state=symbolic_object_resonance_state,
        symbolic_object_resonance_target=symbolic_object_resonance_target,
        symbolic_object_resonance_validation=symbolic_object_resonance_validation,
        social_pressure_state=social_pressure_state,
        social_pressure_target=social_pressure_target,
        social_pressure_validation=social_pressure_validation,
        expectation_variation_state=expectation_variation_state,
        expectation_variation_target=expectation_variation_target,
        expectation_variation_validation=expectation_variation_validation,
        narrative_momentum_state=narrative_momentum_state,
        narrative_momentum_target=narrative_momentum_target,
        narrative_momentum_validation=narrative_momentum_validation,
        relationship_state_record=relationship_state_record,
        relationship_dynamics_target=relationship_dynamics_target,
        relationship_state_validation=relationship_state_validation,
        spoken_line_count=spoken_line_count,
        action_line_count=action_line_count,
        initiative_summary=initiative_summary,
        last_actor_outcome_summary=last_actor_outcome_summary,
        scene_assessment_core=scene_assessment,
        scene_plan_ref=_opt_str(
            graph_state.get("scene_plan_ref"),
            graph_state.get("scene_plan_id"),
            structured.get("scene_plan_ref"),
        ),
        emotional_shift=_as_dict(
            graph_state.get("emotional_shift") or structured.get("emotional_shift")
        ),
        social_outcome=_opt_str(
            graph_state.get("social_outcome"), structured.get("social_outcome")
        ),
        dramatic_direction=_opt_str(
            graph_state.get("dramatic_direction"),
            structured.get("dramatic_direction"),
        ),
        dramatic_effect_gate=gate,
        social_state_summary=_social_state_summary_from_graph_state(graph_state),
        character_mind_summary=_as_dict(graph_state.get("character_mind_summary")),
        validation_status=_opt_str(validation.get("status")),
        validation_reason=_opt_str(validation.get("reason")),
        validator_layers_used=_resolve_validator_layers(validation, gate),
        continuity_impacts=[
            x for x in (graph_state.get("continuity_impacts") or []) if isinstance(x, dict)
        ],
        realized_secondary_responder_ids=realized_secondary_responder_ids,
        interruption_actor_id=interruption_actor_id,
        spoken_actor_summaries=spoken_actor_summaries,
        action_actor_summaries=action_actor_summaries,
        social_pressure_shift=social_pressure_shift,
        carry_forward_tension_notes=carry_forward_tension_notes,
        initiative_seizer_id=initiative_seizer_id,
        initiative_loser_id=initiative_loser_id,
        initiative_pressure_label=initiative_pressure_label,
        npc_agency_simulation=npc_agency_simulation,
        npc_long_horizon_state=npc_long_horizon_state,
        npc_private_plans=npc_private_plans,
        npc_plan_conflict_resolution=npc_plan_conflict_resolution,
        dramatic_irony=dramatic_irony,
        npc_agency_closure=npc_agency_closure or {},
        unresolved_npc_initiatives=carried_forward_npc_initiatives,
        carried_forward_npc_initiatives=carried_forward_npc_initiatives,
    )

