"""Evidence-based Pi7 NPC agency claim readiness."""

from __future__ import annotations

from typing import Any

from ai_stack.npc_agency.npc_agency_contracts import (
    NPC_AGENCY_CLAIM_BOUNDED_RUNTIME_STATUS,
    NPC_AGENCY_CLAIM_FULL_LONG_HORIZON_READY_STATUS,
    NPC_AGENCY_CLAIM_LIVE_STAGING_READY_STATUS,
    NPC_AGENCY_CLAIM_READINESS_SCHEMA_VERSION,
    NPC_AGENCY_CLOSURE_SCHEMA_VERSION,
    NPC_AGENCY_CLOSURE_STATUS_VALUES,
    NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
    NPC_AGENCY_SIMULATION_SCHEMA_VERSION,
    NPC_LONG_HORIZON_STATE_SCHEMA_VERSION,
    NPC_PLAN_CONFLICT_RESOLUTION_SCHEMA_VERSION,
    NPC_PRIVATE_PLAN_SCHEMA_VERSION,
    clean_text,
    coerce_dict_rows,
)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    return str(value or "").strip().lower() in {"1", "true", "yes", "passed", "ok"}


def _gate_record(passed: bool, *, evidence: dict[str, Any] | None = None, blocker: str | None = None) -> dict[str, Any]:
    return {
        "passed": bool(passed),
        "evidence": evidence or {},
        "blocker": blocker if not passed else None,
    }


