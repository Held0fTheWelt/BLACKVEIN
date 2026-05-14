"""Tests for planner-truth preservation and the runtime-truth surface.

Two structural contract additions are pinned here:

- ``StoryNarrativeCommitRecord.planner_truth`` preserves the dramatic planner
  state the validator and director used to shape a turn, so the persistent
  commit record can explain accepted turns truthfully rather than only that
  they were accepted.
- ``runtime_config_status().runtime_truth_surface`` publishes the active
  runtime lane — authority source, runtime graph mode, LangGraph
  availability, generation execution mode, expected vs. active route family,
  prompt-template source, and commit / schema contract versions — without
  collapsing loader or preview state into live state.
"""

from __future__ import annotations

from story_runtime_core import ModelRegistry

from ai_stack.npc_agency_contracts import (
    NPC_AGENCY_CLOSURE_CARRY_FORWARD_STATUS,
    NPC_AGENCY_CLOSURE_SCHEMA_VERSION,
    NPC_LONG_HORIZON_STATE_SCHEMA_VERSION,
    NPC_PLAN_CONFLICT_RESOLUTION_SCHEMA_VERSION,
    NPC_PRIVATE_PLAN_SCHEMA_VERSION,
    NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
    NPC_AGENCY_SIMULATION_SCHEMA_VERSION,
)
from app.story_runtime.commit_models import (
    PlannerTruth,
    StoryNarrativeCommitRecord,
    resolve_narrative_commit,
)
from app.story_runtime.manager import StoryRuntimeManager


def _projection() -> dict:
    return {
        "scenes": [{"scene_id": "s1"}, {"scene_id": "s2"}],
        "start_scene_id": "s1",
        "transition_hints": [{"from": "s1", "to": "s2"}],
    }


def test_planner_truth_populated_from_graph_state() -> None:
    rec = resolve_narrative_commit(
        turn_number=3,
        prior_scene_id="s1",
        player_input="press the issue",
        interpreted_input={"kind": "free_narration"},
        generation={
            "success": True,
            "metadata": {
                "structured_output": {
                    "responder_id": "annette",
                    "primary_responder_id": "annette",
                    "secondary_responder_ids": ["alain"],
                    "function_type": "pressure_probe",
                    "social_outcome": "tension_escalates",
                    "dramatic_direction": "escalate",
                    "initiative_events": [
                        {"actor_id": "annette", "type": "interrupt"},
                        {"actor_id": "alain", "type": "counter"},
                    ],
                    "emotional_shift": {"annette": "agitated"},
                },
            },
        },
        runtime_projection=_projection(),
        graph_state={
            "selected_scene_function": "pressure_probe",
            "scene_assessment": {"core": "stalled"},
            "validation_outcome": {
                "status": "approved",
                "reason": "scope_ok",
                "layers_used": ["scene_packet", "responder_scope"],
            },
            "responder_id": "annette",
            "selected_responder_set": [{"actor_id": "annette"}, {"actor_id": "alain"}],
            "responder_scope": ["annette", "alain"],
            "pacing_mode": "measured",
            "silence_mode": "break",
            "social_outcome": "tension_escalates",
            "dramatic_direction": "escalate",
            "visible_output_bundle": {
                "spoken_lines": [{"speaker_id": "annette", "text": "Enough."}],
                "action_lines": [{"actor_id": "alain", "text": "leans in"}],
            },
            "emotional_shift": {"annette": "agitated"},
            "dramatic_effect_gate": {"passed": True, "tags": ["escalation"]},
            "social_state_record": {
                "prior_continuity_classes": ["blame_pressure"],
                "scene_pressure_state": "high_blame",
                "active_thread_count": 2,
                "thread_pressure_summary_present": True,
                "guidance_phase_key": "phase_2_moral_negotiation",
                "responder_asymmetry_code": "blame_on_host_spouse_axis",
                "social_risk_band": "high",
            },
            "character_mind_summary": {"annette": {"stance": "defensive"}},
            "continuity_impacts": [{"class": "tension_escalation"}],
        },
    )

    assert isinstance(rec, StoryNarrativeCommitRecord)
    assert rec.commit_contract_version == "story_narrative_commit_record.v4"

    pt = rec.planner_truth
    assert isinstance(pt, PlannerTruth)
    assert pt.selected_scene_function == "pressure_probe"
    assert pt.responder_id == "annette"
    assert pt.primary_responder_id == "annette"
    assert pt.secondary_responder_ids == ["alain"]
    assert pt.responder_scope == ["annette", "alain"]
    assert pt.function_type == "pressure_probe"
    assert pt.pacing_mode == "measured"
    assert pt.silence_mode == "break"
    assert pt.spoken_line_count == 1
    assert pt.action_line_count == 1
    assert pt.initiative_summary["event_count"] == 2
    assert pt.initiative_summary["event_types"] == ["interrupt", "counter"]
    assert pt.initiative_summary["actors"] == ["annette", "alain"]
    assert "primary_responder=annette" in (pt.last_actor_outcome_summary or "")
    assert "spoken_lines=1" in (pt.last_actor_outcome_summary or "")
    assert "action_lines=1" in (pt.last_actor_outcome_summary or "")
    assert pt.social_outcome == "tension_escalates"
    assert pt.dramatic_direction == "escalate"
    assert pt.emotional_shift == {"annette": "agitated"}
    assert pt.scene_assessment_core == {"core": "stalled"}
    assert pt.dramatic_effect_gate == {"passed": True, "tags": ["escalation"]}
    assert pt.social_state_summary["summary_source"] == "social_state_record"
    assert pt.social_state_summary["validated"] is True
    assert pt.social_state_summary["social_risk_band"] == "high"
    assert pt.social_state_summary["responder_asymmetry_code"] == "blame_on_host_spouse_axis"
    assert pt.social_state_summary["record"]["scene_pressure_state"] == "high_blame"
    assert pt.social_state_summary["fingerprint"]
    assert pt.character_mind_summary == {"annette": {"stance": "defensive"}}
    assert pt.validation_status == "approved"
    assert pt.validation_reason == "scope_ok"
    assert pt.validator_layers_used == ["scene_packet", "responder_scope"]
    assert pt.continuity_impacts == [{"class": "tension_escalation"}]


