"""Previous-reply continuity and re-entry shell readout hooks."""

from __future__ import annotations

from .common import *
from .environment_readout import *
from .social_pressure_readout import *
from .response_surface_readout import *

def _previous_reply_continuity_context(*, state: dict[str, Any], committed_state: dict[str, Any]) -> dict[str, Any]:
    direct = committed_state.get("previous_reply_continuity_context")
    if isinstance(direct, dict):
        return direct
    last_turn = state.get("last_committed_turn")
    if isinstance(last_turn, dict):
        after = last_turn.get("committed_state_after")
        if isinstance(after, dict):
            prior = after.get("previous_reply_continuity_context")
            if isinstance(prior, dict):
                return prior
    return {}


def _earlier_reply_continuity_context(*, state: dict[str, Any], committed_state: dict[str, Any]) -> dict[str, Any]:
    direct = committed_state.get("earlier_reply_continuity_context")
    if isinstance(direct, dict):
        return direct
    last_turn = state.get("last_committed_turn")
    if isinstance(last_turn, dict):
        after = last_turn.get("committed_state_after")
        if isinstance(after, dict):
            prior = after.get("earlier_reply_continuity_context")
            if isinstance(prior, dict):
                return prior
    return {}


def _response_countermove_link_now(*, previous_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str) -> str:
    if not isinstance(previous_reply_context, dict) or not previous_reply_context:
        return ""
    previous_exchange = str(previous_reply_context.get("exchange_label") or "").strip()
    previous_surface = str(previous_reply_context.get("surface_token") or "").strip()
    if not previous_exchange:
        return ""
    current_exchange = _response_exchange_label_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    current_surface = _response_surface_token_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    same_surface = previous_surface and current_surface != "room" and previous_surface == current_surface
    if same_surface:
        if previous_exchange in {"failed repair", "brittle repair", "containment"} and current_exchange in {"accusation", "exposure", "status judgment"}:
            return f"turning the last {previous_exchange} back through the same {current_surface}"
        if previous_exchange in {"accusation", "status judgment", "exposure"} and current_exchange in {"failed repair", "brittle repair", "containment", "evasive pressure"}:
            return f"answering the last {previous_exchange} on the same {current_surface}"
        if previous_exchange == "evasive pressure":
            return f"after the last evasive turn left the same {current_surface} live"
        if previous_exchange == current_exchange:
            return f"carrying the last {current_exchange} forward on the same {current_surface}"
        return f"turning the last {previous_exchange} into {current_exchange} on the same {current_surface}"
    if previous_exchange in {"failed repair", "brittle repair", "containment"} and current_exchange in {"accusation", "exposure", "status judgment"}:
        return f"after the last {previous_exchange} only reopened the room"
    if previous_exchange in {"accusation", "status judgment", "exposure"} and current_exchange in {"failed repair", "brittle repair", "containment", "evasive pressure"}:
        return f"because the last {previous_exchange} forced a defensive return"
    if previous_exchange == "evasive pressure" and current_exchange in {"failed repair", "brittle repair", "accusation", "exposure", "status judgment"}:
        return "because the last evasive turn left the pressure live"
    if previous_exchange in {"failed repair", "brittle repair", "containment"} and current_exchange in {"failed repair", "brittle repair", "containment"}:
        return "because the room could not get out of the last repair loop"
    return "because the last visible answer left the pressure live"


def _response_delayed_countermove_link_now(*, earlier_reply_context: dict[str, Any], previous_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str) -> str:
    if not isinstance(earlier_reply_context, dict) or not earlier_reply_context:
        return ""
    earlier_exchange = str(earlier_reply_context.get("exchange_label") or "").strip()
    earlier_surface = str(earlier_reply_context.get("surface_token") or "").strip()
    previous_surface = str(previous_reply_context.get("surface_token") or "").strip() if isinstance(previous_reply_context, dict) else ""
    if not earlier_exchange:
        return ""
    current_exchange = _response_exchange_label_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    current_surface = _response_surface_token_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    if current_surface == "room" or not earlier_surface or earlier_surface != current_surface:
        return ""
    if previous_surface and previous_surface == current_surface:
        return ""
    if earlier_exchange in {"failed repair", "brittle repair", "containment"} and current_exchange in {"accusation", "exposure", "status judgment"}:
        return f"pulling the earlier {earlier_exchange} back onto the same {current_surface}"
    if earlier_exchange in {"accusation", "status judgment", "exposure"} and current_exchange in {"failed repair", "brittle repair", "containment", "evasive pressure"}:
        return f"answering the earlier {earlier_exchange} back on the same {current_surface}"
    if earlier_exchange == current_exchange:
        return f"bringing the earlier {current_exchange} back onto the same {current_surface}"
    return f"bringing the earlier {earlier_exchange} back as {current_exchange} on the same {current_surface}"


