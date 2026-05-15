from __future__ import annotations

from typing import Any

from ai_stack.langgraph_runtime_executor import (
    RuntimeTurnGraphExecutor,
    _build_authority_aspect_records,
    _build_runtime_aspect_validation,
)
from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.narrative_momentum_contracts import (
    NARRATIVE_MOMENTUM_FAILURE_EVENT_MISSING,
    NARRATIVE_MOMENTUM_SCHEMA_VERSION,
)
from ai_stack.narrative_momentum_engine import derive_narrative_momentum
from ai_stack.dramatic_capability_contracts import (
    NPC_COERCIVE_ACTION_TYPES,
    NPC_ACTION_CONTROLS_HUMAN_ACTOR_REASON,
    NPC_FORCE_PLAYER_SPEECH_FORBIDDEN,
)
from ai_stack.npc_agency_contracts import normalize_npc_agency_plan
from ai_stack.runtime_dramatic_capabilities import build_capability_selection_record
from ai_stack.runtime_aspect_ledger import (
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_COMMIT,
    ASPECT_NARRATIVE_MOMENTUM,
    ASPECT_NPC_AGENCY,
    ASPECT_NPC_AUTHORITY,
    ASPECT_SOCIAL_PRESSURE,
    ASPECT_TONAL_CONSISTENCY,
    ASPECT_VALIDATION,
    build_runtime_intelligence_projection,
    initialize_runtime_aspect_ledger,
)
from ai_stack.social_pressure_contracts import (
    SOCIAL_PRESSURE_BANDS,
    SOCIAL_PRESSURE_SCHEMA_VERSION,
)
from ai_stack.social_pressure_engine import derive_social_pressure
from ai_stack.tonal_consistency_engine import derive_tonal_consistency


def _coercive_action_type() -> str:
    return sorted(NPC_COERCIVE_ACTION_TYPES)[0]


def _state(
    *,
    player_input_kind: str = "action",
    verb: str = "move_to",
    target_query: str = "Bad",
) -> dict[str, Any]:
    return {
        "session_id": "s-authority",
        "module_id": "god_of_carnage",
        "current_scene_id": "living_room",
        "player_input": "Gehe ins Bad",
        "turn_number": 1,
        "nodes_executed": [],
        "node_outcomes": {},
        "interpreted_input": {
            "player_input_kind": player_input_kind,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        },
        "player_action_frame": {
            "player_input_kind": player_input_kind,
            "verb": verb,
            "action_kind": "movement" if verb == "move_to" else "perception",
            "target_query": target_query,
            "resolved_target_id": "bathroom" if target_query == "Bad" else "window",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "source_text": "Gehe ins Bad",
            "affordance_resolution": {
                "affordance_status": "allowed",
                "action_commit_policy": "commit_action",
                "requires_narrator": True,
            },
        },
        "affordance_resolution": {
            "affordance_status": "allowed",
            "action_commit_policy": "commit_action",
            "requires_narrator": True,
        },
        "actor_lane_context": {
            "human_actor_id": "annette_reille",
            "selected_player_role": "annette_reille",
            "npc_actor_ids": ["michel_longstreet", "alain_reille"],
            "actor_lanes": {
                "annette_reille": "human",
                "michel_longstreet": "npc",
                "alain_reille": "npc",
            },
        },
        "turn_aspect_ledger": initialize_runtime_aspect_ledger(
            session_id="s-authority",
            module_id="god_of_carnage",
            turn_number=1,
            turn_kind="player",
            raw_player_input="Gehe ins Bad",
        ),
    }


def _generation(structured: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": True,
        "content": "structured",
        "metadata": {"structured_output": structured},
    }


def _social_pressure_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    policy = load_module_runtime_policy("god_of_carnage", "solo_test").to_dict()
    social_policy = policy["runtime_governance_policy"]["social_pressure"]
    source_scores = social_policy["source_scores"]
    social_risk_band = max(
        source_scores["social_risk_band"],
        key=source_scores["social_risk_band"].get,
    )
    thread_pressure_state = max(
        source_scores["thread_pressure_state"],
        key=source_scores["thread_pressure_state"].get,
    )
    pressure = derive_social_pressure(
        scene_assessment={"thread_pressure_state": thread_pressure_state},
        social_state_record={"social_risk_band": social_risk_band},
        module_runtime_policy=policy,
    )
    return policy, pressure


