"""Authoritative progression merge: command vs model structured_output vs token scan."""

from __future__ import annotations

from typing import Any

import pytest

from app.story_runtime import StoryRuntimeManager


class _FakeTurnGraph:
    """Minimal graph payload for progression commit tests (no LangChain)."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return self._payload


def _base_graph_payload(
    *,
    interpreted_input: dict[str, Any],
    generation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "interpreted_input": interpreted_input,
        "generation": generation,
        "graph_diagnostics": {"errors": []},
        "retrieval": {},
        "routing": {},
    }


@pytest.fixture
def progression_manager() -> StoryRuntimeManager:
    return StoryRuntimeManager()


def test_model_structured_proposal_commits_when_legal(progression_manager: StoryRuntimeManager) -> None:
    payload = _base_graph_payload(
        interpreted_input={"kind": "speech", "confidence": 0.8},
        generation={
            "success": True,
            "metadata": {
                "structured_output": {
                    "narrative_response": "You move forward.",
                    "proposed_scene_id": "scene_2",
                    "intent_summary": "advance",
                }
            },
        },
    )
    progression_manager.turn_graph = _FakeTurnGraph(payload)
    session = progression_manager.create_session(
        module_id="test_mod",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )
    turn = progression_manager.execute_turn(
        session_id=session.session_id,
        player_input="I continue the conversation calmly.",
    )
    state = progression_manager.get_state(session.session_id)

    nc = turn["narrative_commit"]
    assert nc["allowed"] is True
    assert nc["selected_candidate_source"] == "model_structured_output"
    assert nc["model_structured_proposed_scene_id"] == "scene_2"
    assert state["current_scene_id"] == "scene_2"
    assert nc["candidate_sources"]
    hist = state["last_committed_turn"] or {}
    assert hist.get("narrative_commit", {}).get("allowed") is True
    assert "graph" not in hist


def test_explicit_command_beats_model_proposal(progression_manager: StoryRuntimeManager) -> None:
    payload = _base_graph_payload(
        interpreted_input={
            "kind": "explicit_command",
            "command_name": "move",
            "command_args": ["scene_2"],
            "confidence": 0.99,
        },
        generation={
            "success": True,
            "metadata": {
                "structured_output": {
                    "narrative_response": "",
                    "proposed_scene_id": "scene_3",
                    "intent_summary": "wrong",
                }
            },
        },
    )
    progression_manager.turn_graph = _FakeTurnGraph(payload)
    session = progression_manager.create_session(
        module_id="test_mod",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}, {"id": "scene_3"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )
    turn = progression_manager.execute_turn(session_id=session.session_id, player_input="/move scene_2")
    nc = turn["narrative_commit"]
    assert nc["allowed"] is True
    assert nc["committed_scene_id"] == "scene_2"
    assert nc["selected_candidate_source"] == "explicit_command"


def test_unknown_model_proposal_is_audited_not_selected(progression_manager: StoryRuntimeManager) -> None:
    payload = _base_graph_payload(
        interpreted_input={"kind": "speech", "confidence": 0.8},
        generation={
            "success": True,
            "metadata": {
                "structured_output": {
                    "narrative_response": "x",
                    "proposed_scene_id": "scene_99",
                    "intent_summary": "",
                }
            },
        },
    )
    progression_manager.turn_graph = _FakeTurnGraph(payload)
    session = progression_manager.create_session(
        module_id="test_mod",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )
    turn = progression_manager.execute_turn(
        session_id=session.session_id,
        player_input="Nothing special here.",
    )
    nc = turn["narrative_commit"]
    assert nc["commit_reason_code"] == "no_scene_proposal"
    assert nc["model_structured_proposed_scene_id"] == "scene_99"
    sources = nc["candidate_sources"]
    assert any(s.get("source") == "model_structured_output" and s.get("rejected_unknown_scene") for s in sources)


def test_diagnostics_envelope_has_graph_authoritative_history_tail_does_not(progression_manager: StoryRuntimeManager) -> None:
    payload = _base_graph_payload(
        interpreted_input={"kind": "speech", "confidence": 0.8},
        generation={
            "success": True,
            "metadata": {
                "structured_output": {"narrative_response": "", "proposed_scene_id": "scene_2", "intent_summary": ""}
            },
        },
    )
    progression_manager.turn_graph = _FakeTurnGraph(payload)
    session = progression_manager.create_session(
        module_id="test_mod",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )
    progression_manager.execute_turn(session_id=session.session_id, player_input="plain text")
    diag = progression_manager.get_diagnostics(session.session_id)
    assert "graph" in diag["diagnostics"][-1]
    tail = diag["authoritative_history_tail"][-1]
    assert "graph" not in tail
    assert "narrative_commit" in tail