def _response_interruption_reentry_hook_now(*, previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str) -> str:
    current_exchange = _response_exchange_label_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    current_surface = _response_surface_token_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    previous_exchange = str(previous_reply_context.get("exchange_label") or "").strip() if isinstance(previous_reply_context, dict) else ""
    previous_surface = str(previous_reply_context.get("surface_token") or "").strip() if isinstance(previous_reply_context, dict) else ""
    earlier_exchange = str(earlier_reply_context.get("exchange_label") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    earlier_surface = str(earlier_reply_context.get("surface_token") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    same_surface = current_surface != "room" and previous_surface and previous_surface == current_surface

    if current_exchange == "evasive pressure":
        if same_surface and previous_exchange in {"accusation", "status judgment", "exposure"}:
            return f"trying to answer around the point on the same {current_surface}"
        if same_surface and previous_exchange in {"failed repair", "brittle repair", "containment"}:
            return f"trying to slide the same {current_surface} sideways without settling it"
        if previous_exchange in {"accusation", "status judgment", "exposure"}:
            return "trying to answer around the point without settling it"
        if previous_exchange in {"failed repair", "brittle repair", "containment"}:
            return "trying to shift the line sideways without settling it"

    if previous_exchange == "evasive pressure":
        if same_surface and current_exchange in {"accusation", "status judgment", "exposure", "failed repair", "brittle repair", "containment"}:
            return f"not letting the last dodge stand on the same {current_surface}"
        if current_exchange in {"accusation", "status judgment", "exposure", "failed repair", "brittle repair", "containment"}:
            return "not letting the last dodge settle into a subject shift"

    if earlier_exchange == "evasive pressure" and current_surface != "room" and earlier_surface == current_surface and previous_surface != current_surface and current_exchange != "evasive pressure":
        return f"dragging the earlier dodge back onto the same {current_surface}"

    return ""


def _response_rhythm_pressure_hook_now(*, previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str, responder_actor: str | None) -> str:
    current_exchange = _response_exchange_label_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    current_surface = _response_surface_token_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    previous_exchange = str(previous_reply_context.get("exchange_label") or "").strip() if isinstance(previous_reply_context, dict) else ""
    previous_surface = str(previous_reply_context.get("surface_token") or "").strip() if isinstance(previous_reply_context, dict) else ""
    earlier_exchange = str(earlier_reply_context.get("exchange_label") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    earlier_surface = str(earlier_reply_context.get("surface_token") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    same_surface = current_surface != "room" and previous_surface and previous_surface == current_surface
    earlier_same_surface = current_surface != "room" and earlier_surface and earlier_surface == current_surface and previous_surface != current_surface

    if current_exchange == "evasive pressure":
        if same_surface and previous_exchange in {"accusation", "status judgment", "exposure"}:
            if _actor_has(responder_actor, "guest") and _actor_has_any(responder_actor, "lawyer", "pragmatist", "procedure"):
                return f"buying a beat on the same {current_surface} instead of answering it"
            if _actor_has(responder_actor, "host") and _actor_has_any(responder_actor, "practical", "conflict", "spouse"):
                return f"talking across the same {current_surface} instead of settling it"
            return f"letting a beat hang on the same {current_surface} instead of answering it"
        if same_surface and previous_exchange in {"failed repair", "brittle repair", "containment"}:
            return f"letting the same {current_surface} hang for a beat instead of settling it"

    if previous_exchange == "evasive pressure" and current_exchange in {"accusation", "status judgment", "exposure", "failed repair", "brittle repair", "containment"} and same_surface:
        if _actor_has_any(responder_actor, "moral", "ideal", "injured", "mother", "pressure holder", "observer"):
            return f"cutting back in before the dodge on the same {current_surface} can go quiet"
        return f"cutting back across the dodge on the same {current_surface} before it can settle"

    if earlier_same_surface and earlier_exchange == "evasive pressure" and current_exchange != "evasive pressure":
        return f"breaking the earlier pause back over the same {current_surface}"

    return ""


def _response_pressure_relay_hook_now(*, previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str, responder_actor: str | None) -> str:
    current_exchange = _response_exchange_label_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    current_surface = _response_surface_token_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    current_actor = (responder_actor or "").strip().lower()
    previous_exchange = str(previous_reply_context.get("exchange_label") or "").strip() if isinstance(previous_reply_context, dict) else ""
    previous_surface = str(previous_reply_context.get("surface_token") or "").strip() if isinstance(previous_reply_context, dict) else ""
    previous_actor = str(previous_reply_context.get("responder_actor") or "").strip().lower() if isinstance(previous_reply_context, dict) else ""
    earlier_exchange = str(earlier_reply_context.get("exchange_label") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    earlier_surface = str(earlier_reply_context.get("surface_token") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    earlier_actor = str(earlier_reply_context.get("responder_actor") or "").strip().lower() if isinstance(earlier_reply_context, dict) else ""

    if current_surface == "room" or not current_actor or not previous_actor or previous_actor == current_actor:
        return ""
    if previous_surface != current_surface:
        return ""

    assertive_exchanges = {"accusation", "status judgment", "exposure"}
    repair_exchanges = {"failed repair", "brittle repair", "containment"}
    across_room = " across the room" if _responder_social_side(previous_actor) != _responder_social_side(current_actor) else ""
    earlier_same_surface = earlier_surface == current_surface and bool(earlier_exchange)

    if previous_exchange == "evasive pressure" and current_exchange in assertive_exchanges | repair_exchanges:
        if earlier_same_surface and earlier_actor and earlier_actor not in {current_actor, previous_actor}:
            return f"letting the same {current_surface} pressure jump speakers{across_room} before the dodge can settle"
        return ""

    if previous_exchange in assertive_exchanges and current_exchange in assertive_exchanges:
        if earlier_same_surface and earlier_actor and earlier_actor not in {current_actor, previous_actor}:
            return f"letting the same {current_surface} pressure jump speakers{across_room} before it can cool"
        return f"picking up the same {current_surface}{across_room} before it can cool"

    if previous_exchange in assertive_exchanges and current_exchange in repair_exchanges:
        return f"taking up the same {current_surface}{across_room} without letting it drop"

    return ""


def _response_micro_weave_hook_now(*, previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str) -> str:
    current_exchange = _response_exchange_label_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    current_surface = _response_surface_token_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    previous_exchange = str(previous_reply_context.get("exchange_label") or "").strip() if isinstance(previous_reply_context, dict) else ""
    previous_surface = str(previous_reply_context.get("surface_token") or "").strip() if isinstance(previous_reply_context, dict) else ""
    earlier_exchange = str(earlier_reply_context.get("exchange_label") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    earlier_surface = str(earlier_reply_context.get("surface_token") or "").strip() if isinstance(earlier_reply_context, dict) else ""

    if current_surface == "room" or current_exchange == "evasive pressure":
        return ""
    if previous_exchange != "evasive pressure":
        return ""
    if not earlier_exchange or earlier_exchange == "evasive pressure":
        return ""
    if previous_surface != current_surface or earlier_surface != current_surface:
        return ""

    if current_exchange in {"accusation", "exposure", "status judgment"}:
        return f"reopening the same {current_surface} through the dodge before the point can die"
    if current_exchange in {"failed repair", "brittle repair", "containment"}:
        return f"forcing the same {current_surface} back into answer before the dodge can stand"
    return f"bringing the same {current_surface} back through the dodge before it can die"


def _response_continuity_hook_now(*, previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str, responder_actor: str | None) -> str:
    relay = _response_pressure_relay_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
        responder_actor=responder_actor,
    )
    micro_weave = _response_micro_weave_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    rhythm = _response_rhythm_pressure_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
        responder_actor=responder_actor,
    )
    interruption = _response_interruption_reentry_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    immediate = _response_countermove_link_now(
        previous_reply_context=previous_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    delayed = _response_delayed_countermove_link_now(
        earlier_reply_context=earlier_reply_context,
        previous_reply_context=previous_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    generic_immediate = {
        "after the last evasive turn left the pressure live",
        "because the last evasive turn left the pressure live",
        "because the room could not get out of the last repair loop",
        "because the last visible answer left the pressure live",
    }
    generic_interruption = {
        "not letting the last dodge settle into a subject shift",
    }
    if relay:
        return relay
    if micro_weave:
        return micro_weave
    if rhythm:
        return rhythm
    if delayed and interruption in generic_interruption:
        return delayed
    if interruption:
        return interruption
    if delayed and (not immediate or immediate in generic_immediate or immediate.startswith("after the last ") or immediate.startswith("because the last ") or immediate.startswith("because the room could not")):
        return delayed
    return immediate

__all__ = (
    '_previous_reply_continuity_context',
    '_earlier_reply_continuity_context',
    '_response_countermove_link_now',
    '_response_delayed_countermove_link_now',
    '_response_interruption_reentry_hook_now',
    '_response_rhythm_pressure_hook_now',
    '_response_pressure_relay_hook_now',
    '_response_micro_weave_hook_now',
    '_response_continuity_hook_now',
)
