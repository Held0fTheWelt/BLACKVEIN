"""Deterministic NPC agency planners for Pi7."""

from __future__ import annotations

from typing import Any

from ai_stack.npc_agency_contracts import (
    DEFAULT_ALLOWED_BLOCK_TYPES,
    DEFAULT_ALLOWED_OUTPUT_LANES,
    NPC_AGENCY_PLAN_PARTIAL_STATUS,
    NPC_AGENCY_PLANNER_SCOPE_INDEPENDENT,
    NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
    NPC_AGENCY_SIMULATION_SCHEMA_VERSION,
    canonical_actor_id,
    clean_text,
    coerce_dict_rows,
    dedupe_strings,
    is_forbidden_actor_id,
    normalize_npc_agency_simulation,
    normalize_npc_agency_plan,
    npc_actor_ids_from_context,
)
from ai_stack.npc_agency_long_horizon import (
    build_npc_long_horizon_state,
    build_npc_private_plans,
    resolve_npc_private_plans,
)


NPC_AGENCY_PLANNER_CONTRACT = "npc_agency_planner.v1"
NPC_AGENCY_SIMULATION_PLANNER_CONTRACT = "npc_agency_planner.v2"


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
        actor_id = canonical_actor_id(row.get("runtime_actor_id") or row.get("actor_id") or row.get("character_key"))
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

    closure = prior.get("npc_agency_closure")
    if isinstance(closure, dict):
        actor_ids.extend(closure.get("unresolved_actor_ids") or [])
        actor_ids.extend(closure.get("missing_required_actor_ids") or [])
        for row in coerce_dict_rows(closure.get("carried_forward_npc_initiatives")):
            actor_ids.append(row.get("actor_id") or row.get("responder_id"))

    return dedupe_strings(actor_ids)


def _social_pressure_signal(social_state_record: dict[str, Any] | None) -> dict[str, Any]:
    social = social_state_record if isinstance(social_state_record, dict) else {}
    if not social:
        return {"present": False, "reason_codes": []}

    relationship_codes = dedupe_strings(
        social.get("relationship_pressure_codes")
        if isinstance(social.get("relationship_pressure_codes"), list)
        else []
    )
    legacy_shift = clean_text(social.get("social_pressure_shift") or social.get("pressure_shift"))
    risk_band = clean_text(social.get("social_risk_band"))
    asymmetry = clean_text(social.get("responder_asymmetry_code"))
    pressure_state = clean_text(social.get("scene_pressure_state"))
    continuity_status = clean_text(social.get("social_continuity_status"))

    reason_codes: list[str] = list(relationship_codes)
    if legacy_shift:
        reason_codes.append("legacy_social_pressure_shift")
    if risk_band == "high":
        reason_codes.append("risk:high")
    if asymmetry and asymmetry != "neutral":
        reason_codes.append(f"asymmetry:{asymmetry}")
    if pressure_state in {"high_blame", "thread_pressure_high"}:
        reason_codes.append(f"scene_pressure:{pressure_state}")
    if continuity_status == "social_state_shifted":
        reason_codes.append("continuity:social_state_shifted")
    reason_codes = dedupe_strings(reason_codes)

    if legacy_shift:
        return {
            "present": True,
            "field": "social_pressure_shift",
            "value": legacy_shift,
            "reason_codes": reason_codes,
        }
    if relationship_codes:
        return {
            "present": True,
            "field": "relationship_pressure_codes",
            "value": ",".join(relationship_codes[:4]),
            "reason_codes": reason_codes,
        }
    if risk_band == "high":
        return {
            "present": True,
            "field": "social_risk_band",
            "value": risk_band,
            "reason_codes": reason_codes,
        }
    if asymmetry and asymmetry != "neutral":
        return {
            "present": True,
            "field": "responder_asymmetry_code",
            "value": asymmetry,
            "reason_codes": reason_codes,
        }
    if pressure_state in {"high_blame", "thread_pressure_high"}:
        return {
            "present": True,
            "field": "scene_pressure_state",
            "value": pressure_state,
            "reason_codes": reason_codes,
        }
    if continuity_status == "social_state_shifted":
        return {
            "present": True,
            "field": "social_continuity_status",
            "value": continuity_status,
            "reason_codes": reason_codes,
        }
    return {"present": False, "reason_codes": reason_codes}


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

    social_signal = _social_pressure_signal(social_state_record)
    if social_signal.get("present"):
        evidence.append(
            {
                "source": "social_state_record",
                "field": social_signal.get("field"),
                "value": social_signal.get("value"),
                "reason_codes": list(social_signal.get("reason_codes") or [])[:6],
            }
        )

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
    if _social_pressure_signal(social_state_record).get("present"):
        codes.append("social_pressure_guided")
    if unresolved_actor_ids:
        codes.append("unresolved_npc_initiative_carried_forward")
    return codes


