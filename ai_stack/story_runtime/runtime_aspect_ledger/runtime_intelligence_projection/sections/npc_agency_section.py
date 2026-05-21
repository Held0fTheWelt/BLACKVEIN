"""Projection section builder for `npc_agency`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_NPC_AGENCY_SECTION_PARAMS = ('npc_agency_actual', 'npc_agency_expected', 'npc_agency_rec', 'npc_agency_selected')


def build_npc_agency_section(**values: Any) -> dict[str, Any]:
    """Return the npc agency diagnostic section from normalized ledger records."""
    npc_agency_actual = values['npc_agency_actual']
    npc_agency_expected = values['npc_agency_expected']
    npc_agency_rec = values['npc_agency_rec']
    npc_agency_selected = values['npc_agency_selected']
    return {
                    "contract_status": npc_agency_expected.get("contract_status")
                    or npc_agency_actual.get("contract_status"),
                    "not_full_multi_agent_simulation": bool(
                        npc_agency_expected.get("not_full_multi_agent_simulation")
                        or npc_agency_actual.get("not_full_multi_agent_simulation")
                    ),
                    "independent_planning_used": bool(
                        npc_agency_actual.get("independent_planning_used")
                        or npc_agency_expected.get("independent_planning_expected")
                    ),
                    "planner_scope": npc_agency_actual.get("planner_scope"),
                    "candidate_actor_ids": npc_agency_actual.get("candidate_actor_ids")
                    or npc_agency_expected.get("candidate_actor_ids")
                    or [],
                    "planned_actor_ids": npc_agency_actual.get("planned_actor_ids") or [],
                    "realized_actor_ids": npc_agency_actual.get("realized_actor_ids") or [],
                    "missing_required_actor_ids": npc_agency_actual.get("missing_required_actor_ids")
                    or [],
                    "carry_forward_actor_ids": npc_agency_actual.get("carry_forward_actor_ids") or [],
                    "closure_status": npc_agency_actual.get("closure_status"),
                    "long_horizon_state_present": bool(
                        npc_agency_actual.get("long_horizon_state_present")
                        or npc_agency_expected.get("long_horizon_state_present")
                    ),
                    "intention_threads_active": int(npc_agency_actual.get("intention_threads_active") or 0),
                    "intention_threads_carried_forward": int(
                        npc_agency_actual.get("intention_threads_carried_forward") or 0
                    ),
                    "private_plan_resolution_present": bool(
                        npc_agency_actual.get("private_plan_resolution_present")
                        or npc_agency_expected.get("private_plan_resolution_present")
                    ),
                    "private_plan_visibility_respected": bool(
                        npc_agency_actual.get("private_plan_visibility_respected")
                    ),
                    "selected_private_plan_ids": npc_agency_actual.get("selected_private_plan_ids")
                    or npc_agency_selected.get("selected_private_plan_ids")
                    or [],
                    "selected_private_plan_actor_ids": npc_agency_actual.get("selected_private_plan_actor_ids")
                    or npc_agency_selected.get("selected_private_plan_actor_ids")
                    or [],
                    "withheld_private_plan_ids": npc_agency_actual.get("withheld_private_plan_ids") or [],
                    "unrealized_selected_private_plan_actor_ids": npc_agency_actual.get(
                        "unrealized_selected_private_plan_actor_ids"
                    )
                    or [],
                    "error_codes": npc_agency_actual.get("error_codes") or [],
                    "multi_npc_initiative_realized": bool(
                        npc_agency_actual.get("multi_npc_initiative_realized")
                    ),
                    "failure_reason": npc_agency_rec.get("failure_reason")
                    or (_record_reasons(npc_agency_rec)[0] if _record_reasons(npc_agency_rec) else None),
                    "status": npc_agency_rec.get("status"),
                }

