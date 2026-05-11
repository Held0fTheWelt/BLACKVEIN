from __future__ import annotations

from pathlib import Path

from ai_stack.goc_turn_seams import run_validation_seam
from ai_stack.player_action_resolution import resolve_player_action


def _runtime_projection() -> dict:
    return {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette_reille",
        "npc_actor_ids": ["alain_reille", "veronique_vallon", "michel_longstreet"],
        "actor_lanes": {
            "annette_reille": "human",
            "alain_reille": "npc",
            "veronique_vallon": "npc",
            "michel_longstreet": "npc",
        },
    }


def _content_root() -> Path:
    return Path(__file__).resolve().parents[2] / "content" / "modules"


def test_gehe_ins_bad_resolves_movement_offscreen() -> None:
    out = resolve_player_action(
        raw_text="Gehe ins Bad",
        interpreted_input={
            "player_input_kind": "action",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "projection_captures": {"room": "ins Bad"},
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )
    frame = out["player_action_frame"]
    assert frame["player_input_kind"] == "action"
    assert frame["verb"] == "move_to"
    assert frame["target_query"] == "ins Bad"
    assert frame["resolved_target_type"] == "location"
    assert frame["resolved_target_id"] == "bathroom"
    assert frame["affordance_status"] == "allowed_offscreen"
    assert frame["narrator_response_expected"] is True
    assert frame["npc_response_expected"] is False


def test_schau_aus_dem_fenster_resolves_perception_object() -> None:
    out = resolve_player_action(
        raw_text="Schau aus dem Fenster",
        interpreted_input={
            "player_input_kind": "perception",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )
    frame = out["player_action_frame"]
    assert frame["verb"] == "look_at"
    assert frame["resolved_target_type"] == "object"
    assert frame["resolved_target_id"] == "window"
    assert frame["affordance_status"] == "allowed"
    assert frame["narrator_response_expected"] is True
    assert frame["npc_response_expected"] is False


def test_gibt_es_hier_ein_bad_stays_question_speech() -> None:
    out = resolve_player_action(
        raw_text="Gibt es hier ein Bad?",
        interpreted_input={
            "player_input_kind": "speech",
            "narrator_response_expected": False,
            "npc_response_expected": True,
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )
    frame = out["player_action_frame"]
    assert frame["player_input_kind"] == "speech"
    assert frame["verb"] == "ask"
    assert frame["affordance_status"] == "allowed"
    assert frame["npc_response_expected"] is True


def test_unknown_target_returns_clarification_status() -> None:
    out = resolve_player_action(
        raw_text="Gehe nach Mordor",
        interpreted_input={
            "player_input_kind": "action",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "projection_captures": {"room": "nach Mordor"},
            "actor_id": "annette_reille",
        },
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )
    aff = out["affordance_resolution"]
    assert aff["affordance_status"] == "unknown_target"
    assert aff["action_commit_policy"] == "needs_clarification"


def test_continuity_pressure_reject_overridden_by_allowed_resolution(monkeypatch) -> None:
    class _FakeGateResult:
        value = "rejected_continuity_pressure"

    class _FakeGateOut:
        gate_result = _FakeGateResult()
        legacy_fallback_used = False
        rejection_reasons: list[str] = []

        @staticmethod
        def to_runtime_dict() -> dict:
            return {"gate_result": "rejected_continuity_pressure"}

    monkeypatch.setattr("ai_stack.goc_turn_seams.evaluate_dramatic_effect_gate", lambda _ctx: _FakeGateOut())

    result = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=[{"effect_type": "narrative_projection", "description": "x"}],
        generation={"success": True, "metadata": {"structured_output": {}}},
        affordance_resolution={
            "affordance_status": "allowed_offscreen",
            "action_commit_policy": "commit_action",
        },
        player_action_frame={
            "player_input_kind": "action",
            "verb": "move_to",
            "resolved_target_id": "bathroom",
        },
    )
    assert result["status"] == "approved"
    assert result["reason"] == "action_resolution_continuity_supported"
    assert result["continuity_pressure_resolution"]["override_applied"] is True
