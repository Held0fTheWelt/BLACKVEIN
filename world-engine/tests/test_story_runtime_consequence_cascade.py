"""Tests for Π21 consequence-cascade continuity evidence."""

from __future__ import annotations

import copy
from typing import Any

from ai_stack.consequence_cascade_contracts import (
    consequence_cascade_policy_from_module_runtime,
)
from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.runtime_aspect_ledger import ASPECT_CONSEQUENCE_CASCADE
from app.story_runtime import StoryRuntimeManager
from story_runtime_core.consequences import CONSEQUENCE_CASCADE_FEEDBACK_CONTRACT


class _RecordingFakeTurnGraph:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.last_kwargs: dict[str, Any] = {}

    def run(self, **kwargs: Any) -> dict[str, Any]:
        self.last_kwargs = dict(kwargs)
        return copy.deepcopy(self._payload)


def _cascade_policy() -> dict[str, Any]:
    module_policy = load_module_runtime_policy("god_of_carnage").to_dict()
    return consequence_cascade_policy_from_module_runtime(module_policy)


def _derived_continuity_class(policy: dict[str, Any]) -> str:
    classes = policy["allowed_continuity_classes"]
    assert classes
    return str(classes[0])


def _payload(continuity_class: str) -> dict[str, Any]:
    return {
        "interpreted_input": {"kind": "speech", "confidence": 0.8},
        "generation": {"success": True, "metadata": {}, "content": "x" * 120},
        "graph_diagnostics": {"errors": []},
        "retrieval": {"domain": "runtime", "status": "ok"},
        "routing": {"selected_model": "mock"},
        "validation_outcome": {"status": "approved", "reason": "test_fixture"},
        "visible_output_bundle": {"gm_narration": ["Fixture narration for tests."]},
        "committed_result": {"commit_applied": True, "committed_effects": []},
        "continuity_impacts": [{"class": continuity_class}],
    }


def test_manager_passes_consequence_cascade_to_graph_and_records_ledger_aspect() -> None:
    policy = _cascade_policy()
    continuity_class = _derived_continuity_class(policy)
    fake = _RecordingFakeTurnGraph(_payload(continuity_class))
    manager = StoryRuntimeManager()
    manager.turn_graph = fake  # type: ignore[assignment]
    session = manager.create_session(
        module_id="god_of_carnage",
        runtime_projection={
            "start_scene_id": "scene_1",
            "module_id": "god_of_carnage",
            "human_actor_id": "annette_reille",
            "selected_player_role": "annette_reille",
            "npc_actor_ids": ["michel_longstreet", "veronique_vallon", "alain_reille"],
            "actor_lanes": {
                "annette_reille": "human",
                "michel_longstreet": "npc",
                "veronique_vallon": "npc",
                "alain_reille": "npc",
            },
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}],
        },
    )

    manager.execute_turn(session_id=session.session_id, player_input="first")
    manager.execute_turn(session_id=session.session_id, player_input="second")

    prior = fake.last_kwargs["prior_consequence_cascade_state"]
    assert prior["feedback_contract"] == CONSEQUENCE_CASCADE_FEEDBACK_CONTRACT
    assert prior["atom_count"] >= 1
    assert prior["edge_count"] >= 1
    assert len(prior["items"]) <= policy["max_graph_items"]

    latest = session.history[-1]
    aspect = latest["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_CONSEQUENCE_CASCADE]
    assert aspect["status"] == "passed"
    assert aspect["actual"]["contract_pass"] is True
    assert aspect["actual"]["atom_count"] >= 1
    assert aspect["actual"]["edge_count"] >= 1
    state = manager.get_state(session.session_id)
    assert state["committed_state"]["consequence_cascade"]["atom_count"] >= 1
    assert state["consequence_cascade"]["edge_count"] >= 1
