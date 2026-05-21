"""Projection section builder for `input`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_INPUT_SECTION_PARAMS = ('action_actual', 'input_actual')


def build_input_section(**values: Any) -> dict[str, Any]:
    action_actual = values['action_actual']
    input_actual = values['input_actual']
    return {
                    "player_input_kind": input_actual.get("player_input_kind")
                    or input_actual.get("input_kind")
                    or action_actual.get("input_kind"),
                    "semantic_move": action_actual.get("semantic_move")
                    or action_actual.get("semantic_move_kind")
                    or action_actual.get("action_kind"),
                    "player_action_frame": action_actual.get("player_action_frame") or {},
                    "affordance_resolution": action_actual.get("affordance_resolution") or {},
                    "local_context_transition": action_actual.get("local_context_transition") or {},
                }

