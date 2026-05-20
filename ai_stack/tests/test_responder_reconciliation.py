"""Tests for responder reconciliation in the validate-seam node.

The director-selected responder set is the authoritative scope for a scene.
When the model proposes a responder id or responder scope in its structured
output, the runtime must:

- accept the model's claim when it falls within the director's scope,
- drop any actor the model introduced that is not in scope, and
- record the outcome under ``responder_reconciliation`` on state.

The reconciliation dict is plain data; these tests exercise
``_reconcile_model_responders`` directly rather than spinning up the full
LangGraph pipeline.
"""

from __future__ import annotations

from ai_stack.langgraph.langgraph_runtime_executor import _actor_lane_validation, _reconcile_model_responders


def _state(selected: list[dict]) -> dict:
    return {"selected_responder_set": selected}


def _generation_with_structured(structured: dict) -> dict:
    return {
        "success": True,
        "metadata": {"structured_output": structured},
    }


def test_model_responder_in_scope_is_accepted() -> None:
    state = _state(
        [
            {"actor_id": "annette_reille"},
            {"actor_id": "alain_reille"},
        ]
    )
    generation = _generation_with_structured(
        {
            "responder_id": "alain_reille",
            "responder_actor_ids": ["alain_reille"],
        }
    )
    out = _reconcile_model_responders(state, generation)
    assert out["outcome"] == "model_responder_accepted"
    assert out["effective_responder_id"] == "alain_reille"
    assert out["effective_responder_scope"] == ["alain_reille"]
    assert out["dropped_out_of_scope_actors"] == []
    assert out["dropped_out_of_scope_count"] == 0


def test_primary_responder_and_secondary_scope_fields_are_supported() -> None:
    state = _state(
        [
            {"actor_id": "annette_reille"},
            {"actor_id": "alain_reille"},
            {"actor_id": "veronique_vallon"},
        ]
    )
    generation = _generation_with_structured(
        {
            "primary_responder_id": "annette_reille",
            "secondary_responder_ids": ["alain_reille", "ghost_actor"],
        }
    )
    out = _reconcile_model_responders(state, generation)
    assert out["effective_responder_id"] == "annette_reille"
    assert out["effective_responder_scope"] == ["alain_reille", "annette_reille"]
    assert out["dropped_out_of_scope_actors"] == ["ghost_actor"]


def test_model_responder_out_of_scope_is_dropped_and_director_used() -> None:
    state = _state(
        [
            {"actor_id": "annette_reille"},
            {"actor_id": "alain_reille"},
        ]
    )
    generation = _generation_with_structured(
        {
            "responder_id": "ghost_character",
            "responder_actor_ids": ["ghost_character", "alain_reille"],
        }
    )
    out = _reconcile_model_responders(state, generation)
    assert out["outcome"] == "model_responder_out_of_scope_dropped"
    assert out["effective_responder_id"] == "annette_reille"
    assert out["effective_responder_scope"] == ["alain_reille"]
    assert out["dropped_out_of_scope_actors"] == ["ghost_character"]
    assert out["dropped_out_of_scope_count"] == 1


def test_model_proposes_no_responder_then_director_primary_used() -> None:
    state = _state([{"actor_id": "annette_reille"}])
    generation = _generation_with_structured({})
    out = _reconcile_model_responders(state, generation)
    assert out["outcome"] == "director_primary_responder_used"
    assert out["effective_responder_id"] == "annette_reille"


def test_model_responder_missing_from_director_scope_falls_back() -> None:
    # Director scope exists but the model's primary is not in it and its
    # scope list is empty — the director primary is used and the outcome
    # reflects that the model's responder was missing from scope.
    state = _state([{"actor_id": "annette_reille"}])
    generation = _generation_with_structured(
        {"responder_id": "outsider", "responder_actor_ids": []}
    )
    out = _reconcile_model_responders(state, generation)
    assert out["outcome"] == "model_responder_out_of_scope_dropped"
    assert out["effective_responder_id"] == "annette_reille"
    assert out["dropped_out_of_scope_actors"] == ["outsider"]


def test_no_director_scope_accepts_model_responder_as_effective() -> None:
    # When the director publishes no responder scope (for example in tests or
    # in modules that have not yet wired responder selection), the model's
    # proposed responder is accepted as the effective responder so the turn
    # still has a concrete actor to render — but no actor is dropped.
    state = _state([])
    generation = _generation_with_structured({"responder_id": "solo_actor"})
    out = _reconcile_model_responders(state, generation)
    assert out["outcome"] == "model_responder_accepted"
    assert out["effective_responder_id"] == "solo_actor"
    assert out["dropped_out_of_scope_count"] == 0


def test_empty_director_scope_and_empty_model_is_empty_reconciliation() -> None:
    out = _reconcile_model_responders(_state([]), {"metadata": {}})
    assert out["outcome"] == "no_director_scope_available"
    assert out["effective_responder_id"] is None
    assert out["effective_responder_scope"] == []


def test_actor_lane_validation_rejects_out_of_scope_speaker_and_action_actor() -> None:
    state = {
        "selected_responder_set": [{"actor_id": "annette_reille"}],
        "character_mind_records": [{"runtime_actor_id": "annette_reille"}],
        "selected_scene_function": "probe_motive",
        "prior_continuity_impacts": [],
    }
    generation = _generation_with_structured(
        {
            "primary_responder_id": "annette_reille",
            "spoken_lines": [{"speaker_id": "ghost_actor", "text": "No."}],
            "action_lines": [{"actor_id": "ghost_actor", "text": "He interrupts."}],
        }
    )
    out = _actor_lane_validation(state, generation)
    assert out["status"] == "rejected"
    assert out["reason"] == "actor_lane_illegal_actor"
    assert "ghost_actor" in out["illegal_actor_ids"]


def test_actor_lane_validation_rejects_incompatible_initiative_for_withhold_scene() -> None:
    state = {
        "selected_responder_set": [{"actor_id": "annette_reille"}],
        "character_mind_records": [{"runtime_actor_id": "annette_reille"}],
        "selected_scene_function": "withhold_or_evade",
        "prior_continuity_impacts": [{"class": "repair_attempt"}],
    }
    generation = _generation_with_structured(
        {
            "primary_responder_id": "annette_reille",
            "initiative_events": [
                {"actor_id": "annette_reille", "type": "interrupt", "reason": "pressure"},
            ],
        }
    )
    out = _actor_lane_validation(state, generation)
    assert out["status"] == "rejected"
    assert out["reason"] == "actor_lane_scene_function_mismatch"
    assert out["scene_function_compatibility"] == "mismatch"
