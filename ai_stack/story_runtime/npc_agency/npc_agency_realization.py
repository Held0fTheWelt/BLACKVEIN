"""Realization and closure helpers for Pi7 NPC agency."""

from __future__ import annotations

from typing import Any

from ai_stack.story_runtime.npc_agency.npc_agency_contracts import (
    NPC_AGENCY_CLOSURE_BLOCKED_BY_PLAYER_ACTION_STATUS,
    NPC_AGENCY_CLOSURE_CARRY_FORWARD_STATUS,
    NPC_AGENCY_CLOSURE_CLOSED_STATUS,
    NPC_AGENCY_CLOSURE_EXPIRED_BY_SCENE_TRANSITION_STATUS,
    NPC_AGENCY_CLOSURE_SCHEMA_VERSION,
    NPC_AGENCY_CLOSURE_SUPERSEDED_STATUS,
    NPC_AGENCY_PLAN_PARTIAL_STATUS,
    NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
    clean_text,
    coerce_dict_rows,
    dedupe_strings,
    forbidden_planned_actor_ids,
    is_forbidden_actor_id,
    normalize_npc_agency_simulation,
    normalize_npc_agency_plan,
    planned_actor_ids_from_plan,
)


NPC_INITIATIVE_REALIZATION_SCHEMA_VERSION = "npc_initiative_realization_v1"
NPC_INITIATIVE_VALIDATION_SCHEMA_VERSION = "npc_initiative_validation_v1"


def _collect_actor_ids_from_rows(rows: list[dict[str, Any]], *, speaker_key: str, actor_key: str) -> list[str]:
    actor_ids: list[str] = []
    for row in rows:
        actor_id = clean_text(row.get(speaker_key) or row.get(actor_key))
        if actor_id and actor_id not in actor_ids:
            actor_ids.append(actor_id)
    return actor_ids


def realized_actor_ids_from_structured_output(structured_output: dict[str, Any] | None) -> list[str]:
    output = structured_output if isinstance(structured_output, dict) else {}
    spoken_rows = coerce_dict_rows(output.get("spoken_lines"))
    action_rows = coerce_dict_rows(output.get("action_lines"))
    return _collect_actor_ids_from_rows(
        spoken_rows + action_rows,
        speaker_key="speaker_id",
        actor_key="actor_id",
    )


def _private_plan_evidence(simulation: dict[str, Any] | None) -> dict[str, Any]:
    source = simulation if isinstance(simulation, dict) else {}
    private_plans = coerce_dict_rows(source.get("npc_private_plans"))
    conflict = (
        source.get("npc_plan_conflict_resolution")
        if isinstance(source.get("npc_plan_conflict_resolution"), dict)
        else {}
    )
    selected_ids = dedupe_strings(conflict.get("selected_private_plan_ids") or [])
    if not selected_ids and len(private_plans) == 1:
        selected_ids = dedupe_strings([private_plans[0].get("private_plan_id")])
    selected_id_set = set(selected_ids)
    selected_plans = [
        row
        for row in private_plans
        if clean_text(row.get("private_plan_id")) in selected_id_set
    ]
    withheld_ids = dedupe_strings(
        conflict.get("withheld_private_plan_ids")
        or [
            row.get("private_plan_id")
            for row in private_plans
            if clean_text(row.get("private_plan_id")) not in selected_id_set
        ]
    )
    withheld_id_set = set(withheld_ids)
    withheld_plans = [
        row
        for row in private_plans
        if clean_text(row.get("private_plan_id")) in withheld_id_set
    ]
    return {
        "private_plan_resolution_present": bool(private_plans and selected_ids),
        "selected_private_plan_ids": selected_ids,
        "selected_private_plan_actor_ids": dedupe_strings(
            [row.get("actor_id") for row in selected_plans]
        ),
        "withheld_private_plan_ids": withheld_ids,
        "withheld_private_plan_actor_ids": dedupe_strings(
            [row.get("actor_id") for row in withheld_plans]
        ),
        "selected_private_plan_source_intention_thread_ids": dedupe_strings(
            [
                thread_id
                for row in selected_plans
                for thread_id in (row.get("source_intention_thread_ids") or [])
            ]
        ),
        "private_plan_by_actor": {
            clean_text(row.get("actor_id")): row
            for row in selected_plans
            if clean_text(row.get("actor_id"))
        },
    }


