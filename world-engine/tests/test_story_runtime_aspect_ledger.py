from __future__ import annotations

from typing import Any

from ai_stack import RuntimeTurnGraphExecutor
from ai_stack.runtime_aspect_ledger import (
    ASPECT_BEAT,
    ASPECT_COMMIT,
    ASPECT_NARRATOR_AUTHORITY,
    ASPECT_VALIDATION,
    ASPECT_VISIBLE_PROJECTION,
    initialize_runtime_aspect_ledger,
    make_aspect_record,
    set_aspect_record,
)

from app.story_runtime import StoryRuntimeManager
from app.story_runtime.manager import (
    _live_scene_blocks_from_visible_bundle,
    _record_visible_projection_aspect,
)


class _FakeGraphInvoker:
    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        return state


class _FakeTurnGraph:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return dict(self._payload)


def _envelope(
    *,
    interpreted_input: dict[str, Any],
    generation: dict[str, Any],
) -> dict[str, Any]:
    gen = dict(generation)
    if "content" not in gen and "model_raw_text" not in gen:
        gen["content"] = "x" * 120
    return {
        "interpreted_input": interpreted_input,
        "generation": gen,
        "graph_diagnostics": {"errors": []},
        "retrieval": {"domain": "runtime", "status": "ok"},
        "routing": {"selected_model": "mock"},
        "validation_outcome": {"status": "approved", "reason": "test_fixture"},
        "visible_output_bundle": {"gm_narration": ["Fixture narration."]},
        "committed_result": {"commit_applied": True, "committed_effects": []},
    }


def _opening_envelope(start_scene_id: str) -> dict[str, Any]:
    return _envelope(
        interpreted_input={"kind": "speech", "confidence": 0.9},
        generation={
            "success": True,
            "metadata": {
                "structured_output": {
                    "narrative_response": "Opening fixture.",
                    "proposed_scene_id": start_scene_id,
                    "intent_summary": "",
                }
            },
        },
    )


def test_turn_emits_runtime_aspect_ledger() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    executor._graph = _FakeGraphInvoker()  # type: ignore[attr-defined]

    state = executor.run(
        session_id="session-1",
        module_id="m",
        current_scene_id="scene-1",
        player_input="Ich nehme ein Bier aus dem Kuehlschrank",
        turn_number=1,
        turn_initiator_type="player",
        trace_id="trace-1",
    )

    ledger = state["turn_aspect_ledger"]
    assert ledger["session_id"] == "session-1"
    assert ledger["turn_number"] == 1
    assert ledger["turn_aspect_ledger"]["input"]["actual"]["raw_player_input"].startswith("Ich nehme")
    assert ledger["turn_aspect_ledger"]["action_resolution"]["applicable"] is True


def test_recoverable_turn_emits_runtime_aspect_ledger() -> None:
    manager = StoryRuntimeManager()
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    payload = _envelope(
        interpreted_input={"kind": "action", "player_input_kind": "action", "confidence": 0.81},
        generation={"success": True, "metadata": {}},
    )
    payload["validation_outcome"] = {
        "status": "rejected",
        "reason": "dramatic_effect_reject_continuity_pressure",
    }
    manager.turn_graph = _FakeTurnGraph(payload)  # type: ignore[assignment]

    turn = manager.execute_turn(session_id=session.session_id, player_input="Gehe ins Bad")

    ledger = turn["turn_aspect_ledger"]
    assert ledger["turn_number"] == 1
    assert ledger["turn_kind"] == "player_rejected_recoverable"
    assert ledger["turn_aspect_ledger"][ASPECT_VALIDATION]["status"] == "failed"
    assert (
        ledger["turn_aspect_ledger"][ASPECT_VALIDATION]["failure_reason"]
        == "dramatic_effect_reject_continuity_pressure"
    )
    assert ledger["turn_aspect_ledger"][ASPECT_VISIBLE_PROJECTION]["status"] == "passed"
    assert turn["diagnostics"]["turn_aspect_ledger"] == ledger


