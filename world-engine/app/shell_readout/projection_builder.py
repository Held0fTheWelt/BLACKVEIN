"""Public shell readout projection and visible output framing."""

from __future__ import annotations

from .common import *
from .environment_readout import *
from .social_pressure_readout import *
from .response_surface_readout import *
from .response_continuity_readout import *

def _response_line_prefix_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], responder_actor: str | None, selected_scene_function: str, thread_continuity: dict[str, Any], previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any]) -> str:
    actor = responder_actor.title() if responder_actor else "Someone"
    exchange_type = _response_exchange_type_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    voice = _response_voice_phrase_now(social_state=social_state, responder_actor=responder_actor)
    heat = _response_surface_heat_phrase_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        responder_actor=responder_actor,
    )
    signature = _response_performance_signature_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    tail = _response_carryover_tail_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        thread_continuity=thread_continuity,
    )
    countermove = _response_continuity_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
        responder_actor=responder_actor,
    )
    base = f"{actor}, {voice}, answers in {exchange_type}"
    if heat:
        base = f"{base} with {heat}"
    if signature:
        base = f"{base}, in {signature}"
    if countermove:
        base = f"{base}, {countermove}"
    if tail:
        return f"{base}, {tail}"
    return base


def frame_story_runtime_visible_output_bundle(*, visible_output_bundle: dict[str, Any] | None, shell_readout_projection: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(visible_output_bundle, dict):
        return None
    if not isinstance(shell_readout_projection, dict):
        return dict(visible_output_bundle)
    prefix = shell_readout_projection.get("response_line_prefix_now")
    if not isinstance(prefix, str) or not prefix.strip():
        prefix = shell_readout_projection.get("response_address_source_now")
    if not isinstance(prefix, str) or not prefix.strip():
        return dict(visible_output_bundle)

    framed = dict(visible_output_bundle)
    for key in ("gm_narration", "spoken_lines"):
        lines = framed.get(key)
        if isinstance(lines, list) and lines:
            copied = [str(x) for x in lines]
            first = copied[0].strip()
            if first:
                copied[0] = f"{prefix.strip()} — {first}"
            framed[key] = copied
    return framed


def _response_pressure_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any]) -> str:
    values = open_pressures + consequences
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return _readout_text("world_engine.readout.response_pressure.failed_exit")
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return _readout_text("world_engine.readout.response_pressure.exposure")
    if _contains_any(values, "book", "art"):
        return _readout_text("world_engine.readout.response_pressure.judgment")
    if _contains_any(values, "flower", "tulip"):
        return _readout_text("world_engine.readout.response_pressure.hospitality")
    if _contains_any(values, "phone"):
        return _readout_text("world_engine.readout.response_pressure.humiliation")
    if _has_hosting_surface(values):
        return _readout_text("world_engine.readout.response_pressure.hosting")
    if str(social_state.get("scene_pressure_state") or "") == "high_blame":
        return _readout_text("world_engine.readout.response_pressure.answerability")
    return _readout_text("world_engine.readout.response_pressure.default")


def _response_address_source_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], responder_actor: str | None, selected_scene_function: str = "") -> str:
    actor = responder_actor.title() if responder_actor else "Someone"
    voice = _response_voice_phrase_now(social_state=social_state, responder_actor=responder_actor)
    exchange_type = _response_exchange_type_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    heat = _response_surface_heat_phrase_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        responder_actor=responder_actor,
    )
    signature = _response_performance_signature_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    if heat:
        return f"{actor} answers {voice} in {exchange_type}, with {heat}, in {signature}."
    return f"{actor} answers {voice} in {exchange_type}, in {signature}."


def _response_exchange_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str, thread_continuity: dict[str, Any], previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], responder_actor: str | None = None) -> str:
    exchange_type = _response_exchange_type_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    cause = _response_cause_compressed_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    carry = _response_carryover_exchange_phrase_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        thread_continuity=thread_continuity,
    )
    pull = _response_recentering_pull_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    countermove = _response_continuity_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
        responder_actor=responder_actor,
    )
    if carry and countermove:
        return f"Your act drew {_with_indefinite_article(exchange_type)} answer {cause}, {countermove}, {carry}, and let the reply {pull}."
    if carry:
        return f"Your act drew {_with_indefinite_article(exchange_type)} answer {cause}, {carry}, and let the reply {pull}."
    if countermove:
        return f"Your act drew {_with_indefinite_article(exchange_type)} answer {cause}, {countermove}, and let the reply {pull}."
    return f"Your act drew {_with_indefinite_article(exchange_type)} answer {cause}, and let the reply {pull}."