def _narrative_momentum_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    policy = load_module_runtime_policy("god_of_carnage", "solo_test").to_dict()
    momentum = derive_narrative_momentum(
        scene_plan_record={"semantic_move_kind": "escalate"},
        scene_energy_target={"target_transition": "rise"},
        pacing_rhythm_target={"cadence": "press"},
        social_pressure_target={"target_band": "high"},
        prior_narrative_momentum_state={
            "current_state": "resting",
            "current_score": 0.2,
        },
        module_runtime_policy=policy,
    )
    return policy, momentum


def _tonal_consistency_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    policy = load_module_runtime_policy("god_of_carnage", "solo_test").to_dict()
    tonal = derive_tonal_consistency(
        scene_plan_record={"selected_scene_function": "establish_pressure"},
        scene_energy_target={"target_transition": "rise"},
        pacing_rhythm_target={"cadence": "press"},
        social_pressure_target={"target_band": "high"},
        module_runtime_policy=policy,
    )
    return policy, tonal


def test_movement_requires_narrator_authority() -> None:
    narrator, _npc = _build_authority_aspect_records(
        state=_state(),
        generation=_generation({"spoken_lines": []}),
        proposed_state_effects=[],
    )

    assert narrator["status"] == "failed"
    assert narrator["failure_reason"] == "narrator_required_missing"
    assert narrator["expected_owner"] == "narrator"


def test_perception_requires_narrator_authority() -> None:
    state = _state(player_input_kind="perception", verb="look_at", target_query="Fenster")

    narrator, _npc = _build_authority_aspect_records(
        state=state,
        generation=_generation({"spoken_lines": []}),
        proposed_state_effects=[],
    )

    assert narrator["status"] == "failed"
    assert narrator["failure_reason"] == "narrator_required_missing"


def test_npc_social_reaction_allowed_after_player_action() -> None:
    narrator, npc = _build_authority_aspect_records(
        state=_state(),
        generation=_generation(
            {
                "narration_summary": "Annette steps toward the bathroom door.",
                "spoken_lines": [
                    {"speaker_id": "michel_longstreet", "text": "Please, stay calm."}
                ],
            }
        ),
        proposed_state_effects=[],
    )

    assert narrator["status"] == "passed"
    assert npc["status"] == "passed"
    assert npc["actual"]["npc_takeover_detected"] is False


def test_npc_cannot_execute_player_action() -> None:
    _narrator, npc = _build_authority_aspect_records(
        state=_state(),
        generation=_generation(
            {
                "narration_summary": "The room tightens around the movement.",
                "action_lines": [
                    {"actor_id": "michel_longstreet", "text": "Michel geht ins Bad."}
                ],
            }
        ),
        proposed_state_effects=[],
    )

    assert npc["status"] == "failed"
    assert npc["failure_reason"] == "npc_executed_player_action"
    assert npc["offending_actor_id"] == "michel_longstreet"


def test_npc_cannot_narrate_player_perception() -> None:
    state = _state(player_input_kind="perception", verb="look_at", target_query="Fenster")

    _narrator, npc = _build_authority_aspect_records(
        state=state,
        generation=_generation(
            {
                "narration_summary": "Annette looks toward the window.",
                "spoken_lines": [
                    {"speaker_id": "alain_reille", "text": "Annette sieht aus dem Fenster."}
                ],
            }
        ),
        proposed_state_effects=[],
    )

    assert npc["status"] == "failed"
    assert npc["failure_reason"] == "npc_narrated_player_perception"
    assert npc["expected_owner"] == "narrator"


def test_npc_structured_coercion_of_human_actor_rejected_by_runtime_aspect() -> None:
    state = _state(player_input_kind="speech", verb="", target_query="")

    _narrator, npc = _build_authority_aspect_records(
        state=state,
        generation=_generation(
            {
                "narration_summary": "Narrator consequence.",
                "action_lines": [
                    {
                        "actor_id": "michel_longstreet",
                        "target_actor_id": state["actor_lane_context"]["human_actor_id"],
                        "action_type": _coercive_action_type(),
                    }
                ],
            }
        ),
        proposed_state_effects=[],
    )

    assert npc["status"] == "failed"
    assert npc["failure_reason"] == NPC_ACTION_CONTROLS_HUMAN_ACTOR_REASON
    assert npc["actual"]["npc_takeover_detected"] is True