def test_planner_truth_persists_current_npc_agency_closure() -> None:
    actor_ids = ["npc_primary", "npc_secondary"]
    simulation = {
        "schema_version": NPC_AGENCY_SIMULATION_SCHEMA_VERSION,
        "contract_status": NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
        "independent_planning_used": True,
        "turn_number": 4,
        "candidate_actor_ids": actor_ids,
        "npc_agency_plan": {
            "primary_responder_id": actor_ids[0],
            "secondary_responder_ids": [actor_ids[1]],
            "required_actor_ids": actor_ids,
            "npc_initiatives": [
                {"actor_id": actor_id, "required": True}
                for actor_id in actor_ids
            ],
        },
        "npc_long_horizon_state": {
            "schema_version": NPC_LONG_HORIZON_STATE_SCHEMA_VERSION,
            "actor_states": [
                {
                    "actor_id": actor_id,
                    "active_intention_thread_ids": [f"{actor_id}:intention:4"],
                }
                for actor_id in actor_ids
            ],
            "intention_threads": [
                {
                    "schema_version": "npc_intention_thread.v1",
                    "thread_id": f"{actor_id}:intention:4",
                    "actor_id": actor_id,
                    "status": "active",
                }
                for actor_id in actor_ids
            ],
        },
        "npc_private_plans": [
            {
                "schema_version": NPC_PRIVATE_PLAN_SCHEMA_VERSION,
                "private_plan_id": f"{actor_id}:private_plan:4",
                "actor_id": actor_id,
                "source_intention_thread_ids": [f"{actor_id}:intention:4"],
            }
            for actor_id in actor_ids
        ],
        "npc_plan_conflict_resolution": {
            "schema_version": NPC_PLAN_CONFLICT_RESOLUTION_SCHEMA_VERSION,
            "selected_private_plan_ids": [f"{actor_id}:private_plan:4" for actor_id in actor_ids],
            "visible_actor_ids": actor_ids,
            "withheld_private_plan_ids": [],
        },
    }
    validation = {
        "schema_version": "npc_initiative_validation_v1",
        "status": "rejected",
        "contract_status": NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
        "not_full_multi_agent_simulation": False,
        "independent_planning_used": True,
        "missing_required_actor_ids": [actor_ids[1]],
        "realized_actor_ids": [actor_ids[0]],
        "npc_agency_simulation": simulation,
        "npc_agency_plan": simulation["npc_agency_plan"],
        "npc_initiative_realization_v1": {
            "planned_actor_ids": actor_ids,
            "realized_initiative_actor_ids": [actor_ids[0]],
            "unrealized_required_initiative_actor_ids": [actor_ids[1]],
        },
    }

    rec = resolve_narrative_commit(
        turn_number=4,
        prior_scene_id="s1",
        player_input="continue",
        interpreted_input={"kind": "free_narration"},
        generation={"metadata": {"structured_output": {}}},
        runtime_projection=_projection(),
        graph_state={
            "turn_number": 4,
            "dramatic_generation_packet": {"npc_agency_simulation": simulation},
            "npc_initiative_validation": validation,
            "actor_lane_context": {"ai_allowed_actor_ids": actor_ids, "npc_actor_ids": actor_ids},
        },
    )

    pt = rec.planner_truth
    assert pt.npc_agency_simulation["schema_version"] == NPC_AGENCY_SIMULATION_SCHEMA_VERSION
    assert pt.npc_long_horizon_state["schema_version"] == NPC_LONG_HORIZON_STATE_SCHEMA_VERSION
    assert {row["schema_version"] for row in pt.npc_private_plans} == {NPC_PRIVATE_PLAN_SCHEMA_VERSION}
    assert pt.npc_plan_conflict_resolution["schema_version"] == NPC_PLAN_CONFLICT_RESOLUTION_SCHEMA_VERSION
    assert pt.npc_agency_closure["schema_version"] == NPC_AGENCY_CLOSURE_SCHEMA_VERSION
    assert pt.npc_agency_closure["closure_status"] == NPC_AGENCY_CLOSURE_CARRY_FORWARD_STATUS
    assert pt.unresolved_npc_initiatives == pt.npc_agency_closure["carried_forward_npc_initiatives"]
    assert [row["actor_id"] for row in pt.carried_forward_npc_initiatives] == validation["missing_required_actor_ids"]
    assert pt.npc_agency_closure["carried_forward_private_plan_ids"] == [f"{actor_ids[1]}:private_plan:4"]
    assert pt.npc_agency_closure["carried_forward_intention_thread_ids"] == [f"{actor_ids[1]}:intention:4"]