def _who_answers_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], responder_actor: str | None, selected_scene_function: str, social_state: dict[str, Any] | None = None) -> str:
    actor = responder_actor.title() if responder_actor else "Someone"
    side = _responder_social_side(responder_actor)
    line = _response_pressure_line_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state or {})
    mask = _response_mask_slip_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    if line == "spouse-axis embarrassment":
        return f"{actor} is the one answering now; the {side} is speaking through spouse embarrassment, with {mask}."
    if line == "cross-couple strain":
        return f"{actor} is the one answering now; the {side} is speaking through cross-couple strain, with {mask}."
    return f"{actor} is the one answering now; the {side} is speaking through {line}, with {mask}."


def _why_this_reply_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str, previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], responder_actor: str | None = None) -> str:
    values = open_pressures + consequences
    side = _responder_social_side(responder_actor)
    asym = str(social_state.get("responder_asymmetry_code") or "")
    pull = _response_recentering_pull_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    signature = _response_performance_signature_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    countermove = _response_continuity_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
        responder_actor=responder_actor,
    )
    hook = f", {countermove}," if countermove else ""
    variables = {
        "side": side,
        "hook": hook,
        "pull": pull,
        "signature": signature,
    }
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        if asym == "blame_on_host_spouse_axis":
            return _readout_text("world_engine.readout.why_reply.failed_repair_spouse", **variables)
        return _readout_text("world_engine.readout.why_reply.failed_repair", **variables)
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return _readout_text("world_engine.readout.why_reply.exposure", **variables)
    if _contains_any(values, "book", "art"):
        if asym != "alliance_reposition_active":
            return _readout_text("world_engine.readout.why_reply.taste_status_side", **variables)
        return _readout_text("world_engine.readout.why_reply.taste_status_cross", **variables)
    if _contains_any(values, "flower", "tulip"):
        return _readout_text("world_engine.readout.why_reply.hospitality", **variables)
    if _contains_any(values, "phone"):
        return _readout_text("world_engine.readout.why_reply.humiliation", **variables)
    if asym == "alliance_reposition_active":
        return _readout_text("world_engine.readout.why_reply.alliance", **variables)
    if selected_scene_function == "repair_or_stabilize":
        return _readout_text("world_engine.readout.why_reply.repair", **variables)
    if selected_scene_function == "redirect_blame":
        return _readout_text("world_engine.readout.why_reply.redirect_blame", **variables)
    if selected_scene_function == "withhold_or_evade":
        return _readout_text("world_engine.readout.why_reply.withhold", **variables)
    return _readout_text("world_engine.readout.why_reply.default", **variables)


def _observation_foothold_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str, responder_actor: str | None = None) -> str:
    values = open_pressures + consequences
    side = _responder_social_side(responder_actor)
    pull = _response_recentering_pull_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    variables = {"side": side, "pull": pull}
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return _readout_text("world_engine.readout.observation.failed_exit", **variables)
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return _readout_text("world_engine.readout.observation.exposure", **variables)
    if _contains_any(values, "book", "art"):
        return _readout_text("world_engine.readout.observation.judgment", **variables)
    if _contains_any(values, "flower", "tulip"):
        return _readout_text("world_engine.readout.observation.hospitality", **variables)
    if _contains_any(values, "phone"):
        return _readout_text("world_engine.readout.observation.humiliation", **variables)
    if selected_scene_function == "repair_or_stabilize":
        return _readout_text("world_engine.readout.observation.repair", **variables)
    if selected_scene_function == "redirect_blame":
        return _readout_text("world_engine.readout.observation.blame", **variables)
    return _readout_text("world_engine.readout.observation.default", **variables)