def test_authority_violation_written_to_aspect_ledger() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    executor.max_self_correction_attempts = 0
    executor.allow_degraded_commit_after_retries = False
    state = _state()
    state["generation"] = _generation(
        {
            "narration_summary": "The movement lands in the room.",
            "action_lines": [
                {"actor_id": "michel_longstreet", "text": "Michel geht ins Bad."}
            ],
        }
    )
    state["proposed_state_effects"] = [
        {"effect_type": "narrative_projection", "description": "The movement lands in the room."}
    ]

    update = executor._validate_seam(state)

    ledger = update["turn_aspect_ledger"]
    npc = ledger["turn_aspect_ledger"][ASPECT_NPC_AUTHORITY]
    cap = ledger["turn_aspect_ledger"][ASPECT_CAPABILITY_SELECTION]
    assert npc["status"] == "failed"
    assert npc["failure_reason"] == "npc_executed_player_action"
    assert cap["status"] == "failed"
    assert cap["actual"]["forbidden_capability_realized"] is True
    assert "npc.execute_player_action.forbidden" in cap["actual"]["realized_capabilities"]
    assert update["validation_outcome"]["status"] == "rejected"
    assert update["validation_outcome"]["reason"] == "npc_executed_player_action"
    assert update["validation_outcome"]["authority_contract_violation"] is True


def test_structured_npc_coercion_written_to_aspect_ledger_and_capability_violation() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    executor.max_self_correction_attempts = 0
    executor.allow_degraded_commit_after_retries = False
    state = _state(player_input_kind="speech", verb="", target_query="")
    state["generation"] = _generation(
        {
            "narration_summary": "Narrator consequence.",
            "action_lines": [
                {
                    "actor_id": "michel_longstreet",
                    "target_actor_id": state["actor_lane_context"]["human_actor_id"],
                    "action_type": _coercive_action_type(),
                }
            ],
        }
    )
    state["proposed_state_effects"] = [
        {"effect_type": "narrative_projection", "description": "Narrator consequence."}
    ]

    update = executor._validate_seam(state)

    ledger = update["turn_aspect_ledger"]
    npc = ledger["turn_aspect_ledger"][ASPECT_NPC_AUTHORITY]
    cap = ledger["turn_aspect_ledger"][ASPECT_CAPABILITY_SELECTION]
    assert update["validation_outcome"]["status"] == "rejected"
    assert update["validation_outcome"]["reason"] == NPC_ACTION_CONTROLS_HUMAN_ACTOR_REASON
    assert npc["failure_reason"] == NPC_ACTION_CONTROLS_HUMAN_ACTOR_REASON
    assert NPC_FORCE_PLAYER_SPEECH_FORBIDDEN in cap["actual"]["violated_capabilities"]