def test_planner_truth_absent_when_graph_state_not_provided() -> None:
    """No graph_state → planner_truth present but empty (distinguishes missing
    from negatively-asserted). Back-compat: existing callers that don't pass
    graph_state still receive a valid record."""
    rec = resolve_narrative_commit(
        turn_number=1,
        prior_scene_id="s1",
        player_input="hello",
        interpreted_input={"kind": "free_narration"},
        generation=None,
        runtime_projection=_projection(),
    )

    pt = rec.planner_truth
    assert pt.selected_scene_function is None
    assert pt.responder_id is None
    assert pt.validation_status is None
    assert pt.responder_scope == []
    assert pt.validator_layers_used == []
    assert pt.emotional_shift == {}


def test_prior_social_state_read_back_from_session_history() -> None:
    from app.story_runtime.manager import (
        StorySession,
        _prior_social_state_record_from_session,
    )

    prior_record = {
        "prior_continuity_classes": ["blame_pressure"],
        "scene_pressure_state": "high_blame",
        "active_thread_count": 1,
        "thread_pressure_summary_present": True,
        "guidance_phase_key": "phase_2_moral_negotiation",
        "responder_asymmetry_code": "blame_on_host_spouse_axis",
        "social_risk_band": "high",
        "social_continuity_status": "initial_social_state",
    }
    s = StorySession(
        session_id="sess-social-test",
        module_id="god_of_carnage",
        runtime_projection={"scenes": [], "start_scene_id": "s1"},
    )
    s.history.append(
        {
            "turn_number": 1,
            "narrative_commit": {
                "planner_truth": {
                    "social_state_summary": {
                        "summary_source": "social_state_record",
                        "record": prior_record,
                        "fingerprint": "abc123",
                    }
                }
            },
        }
    )

    assert _prior_social_state_record_from_session(s) == prior_record