def _projection() -> dict[str, Any]:
    return {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette_reille",
        "npc_actor_ids": ["michel_longstreet"],
        "actor_lanes": {"annette_reille": "human", "michel_longstreet": "npc"},
    }


def _ledger_with_required_narrator() -> dict[str, Any]:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-visible-origin",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Gehe ins Bad",
    )
    return set_aspect_record(
        ledger,
        ASPECT_NARRATOR_AUTHORITY,
        make_aspect_record(
            applicable=True,
            status="passed",
            expected={"required": True},
            actual={"narrator_block_present": True},
            source="runtime",
            expected_owner="narrator",
            actual_owner="narrator",
        ),
    )


def _ledger_with_required_beat(*, contractually_required: bool = False) -> dict[str, Any]:
    ledger = _ledger_with_required_narrator()
    return set_aspect_record(
        ledger,
        ASPECT_BEAT,
        make_aspect_record(
            applicable=True,
            status="partial",
            expected={
                "prior_beat_id": "civilized_negotiation",
                "candidate_beats": ["courtesy_pressure", "domestic_disruption"],
                "expected_realization": ["narrator_physical_consequence"],
                "contractually_required": contractually_required,
            },
            selected={
                "selected_beat_id": "domestic_disruption",
                "selection_reason": "player disrupts polite social frame",
                "transition_allowed": True,
            },
            actual={"realized": None, "committed": True},
            reasons=["beat_selected_not_yet_realized"],
            source="runtime",
            selected_beat="domestic_disruption",
        ),
    )


def test_visible_narrator_block_has_origin_aspect() -> None:
    graph_state = {
        "turn_aspect_ledger": _ledger_with_required_narrator(),
        "player_action_frame": {"player_input_kind": "action"},
    }

    blocks = _live_scene_blocks_from_visible_bundle(
        {"gm_narration": ["Annette reaches the bathroom door."]},
        turn_number=1,
        runtime_projection=_projection(),
        graph_state=graph_state,
    )

    narrator = next(block for block in blocks if block["block_type"] == "narrator")
    assert narrator["origin_aspect"] == "narrator_authority"
    assert narrator["origin_capability"] == "narrator.physical_consequence"
    assert narrator["authority_owner"] == "narrator"


def test_visible_npc_block_has_origin_capability() -> None:
    blocks = _live_scene_blocks_from_visible_bundle(
        {"spoken_lines": [{"speaker_id": "michel_longstreet", "text": "Annette, wait."}]},
        turn_number=1,
        runtime_projection=_projection(),
        graph_state={"turn_aspect_ledger": _ledger_with_required_narrator()},
    )

    actor = next(block for block in blocks if block["block_type"] == "actor_line")
    assert actor["origin_aspect"] == "npc_authority"
    assert actor["origin_capability"] == "npc.dialogue"
    assert actor["authority_owner"] == "npc"


def test_visible_projection_preserves_origin_metadata() -> None:
    graph_state = {
        "turn_aspect_ledger": _ledger_with_required_narrator(),
        "player_action_frame": {"player_input_kind": "action"},
    }
    blocks = _live_scene_blocks_from_visible_bundle(
        {
            "gm_narration": ["Annette reaches the bathroom door."],
            "spoken_lines": [{"speaker_id": "michel_longstreet", "text": "Annette, wait."}],
        },
        turn_number=1,
        runtime_projection=_projection(),
        graph_state=graph_state,
    )

    ledger = _record_visible_projection_aspect(
        ledger=graph_state["turn_aspect_ledger"],
        session_id="s-visible-origin",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Gehe ins Bad",
        trace_id="trace-visible-origin",
        scene_blocks=blocks,
    )

    visible = ledger["turn_aspect_ledger"][ASPECT_VISIBLE_PROJECTION]
    assert visible["status"] == "passed"
    assert visible["actual"]["visible_block_origin_present"] is True
    assert visible["actual"]["required_narrator_block_present"] is True