def test_validation_reads_narrator_authority_aspect() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    executor.max_self_correction_attempts = 0
    executor.allow_degraded_commit_after_retries = False
    state = _state()
    state["generation"] = _generation({"spoken_lines": []})
    state["proposed_state_effects"] = []

    update = executor._validate_seam(state)

    assert update["validation_outcome"]["status"] == "rejected"
    assert update["validation_outcome"]["reason"] == "narrator_required_missing"
    validation = update["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_VALIDATION]
    assert validation["status"] == "failed"
    assert validation["failure_reason"] == "narrator_required_missing"


def test_npc_agency_missing_required_initiative_rejects_validation_as_recoverable() -> None:
    state = _state()
    responders = [
        {"actor_id": actor_id, "role": role}
        for actor_id, role in zip(
            state["actor_lane_context"]["npc_actor_ids"],
            ("primary_responder", "secondary_reactor"),
        )
    ]
    expected_actor_ids = [row["actor_id"] for row in responders]
    state["selected_responder_set"] = responders
    plan = normalize_npc_agency_plan(
        {},
        selected_primary_responder_id=expected_actor_ids[0],
        selected_secondary_responder_ids=expected_actor_ids[1:],
        preferred_reaction_order_ids=expected_actor_ids,
        actor_lane_context=state["actor_lane_context"],
    )
    structured_output = {
        "schema_version": "runtime_actor_turn_v1",
        "narration_summary": "The room registers the move while the remaining NPC pressure stays visible.",
        "primary_responder_id": expected_actor_ids[0],
        "spoken_lines": [{"speaker_id": expected_actor_ids[0], "text": "Stay here."}],
        "action_lines": [],
        "initiative_events": [],
    }
    generation = _generation(structured_output)
    proposed = [
        {
            "effect_type": "narrative_projection",
            "description": structured_output["narration_summary"],
        }
    ]
    state["dramatic_generation_packet"] = {"npc_agency_plan": plan}

    result = _build_runtime_aspect_validation(
        state=state,
        generation=generation,
        proposed_state_effects=proposed,
        outcome={"status": "approved", "reason": "seam_ok"},
    )

    npc_validation = result["npc_initiative_validation"]
    expected_missing = [
        actor_id
        for actor_id in plan["required_actor_ids"]
        if actor_id not in npc_validation["realized_actor_ids"]
    ]
    assert result["outcome"]["status"] == "rejected"
    assert result["outcome"]["reason"] == npc_validation["feedback_code"]
    assert result["outcome"]["validator_lane"] == npc_validation["schema_version"]
    assert result["outcome"]["npc_agency_contract_violation"] is True
    assert result["outcome"]["recoverable_rejection"] is True
    assert npc_validation["missing_required_actor_ids"] == expected_missing
    aspect = result["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_NPC_AGENCY]
    assert aspect["status"] == "failed"
    assert aspect["failure_reason"] == npc_validation["feedback_code"]
    assert aspect["actual"]["missing_required_actor_ids"] == expected_missing
    assert aspect["actual"]["not_full_multi_agent_simulation"] is True


def test_player_object_interaction_selects_player_and_narrator_capabilities() -> None:
    record = build_capability_selection_record(
        interpreted_input={"player_input_kind": "action", "npc_response_expected": False},
        player_action_frame={
            "player_input_kind": "action",
            "action_kind": "object_interaction",
            "verb": "take",
        },
        affordance_resolution={"action_commit_policy": "commit_action"},
        narrator_authority={
            "expected": {"required": True},
            "actual": {"narrator_block_present": True},
        },
        npc_authority={"actual": {"spoken_line_count": 0, "action_line_count": 0}},
    )

    assert "player.object_interaction.request" in record["selected_capabilities"]
    assert "narrator.object_state.describe" in record["selected_capabilities"]
    assert "narrator.object_state.describe" in record["realized_capabilities"]
    assert record["status"] == "passed"


def test_perception_request_is_realized_when_narrator_result_is_visible() -> None:
    record = build_capability_selection_record(
        interpreted_input={"player_input_kind": "perception", "npc_response_expected": False},
        player_action_frame={
            "player_input_kind": "perception",
            "action_kind": "perception",
            "verb": "look_at",
        },
        affordance_resolution={"action_commit_policy": "observe_only"},
        narrator_authority={
            "expected": {"required": True},
            "actual": {"narrator_block_present": True, "consequence_realized": True},
        },
        npc_authority={"actual": {"spoken_line_count": 0, "action_line_count": 0}},
    )

    assert "player.perception.request" in record["selected_capabilities"]
    assert "narrator.perception_result.describe" in record["selected_capabilities"]
    assert "player.perception.request" in record["realized_capabilities"]
    assert "narrator.perception_result.describe" in record["realized_capabilities"]
    assert record["status"] == "passed"


def test_npc_execute_player_action_is_blocked_capability() -> None:
    record = build_capability_selection_record(
        interpreted_input={"player_input_kind": "action"},
        player_action_frame={"player_input_kind": "action", "action_kind": "movement", "verb": "move_to"},
        affordance_resolution={"action_commit_policy": "commit_action"},
        narrator_authority={
            "expected": {"required": True},
            "actual": {"narrator_block_present": True},
        },
        npc_authority={
            "failure_reason": "npc_executed_player_action",
            "offending_actor_id": "michel_longstreet",
            "actual": {"spoken_line_count": 0, "action_line_count": 1},
        },
    )

    assert "npc.execute_player_action.forbidden" in record["blocked_capabilities"]
    assert "npc.execute_player_action.forbidden" in record["realized_capabilities"]
    assert record["violations"][0]["capability"] == "npc.execute_player_action.forbidden"
    assert record["status"] == "failed"


def test_selected_capability_must_be_realized_or_marked_missing() -> None:
    record = build_capability_selection_record(
        interpreted_input={"player_input_kind": "action"},
        player_action_frame={"player_input_kind": "action", "action_kind": "movement", "verb": "move_to"},
        affordance_resolution={"action_commit_policy": "commit_action"},
        narrator_authority={
            "expected": {"required": True},
            "actual": {"narrator_block_present": False},
        },
        npc_authority={"actual": {"spoken_line_count": 0, "action_line_count": 0}},
    )

    assert "narrator.location_transition.describe" in record["selected_capabilities"]
    assert "narrator.location_transition.describe" in record["missing_required_capabilities"]
    assert record["status"] == "partial"


def test_action_resolution_short_path_is_enabled_by_module_policy_not_module_id() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    executor.action_resolution_short_path_enabled = True
    state = {
        "module_id": "example_module",
        "player_action_frame": {
            "player_input_kind": "movement_action",
            "action_kind": "movement",
            "verb": "move_to",
        },
        "affordance_resolution": {
            "affordance_status": "allowed",
            "action_commit_policy": "commit_action",
        },
        "module_runtime_policy": {
            "runtime_governance_policy": {
                "action_resolution_short_path": {
                    "enabled": True,
                    "allowed_player_input_kinds": ["movement_action"],
                    "allowed_verbs": ["move_to"],
                    "blocked_player_input_kinds": ["speech"],
                }
            }
        },
    }

    assert executor._route_after_resolve_player_action(state) == "authoritative_action_resolution"
    state["module_runtime_policy"]["runtime_governance_policy"]["action_resolution_short_path"]["enabled"] = False
    assert executor._route_after_resolve_player_action(state) == "full_pipeline"


def test_pure_speech_selects_speech_and_direct_answer_without_narrator_requirement() -> None:
    record = build_capability_selection_record(
        interpreted_input={"player_input_kind": "speech", "npc_response_expected": True},
        player_action_frame={"player_input_kind": "speech", "speech_text": "What happened?"},
        affordance_resolution={"action_commit_policy": "commit_speech"},
        narrator_authority={
            "expected": {"required": False},
            "actual": {"narrator_block_present": False},
        },
        npc_authority={"actual": {"spoken_line_count": 1, "action_line_count": 0}},
    )

    assert "player.speech.request" in record["selected_capabilities"]
    assert "npc.direct_answer.allowed" in record["selected_capabilities"]
    assert "npc.direct_answer.allowed" in record["realized_capabilities"]
    assert not any(cap.startswith("narrator.") for cap in record["required_capabilities"])
    assert record["status"] == "passed"


def test_commit_records_player_action_outcome() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    state = _state()
    state["validation_outcome"] = {"status": "approved", "reason": "test"}
    state["proposed_state_effects"] = [
        {"effect_type": "narrative_projection", "description": "Annette moves."}
    ]

    update = executor._commit_seam(state)

    commit = update["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_COMMIT]
    assert commit["status"] == "passed"
    assert commit["actual"]["commit_applied"] is True
    assert commit["actual"]["player_action_committed"] is True
    assert commit["actual"]["validation_rejection_not_committed"] is False


def test_commit_seam_passes_candidate_deltas_to_state_delta_boundary() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    state = _state()
    state["validation_outcome"] = {"status": "approved", "reason": "test"}
    state["proposed_state_effects"] = [
        {"effect_type": "narrative_projection", "description": "Annette moves."}
    ]
    state["candidate_deltas"] = [
        {"path": "human_actor_id", "operation": "replace", "value": "alain_reille"}
    ]

    update = executor._commit_seam(state)

    committed = update["committed_result"]
    commit = update["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_COMMIT]
    rejection = committed["state_delta_rejection"]
    assert committed["commit_applied"] is False
    assert rejection["path"] == state["candidate_deltas"][0]["path"]
    assert commit["status"] == "failed"
    assert commit["failure_class"] == "hard_contract_failure"
    assert commit["failure_reason"] == rejection["error_code"]
    assert commit["actual"]["state_delta_rejection"] == rejection


def test_recoverable_commit_records_failed_aspects() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    state = _state()
    state["validation_outcome"] = {
        "status": "rejected",
        "reason": "narrator_required_missing",
        "recoverable_rejection": True,
    }
    state["proposed_state_effects"] = [
        {"effect_type": "narrative_projection", "description": "Should not commit."}
    ]

    update = executor._commit_seam(state)

    commit = update["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_COMMIT]
    assert update["committed_result"]["commit_applied"] is False
    assert commit["status"] == "passed"
    assert commit["actual"]["validation_rejection_not_committed"] is True
    assert commit["actual"]["deliberately_not_committed_failure"] == "narrator_required_missing"


def test_social_pressure_validator_ledger_keeps_normalized_policy() -> None:
    policy, pressure = _social_pressure_fixture()
    social_policy = policy["runtime_governance_policy"]["social_pressure"]
    state = _state()
    state["module_runtime_policy"] = policy
    state["social_pressure_state"] = pressure["state"]
    state["social_pressure_target"] = pressure["target"]

    result = _build_runtime_aspect_validation(
        state=state,
        generation=_generation(
            {
                "narration_summary": "The room registers the movement.",
                "action_lines": [],
                "spoken_lines": [],
            }
        ),
        proposed_state_effects=[
            {
                "effect_type": "narrative_projection",
                "description": "The room registers the movement.",
            }
        ],
        outcome={"status": "approved", "reason": "seam_ok"},
    )

    aspect = result["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_SOCIAL_PRESSURE]
    assert aspect["expected"]["schema_version"] == SOCIAL_PRESSURE_SCHEMA_VERSION
    assert aspect["expected"]["policy_present"] is True
    assert aspect["expected"]["policy_enabled"] == social_policy["enabled"]
    assert aspect["actual"]["contract_pass"] is True

    projection = build_runtime_intelligence_projection(result["turn_aspect_ledger"])
    pressure_projection = projection[ASPECT_SOCIAL_PRESSURE]
    assert pressure_projection["policy_present"] is True
    assert pressure_projection["policy_enabled"] == social_policy["enabled"]
    assert pressure_projection["target_band"] == pressure["target"]["target_band"]


def test_narrative_momentum_validator_ledger_keeps_state_machine_policy() -> None:
    policy, momentum = _narrative_momentum_fixture()
    momentum_policy = policy["runtime_governance_policy"]["narrative_momentum"]
    state = _state()
    state["module_runtime_policy"] = policy
    state["narrative_momentum_state"] = momentum["state"]
    state["narrative_momentum_target"] = momentum["target"]

    result = _build_runtime_aspect_validation(
        state=state,
        generation=_generation(
            {
                "narration_summary": "The room tightens around Annette's choice.",
                "action_lines": [],
                "spoken_lines": [],
                "narrative_momentum_events": [
                    {
                        "event_type": "advance",
                        "momentum_state": momentum["target"]["target_state"],
                        "source_refs": momentum["target"]["selected_driver_refs"][:1],
                    }
                ],
            }
        ),
        proposed_state_effects=[
            {
                "effect_type": "narrative_projection",
                "description": "The room tightens around Annette's choice.",
            }
        ],
        outcome={"status": "approved", "reason": "seam_ok"},
    )

    aspect = result["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_NARRATIVE_MOMENTUM]
    assert aspect["expected"]["schema_version"] == NARRATIVE_MOMENTUM_SCHEMA_VERSION
    assert aspect["expected"]["policy_present"] is True
    assert aspect["expected"]["policy_enabled"] == momentum_policy["enabled"]
    assert aspect["selected"]["target_state"] == momentum["target"]["target_state"]
    assert aspect["actual"]["contract_pass"] is True

    projection = build_runtime_intelligence_projection(result["turn_aspect_ledger"])
    momentum_projection = projection[ASPECT_NARRATIVE_MOMENTUM]
    assert momentum_projection["policy_present"] is True
    assert momentum_projection["target_state"] == momentum["target"]["target_state"]
    assert momentum_projection["transition_allowed"] is True
    assert momentum_projection["progress_event_count"] == 1


def test_runtime_aspect_failure_triggers_self_correction_before_final_validation() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    executor.max_self_correction_attempts = 3
    executor.allow_degraded_commit_after_retries = False
    state = _state()
    state["generation"] = _generation(
        {
            "narration_summary": "The movement lands in the room.",
            "action_lines": [
                {"actor_id": "michel_longstreet", "text": "Michel geht ins Bad."}
            ],
        }
    )
    state["proposed_state_effects"] = [
        {"effect_type": "narrative_projection", "description": "The movement lands in the room."}
    ]

    def _fake_self_correct(
        _current_state,
        _current_generation,
        _current_proposed,
        feedback_codes,
        attempt_index,
        preserve_actor_lanes=False,
        **_retry_context_kwargs,
    ):
        return (
            _generation(
                {
                    "narration_summary": "Annette reaches the bathroom door; the room notices the movement.",
                    "action_lines": [],
                    "spoken_lines": [],
                }
            ),
            [
                {
                    "effect_type": "narrative_projection",
                    "description": "Annette reaches the bathroom door; the room notices the movement.",
                }
            ],
            {
                "attempt_index": attempt_index,
                "candidate_model": "test-model",
                "feedback_codes": list(feedback_codes),
                "success": True,
                "parser_error": None,
                "preserve_actor_lanes": preserve_actor_lanes,
            },
        )

    executor._self_correct_generation = _fake_self_correct

    update = executor._validate_seam(state)

    assert update["validation_outcome"]["status"] == "approved"
    assert update["self_correction"]["attempt_count"] == 1
    attempt = update["self_correction"]["attempts"][0]
    assert attempt["trigger_source"] == "runtime_aspect"
    assert attempt["failure_reason_before_retry"] == "npc_executed_player_action"
    assert attempt["runtime_aspect_failure_before_retry"]["failure_reason"] == "npc_executed_player_action"
    assert "npc_executed_player_action" in attempt["feedback_codes"]
    assert attempt["resolved_failure"] is True


def test_social_pressure_failure_triggers_social_pressure_retry_diagnostics() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    executor.max_self_correction_attempts = 1
    executor.allow_degraded_commit_after_retries = False
    policy, pressure = _social_pressure_fixture()
    state = _state()
    state["module_runtime_policy"] = policy
    state["social_pressure_state"] = pressure["state"]
    state["social_pressure_target"] = {
        **pressure["target"],
        "target_band": next(
            band for band in sorted(SOCIAL_PRESSURE_BANDS) if band != pressure["target"]["target_band"]
        ),
    }
    state["generation"] = _generation(
        {
            "narration_summary": "The room registers the movement.",
            "action_lines": [],
            "spoken_lines": [],
        }
    )
    state["proposed_state_effects"] = [
        {
            "effect_type": "narrative_projection",
            "description": "The room registers the movement.",
        }
    ]
    captured_feedback: dict[str, Any] = {}

    def _fake_synthesize(
        _current_state,
        *,
        validation_feedback,
        attempt_index,
    ):
        captured_feedback.update(validation_feedback)
        return ({}, {"attempt_index": attempt_index}, "")

    def _fake_self_correct(
        _current_state,
        _current_generation,
        _current_proposed,
        feedback_codes,
        attempt_index,
        preserve_actor_lanes=False,
        **_retry_context_kwargs,
    ):
        return (
            _current_generation,
            list(_current_proposed),
            {
                "attempt_index": attempt_index,
                "candidate_model": "test-model",
                "feedback_codes": list(feedback_codes),
                "success": True,
                "parser_error": None,
                "preserve_actor_lanes": preserve_actor_lanes,
            },
        )

    executor._synthesize_context_for_retry = _fake_synthesize
    executor._self_correct_generation = _fake_self_correct

    update = executor._validate_seam(state)

    assert update["self_correction"]["attempt_count"] == 1
    attempt = update["self_correction"]["attempts"][0]
    assert attempt["trigger_source"] == "social_pressure"
    assert attempt["social_pressure_failure_before_retry"]["failure_reason"] in (
        attempt["social_pressure_failure_before_retry"]["failure_codes"]
    )
    assert captured_feedback["trigger_source"] == "social_pressure"
    assert captured_feedback["social_pressure_failure_before_retry"] == (
        attempt["social_pressure_failure_before_retry"]
    )


def test_tonal_consistency_failure_triggers_hard_live_retry_diagnostics() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    executor.max_self_correction_attempts = 1
    executor.allow_degraded_commit_after_retries = False
    policy, tonal = _tonal_consistency_fixture()
    state = _state()
    state["module_runtime_policy"] = policy
    state["tonal_consistency_target"] = tonal["target"]
    state["generation"] = _generation(
        {
            "narration_summary": "Quest debug fallback.",
            "action_lines": [],
            "spoken_lines": [],
        }
    )
    state["proposed_state_effects"] = [
        {
            "effect_type": "narrative_projection",
            "description": "Quest debug fallback.",
        }
    ]
    captured_feedback: dict[str, Any] = {}

    def _fake_synthesize(
        _current_state,
        *,
        validation_feedback,
        attempt_index,
    ):
        captured_feedback.update(validation_feedback)
        return ({}, {"attempt_index": attempt_index}, "")

    def _fake_self_correct(
        _current_state,
        _current_generation,
        _current_proposed,
        feedback_codes,
        attempt_index,
        preserve_actor_lanes=False,
        **_retry_context_kwargs,
    ):
        return (
            _current_generation,
            list(_current_proposed),
            {
                "attempt_index": attempt_index,
                "candidate_model": "test-model",
                "feedback_codes": list(feedback_codes),
                "success": True,
                "parser_error": None,
                "preserve_actor_lanes": preserve_actor_lanes,
            },
        )

    executor._synthesize_context_for_retry = _fake_synthesize
    executor._self_correct_generation = _fake_self_correct

    update = executor._validate_seam(state)

    assert update["validation_outcome"]["status"] == "rejected"
    assert update["validation_outcome"]["validator_lane"] == "tonal_consistency_validation_v1"
    assert update["self_correction"]["attempt_count"] == 1
    assert update["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_TONAL_CONSISTENCY]["status"] == "failed"
    attempt = update["self_correction"]["attempts"][0]
    assert attempt["trigger_source"] == "tonal_consistency"
    assert attempt["tonal_consistency_failure_before_retry"]["failure_reason"] in (
        attempt["tonal_consistency_failure_before_retry"]["failure_codes"]
    )
    assert captured_feedback["trigger_source"] == "tonal_consistency"
    assert captured_feedback["tonal_consistency_failure_before_retry"] == (
        attempt["tonal_consistency_failure_before_retry"]
    )


def test_narrative_momentum_failure_triggers_momentum_retry_diagnostics() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    executor.max_self_correction_attempts = 1
    executor.allow_degraded_commit_after_retries = False
    policy, momentum = _narrative_momentum_fixture()
    state = _state()
    state["module_runtime_policy"] = policy
    state["narrative_momentum_state"] = momentum["state"]
    state["narrative_momentum_target"] = momentum["target"]
    state["generation"] = _generation(
        {
            "narration_summary": "The room tightens around Annette's choice.",
            "action_lines": [],
            "spoken_lines": [],
        }
    )
    state["proposed_state_effects"] = [
        {
            "effect_type": "narrative_projection",
            "description": "The room tightens around Annette's choice.",
        }
    ]
    captured_feedback: dict[str, Any] = {}

    def _fake_synthesize(
        _current_state,
        *,
        validation_feedback,
        attempt_index,
    ):
        captured_feedback.update(validation_feedback)
        return ({}, {"attempt_index": attempt_index}, "")

    def _fake_self_correct(
        _current_state,
        _current_generation,
        _current_proposed,
        feedback_codes,
        attempt_index,
        preserve_actor_lanes=False,
        **_retry_context_kwargs,
    ):
        return (
            _generation(
                {
                    "narration_summary": "The room tightens around Annette's choice.",
                    "action_lines": [],
                    "spoken_lines": [],
                    "narrative_momentum_events": [
                        {
                            "event_type": "advance",
                            "momentum_state": momentum["target"]["target_state"],
                            "source_refs": momentum["target"]["selected_driver_refs"][:1],
                        }
                    ],
                }
            ),
            list(_current_proposed),
            {
                "attempt_index": attempt_index,
                "candidate_model": "test-model",
                "feedback_codes": list(feedback_codes),
                "success": True,
                "parser_error": None,
                "preserve_actor_lanes": preserve_actor_lanes,
            },
        )

    executor._synthesize_context_for_retry = _fake_synthesize
    executor._self_correct_generation = _fake_self_correct

    update = executor._validate_seam(state)

    assert update["validation_outcome"]["status"] == "approved"
    assert update["self_correction"]["attempt_count"] == 1
    attempt = update["self_correction"]["attempts"][0]
    assert attempt["trigger_source"] == "narrative_momentum"
    assert attempt["narrative_momentum_failure_before_retry"]["failure_reason"] == (
        NARRATIVE_MOMENTUM_FAILURE_EVENT_MISSING
    )
    assert NARRATIVE_MOMENTUM_FAILURE_EVENT_MISSING in attempt["feedback_codes"]
    assert captured_feedback["trigger_source"] == "narrative_momentum"
    assert captured_feedback["narrative_momentum_failure_before_retry"] == (
        attempt["narrative_momentum_failure_before_retry"]
    )


def test_missing_narrator_authority_triggers_self_correction() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    executor.max_self_correction_attempts = 1
    executor.allow_degraded_commit_after_retries = False
    state = _state()
    state["generation"] = _generation({"spoken_lines": []})
    state["proposed_state_effects"] = []

    def _fake_self_correct(
        _current_state,
        _current_generation,
        _current_proposed,
        feedback_codes,
        attempt_index,
        preserve_actor_lanes=False,
        **_retry_context_kwargs,
    ):
        return (
            _generation(
                {
                    "narration_summary": "Annette stops at the bathroom threshold.",
                    "spoken_lines": [],
                    "action_lines": [],
                }
            ),
            [
                {
                    "effect_type": "narrative_projection",
                    "description": "Annette stops at the bathroom threshold.",
                }
            ],
            {
                "attempt_index": attempt_index,
                "candidate_model": "test-model",
                "feedback_codes": list(feedback_codes),
                "success": True,
                "parser_error": None,
                "preserve_actor_lanes": preserve_actor_lanes,
            },
        )

    executor._self_correct_generation = _fake_self_correct

    update = executor._validate_seam(state)

    assert update["validation_outcome"]["status"] == "approved"
    assert update["self_correction"]["attempt_count"] == 1
    attempt = update["self_correction"]["attempts"][0]
    assert attempt["trigger_source"] == "runtime_aspect"
    assert attempt["failure_reason_before_retry"] == "narrator_required_missing"
    assert "narrator_required_missing" in attempt["feedback_codes"]