def test_runtime_config_status_exposes_live_truth_surface_without_governed_config() -> None:
    mgr = StoryRuntimeManager(governed_runtime_config=None)
    status = mgr.runtime_config_status()
    ts = status.get("runtime_truth_surface")

    assert isinstance(ts, dict)
    # The truth surface contract requires every field in this set to be
    # present; missing fields would leave operators unable to distinguish
    # loaded state from active state.
    expected_keys = {
        "authority_source",
        "runtime_graph_mode",
        "graph_executor_class",
        "langgraph_available",
        "generation_execution_mode",
        "expected_live_route_family",
        "expected_live_route_available",
        "active_route_ids",
        "prompt_template_source",
        "prompt_template_fallback_in_effect",
        "commit_contract_version",
        "runtime_output_schema_version",
        "live_player_governance_enforced",
        "module_scope_advertised",
        "module_scope_truth",
    }
    missing = expected_keys - set(ts.keys())
    assert not missing, f"runtime_truth_surface missing fields: {missing}"

    # No governed config was provided → truth surface must report that honestly,
    # not paper over it by pretending governance is active.
    assert ts["authority_source"] == "blocked_no_authoritative_config"
    assert ts["expected_live_route_available"] is False
    assert ts["active_route_ids"] == []
    assert ts["commit_contract_version"] == "story_narrative_commit_record.v4"
    scope_truth = ts["module_scope_truth"]
    assert scope_truth["contract"] == "story_runtime_module_scope.v1"
    assert scope_truth["runtime_scope"] == "module_specific"
    assert scope_truth["supported_live_module_ids"] == ["god_of_carnage"]
    assert ts["runtime_graph_mode"] in {
        "langgraph_runtime_turn_graph",
        "no_graph",
        "injected_test_graph",
    }


def test_story_state_reports_unsupported_module_scope_honestly() -> None:
    mgr = StoryRuntimeManager(registry=ModelRegistry(), adapters={})
    session = mgr.create_session(
        module_id="other_module",
        runtime_projection={"module_id": "other_module", "start_scene_id": "s1"},
    )

    state = mgr.get_state(session.session_id)
    scope_truth = state["module_scope_truth"]
    assert scope_truth["contract"] == "story_runtime_module_scope.v1"
    assert scope_truth["requested_module_id"] == "other_module"
    assert scope_truth["requested_module_supported"] is False
    assert scope_truth["runtime_scope"] == "module_specific"


def test_runtime_truth_surface_reports_governed_runtime_when_resolved_config_valid() -> None:
    cfg = {
        "config_version": "v-test-1",
        "generation_execution_mode": "ai_only",
        "providers": [
            {
                "provider_id": "mock_provider",
                "provider_type": "mock",
            }
        ],
        "models": [
            {
                "provider_id": "mock_provider",
                "model_id": "mock_llm",
                "model_role": "llm",
                "model_name": "mock-llm",
                "structured_output_capable": True,
            },
            {
                "provider_id": "mock_provider",
                "model_id": "mock_mock",
                "model_role": "mock",
                "model_name": "mock-mock",
            },
        ],
        "routes": [
            {
                "route_id": "narrative_live_generation_global",
                "preferred_model_id": "mock_llm",
                "mock_model_id": "mock_mock",
            }
        ],
    }
    mgr = StoryRuntimeManager(governed_runtime_config=cfg)
    ts = mgr.runtime_config_status().get("runtime_truth_surface") or {}

    assert ts["authority_source"] == "governed_resolved_runtime_config"
    assert ts["generation_execution_mode"] == "ai_only"
    assert "narrative_live_generation_global" in ts["active_route_ids"]
    assert ts["expected_live_route_available"] is True
