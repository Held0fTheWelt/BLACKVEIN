"""Environment state shell readout projection helpers."""

from __future__ import annotations

from .common import *

def _environment_surface_token(environment_state: dict[str, Any]) -> str:
    salient = environment_state.get("salient_object_ids")
    if isinstance(salient, list):
        for item in salient:
            token = str(item or "").strip()
            if token:
                return token
    current = str(environment_state.get("current_room_id") or environment_state.get("current_area") or "").strip()
    return current or ""


def _environment_projection(environment_state: dict[str, Any]) -> dict[str, Any]:
    if not environment_state:
        return {}
    return {
        "contract": "shell_environment_state_projection.v1",
        "current_room_id": environment_state.get("current_room_id") or environment_state.get("current_area"),
        "previous_room_id": environment_state.get("previous_room_id") or environment_state.get("previous_area"),
        "visible_room_ids": environment_state.get("visible_room_ids") if isinstance(environment_state.get("visible_room_ids"), list) else [],
        "salient_object_ids": environment_state.get("salient_object_ids") if isinstance(environment_state.get("salient_object_ids"), list) else [],
        "last_environment_events": environment_state.get("last_environment_events") if isinstance(environment_state.get("last_environment_events"), list) else [],
    }


def _environment_live_surface_now(environment_state: dict[str, Any]) -> str:
    token = _environment_surface_token(environment_state)
    if not token:
        return ""
    return f"Environment state marks {token} as the active surface right now."


def _environment_salient_object_now(environment_state: dict[str, Any]) -> str:
    token = _environment_surface_token(environment_state)
    if not token:
        return ""
    return f"Environment state is carrying salience through {token}."


def _environment_situational_affordance_now(environment_state: dict[str, Any]) -> str:
    current = str(environment_state.get("current_room_id") or environment_state.get("current_area") or "").strip()
    visible = environment_state.get("visible_room_ids") if isinstance(environment_state.get("visible_room_ids"), list) else []
    if not current:
        return ""
    visible_count = len([x for x in visible if str(x).strip()])
    return f"Environment state keeps {current} active with {visible_count} visible room link(s)."

__all__ = (
    '_environment_surface_token',
    '_environment_projection',
    '_environment_live_surface_now',
    '_environment_salient_object_now',
    '_environment_situational_affordance_now',
)