def build_story_runtime_shell_readout(*, state: dict[str, Any], last_diagnostic: dict[str, Any] | None) -> dict[str, Any]:
    committed_state = state.get("committed_state") if isinstance(state.get("committed_state"), dict) else {}
    current_scene_id = str(state.get("current_scene_id") or committed_state.get("current_scene_id") or "")
    open_pressures = _open_pressures(committed_state)
    consequences = _last_consequences(committed_state)
    thread_continuity = _thread_continuity(committed_state)
    environment_state = _environment_state(committed_state)
    previous_reply_context = _previous_reply_continuity_context(state=state, committed_state=committed_state)
    earlier_reply_context = _earlier_reply_continuity_context(state=state, committed_state=committed_state)
    social_state = _social_state_record(last_diagnostic)
    responder_actor = _first_responder_actor(last_diagnostic)
    selected_scene_function = _selected_scene_function(last_diagnostic)
    env_live_surface = _environment_live_surface_now(environment_state)
    env_salient_object = _environment_salient_object_now(environment_state)
    env_situational_affordance = _environment_situational_affordance_now(environment_state)

    return {
        "social_weather_now": _social_weather_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "environment_state_now": _environment_projection(environment_state),
        "live_surface_now": env_live_surface or _live_surface_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "carryover_now": _carryover_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, thread_continuity=thread_continuity),
        "social_geometry_now": _social_geometry_now(open_pressures=open_pressures, social_state=social_state, responder_actor=responder_actor, current_scene_id=current_scene_id),
        "situational_freedom_now": _situational_freedom_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "address_pressure_now": _address_pressure_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, responder_actor=responder_actor),
        "social_moment_now": _social_moment_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "response_pressure_now": _response_pressure_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "response_performance_signature_now": _response_performance_signature_now(responder_actor=responder_actor, selected_scene_function=selected_scene_function, current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "response_mask_slip_now": _response_mask_slip_now(responder_actor=responder_actor, selected_scene_function=selected_scene_function, current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "response_recentering_now": _response_recentering_pull_now(responder_actor=responder_actor, selected_scene_function=selected_scene_function, current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "response_address_source_now": _response_address_source_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, responder_actor=responder_actor, selected_scene_function=selected_scene_function),
        "response_exchange_now": _response_exchange_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, selected_scene_function=selected_scene_function, thread_continuity=thread_continuity, previous_reply_context=previous_reply_context, earlier_reply_context=earlier_reply_context, responder_actor=responder_actor),
        "response_exchange_label_now": _response_exchange_label_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, selected_scene_function=selected_scene_function),
        "response_carryover_now": _response_carryover_tail_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, thread_continuity=thread_continuity),
        "response_line_prefix_now": _response_line_prefix_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, responder_actor=responder_actor, selected_scene_function=selected_scene_function, thread_continuity=thread_continuity, previous_reply_context=previous_reply_context, earlier_reply_context=earlier_reply_context),
        "who_answers_now": _who_answers_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, responder_actor=responder_actor, selected_scene_function=selected_scene_function, social_state=social_state),
        "why_this_reply_now": _why_this_reply_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, selected_scene_function=selected_scene_function, previous_reply_context=previous_reply_context, earlier_reply_context=earlier_reply_context, responder_actor=responder_actor),
        "observation_foothold_now": _observation_foothold_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, selected_scene_function=selected_scene_function, responder_actor=responder_actor),
        "room_pressure_now": _room_pressure_now(current_scene_id=current_scene_id, open_pressures=open_pressures, social_state=social_state),
        "zone_sensitivity_now": _zone_sensitivity_now(current_scene_id=current_scene_id, open_pressures=open_pressures, social_state=social_state),
        "salient_object_now": env_salient_object or _salient_object_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "object_sensitivity_now": _object_sensitivity_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "continued_wound_now": _continued_wound_now(open_pressures=open_pressures, social_state=social_state, thread_continuity=thread_continuity),
        "role_pressure_now": _role_pressure_now(social_state=social_state, responder_actor=responder_actor),
        "dominant_social_reading_now": _dominant_social_reading_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "social_axis_now": _social_axis_now(open_pressures=open_pressures, social_state=social_state, responder_actor=responder_actor),
        "host_guest_pressure_now": _host_guest_pressure_now(open_pressures=open_pressures, social_state=social_state, responder_actor=responder_actor),
        "spouse_axis_now": _spouse_axis_now(current_scene_id=current_scene_id, open_pressures=open_pressures, social_state=social_state),
        "cross_couple_now": _cross_couple_now(open_pressures=open_pressures, social_state=social_state),
        "pressure_redistribution_now": _pressure_redistribution_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "callback_pressure_now": _callback_summary(open_pressures=open_pressures, social_state=social_state, thread_continuity=thread_continuity),
        "callback_role_frame_now": _callback_role_frame_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, thread_continuity=thread_continuity),
        "active_pressure_now": _active_pressure_summary(open_pressures),
        "recent_act_social_meaning": _recent_act_social_meaning(open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "object_social_reading_now": _object_social_reading_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "situational_affordance_now": env_situational_affordance or _situational_affordance_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "reaction_delta_now": _reaction_delta_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "carryover_delta_now": _carryover_delta_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, thread_continuity=thread_continuity),
        "pressure_shift_delta_now": _pressure_shift_delta_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "hot_surface_delta_now": _hot_surface_delta_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
    }

__all__ = (
    '_response_line_prefix_now',
    'frame_story_runtime_visible_output_bundle',
    '_response_pressure_now',
    '_response_address_source_now',
    '_response_exchange_now',
    '_who_answers_now',
    '_why_this_reply_now',
    '_observation_foothold_now',
    'build_story_runtime_shell_readout',
)
