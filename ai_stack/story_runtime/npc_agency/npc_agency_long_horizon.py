"""Long-horizon deterministic NPC agency projections for Pi7."""

from __future__ import annotations

from typing import Any

from ai_stack.story_runtime.npc_agency.npc_agency_contracts import (
    NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
    NPC_INTENTION_THREAD_ACTIVE_STATUS,
    NPC_INTENTION_THREAD_SCHEMA_VERSION,
    NPC_LONG_HORIZON_STATE_SCHEMA_VERSION,
    NPC_PLAN_CONFLICT_RESOLUTION_POLICY_REQUIRED_FIRST,
    NPC_PLAN_CONFLICT_RESOLUTION_SCHEMA_VERSION,
    NPC_PRIVATE_PLAN_VISIBILITY_RESOLVER_MAY_SURFACE,
    NPC_PRIVATE_PLAN_SCHEMA_VERSION,
    canonical_actor_id,
    clean_text,
    coerce_dict_rows,
    dedupe_strings,
    is_forbidden_actor_id,
)


def _prior_long_horizon_actor_state(prior_planner_truth: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    state = prior.get("npc_long_horizon_state") if isinstance(prior.get("npc_long_horizon_state"), dict) else {}
    rows = coerce_dict_rows(state.get("actor_states"))
    return {
        canonical_actor_id(row.get("actor_id")): row
        for row in rows
        if canonical_actor_id(row.get("actor_id"))
    }


def _prior_long_horizon_threads(prior_planner_truth: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    state = prior.get("npc_long_horizon_state") if isinstance(prior.get("npc_long_horizon_state"), dict) else {}
    rows = coerce_dict_rows(state.get("intention_threads"))
    return {
        clean_text(row.get("thread_id")): row
        for row in rows
        if clean_text(row.get("thread_id"))
    }


def _thread_id(actor_id: str, turn_number: Any) -> str:
    turn = clean_text(turn_number) or "unknown"
    return f"{actor_id}:intention:{turn}"


def _proposal_by_actor(simulation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        canonical_actor_id(row.get("actor_id")): row
        for row in coerce_dict_rows(simulation.get("npc_intent_proposals"))
        if canonical_actor_id(row.get("actor_id"))
    }


def build_npc_long_horizon_state(
    simulation: dict[str, Any] | None,
    *,
    prior_planner_truth: dict[str, Any] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    turn_number: Any = None,
) -> dict[str, Any] | None:
    """Build a durable per-NPC intention state from committed planner truth."""
    source = simulation if isinstance(simulation, dict) else {}
    candidate_actor_ids = [
        canonical_actor_id(actor_id)
        for actor_id in source.get("candidate_actor_ids") or []
        if canonical_actor_id(actor_id)
        and not is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context)
    ]
    candidate_actor_ids = dedupe_strings(candidate_actor_ids)
    if not candidate_actor_ids:
        return None

    prior_by_actor = _prior_long_horizon_actor_state(prior_planner_truth)
    prior_threads = _prior_long_horizon_threads(prior_planner_truth)
    proposal_by_actor = _proposal_by_actor(source)
    graph = source.get("npc_interaction_graph") if isinstance(source.get("npc_interaction_graph"), dict) else {}
    edges = coerce_dict_rows(graph.get("edges"))
    current_turn = source.get("turn_number", turn_number)

    actor_states: list[dict[str, Any]] = []
    intention_threads: list[dict[str, Any]] = []
    emitted_thread_ids: set[str] = set()
    for actor_id in candidate_actor_ids:
        prior = prior_by_actor.get(actor_id, {})
        proposal = proposal_by_actor.get(actor_id, {})
        thread_id = _thread_id(actor_id, turn_number if turn_number is not None else current_turn)
        prior_thread_ids = dedupe_strings(prior.get("active_intention_thread_ids") or [])
        active_thread_ids = dedupe_strings([*prior_thread_ids, thread_id])
        target_actor_id = canonical_actor_id(proposal.get("target_actor_id")) or None
        relationship_actor_ids = dedupe_strings(
            [
                edge.get("target_actor_id")
                for edge in edges
                if canonical_actor_id(edge.get("source_actor_id")) == actor_id
            ]
            + [
                edge.get("source_actor_id")
                for edge in edges
                if canonical_actor_id(edge.get("target_actor_id")) == actor_id
            ]
        )
        relationship_actor_ids = [
            canonical_actor_id(value)
            for value in relationship_actor_ids
            if canonical_actor_id(value)
            and not is_forbidden_actor_id(value, actor_lane_context=actor_lane_context)
        ]
        durable_goal_codes = dedupe_strings(
            list(prior.get("durable_goal_codes") or [])
            + [proposal.get("intent"), proposal.get("requirement_scope")]
        )
        actor_states.append(
            {
                "actor_id": actor_id,
                "active_intention_thread_ids": active_thread_ids,
                "durable_goal_codes": durable_goal_codes,
                "relationship_actor_ids": relationship_actor_ids,
                "open_pressure_count": len(active_thread_ids),
                "last_planned_turn": current_turn,
                "carry_forward_count": int(prior.get("carry_forward_count") or 0)
                + (1 if actor_id in (source.get("carry_forward_actor_ids") or []) else 0),
            }
        )
        for prior_thread_id in prior_thread_ids:
            if prior_thread_id in emitted_thread_ids or prior_thread_id == thread_id:
                continue
            prior_thread = dict(prior_threads.get(prior_thread_id) or {})
            prior_thread.update(
                {
                    "schema_version": prior_thread.get("schema_version")
                    or NPC_INTENTION_THREAD_SCHEMA_VERSION,
                    "thread_id": prior_thread_id,
                    "actor_id": prior_thread.get("actor_id") or actor_id,
                    "status": prior_thread.get("status") or NPC_INTENTION_THREAD_ACTIVE_STATUS,
                    "last_seen_turn": current_turn,
                    "source_schema_version": prior_thread.get("source_schema_version")
                    or NPC_LONG_HORIZON_STATE_SCHEMA_VERSION,
                }
            )
            intention_threads.append(prior_thread)
            emitted_thread_ids.add(prior_thread_id)
        intention_threads.append(
            {
                "schema_version": NPC_INTENTION_THREAD_SCHEMA_VERSION,
                "thread_id": thread_id,
                "actor_id": actor_id,
                "target_actor_id": target_actor_id,
                "intent": clean_text(proposal.get("intent")) or "maintain_scene_pressure",
                "requirement_scope": clean_text(proposal.get("requirement_scope")) or None,
                "status": NPC_INTENTION_THREAD_ACTIVE_STATUS,
                "created_turn": current_turn,
                "last_seen_turn": current_turn,
                "source_schema_version": source.get("schema_version"),
            }
        )
        emitted_thread_ids.add(thread_id)

    return {
        "schema_version": NPC_LONG_HORIZON_STATE_SCHEMA_VERSION,
        "contract_status": NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
        "turn_number": current_turn,
        "candidate_actor_ids": candidate_actor_ids,
        "actor_states": actor_states,
        "intention_threads": intention_threads,
        "long_horizon_state_used": True,
    }


def build_npc_private_plans(
    simulation: dict[str, Any] | None,
    *,
    long_horizon_state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    source = simulation if isinstance(simulation, dict) else {}
    state = long_horizon_state if isinstance(long_horizon_state, dict) else {}
    actor_state_by_id = {
        canonical_actor_id(row.get("actor_id")): row
        for row in coerce_dict_rows(state.get("actor_states"))
        if canonical_actor_id(row.get("actor_id"))
    }
    plans: list[dict[str, Any]] = []
    for row in coerce_dict_rows(source.get("npc_intent_proposals")):
        actor_id = canonical_actor_id(row.get("actor_id"))
        if not actor_id:
            continue
        actor_state = actor_state_by_id.get(actor_id, {})
        plan_id = f"{actor_id}:private_plan:{clean_text(source.get('turn_number')) or len(plans) + 1}"
        plans.append(
            {
                "schema_version": NPC_PRIVATE_PLAN_SCHEMA_VERSION,
                "private_plan_id": plan_id,
                "actor_id": actor_id,
                "source_intention_thread_ids": list(actor_state.get("active_intention_thread_ids") or []),
                "intent": clean_text(row.get("intent")) or "maintain_scene_pressure",
                "target_actor_id": canonical_actor_id(row.get("target_actor_id")) or None,
                "required": bool(row.get("required")),
                "requirement_scope": clean_text(row.get("requirement_scope")) or None,
                "priority_score": int(row.get("priority_score") or 0),
                "visible_resolution_policy": row.get("resolution_policy"),
                "private_plan_visibility": NPC_PRIVATE_PLAN_VISIBILITY_RESOLVER_MAY_SURFACE,
            }
        )
    return plans


def resolve_npc_private_plans(
    private_plans: list[dict[str, Any]],
    *,
    required_actor_ids: list[str] | None = None,
    primary_actor_id: str | None = None,
) -> dict[str, Any]:
    required = dedupe_strings(required_actor_ids or [])
    primary = canonical_actor_id(primary_actor_id)
    ordered = sorted(
        [row for row in private_plans if isinstance(row, dict)],
        key=lambda row: (
            0 if canonical_actor_id(row.get("actor_id")) in required else 1,
            0 if canonical_actor_id(row.get("actor_id")) == primary else 1,
            -int(row.get("priority_score") or 0),
            clean_text(row.get("private_plan_id")),
        ),
    )
    selected = [
        row
        for row in ordered
        if canonical_actor_id(row.get("actor_id")) in required
    ]
    if not selected and ordered:
        selected = ordered[:1]
    selected_ids = {clean_text(row.get("private_plan_id")) for row in selected}
    return {
        "schema_version": NPC_PLAN_CONFLICT_RESOLUTION_SCHEMA_VERSION,
        "policy": NPC_PLAN_CONFLICT_RESOLUTION_POLICY_REQUIRED_FIRST,
        "selected_private_plan_ids": [row.get("private_plan_id") for row in selected],
        "visible_actor_ids": [canonical_actor_id(row.get("actor_id")) for row in selected],
        "withheld_private_plan_ids": [
            row.get("private_plan_id")
            for row in ordered
            if clean_text(row.get("private_plan_id")) not in selected_ids
        ],
        "minimum_secondary_initiatives_required": 1
        if len([actor_id for actor_id in required if actor_id != primary]) > 0
        else 0,
    }