def assess_npc_agency_claim_readiness(
    *,
    simulation: dict[str, Any] | None = None,
    closure: dict[str, Any] | None = None,
    runtime_aspect: dict[str, Any] | None = None,
    live_trace_evidence: dict[str, Any] | None = None,
    operator_evidence: dict[str, Any] | None = None,
    mcp_evidence: dict[str, Any] | None = None,
    replay_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the only supported readiness surface for Pi7 status promotion."""
    sim = simulation if isinstance(simulation, dict) else {}
    close = closure if isinstance(closure, dict) else {}
    aspect = runtime_aspect if isinstance(runtime_aspect, dict) else {}
    live = live_trace_evidence if isinstance(live_trace_evidence, dict) else {}
    operator = operator_evidence if isinstance(operator_evidence, dict) else {}
    mcp = mcp_evidence if isinstance(mcp_evidence, dict) else {}
    replay = replay_evidence if isinstance(replay_evidence, dict) else {}

    long_state = sim.get("npc_long_horizon_state") if isinstance(sim.get("npc_long_horizon_state"), dict) else {}
    private_plans = coerce_dict_rows(sim.get("npc_private_plans"))
    conflict = (
        sim.get("npc_plan_conflict_resolution")
        if isinstance(sim.get("npc_plan_conflict_resolution"), dict)
        else {}
    )

    bounded_pass = (
        sim.get("schema_version") == NPC_AGENCY_SIMULATION_SCHEMA_VERSION
        and sim.get("contract_status") == NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS
        and bool(sim.get("independent_planning_used"))
        and sim.get("not_full_multi_agent_simulation") is False
    )
    long_horizon_pass = (
        long_state.get("schema_version") == NPC_LONG_HORIZON_STATE_SCHEMA_VERSION
        and bool(coerce_dict_rows(long_state.get("actor_states")))
        and bool(coerce_dict_rows(long_state.get("intention_threads")))
    )
    private_plan_pass = (
        bool(private_plans)
        and all(row.get("schema_version") == NPC_PRIVATE_PLAN_SCHEMA_VERSION for row in private_plans)
        and conflict.get("schema_version") == NPC_PLAN_CONFLICT_RESOLUTION_SCHEMA_VERSION
        and bool(conflict.get("selected_private_plan_ids"))
    )
    closure_pass = (
        close.get("schema_version") == NPC_AGENCY_CLOSURE_SCHEMA_VERSION
        and clean_text(close.get("closure_status")) in NPC_AGENCY_CLOSURE_STATUS_VALUES
        and "durable_carry_forward_required" in close
    )
    live_pass = all(
        [
            _truthy(live.get("live_trace_present")),
            _truthy(live.get("non_mock_generation_pass")),
            not _truthy(live.get("fallback_used")),
            _truthy(operator.get("operator_npc_agency_breakdown_present")),
            _truthy(mcp.get("runtime_aspect_matrix_present")),
            _truthy(replay.get("player_visible_replay_present")),
        ]
    )
    forbidden_actor_absent = aspect.get("npc_forbidden_actor_absent")
    if forbidden_actor_absent is None:
        forbidden_actor_absent = aspect.get("forbidden_actor_absent")
    if forbidden_actor_absent is None:
        forbidden_actor_absent = True
    aspect_pass = (
        _truthy(aspect.get("npc_independent_planning_used") or aspect.get("independent_planning_used"))
        and _truthy(forbidden_actor_absent)
        and _truthy(aspect.get("long_horizon_state_present"))
        and _truthy(aspect.get("private_plan_resolution_present"))
        and _truthy(aspect.get("private_plan_visibility_respected"))
    )

    gates = {
        "bounded_runtime_simulation": _gate_record(
            bounded_pass,
            evidence={
                "schema_version": sim.get("schema_version"),
                "contract_status": sim.get("contract_status"),
                "independent_planning_used": sim.get("independent_planning_used"),
            },
            blocker="bounded_runtime_simulation_evidence_missing",
        ),
        "long_horizon_state": _gate_record(
            long_horizon_pass,
            evidence={"schema_version": long_state.get("schema_version")},
            blocker="long_horizon_state_evidence_missing",
        ),
        "private_independent_planning": _gate_record(
            private_plan_pass,
            evidence={
                "private_plan_count": len(private_plans),
                "conflict_resolution_schema": conflict.get("schema_version"),
            },
            blocker="private_plan_resolution_evidence_missing",
        ),
        "durable_closure": _gate_record(
            closure_pass,
            evidence={
                "schema_version": close.get("schema_version"),
                "closure_status": close.get("closure_status"),
            },
            blocker="durable_closure_evidence_missing",
        ),
        "operator_mcp_trace_surface": _gate_record(
            aspect_pass,
            evidence={
                "runtime_aspect_present": bool(aspect),
                "long_horizon_state_present": aspect.get("long_horizon_state_present"),
                "private_plan_resolution_present": aspect.get("private_plan_resolution_present"),
                "private_plan_visibility_respected": aspect.get("private_plan_visibility_respected"),
            },
            blocker="runtime_aspect_evidence_missing",
        ),
        "live_staging": _gate_record(
            live_pass,
            evidence={
                "live_trace_present": live.get("live_trace_present"),
                "non_mock_generation_pass": live.get("non_mock_generation_pass"),
                "runtime_aspect_matrix_present": mcp.get("runtime_aspect_matrix_present"),
            },
            blocker="live_staging_evidence_missing",
        ),
    }
    blockers = [
        row["blocker"]
        for row in gates.values()
        if isinstance(row, dict) and row.get("blocker")
    ]
    implementation_ready = all(
        gates[key]["passed"]
        for key in (
            "bounded_runtime_simulation",
            "long_horizon_state",
            "private_independent_planning",
            "durable_closure",
            "operator_mcp_trace_surface",
        )
    )
    if implementation_ready and gates["live_staging"]["passed"]:
        status = NPC_AGENCY_CLAIM_FULL_LONG_HORIZON_READY_STATUS
    elif gates["bounded_runtime_simulation"]["passed"] and gates["live_staging"]["passed"]:
        status = NPC_AGENCY_CLAIM_LIVE_STAGING_READY_STATUS
    else:
        status = NPC_AGENCY_CLAIM_BOUNDED_RUNTIME_STATUS

    return {
        "schema_version": NPC_AGENCY_CLAIM_READINESS_SCHEMA_VERSION,
        "claim_status": status,
        "full_claim_allowed": status == NPC_AGENCY_CLAIM_FULL_LONG_HORIZON_READY_STATUS,
        "implementation_ready": implementation_ready,
        "live_staging_ready": bool(gates["live_staging"]["passed"]),
        "gates": gates,
        "blockers": blockers,
    }