def _simulation_and_plan_payload(
    agency: dict[str, Any] | None,
    *,
    actor_lane_context: dict[str, Any] | None = None,
    turn_number: Any = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    raw = agency if isinstance(agency, dict) else {}
    simulation = None
    if raw.get("contract") == "npc_agency_simulation.v1" or isinstance(raw.get("npc_agency_plan"), dict):
        simulation = normalize_npc_agency_simulation(
            raw,
            actor_lane_context=actor_lane_context,
            turn_number=turn_number,
        )
    plan_payload = (
        simulation.get("npc_agency_plan")
        if isinstance(simulation, dict) and isinstance(simulation.get("npc_agency_plan"), dict)
        else raw
    )
    normalized_plan = normalize_npc_agency_plan(
        plan_payload,
        actor_lane_context=actor_lane_context,
        turn_number=turn_number,
    )
    return simulation, normalized_plan


def build_npc_initiative_realization(
    plan: dict[str, Any] | None,
    *,
    selected_primary_responder_id: str | None = None,
    selected_secondary_responder_ids: list[str] | None = None,
    preferred_reaction_order_ids: list[str] | None = None,
    realized_actor_ids: list[str] | None = None,
    generated_initiative_rows: list[dict[str, Any]] | None = None,
    validated_initiative_rows: list[dict[str, Any]] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    turn_number: Any = None,
) -> dict[str, Any] | None:
    simulation, normalized = _simulation_and_plan_payload(
        plan,
        actor_lane_context=actor_lane_context,
        turn_number=turn_number,
    )
    if normalized and (
        selected_primary_responder_id
        or selected_secondary_responder_ids
        or preferred_reaction_order_ids
    ):
        normalized = normalize_npc_agency_plan(
            normalized,
            selected_primary_responder_id=selected_primary_responder_id,
            selected_secondary_responder_ids=selected_secondary_responder_ids or [],
            preferred_reaction_order_ids=preferred_reaction_order_ids or [],
            actor_lane_context=actor_lane_context,
            turn_number=turn_number,
        )
    if not normalized:
        return None

    initiatives = coerce_dict_rows(normalized.get("npc_initiatives"))
    planned_actor_ids = dedupe_strings([row.get("actor_id") for row in initiatives])
    if not planned_actor_ids:
        return None

    required_actor_ids = dedupe_strings(
        list(normalized.get("required_actor_ids") or [])
        + [row.get("actor_id") for row in initiatives if bool(row.get("required"))]
    )
    realized_ids = dedupe_strings(realized_actor_ids or [])
    realized_initiative_actor_ids = [
        actor_id for actor_id in planned_actor_ids if actor_id in realized_ids
    ]
    generated_event_actor_ids = _collect_actor_ids_from_rows(
        generated_initiative_rows or [],
        speaker_key="actor_id",
        actor_key="actor_id",
    )
    preserved_event_actor_ids = _collect_actor_ids_from_rows(
        validated_initiative_rows or [],
        speaker_key="actor_id",
        actor_key="actor_id",
    )

    full_simulation = isinstance(simulation, dict)
    private_plan_evidence = _private_plan_evidence(simulation)
    unrealized_selected_private_plan_actor_ids = [
        actor_id
        for actor_id in private_plan_evidence["selected_private_plan_actor_ids"]
        if actor_id not in realized_initiative_actor_ids
    ]
    withheld_required_actor_ids = [
        actor_id
        for actor_id in private_plan_evidence["withheld_private_plan_actor_ids"]
        if actor_id in required_actor_ids
    ]
    result = {
        "schema_version": NPC_INITIATIVE_REALIZATION_SCHEMA_VERSION,
        "contract_status": (
            NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS
            if full_simulation
            else NPC_AGENCY_PLAN_PARTIAL_STATUS
        ),
        "not_full_multi_agent_simulation": not full_simulation,
        "independent_planning_used": bool(
            simulation.get("independent_planning_used")
            if isinstance(simulation, dict)
            else False
        ),
        "candidate_actor_ids": list(simulation.get("candidate_actor_ids") or [])
        if isinstance(simulation, dict)
        else planned_actor_ids,
        "planned_actor_ids": planned_actor_ids,
        "realized_initiative_actor_ids": realized_initiative_actor_ids,
        "missing_initiative_actor_ids": [
            actor_id for actor_id in planned_actor_ids if actor_id not in realized_initiative_actor_ids
        ],
        "required_actor_ids": required_actor_ids,
        "unrealized_required_initiative_actor_ids": [
            actor_id for actor_id in required_actor_ids if actor_id not in realized_initiative_actor_ids
        ],
        "generated_initiative_event_actor_ids": generated_event_actor_ids,
        "preserved_initiative_event_actor_ids": preserved_event_actor_ids,
        "initiative_event_only_actor_ids": [
            actor_id
            for actor_id in preserved_event_actor_ids
            if actor_id in planned_actor_ids and actor_id not in realized_initiative_actor_ids
        ],
        "multi_npc_initiative_realized": len(realized_initiative_actor_ids) >= 2,
        "private_plan_resolution_present": private_plan_evidence["private_plan_resolution_present"],
        "selected_private_plan_ids": private_plan_evidence["selected_private_plan_ids"],
        "selected_private_plan_actor_ids": private_plan_evidence["selected_private_plan_actor_ids"],
        "withheld_private_plan_ids": private_plan_evidence["withheld_private_plan_ids"],
        "withheld_private_plan_actor_ids": private_plan_evidence["withheld_private_plan_actor_ids"],
        "selected_private_plan_source_intention_thread_ids": private_plan_evidence[
            "selected_private_plan_source_intention_thread_ids"
        ],
        "unrealized_selected_private_plan_actor_ids": unrealized_selected_private_plan_actor_ids,
        "withheld_required_actor_ids": withheld_required_actor_ids,
        "private_plan_visibility_respected": not bool(withheld_required_actor_ids),
    }
    if not full_simulation:
        result["partial_implementation_reason"] = (
            "Tracks nominated NPC initiative realization in validated actor lanes; "
            "does not simulate independent multi-agent planning."
        )
    return result


def validate_npc_initiative_realization(
    plan: dict[str, Any] | None,
    structured_output: dict[str, Any] | None,
    *,
    actor_lane_context: dict[str, Any] | None = None,
    strict_required: bool = True,
) -> dict[str, Any]:
    realized_actor_ids = realized_actor_ids_from_structured_output(structured_output)
    initiative_rows = coerce_dict_rows(
        structured_output.get("initiative_events") if isinstance(structured_output, dict) else []
    )
    simulation, normalized = _simulation_and_plan_payload(
        plan,
        actor_lane_context=actor_lane_context,
    )
    realization = build_npc_initiative_realization(
        simulation if isinstance(simulation, dict) else normalized,
        realized_actor_ids=realized_actor_ids,
        generated_initiative_rows=initiative_rows,
        validated_initiative_rows=initiative_rows,
        actor_lane_context=actor_lane_context,
    )

    missing_required_actor_ids = (
        list(realization.get("unrealized_required_initiative_actor_ids") or [])
        if isinstance(realization, dict)
        else []
    )
    forbidden_plan_ids = forbidden_planned_actor_ids(
        normalized,
        actor_lane_context=actor_lane_context,
    )
    forbidden_realized_actor_ids = [
        actor_id
        for actor_id in realized_actor_ids
        if is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context)
    ]

    error_codes: list[str] = []
    if not normalized:
        error_codes.append("npc_agency_plan_empty")
    if forbidden_plan_ids:
        error_codes.append("npc_initiative_forbidden_actor_planned")
    if forbidden_realized_actor_ids:
        error_codes.append("npc_initiative_forbidden_actor_realized")
    if missing_required_actor_ids:
        error_codes.append("npc_initiative_missing_required")
    unrealized_selected_private_plan_actor_ids = (
        list(realization.get("unrealized_selected_private_plan_actor_ids") or [])
        if isinstance(realization, dict)
        else []
    )
    withheld_required_actor_ids = (
        list(realization.get("withheld_required_actor_ids") or [])
        if isinstance(realization, dict)
        else []
    )
    if unrealized_selected_private_plan_actor_ids:
        error_codes.append("npc_private_plan_selected_actor_unrealized")
    if withheld_required_actor_ids:
        error_codes.append("npc_private_plan_visibility_violation")

    secondary_ids = list(normalized.get("secondary_responder_ids") or []) if isinstance(normalized, dict) else []
    minimum_secondary = (
        int(normalized.get("minimum_secondary_initiatives_required") or 0)
        if isinstance(normalized, dict)
        else 0
    )
    realized_secondary_ids = [actor_id for actor_id in secondary_ids if actor_id in realized_actor_ids]
    if minimum_secondary > 0 and not realized_secondary_ids:
        error_codes.append("npc_initiative_missing_required_secondary")

    strict_failure = bool(
        forbidden_plan_ids
        or forbidden_realized_actor_ids
        or withheld_required_actor_ids
        or not normalized
    )
    required_failure = bool(
        missing_required_actor_ids
        or unrealized_selected_private_plan_actor_ids
        or "npc_initiative_missing_required_secondary" in error_codes
    )
    if strict_failure or (strict_required and required_failure):
        status = "rejected"
    elif required_failure:
        status = "degraded"
    else:
        status = "approved"

    full_simulation = isinstance(simulation, dict)
    result = {
        "schema_version": NPC_INITIATIVE_VALIDATION_SCHEMA_VERSION,
        "contract_status": (
            NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS
            if full_simulation
            else NPC_AGENCY_PLAN_PARTIAL_STATUS
        ),
        "not_full_multi_agent_simulation": not full_simulation,
        "independent_planning_used": bool(
            simulation.get("independent_planning_used")
            if isinstance(simulation, dict)
            else False
        ),
        "status": status,
        "contract_pass": status == "approved",
        "error_codes": dedupe_strings(error_codes),
        "feedback_code": error_codes[0] if error_codes else None,
        "missing_required_actor_ids": missing_required_actor_ids,
        "unrealized_selected_private_plan_actor_ids": unrealized_selected_private_plan_actor_ids,
        "withheld_required_actor_ids": withheld_required_actor_ids,
        "private_plan_resolution_present": bool(
            realization.get("private_plan_resolution_present")
            if isinstance(realization, dict)
            else False
        ),
        "private_plan_visibility_respected": bool(
            realization.get("private_plan_visibility_respected")
            if isinstance(realization, dict)
            else False
        ),
        "selected_private_plan_ids": list(
            realization.get("selected_private_plan_ids") or []
        )
        if isinstance(realization, dict)
        else [],
        "selected_private_plan_actor_ids": list(
            realization.get("selected_private_plan_actor_ids") or []
        )
        if isinstance(realization, dict)
        else [],
        "withheld_private_plan_ids": list(
            realization.get("withheld_private_plan_ids") or []
        )
        if isinstance(realization, dict)
        else [],
        "selected_private_plan_source_intention_thread_ids": list(
            realization.get("selected_private_plan_source_intention_thread_ids") or []
        )
        if isinstance(realization, dict)
        else [],
        "forbidden_planned_actor_ids": forbidden_plan_ids,
        "forbidden_realized_actor_ids": forbidden_realized_actor_ids,
        "realized_actor_ids": realized_actor_ids,
        "npc_agency_plan": normalized,
        "npc_initiative_realization_v1": realization,
    }
    if full_simulation:
        result["npc_agency_simulation"] = simulation
    return result