def _simulation_rationale_codes(
    *,
    candidate_actor_count: int,
    responder_count: int,
    selected_scene_function: str | None,
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
    unresolved_actor_ids: list[str],
) -> list[str]:
    codes = ["independent_npc_roster_planned"]
    if candidate_actor_count > responder_count:
        codes.append("planner_considered_non_responder_npcs")
    if candidate_actor_count > 1:
        codes.append("multi_npc_participation_available")
    if clean_text(selected_scene_function):
        codes.append("scene_function_guided")
    if isinstance(semantic_move_record, dict) and clean_text(
        semantic_move_record.get("move_type") or semantic_move_record.get("primary_move_type")
    ):
        codes.append("semantic_move_guided")
    if _social_pressure_signal(social_state_record).get("present"):
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


def _candidate_actor_ids_for_simulation(
    *,
    npc_actor_ids: list[Any] | None,
    responders: list[dict[str, Any]],
    character_mind_records: list[Any] | None,
    unresolved_actor_ids: list[str],
    actor_lane_context: dict[str, Any] | None,
) -> list[str]:
    raw_ids: list[Any] = []
    context_ids = npc_actor_ids_from_context(actor_lane_context)
    raw_ids.extend(context_ids)
    raw_ids.extend(npc_actor_ids or [])
    raw_ids.extend(_actor_id_from_responder(row) for row in responders)
    raw_ids.extend(_mind_by_actor(character_mind_records or []).keys())
    raw_ids.extend(unresolved_actor_ids)

    out: list[str] = []
    for raw_actor_id in raw_ids:
        actor_id = canonical_actor_id(raw_actor_id)
        if not actor_id or actor_id in out:
            continue
        if is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context):
            continue
        out.append(actor_id)
    return out


