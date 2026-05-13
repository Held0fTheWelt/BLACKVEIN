"""ADR-0038 Phase C — short paths share recoverable envelope + observability emitters."""

from __future__ import annotations

from typing import Any

import pytest

from app.story_runtime import StoryRuntimeManager
from app.story_runtime.manager import _recoverable_narrator_visible_output_bundle


class _FakeTurnGraph:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return self._payload


class _ExplodingTurnGraph:
    def run(self, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("graph boom")


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
        "visible_output_bundle": {"gm_narration": ["Fixture narration for commit tests."]},
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


@pytest.fixture
def manager() -> StoryRuntimeManager:
    return StoryRuntimeManager()


def test_validation_recoverable_matches_canonical_narrator_bundle(manager: StoryRuntimeManager) -> None:
    payload = _envelope(
        interpreted_input={"kind": "action", "player_input_kind": "action", "confidence": 0.81},
        generation={"success": True, "metadata": {}},
    )
    payload["validation_outcome"] = {
        "status": "rejected",
        "reason": "dramatic_effect_reject_continuity_pressure",
    }
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    manager.turn_graph = _FakeTurnGraph(payload)  # type: ignore[assignment]
    turn = manager.execute_turn(session_id=session.session_id, player_input="Gehe ins Bad")
    assert turn.get("observability_path_summary") is not None
    msg = turn["player_visible_message"]
    ref = _recoverable_narrator_visible_output_bundle(message=msg)
    assert turn["visible_output_bundle"] == ref


def test_graph_exception_recoverable_matches_canonical_narrator_bundle(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    manager.turn_graph = _ExplodingTurnGraph()  # type: ignore[assignment]
    turn = manager.execute_turn(session_id=session.session_id, player_input="anything")
    assert turn.get("observability_path_summary") is not None
    msg = turn["player_visible_message"]
    ref = _recoverable_narrator_visible_output_bundle(message=msg)
    assert turn["visible_output_bundle"] == ref
    assert turn["turn_kind"] == "player_graph_exception_playable"
    hist = manager.get_session(session.session_id).history[-1]
    assert hist.get("lifecycle_state") == "observed"
