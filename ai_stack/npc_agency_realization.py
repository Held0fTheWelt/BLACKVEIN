"""Realization helpers for the partial Pi7 NPC agency projection."""

from __future__ import annotations

from typing import Any

from ai_stack.npc_agency_contracts import (
    NPC_AGENCY_PLAN_PARTIAL_STATUS,
    clean_text,
    coerce_dict_rows,
    dedupe_strings,
    forbidden_planned_actor_ids,
    is_forbidden_actor_id,
    normalize_npc_agency_plan,
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
    normalized = normalize_npc_agency_plan(
        plan,
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

    return {
        "schema_version": NPC_INITIATIVE_REALIZATION_SCHEMA_VERSION,
        "contract_status": NPC_AGENCY_PLAN_PARTIAL_STATUS,
        "not_full_multi_agent_simulation": True,
        "partial_implementation_reason": (
            "Tracks nominated NPC initiative realization in validated actor lanes; "
            "does not simulate independent multi-agent planning."
        ),
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
    }


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
    normalized = normalize_npc_agency_plan(
        plan,
        actor_lane_context=actor_lane_context,
    )
    realization = build_npc_initiative_realization(
        normalized,
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
        plan,
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

    secondary_ids = list(normalized.get("secondary_responder_ids") or []) if isinstance(normalized, dict) else []
    minimum_secondary = (
        int(normalized.get("minimum_secondary_initiatives_required") or 0)
        if isinstance(normalized, dict)
        else 0
    )
    realized_secondary_ids = [actor_id for actor_id in secondary_ids if actor_id in realized_actor_ids]
    if minimum_secondary > 0 and not realized_secondary_ids:
        error_codes.append("npc_initiative_missing_required_secondary")

    strict_failure = bool(forbidden_plan_ids or forbidden_realized_actor_ids or not normalized)
    required_failure = bool(missing_required_actor_ids or "npc_initiative_missing_required_secondary" in error_codes)
    if strict_failure or (strict_required and required_failure):
        status = "rejected"
    elif required_failure:
        status = "degraded"
    else:
        status = "approved"

    return {
        "schema_version": NPC_INITIATIVE_VALIDATION_SCHEMA_VERSION,
        "contract_status": NPC_AGENCY_PLAN_PARTIAL_STATUS,
        "not_full_multi_agent_simulation": True,
        "status": status,
        "contract_pass": status == "approved",
        "error_codes": dedupe_strings(error_codes),
        "feedback_code": error_codes[0] if error_codes else None,
        "missing_required_actor_ids": missing_required_actor_ids,
        "forbidden_planned_actor_ids": forbidden_plan_ids,
        "forbidden_realized_actor_ids": forbidden_realized_actor_ids,
        "realized_actor_ids": realized_actor_ids,
        "npc_agency_plan": normalized,
        "npc_initiative_realization_v1": realization,
    }
