"""Shared NPC agency contracts for the partial Pi7 runtime projection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_stack.goc_frozen_vocab import expand_goc_actor_id_aliases


NPC_AGENCY_PLAN_SCHEMA_VERSION = "npc_agency_plan.v1"
NPC_AGENCY_PLAN_PARTIAL_STATUS = "partial_runtime_projection"
DEFAULT_ALLOWED_BLOCK_TYPES = ("actor_line", "actor_action")
DEFAULT_ALLOWED_OUTPUT_LANES = ("spoken_lines", "action_lines", "initiative_events")
FORBIDDEN_RUNTIME_ACTOR_IDS = frozenset({"visitor"})


@dataclass(frozen=True)
class NPCInitiative:
    actor_id: str
    intent: str
    role: str
    target_actor_id: str | None = None
    required: bool = False
    requirement_scope: str | None = None
    allowed_block_types: tuple[str, ...] = DEFAULT_ALLOWED_BLOCK_TYPES
    allowed_output_lanes: tuple[str, ...] = DEFAULT_ALLOWED_OUTPUT_LANES
    resolved: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        row = {
            "actor_id": self.actor_id,
            "role": self.role,
            "intent": self.intent,
            "allowed_block_types": list(self.allowed_block_types),
            "allowed_output_lanes": list(self.allowed_output_lanes),
            "target_actor_id": self.target_actor_id,
            "required": self.required,
            "requirement_scope": self.requirement_scope,
            "resolved": self.resolved,
        }
        row.update(self.metadata)
        return row


@dataclass(frozen=True)
class NPCAgencyPlan:
    primary_responder_id: str | None
    secondary_responder_ids: tuple[str, ...]
    required_actor_ids: tuple[str, ...]
    npc_initiatives: tuple[NPCInitiative, ...]
    turn_number: Any = None
    minimum_secondary_initiatives_required: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": NPC_AGENCY_PLAN_SCHEMA_VERSION,
            "schema_version": NPC_AGENCY_PLAN_SCHEMA_VERSION,
            "contract_status": NPC_AGENCY_PLAN_PARTIAL_STATUS,
            "implementation_status": NPC_AGENCY_PLAN_PARTIAL_STATUS,
            "not_full_multi_agent_simulation": True,
            "turn_number": self.turn_number,
            "primary_responder_id": self.primary_responder_id,
            "secondary_responder_ids": list(self.secondary_responder_ids),
            "required_actor_ids": list(self.required_actor_ids),
            "minimum_secondary_initiatives_required": self.minimum_secondary_initiatives_required,
            "npc_initiatives": [initiative.to_dict() for initiative in self.npc_initiatives],
        }


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def dedupe_strings(values: list[Any] | tuple[Any, ...]) -> list[str]:
    out: list[str] = []
    for value in values:
        cleaned = clean_text(value)
        if cleaned and cleaned not in out:
            out.append(cleaned)
    return out


def coerce_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return dedupe_strings(value)
    if isinstance(value, tuple):
        return dedupe_strings(value)
    cleaned = clean_text(value)
    return [cleaned] if cleaned else []


def coerce_dict_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def forbidden_actor_ids_from_context(actor_lane_context: dict[str, Any] | None) -> set[str]:
    forbidden: set[str] = set(FORBIDDEN_RUNTIME_ACTOR_IDS)
    ctx = actor_lane_context if isinstance(actor_lane_context, dict) else {}
    raw_ids: list[Any] = []
    raw_forbidden_ids = ctx.get("ai_forbidden_actor_ids")
    if isinstance(raw_forbidden_ids, (list, tuple)):
        raw_ids.extend(raw_forbidden_ids)
    else:
        raw_ids.append(raw_forbidden_ids)
    raw_ids.append(ctx.get("human_actor_id"))
    raw_ids.append(ctx.get("selected_player_role"))
    for raw_actor_id in raw_ids:
        actor_id = clean_text(raw_actor_id)
        if not actor_id:
            continue
        forbidden.update(expand_goc_actor_id_aliases(actor_id))
        forbidden.add(actor_id)
    return {actor_id.lower() for actor_id in forbidden if actor_id}


def is_forbidden_actor_id(actor_id: Any, actor_lane_context: dict[str, Any] | None = None) -> bool:
    cleaned = clean_text(actor_id)
    if not cleaned:
        return False
    aliases = set(expand_goc_actor_id_aliases(cleaned))
    aliases.add(cleaned)
    forbidden = forbidden_actor_ids_from_context(actor_lane_context)
    return any(alias.lower() in forbidden for alias in aliases)


def planned_actor_ids_from_plan(plan: dict[str, Any] | None) -> list[str]:
    normalized = normalize_npc_agency_plan(plan or {})
    if not normalized:
        return []
    initiatives = coerce_dict_rows(normalized.get("npc_initiatives"))
    planned = dedupe_strings([row.get("actor_id") for row in initiatives])
    if planned:
        return planned
    return dedupe_strings(
        [normalized.get("primary_responder_id"), *coerce_string_list(normalized.get("secondary_responder_ids"))]
    )


def required_actor_ids_from_plan(plan: dict[str, Any] | None) -> list[str]:
    normalized = normalize_npc_agency_plan(plan or {})
    if not normalized:
        return []
    initiatives = coerce_dict_rows(normalized.get("npc_initiatives"))
    return dedupe_strings(
        coerce_string_list(normalized.get("required_actor_ids"))
        + [row.get("actor_id") for row in initiatives if bool(row.get("required"))]
    )


def npc_initiatives_from_plan(plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    normalized = normalize_npc_agency_plan(plan or {})
    if not normalized:
        return []
    return coerce_dict_rows(normalized.get("npc_initiatives"))


def forbidden_planned_actor_ids(
    plan: dict[str, Any] | None,
    *,
    actor_lane_context: dict[str, Any] | None = None,
) -> list[str]:
    if not isinstance(plan, dict):
        return []
    raw_actor_ids = dedupe_strings(
        [
            plan.get("primary_responder_id"),
            *coerce_string_list(plan.get("secondary_responder_ids")),
            *[
                row.get("actor_id")
                for row in coerce_dict_rows(plan.get("npc_initiatives"))
                or coerce_dict_rows(plan.get("initiatives"))
            ],
        ]
    )
    return [
        actor_id
        for actor_id in raw_actor_ids
        if is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context)
    ]


def normalize_npc_agency_plan(
    plan: dict[str, Any] | None,
    *,
    selected_primary_responder_id: str | None = None,
    selected_secondary_responder_ids: list[str] | None = None,
    preferred_reaction_order_ids: list[str] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    turn_number: Any = None,
) -> dict[str, Any] | None:
    raw_plan = plan if isinstance(plan, dict) else {}
    legacy_rows = coerce_dict_rows(raw_plan.get("npc_initiatives"))
    if not legacy_rows:
        legacy_rows = coerce_dict_rows(raw_plan.get("initiatives"))

    raw_row_actor_ids = dedupe_strings([row.get("actor_id") for row in legacy_rows])
    selected_secondary = coerce_string_list(selected_secondary_responder_ids or [])
    plan_secondary = coerce_string_list(raw_plan.get("secondary_responder_ids"))

    primary_id = (
        clean_text(raw_plan.get("primary_responder_id"))
        or clean_text(selected_primary_responder_id)
        or (raw_row_actor_ids[0] if raw_row_actor_ids else "")
    )
    if is_forbidden_actor_id(primary_id, actor_lane_context=actor_lane_context):
        primary_id = ""

    secondary_ids = plan_secondary or selected_secondary
    if not secondary_ids and raw_row_actor_ids:
        secondary_ids = [actor_id for actor_id in raw_row_actor_ids if actor_id != primary_id]
    secondary_ids = [
        actor_id
        for actor_id in dedupe_strings(secondary_ids)
        if actor_id != primary_id
        and not is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context)
    ]

    preferred_ids = dedupe_strings(preferred_reaction_order_ids or [])
    planned_actor_ids = preferred_ids or dedupe_strings([primary_id, *secondary_ids]) or raw_row_actor_ids
    for actor_id in raw_row_actor_ids:
        if actor_id not in planned_actor_ids:
            planned_actor_ids.append(actor_id)
    planned_actor_ids = [
        actor_id
        for actor_id in planned_actor_ids
        if not is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context)
    ]
    if primary_id and primary_id not in planned_actor_ids:
        planned_actor_ids.insert(0, primary_id)
    if not primary_id and planned_actor_ids:
        primary_id = planned_actor_ids[0]
    secondary_ids = [actor_id for actor_id in secondary_ids if actor_id != primary_id]
    if not secondary_ids:
        secondary_ids = [actor_id for actor_id in planned_actor_ids if actor_id != primary_id]

    first_secondary_id = secondary_ids[0] if secondary_ids else None
    explicit_required_actor_ids = [
        actor_id
        for actor_id in coerce_string_list(raw_plan.get("required_actor_ids"))
        if not is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context)
    ]
    required_actor_ids = explicit_required_actor_ids or dedupe_strings(
        [primary_id, *([first_secondary_id] if first_secondary_id else [])]
    )
    required_actor_ids = [actor_id for actor_id in required_actor_ids if actor_id in planned_actor_ids]

    row_by_actor = {
        clean_text(row.get("actor_id")): row
        for row in legacy_rows
        if clean_text(row.get("actor_id"))
    }
    initiatives: list[NPCInitiative] = []
    for index, actor_id in enumerate(planned_actor_ids):
        if is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context):
            continue
        row = row_by_actor.get(actor_id, {})
        role = clean_text(row.get("role")) or ("primary_responder" if actor_id == primary_id else "secondary_reactor")
        if actor_id == primary_id:
            fallback_intent = "claim_primary_response"
            requirement_scope = "primary_required"
        elif actor_id == first_secondary_id:
            fallback_intent = "react_to_primary_or_scene_pressure"
            requirement_scope = "one_secondary_minimum"
        else:
            fallback_intent = "react_to_primary_or_scene_pressure"
            requirement_scope = "optional_secondary"

        metadata = {
            key: value
            for key, value in row.items()
            if key
            not in {
                "actor_id",
                "role",
                "intent",
                "initiative_type",
                "allowed_block_types",
                "allowed_output_lanes",
                "target_actor_id",
                "target_id",
                "required",
                "requirement_scope",
                "resolved",
            }
        }
        initiative = NPCInitiative(
            actor_id=actor_id,
            role=role,
            intent=clean_text(row.get("intent")) or clean_text(row.get("initiative_type")) or fallback_intent,
            allowed_block_types=tuple(coerce_string_list(row.get("allowed_block_types")) or DEFAULT_ALLOWED_BLOCK_TYPES),
            allowed_output_lanes=tuple(coerce_string_list(row.get("allowed_output_lanes")) or DEFAULT_ALLOWED_OUTPUT_LANES),
            target_actor_id=clean_text(row.get("target_actor_id") or row.get("target_id")) or None,
            required=bool(row.get("required")) or actor_id in required_actor_ids,
            requirement_scope=clean_text(row.get("requirement_scope")) or requirement_scope,
            resolved=bool(row.get("resolved")),
            metadata=metadata,
        )
        initiatives.append(initiative)

    if not initiatives:
        return None

    normalized = NPCAgencyPlan(
        primary_responder_id=primary_id or None,
        secondary_responder_ids=tuple(secondary_ids),
        required_actor_ids=tuple(required_actor_ids),
        npc_initiatives=tuple(initiatives),
        turn_number=raw_plan.get("turn_number", turn_number),
        minimum_secondary_initiatives_required=1 if secondary_ids else 0,
    ).to_dict()

    for key, value in raw_plan.items():
        if key not in normalized and key != "initiatives":
            normalized[key] = value
    normalized["contract"] = NPC_AGENCY_PLAN_SCHEMA_VERSION
    normalized["schema_version"] = NPC_AGENCY_PLAN_SCHEMA_VERSION
    normalized["contract_status"] = NPC_AGENCY_PLAN_PARTIAL_STATUS
    normalized["implementation_status"] = NPC_AGENCY_PLAN_PARTIAL_STATUS
    normalized["not_full_multi_agent_simulation"] = True
    return normalized
