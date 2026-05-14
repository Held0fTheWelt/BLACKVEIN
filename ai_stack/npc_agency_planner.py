"""Deterministic partial NPC agency planner for Pi7."""

from __future__ import annotations

from typing import Any

from ai_stack.npc_agency_contracts import (
    DEFAULT_ALLOWED_BLOCK_TYPES,
    DEFAULT_ALLOWED_OUTPUT_LANES,
    NPC_AGENCY_PLAN_PARTIAL_STATUS,
    clean_text,
    coerce_dict_rows,
    dedupe_strings,
    is_forbidden_actor_id,
    normalize_npc_agency_plan,
)


NPC_AGENCY_PLANNER_CONTRACT = "npc_agency_planner.v1"


def _actor_id_from_responder(row: Any) -> str:
    if not isinstance(row, dict):
        return ""
    return clean_text(row.get("actor_id") or row.get("responder_id"))


def _ordered_responder_rows(
    responders: list[Any],
    *,
    preferred_reaction_order_ids: list[str] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    row_by_actor: dict[str, dict[str, Any]] = {}
    sortable: list[tuple[int, int, str, dict[str, Any]]] = []
    for index, row in enumerate(responders):
        if not isinstance(row, dict):
            continue
        actor_id = _actor_id_from_responder(row)
        if not actor_id or actor_id in row_by_actor:
            continue
        if is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context):
            continue
        row_by_actor[actor_id] = row
        try:
            order = int(row.get("preferred_reaction_order"))
        except (TypeError, ValueError):
            order = index + 1000
        sortable.append((order, index, actor_id, row))

    preferred_ids = [
        actor_id
        for actor_id in dedupe_strings(preferred_reaction_order_ids or [])
        if actor_id in row_by_actor
    ]
    ordered: list[dict[str, Any]] = [row_by_actor[actor_id] for actor_id in preferred_ids]
    for _, _, actor_id, row in sorted(sortable, key=lambda item: (item[0], item[1], item[2])):
        if actor_id not in preferred_ids:
            ordered.append(row)
    return ordered


def _mind_by_actor(character_mind_records: list[Any]) -> dict[str, dict[str, Any]]:
    minds: dict[str, dict[str, Any]] = {}
    for row in character_mind_records:
        if not isinstance(row, dict):
            continue
        actor_id = clean_text(row.get("runtime_actor_id") or row.get("actor_id") or row.get("character_key"))
        if actor_id and actor_id not in minds:
            minds[actor_id] = row
    return minds


def _unresolved_actor_ids_from_prior(prior_planner_truth: dict[str, Any] | None) -> list[str]:
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    actor_ids: list[Any] = []
    for key in (
        "unresolved_npc_initiatives",
        "npc_initiative_carry_forward",
        "carried_forward_npc_initiatives",
    ):
        for row in coerce_dict_rows(prior.get(key)):
            actor_ids.append(row.get("actor_id") or row.get("responder_id"))

    realization = prior.get("npc_initiative_realization_v1")
    if isinstance(realization, dict):
        actor_ids.extend(realization.get("unrealized_required_initiative_actor_ids") or [])
        actor_ids.extend(realization.get("missing_initiative_actor_ids") or [])

    return dedupe_strings(actor_ids)