def _candidate_priority_score(
    *,
    actor_id: str,
    responder_rank: dict[str, int],
    unresolved_actor_ids: list[str],
    selected_scene_function: str | None,
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
    mind: dict[str, Any],
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    if actor_id in unresolved_actor_ids:
        score += 100
        reasons.append("carry_forward_required")
    if actor_id in responder_rank:
        score += max(0, 50 - responder_rank[actor_id])
        reasons.append("director_selected_responder")
    if clean_text(selected_scene_function):
        score += 10
        reasons.append("scene_function_pressure")
    semantic = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    if clean_text(semantic.get("move_type") or semantic.get("primary_move_type")):
        score += 5
        reasons.append("semantic_move_pressure")
    if _social_pressure_signal(social_state_record).get("present"):
        score += 5
        reasons.append("social_state_pressure")
    if clean_text(mind.get("tactical_posture")) or clean_text(mind.get("pressure_response_bias")):
        score += 1
        reasons.append("character_mind_available")
    return score, reasons


def build_npc_agency_simulation(
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
    npc_actor_ids: list[Any] | None = None,
    npc_response_expected: bool | None = None,
    npc_context_bundle: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    responders = _ordered_responder_rows(
        selected_responder_set,
        preferred_reaction_order_ids=preferred_reaction_order_ids,
        actor_lane_context=actor_lane_context,
    )
    responder_ids = dedupe_strings([canonical_actor_id(_actor_id_from_responder(row)) for row in responders])
    unresolved_actor_ids = [
        canonical_actor_id(actor_id)
        for actor_id in _unresolved_actor_ids_from_prior(prior_planner_truth)
        if not is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context)
    ]
    unresolved_actor_ids = dedupe_strings(unresolved_actor_ids)
    if npc_response_expected is False and not unresolved_actor_ids:
        return None
    if not responder_ids and not unresolved_actor_ids:
        return None
    if len(responder_ids) < 2 and not unresolved_actor_ids:
        return None
    candidate_actor_ids = _candidate_actor_ids_for_simulation(
        npc_actor_ids=npc_actor_ids,
        responders=responders,
        character_mind_records=character_mind_records,
        unresolved_actor_ids=unresolved_actor_ids,
        actor_lane_context=actor_lane_context,
    )
    if not candidate_actor_ids:
        return None

    responder_rank = {actor_id: index for index, actor_id in enumerate(responder_ids)}
    minds = _mind_by_actor(character_mind_records or [])
    evidence = _source_evidence(
        selected_scene_function=selected_scene_function,
        semantic_move_record=semantic_move_record,
        social_state_record=social_state_record,
        prior_planner_truth=prior_planner_truth,
    )
    if isinstance(npc_context_bundle, dict):
        lane_notes = {
            "source": "npc_context_bundle",
            "field": "retrieval_lanes",
            "allowed_memory_lanes": list(npc_context_bundle.get("retrieval_plan", {}).get("allowed_memory_lanes") or []),
            "blocked_memory_lanes": list(npc_context_bundle.get("retrieval_plan", {}).get("blocked_memory_lanes") or []),
        }
        evidence.append(lane_notes)

    scored: list[tuple[int, int, int, str, list[str]]] = []
    for index, actor_id in enumerate(candidate_actor_ids):
        score, reasons = _candidate_priority_score(
            actor_id=actor_id,
            responder_rank=responder_rank,
            unresolved_actor_ids=unresolved_actor_ids,
            selected_scene_function=selected_scene_function,
            semantic_move_record=semantic_move_record,
            social_state_record=social_state_record,
            mind=minds.get(actor_id, {}),
        )
        scored.append((-score, responder_rank.get(actor_id, 999), index, actor_id, reasons))
    ordered_actor_ids = [item[3] for item in sorted(scored, key=lambda item: (item[0], item[1], item[2], item[3]))]
    primary_id = ordered_actor_ids[0]
    secondary_ids = [actor_id for actor_id in ordered_actor_ids if actor_id != primary_id]
    first_secondary_id = secondary_ids[0] if secondary_ids else None
    required_actor_ids = dedupe_strings(
        [
            primary_id,
            *([first_secondary_id] if first_secondary_id else []),
            *[actor_id for actor_id in unresolved_actor_ids if actor_id in ordered_actor_ids],
        ]
    )

    proposals: list[dict[str, Any]] = []
    score_by_actor = {item[3]: -item[0] for item in scored}
    reason_by_actor = {item[3]: item[4] for item in scored}
    for rank, actor_id in enumerate(ordered_actor_ids, start=1):
        mind = minds.get(actor_id, {})
        if actor_id in unresolved_actor_ids:
            role = "carry_forward_initiator"
            intent = "carry_forward_unresolved_initiative"
            requirement_scope = "carry_forward_required"
            required = True
            target_actor_id = primary_id if actor_id != primary_id else first_secondary_id
        elif actor_id == primary_id:
            role = "primary_initiator"
            intent = "claim_scene_pressure"
            requirement_scope = "primary_required"
            required = True
            target_actor_id = first_secondary_id
        elif actor_id == first_secondary_id:
            role = "secondary_reactor"
            intent = "counter_or_react_to_scene_pressure"
            requirement_scope = "one_secondary_minimum"
            required = True
            target_actor_id = primary_id
        elif actor_id in responder_rank:
            role = "selected_responder"
            intent = "react_to_primary_or_scene_pressure"
            requirement_scope = "optional_selected_responder"
            required = False
            target_actor_id = primary_id
        else:
            role = "independent_observer"
            intent = "observe_or_pressure_scene"
            requirement_scope = "optional_roster_actor"
            required = False
            target_actor_id = primary_id
        proposals.append(
            {
                "actor_id": actor_id,
                "role": role,
                "intent": intent,
                "target_actor_id": target_actor_id if target_actor_id != actor_id else None,
                "urgency_rank": rank,
                "priority_score": score_by_actor.get(actor_id, 0),
                "pressure_reason_codes": reason_by_actor.get(actor_id, []),
                "required": bool(required or actor_id in required_actor_ids),
                "requirement_scope": requirement_scope,
                "allowed_block_types": list(DEFAULT_ALLOWED_BLOCK_TYPES),
                "allowed_output_lanes": list(DEFAULT_ALLOWED_OUTPUT_LANES),
                "resolution_policy": "visible_spoken_or_action_lane_required"
                if actor_id in required_actor_ids
                else "optional_visible_or_initiative_event",
                "resolved": False,
                "tactical_posture": mind.get("tactical_posture"),
                "pressure_response_bias": mind.get("pressure_response_bias"),
                "source_evidence": list(evidence),
            }
        )

    plan = normalize_npc_agency_plan(
        {
            "contract": "npc_agency_plan.v1",
            "schema_version": "npc_agency_plan.v1",
            "planner_contract": NPC_AGENCY_SIMULATION_PLANNER_CONTRACT,
            "planner_status": NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
            "planner_scope": NPC_AGENCY_PLANNER_SCOPE_INDEPENDENT,
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
            "planner_rationale_codes": _simulation_rationale_codes(
                candidate_actor_count=len(candidate_actor_ids),
                responder_count=len(responder_ids),
                selected_scene_function=selected_scene_function,
                semantic_move_record=semantic_move_record,
                social_state_record=social_state_record,
                unresolved_actor_ids=unresolved_actor_ids,
            ),
            "source_evidence": evidence,
            "unresolved_actor_ids_from_prior": unresolved_actor_ids,
            "npc_initiatives": proposals,
        },
        selected_primary_responder_id=primary_id,
        selected_secondary_responder_ids=secondary_ids,
        preferred_reaction_order_ids=ordered_actor_ids,
        actor_lane_context=actor_lane_context,
        turn_number=turn_number,
    )
    if not plan:
        return None

    simulation = {
        "contract": NPC_AGENCY_SIMULATION_SCHEMA_VERSION,
        "schema_version": NPC_AGENCY_SIMULATION_SCHEMA_VERSION,
        "contract_status": NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
        "implementation_status": NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
        "not_full_multi_agent_simulation": False,
        "planner_contract": NPC_AGENCY_SIMULATION_PLANNER_CONTRACT,
        "planner_status": NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
        "planner_scope": NPC_AGENCY_PLANNER_SCOPE_INDEPENDENT,
        "independent_planning_used": True,
        "turn_number": turn_number,
        "candidate_actor_ids": candidate_actor_ids,
        "selected_responder_ids": responder_ids,
        "selected_primary_responder_id": responder_ids[0] if responder_ids else None,
        "selected_secondary_responder_ids": responder_ids[1:] if len(responder_ids) > 1 else [],
        "ordered_actor_ids": ordered_actor_ids,
        "required_actor_ids": required_actor_ids,
        "carry_forward_actor_ids": [actor_id for actor_id in unresolved_actor_ids if actor_id in ordered_actor_ids],
        "dropped_carry_forward_actor_ids": [
            actor_id for actor_id in unresolved_actor_ids if actor_id not in ordered_actor_ids
        ],
        "planner_rationale_codes": plan.get("planner_rationale_codes") or [],
        "source_evidence": evidence,
        "npc_intent_proposals": proposals,
        "npc_interaction_graph": {
            "nodes": [{"actor_id": actor_id} for actor_id in ordered_actor_ids],
            "edges": [
                {
                    "source_actor_id": row["actor_id"],
                    "target_actor_id": row.get("target_actor_id"),
                    "edge_type": "initiative_pressure",
                }
                for row in proposals
                if row.get("target_actor_id")
            ],
        },
        "conflict_resolution": {
            "policy": "carry_forward_then_director_priority_then_roster_order",
            "primary_actor_id": primary_id,
            "required_actor_ids": required_actor_ids,
            "minimum_secondary_initiatives_required": 1 if secondary_ids else 0,
        },
        "npc_agency_plan": plan,
    }
    long_horizon_state = build_npc_long_horizon_state(
        simulation,
        prior_planner_truth=prior_planner_truth,
        actor_lane_context=actor_lane_context,
        turn_number=turn_number,
    )
    private_plans = build_npc_private_plans(
        simulation,
        long_horizon_state=long_horizon_state,
    )
    simulation["npc_long_horizon_state"] = long_horizon_state
    simulation["npc_private_plans"] = private_plans
    simulation["npc_plan_conflict_resolution"] = resolve_npc_private_plans(
        private_plans,
        required_actor_ids=required_actor_ids,
        primary_actor_id=primary_id,
    )
    return normalize_npc_agency_simulation(
        simulation,
        actor_lane_context=actor_lane_context,
        turn_number=turn_number,
    )


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
    npc_context_bundle: dict[str, Any] | None = None,
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
    if isinstance(npc_context_bundle, dict):
        evidence.append(
            {
                "source": "npc_context_bundle",
                "field": "retrieval_lanes",
                "allowed_memory_lanes": list(
                    npc_context_bundle.get("retrieval_plan", {}).get("allowed_memory_lanes") or []
                ),
                "blocked_memory_lanes": list(
                    npc_context_bundle.get("retrieval_plan", {}).get("blocked_memory_lanes") or []
                ),
            }
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