def build_npc_agency_closure(
    agency: dict[str, Any] | None,
    *,
    validation: dict[str, Any] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    turn_number: Any = None,
    closure_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    source_validation = validation if isinstance(validation, dict) else {}
    source_agency = (
        source_validation.get("npc_agency_simulation")
        if isinstance(source_validation.get("npc_agency_simulation"), dict)
        else agency
    )
    simulation, plan = _simulation_and_plan_payload(
        source_agency if isinstance(source_agency, dict) else source_validation.get("npc_agency_plan"),
        actor_lane_context=actor_lane_context,
        turn_number=turn_number,
    )
    if not isinstance(plan, dict):
        return None

    realization = (
        source_validation.get("npc_initiative_realization_v1")
        if isinstance(source_validation.get("npc_initiative_realization_v1"), dict)
        else {}
    )
    planned_actor_ids = (
        list(realization.get("planned_actor_ids") or [])
        if realization
        else planned_actor_ids_from_plan(plan)
    )
    realized_actor_ids = dedupe_strings(
        list(source_validation.get("realized_actor_ids") or [])
        + list(realization.get("realized_initiative_actor_ids") or [])
    )
    missing_required_actor_ids = dedupe_strings(
        list(source_validation.get("missing_required_actor_ids") or [])
        + list(realization.get("unrealized_required_initiative_actor_ids") or [])
    )
    private_plan_evidence = _private_plan_evidence(simulation)
    selected_private_plan_by_actor = private_plan_evidence["private_plan_by_actor"]

    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    prior_closure = prior.get("npc_agency_closure") if isinstance(prior.get("npc_agency_closure"), dict) else {}
    prior_rows = coerce_dict_rows(prior_closure.get("carried_forward_npc_initiatives"))
    prior_by_actor = {
        clean_text(row.get("actor_id")): row
        for row in prior_rows
        if clean_text(row.get("actor_id"))
    }
    prior_actor_ids = dedupe_strings([row.get("actor_id") for row in prior_rows])
    closed_actor_ids = [
        actor_id for actor_id in prior_actor_ids if actor_id in realized_actor_ids
    ]
    close_ctx = closure_context if isinstance(closure_context, dict) else {}
    superseded_actor_ids = dedupe_strings(close_ctx.get("superseded_actor_ids") or [])
    blocked_actor_ids = dedupe_strings(close_ctx.get("blocked_by_player_action_actor_ids") or [])
    expired_actor_ids = dedupe_strings(close_ctx.get("expired_by_scene_transition_actor_ids") or [])
    non_carry_actor_ids = set(superseded_actor_ids + blocked_actor_ids + expired_actor_ids)

    initiatives = coerce_dict_rows(plan.get("npc_initiatives"))
    initiative_by_actor = {
        clean_text(row.get("actor_id")): row
        for row in initiatives
        if clean_text(row.get("actor_id"))
    }
    unresolved_actor_ids = dedupe_strings(
        [
            *missing_required_actor_ids,
            *[
                actor_id
                for actor_id in prior_actor_ids
                if actor_id not in realized_actor_ids
                and actor_id not in non_carry_actor_ids
                and not is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context)
            ],
        ]
    )
    unresolved_actor_ids = [actor_id for actor_id in unresolved_actor_ids if actor_id not in non_carry_actor_ids]
    carried_rows: list[dict[str, Any]] = []
    for actor_id in unresolved_actor_ids:
        row = initiative_by_actor.get(actor_id, {})
        prior_row = prior_by_actor.get(actor_id, {})
        private_plan = selected_private_plan_by_actor.get(actor_id, {})
        try:
            count = int(prior_row.get("carry_forward_count") or 0) + 1
        except (TypeError, ValueError):
            count = 1
        carried_rows.append(
            {
                "actor_id": actor_id,
                "turn_number": turn_number,
                "reason": "required_initiative_unrealized"
                if actor_id in missing_required_actor_ids
                else "prior_carry_forward_unclosed",
                "required": True,
                "requirement_scope": row.get("requirement_scope")
                or prior_row.get("requirement_scope")
                or "carry_forward_required",
                "target_actor_id": row.get("target_actor_id") or prior_row.get("target_actor_id"),
                "intent": row.get("intent") or prior_row.get("intent"),
                "private_plan_id": private_plan.get("private_plan_id") or prior_row.get("private_plan_id"),
                "source_intention_thread_ids": list(
                    private_plan.get("source_intention_thread_ids")
                    or prior_row.get("source_intention_thread_ids")
                    or []
                ),
                "resolution_policy": "next_turn_visible_spoken_or_action_lane_required",
                "carry_forward_count": count,
                "source_schema_version": source_validation.get("schema_version")
                or NPC_INITIATIVE_VALIDATION_SCHEMA_VERSION,
            }
        )

    full_simulation = isinstance(simulation, dict)
    if carried_rows:
        closure_status = NPC_AGENCY_CLOSURE_CARRY_FORWARD_STATUS
    elif superseded_actor_ids:
        closure_status = NPC_AGENCY_CLOSURE_SUPERSEDED_STATUS
    elif blocked_actor_ids:
        closure_status = NPC_AGENCY_CLOSURE_BLOCKED_BY_PLAYER_ACTION_STATUS
    elif expired_actor_ids:
        closure_status = NPC_AGENCY_CLOSURE_EXPIRED_BY_SCENE_TRANSITION_STATUS
    else:
        closure_status = NPC_AGENCY_CLOSURE_CLOSED_STATUS
    return {
        "schema_version": NPC_AGENCY_CLOSURE_SCHEMA_VERSION,
        "contract_status": (
            NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS
            if full_simulation
            else NPC_AGENCY_PLAN_PARTIAL_STATUS
        ),
        "closure_status": closure_status,
        "not_full_multi_agent_simulation": not full_simulation,
        "independent_planning_used": bool(
            simulation.get("independent_planning_used")
            if isinstance(simulation, dict)
            else False
        ),
        "turn_number": turn_number,
        "planned_actor_ids": planned_actor_ids,
        "realized_actor_ids": realized_actor_ids,
        "missing_required_actor_ids": missing_required_actor_ids,
        "unresolved_actor_ids": [row["actor_id"] for row in carried_rows],
        "closed_actor_ids": closed_actor_ids,
        "superseded_actor_ids": superseded_actor_ids,
        "blocked_by_player_action_actor_ids": blocked_actor_ids,
        "expired_by_scene_transition_actor_ids": expired_actor_ids,
        "selected_private_plan_ids": private_plan_evidence["selected_private_plan_ids"],
        "withheld_private_plan_ids": private_plan_evidence["withheld_private_plan_ids"],
        "carried_forward_private_plan_ids": dedupe_strings(
            [row.get("private_plan_id") for row in carried_rows]
        ),
        "carried_forward_intention_thread_ids": dedupe_strings(
            [
                thread_id
                for row in carried_rows
                for thread_id in (row.get("source_intention_thread_ids") or [])
            ]
        ),
        "private_plan_resolution_present": private_plan_evidence["private_plan_resolution_present"],
        "carried_forward_npc_initiatives": carried_rows,
        "durable_carry_forward_required": bool(carried_rows),
    }