def _source_evidence(
    *,
    selected_scene_function: str | None,
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
    prior_planner_truth: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    scene_function = clean_text(selected_scene_function)
    if scene_function:
        evidence.append({"source": "selected_scene_function", "value": scene_function})

    semantic = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    move_type = clean_text(semantic.get("move_type") or semantic.get("primary_move_type"))
    if move_type:
        evidence.append({"source": "semantic_move_record", "field": "move_type", "value": move_type})

    social = social_state_record if isinstance(social_state_record, dict) else {}
    social_shift = clean_text(social.get("social_pressure_shift") or social.get("pressure_shift"))
    if social_shift:
        evidence.append({"source": "social_state_record", "field": "social_pressure_shift", "value": social_shift})

    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    carry_forward = clean_text(prior.get("carry_forward_tension_notes"))
    if carry_forward:
        evidence.append({"source": "prior_planner_truth", "field": "carry_forward_tension_notes", "present": True})
    return evidence


def _rationale_codes(
    *,
    responder_count: int,
    selected_scene_function: str | None,
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
    unresolved_actor_ids: list[str],
) -> list[str]:
    codes = ["selected_responder_agency_plan"]
    if responder_count > 1:
        codes.append("multi_npc_participation_available")
    if clean_text(selected_scene_function):
        codes.append("scene_function_guided")
    if isinstance(semantic_move_record, dict) and clean_text(
        semantic_move_record.get("move_type") or semantic_move_record.get("primary_move_type")
    ):
        codes.append("semantic_move_guided")
    if isinstance(social_state_record, dict) and clean_text(
        social_state_record.get("social_pressure_shift") or social_state_record.get("pressure_shift")
    ):
        codes.append("social_pressure_guided")
    if unresolved_actor_ids:
        codes.append("unresolved_npc_initiative_carried_forward")
    return codes


def _intent_for_actor(
    *,
    actor_id: str,
    primary_id: str | None,
    first_secondary_id: str | None,
    role: str,
    selected_scene_function: str | None,
    unresolved_actor_ids: list[str],
) -> tuple[str, str, bool, str | None]:
    if actor_id in unresolved_actor_ids:
        return "carry_forward_unresolved_initiative", "carry_forward_required", True, primary_id
    if actor_id == primary_id:
        scene_function = clean_text(selected_scene_function)
        if scene_function in {"escalate_conflict", "redirect_blame", "probe_motive"}:
            return "claim_scene_pressure", "primary_required", True, None
        return "claim_primary_response", "primary_required", True, None
    if role == "interruption_candidate":
        scope = "one_secondary_minimum" if actor_id == first_secondary_id else "optional_secondary"
        return "interrupt_or_counter_scene_pressure", scope, actor_id == first_secondary_id, primary_id
    scope = "one_secondary_minimum" if actor_id == first_secondary_id else "optional_secondary"
    return "react_to_primary_or_scene_pressure", scope, actor_id == first_secondary_id, primary_id


def build_npc_agency_plan(
    *,
    selected_responder_set: list[Any],
    turn_number: Any = None,
    character_mind_records: list[Any] | None = None,
    social_state_record: dict[str, Any] | None = None,
    semantic_move_record: dict[str, Any] | None = None,
    selected_scene_function: str | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    preferred_reaction_order_ids: list[str] | None = None,
) -> dict[str, Any] | None:
    responders = _ordered_responder_rows(
        selected_responder_set,
        preferred_reaction_order_ids=preferred_reaction_order_ids,
        actor_lane_context=actor_lane_context,
    )
    responder_ids = [_actor_id_from_responder(row) for row in responders]
    responder_ids = dedupe_strings(responder_ids)
    if not responder_ids:
        return None

    primary_id = responder_ids[0]
    secondary_ids = responder_ids[1:]
    first_secondary_id = secondary_ids[0] if secondary_ids else None
    unresolved_actor_ids = [
        actor_id
        for actor_id in _unresolved_actor_ids_from_prior(prior_planner_truth)
        if actor_id in responder_ids
        and not is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context)
    ]
    required_actor_ids = dedupe_strings(
        [primary_id, *([first_secondary_id] if first_secondary_id else []), *unresolved_actor_ids]
    )
    minds = _mind_by_actor(character_mind_records or [])
    evidence = _source_evidence(
        selected_scene_function=selected_scene_function,
        semantic_move_record=semantic_move_record,
        social_state_record=social_state_record,
        prior_planner_truth=prior_planner_truth,
    )

    initiatives: list[dict[str, Any]] = []
    for actor_id in responder_ids:
        responder_row = next((row for row in responders if _actor_id_from_responder(row) == actor_id), {})
        role = clean_text(responder_row.get("role")) or (
            "primary_responder" if actor_id == primary_id else "secondary_reactor"
        )
        intent, requirement_scope, required, target_actor_id = _intent_for_actor(
            actor_id=actor_id,
            primary_id=primary_id,
            first_secondary_id=first_secondary_id,
            role=role,
            selected_scene_function=selected_scene_function,
            unresolved_actor_ids=unresolved_actor_ids,
        )
        mind = minds.get(actor_id, {})
        initiatives.append(
            {
                "actor_id": actor_id,
                "role": role,
                "intent": intent,
                "allowed_block_types": list(DEFAULT_ALLOWED_BLOCK_TYPES),
                "allowed_output_lanes": list(DEFAULT_ALLOWED_OUTPUT_LANES),
                "target_actor_id": target_actor_id if target_actor_id != actor_id else None,
                "required": bool(required or actor_id in required_actor_ids),
                "requirement_scope": requirement_scope,
                "resolution_policy": "visible_spoken_or_action_lane_required"
                if actor_id in required_actor_ids
                else "optional_visible_or_initiative_event",
                "resolved": False,
                "tactical_posture": mind.get("tactical_posture"),
                "pressure_response_bias": mind.get("pressure_response_bias"),
                "source_evidence": list(evidence),
            }
        )

    plan = {
        "contract": "npc_agency_plan.v1",
        "schema_version": "npc_agency_plan.v1",
        "contract_status": NPC_AGENCY_PLAN_PARTIAL_STATUS,
        "implementation_status": NPC_AGENCY_PLAN_PARTIAL_STATUS,
        "not_full_multi_agent_simulation": True,
        "planner_contract": NPC_AGENCY_PLANNER_CONTRACT,
        "planner_status": NPC_AGENCY_PLAN_PARTIAL_STATUS,
        "planner_scope": "bounded_selected_responder_agency",
        "turn_number": turn_number,
        "primary_responder_id": primary_id,
        "secondary_responder_ids": secondary_ids,
        "required_actor_ids": required_actor_ids,
        "minimum_secondary_initiatives_required": 1 if secondary_ids else 0,
        "resolution_policy": {
            "required_lanes": ["spoken_lines", "action_lines"],
            "initiative_event_only_counts_as_realized": False,
            "minimum_secondary_initiatives_required": 1 if secondary_ids else 0,
        },
        "planner_rationale_codes": _rationale_codes(
            responder_count=len(responder_ids),
            selected_scene_function=selected_scene_function,
            semantic_move_record=semantic_move_record,
            social_state_record=social_state_record,
            unresolved_actor_ids=unresolved_actor_ids,
        ),
        "source_evidence": evidence,
        "unresolved_actor_ids_from_prior": unresolved_actor_ids,
        "npc_initiatives": initiatives,
    }
    return normalize_npc_agency_plan(
        plan,
        selected_primary_responder_id=primary_id,
        selected_secondary_responder_ids=secondary_ids,
        preferred_reaction_order_ids=responder_ids,
        actor_lane_context=actor_lane_context,
        turn_number=turn_number,
    )
