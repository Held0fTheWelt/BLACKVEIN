"""Unit tests for deterministic runtime input interpretation."""

from __future__ import annotations

import pytest

from app.runtime.command_resolution import REJECTION_NO_INTERPRETABLE_INTENT, resolve_plan_to_command
from app.runtime.input_interpreter import InputPrimaryMode, interpret_runtime_input


def test_silence_and_dots_no_command():
    plan = interpret_runtime_input("...")
    assert plan.primary_mode == InputPrimaryMode.silence
    cmd, code, _ = resolve_plan_to_command(plan)
    assert cmd is None
    assert code == REJECTION_NO_INTERPRETABLE_INTENT


def test_quoted_line_yields_say():
    plan = interpret_runtime_input('"That is enough."')
    cmd, code, _ = resolve_plan_to_command(plan)
    assert code is None
    assert cmd == {"action": "say", "text": "That is enough."}


def test_i_say_pattern_yields_say():
    plan = interpret_runtime_input('I say "That is enough."')
    cmd, code, _ = resolve_plan_to_command(plan)
    assert code is None
    assert cmd == {"action": "say", "text": "That is enough."}


def test_reaction_emote_stare():
    plan = interpret_runtime_input("I sigh and look away.")
    cmd, code, _ = resolve_plan_to_command(plan)
    assert code is None
    assert cmd is not None
    assert cmd["action"] == "emote"
    assert "look away" in cmd["text"].lower()


def test_inspect_only_with_unique_target():
    visible = ["living_room", "phone", "tulips"]
    plan = interpret_runtime_input("I inspect the phone.", visible_targets=visible)
    cmd, code, _ = resolve_plan_to_command(plan)
    assert code is None
    assert cmd == {"action": "inspect", "target_id": "phone"}

    plan2 = interpret_runtime_input("I inspect the unknown_thing.", visible_targets=visible)
    cmd2, code2, _ = resolve_plan_to_command(plan2)
    assert cmd2 is None
    assert code2 == REJECTION_NO_INTERPRETABLE_INTENT


def test_move_only_with_unique_room():
    rooms = [{"id": "living_room", "name": "Living Room"}]
    plan = interpret_runtime_input("I go to the living room.", reachable_rooms=rooms)
    cmd, code, _ = resolve_plan_to_command(plan)
    assert code is None
    assert cmd == {"action": "move", "target_room_id": "living_room"}


def test_short_ambiguous_no_execution():
    plan = interpret_runtime_input("Fine.")
    cmd, code, _ = resolve_plan_to_command(plan)
    assert cmd is None
    assert code == REJECTION_NO_INTERPRETABLE_INTENT


def test_use_action_with_available_actions():
    actions = [{"id": "steady_breath", "label": "Steady breath", "description": "", "scope": "room", "target_id": None}]
    plan = interpret_runtime_input("I use steady breath", available_actions=actions)
    cmd, code, _ = resolve_plan_to_command(plan)
    assert code is None
    assert cmd == {"action": "use_action", "action_id": "steady_breath"}