def test_beat_realized_when_visible_block_matches_expected_origin() -> None:
    blocks = [
        {
            "id": "b1",
            "block_type": "narrator",
            "text": "Annette's movement breaks the polite frame.",
            "origin_aspect": "narrator_authority",
            "origin_beat_id": "domestic_disruption",
            "origin_capability": "narrator.physical_consequence",
            "authority_owner": "narrator",
        }
    ]

    ledger = _record_visible_projection_aspect(
        ledger=_ledger_with_required_beat(),
        session_id="s-visible-origin",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Ich nehme ein Bier aus dem Kuehlschrank",
        trace_id="trace-visible-origin",
        scene_blocks=blocks,
    )

    beat = ledger["turn_aspect_ledger"][ASPECT_BEAT]
    assert beat["status"] == "passed"
    assert beat["actual"]["realized"] is True
    assert beat["actual"]["missing_expected_realization"] == []


def test_beat_not_realized_when_lost_in_visible_projection() -> None:
    blocks = [
        {
            "id": "b1",
            "block_type": "actor_line",
            "actor_id": "michel_longstreet",
            "text": "Annette, wait.",
            "origin_aspect": "npc_authority",
            "origin_beat_id": "domestic_disruption",
            "origin_capability": "npc.dialogue",
            "authority_owner": "npc",
        }
    ]

    ledger = _record_visible_projection_aspect(
        ledger=_ledger_with_required_beat(),
        session_id="s-visible-origin",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Ich nehme ein Bier aus dem Kuehlschrank",
        trace_id="trace-visible-origin",
        scene_blocks=blocks,
    )

    beat = ledger["turn_aspect_ledger"][ASPECT_BEAT]
    assert beat["status"] == "partial"
    assert beat["failure_reason"] == "beat_realization_not_visible"
    assert beat["failure_class"] == "degradation_only"
    assert beat["lost_at_stage"] == "visible_projection"
    assert beat["actual"]["realized"] is False


def test_required_beat_lost_is_classified_as_hard_contract_failure() -> None:
    ledger = _record_visible_projection_aspect(
        ledger=_ledger_with_required_beat(contractually_required=True),
        session_id="s-visible-origin",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Ich nehme ein Bier aus dem Kuehlschrank",
        trace_id="trace-visible-origin",
        scene_blocks=[],
    )

    beat = ledger["turn_aspect_ledger"][ASPECT_BEAT]
    assert beat["status"] == "failed"
    assert beat["failure_class"] == "hard_contract_failure"
    assert beat["failure_reason"] == "selected_required_beat_lost"
    validation = ledger["turn_aspect_ledger"][ASPECT_VALIDATION]
    commit = ledger["turn_aspect_ledger"][ASPECT_COMMIT]
    assert validation["status"] == "failed"
    assert validation["failure_reason"] == "selected_required_beat_lost"
    assert commit["status"] == "partial"
    assert commit["failure_reason"] == "selected_required_beat_lost"


def test_required_narrator_block_not_lost_in_projection_classifies_validation_and_commit() -> None:
    blocks = [
        {
            "id": "b1",
            "block_type": "actor_line",
            "actor_id": "michel_longstreet",
            "text": "Annette, wait.",
            "origin_aspect": "npc_authority",
            "origin_beat_id": "domestic_disruption",
            "origin_capability": "npc.dialogue",
            "authority_owner": "npc",
        }
    ]

    ledger = _record_visible_projection_aspect(
        ledger=_ledger_with_required_narrator(),
        session_id="s-visible-origin",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Gehe ins Bad",
        trace_id="trace-visible-origin",
        scene_blocks=blocks,
    )

    visible = ledger["turn_aspect_ledger"][ASPECT_VISIBLE_PROJECTION]
    validation = ledger["turn_aspect_ledger"][ASPECT_VALIDATION]
    commit = ledger["turn_aspect_ledger"][ASPECT_COMMIT]
    assert visible["status"] == "failed"
    assert visible["failure_reason"] == "required_narrator_block_lost_in_projection"
    assert validation["status"] == "failed"
    assert validation["failure_class"] == "projection_failure"
    assert validation["actual"]["projection_failure_detected"] is True
    assert commit["status"] == "partial"
    assert commit["actual"]["projection_failure_detected"] is True
