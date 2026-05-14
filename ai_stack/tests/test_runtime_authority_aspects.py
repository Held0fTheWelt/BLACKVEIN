from __future__ import annotations

from typing import Any

from ai_stack.langgraph_runtime_executor import (
    RuntimeTurnGraphExecutor,
    _build_authority_aspect_records,
)
from ai_stack.runtime_dramatic_capabilities import build_capability_selection_record
from ai_stack.runtime_aspect_ledger import (
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_COMMIT,
    ASPECT_NPC_AUTHORITY,
    ASPECT_VALIDATION,
    initialize_runtime_aspect_ledger,
)


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
